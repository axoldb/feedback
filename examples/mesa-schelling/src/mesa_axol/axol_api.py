"""Small example-only AxolDB HTTP/JSON v1 adapter.

This is not the official AxolDB Python SDK. It implements only the public operations
needed by this example and reads the bearer credential from a protected file.
"""

from __future__ import annotations

import json
import hashlib
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


class AxolApiError(RuntimeError):
    def __init__(self, status: int | None, code: str | None) -> None:
        super().__init__(f"AxolDB request failed (HTTP {status}, code {code or 'unavailable'})")
        self.status = status
        self.code = code


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _resource(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def _uvarint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        group = value & 0x7F
        value >>= 7
        encoded.append(group | (0x80 if value else 0))
        if not value:
            return bytes(encoded)


def _genotype_hash(schema_id: str, schema_hash: str, payload: bytes) -> str:
    ace1 = b"ACE1\x00\x14" + _uvarint(len(payload)) + payload
    schema = schema_id.encode("utf-8")
    preimage = (b"AXOL-GENOTYPE\x00\x00\x01" + _uvarint(len(schema)) + schema
                + bytes.fromhex(schema_hash) + _uvarint(len(ace1)) + ace1)
    return hashlib.sha256(preimage).hexdigest()


class AxolClient:
    def __init__(self, endpoint: str, ca_file: Path, credential_file: Path) -> None:
        if not endpoint.startswith("https://") or endpoint.rstrip("/").count("/") != 2:
            raise ValueError("AXOLDB_ENDPOINT must be an https:// origin without a path")
        if credential_file.stat().st_mode & 0o077:
            raise ValueError("credential file must not be accessible by group or others")
        token = credential_file.read_text(encoding="utf-8").strip()
        if not token or any(ord(ch) < 0x21 or ord(ch) > 0x7E for ch in token):
            raise ValueError("credential file must contain one printable bearer credential")
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.context.load_verify_locations(cafile=str(ca_file))
        self.context.check_hostname = True
        self.context.verify_mode = ssl.CERT_REQUIRED

    @classmethod
    def from_environment(cls) -> AxolClient:
        required = ("AXOLDB_ENDPOINT", "AXOLDB_CA_FILE", "AXOLDB_CREDENTIAL_FILE")
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise ValueError("missing environment settings: " + ", ".join(missing))
        return cls(os.environ[required[0]], Path(os.environ[required[1]]), Path(os.environ[required[2]]))

    def request(self, method: str, path: str, body: Any | None = None) -> Any:
        data = None if body is None else canonical_bytes(body)
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.endpoint + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, context=self.context, timeout=120) as response:
                payload = response.read()
                return None if not payload else json.loads(payload)
        except urllib.error.HTTPError as error:
            code = None
            try:
                code = json.loads(error.read()).get("code")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            raise AxolApiError(error.code, code) from None
        except urllib.error.URLError as error:
            raise AxolApiError(None, None) from error

    def version(self) -> str:
        return str(self.request("GET", "/v1/version"))

    def insert_json(self, population_id: str, schema_id: str, schema_hash: str, value: Any) -> str:
        payload = canonical_bytes(value)
        genotype_hash = _genotype_hash(schema_id, schema_hash, payload)
        self.request("POST", f"/v1/populations/{_resource(population_id)}/genotypes", {
            "targetPopulationId": population_id,
            "genotype": {"schemaId": schema_id, "schemaHashHex": schema_hash,
                         "value": {"$kind": "binary", "hex": payload.hex()},
                         "genotypeHashHex": genotype_hash},
        })
        return genotype_hash

    @staticmethod
    def _members(hashes: list[str]) -> list[dict[str, str]]:
        return [{"genotypeHashHex": digest, "multiplicity": str(count)}
                for digest, count in sorted(Counter(hashes).items())]

    def create_population(self, population_id: str, contract_id: str,
                          contract_hash: str, hashes: list[str]) -> str:
        result = self.request("POST", "/v1/populations", {
            "populationId": population_id,
            "contract": {"contractId": contract_id, "contractHashHex": contract_hash},
            "initialGeneration": {"members": self._members(hashes)},
        })
        return str(result["generationId"])

    def publish(self, population_id: str, parent_generation_id: str,
                hashes: list[str], key: str) -> str:
        result = self.request("POST", f"/v1/populations/{_resource(population_id)}/generations", {
            "operations": [{"populationId": population_id,
                            "expectedParentGenerationId": parent_generation_id,
                            "content": {"members": self._members(hashes)}}],
            "isolationLevel": "serializable", "durabilityLevel": "synchronous",
            "idempotency": {"scope": "population", "scopeIdentity": population_id, "key": key},
        })
        if result["outcome"] != "committed":
            raise RuntimeError(f"transaction outcome was {result['outcome']}")
        return str(result["resultGenerations"][population_id])

    def population(self, population_id: str) -> dict[str, Any] | None:
        return self.request("GET", f"/v1/populations/{_resource(population_id)}")

    def generation(self, population_id: str, generation_id: str) -> dict[str, Any] | None:
        return self.request("GET", f"/v1/populations/{_resource(population_id)}/generations/{_resource(generation_id)}")

    def read_json(self, population_id: str, generation_id: str, digest: str) -> Any:
        result = self.request("GET", f"/v1/populations/{_resource(population_id)}/generations/"
                              f"{_resource(generation_id)}/genotypes/{_resource(digest)}")
        if result is None:
            raise RuntimeError("checkpoint member is absent from the requested generation")
        value = result["value"]
        if value.get("$kind") != "binary":
            raise RuntimeError("checkpoint member is not an ACE-1 binary value")
        return json.loads(bytes.fromhex(value["hex"]).decode("utf-8"))
