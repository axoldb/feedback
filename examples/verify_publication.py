#!/usr/bin/env python3
"""Verify the recovered, immutable example payloads from a Git checkout.

Standard library only; no server, credential or network access. Run from any cwd:
python examples/verify_publication.py --output /outside/repo/audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ACCEPTED = "c36eb378f53355a004edbdaad787499ea0f7294e"
EXAMPLES = ("deap-knapsack", "mesa-schelling", "native-integer-evolution",
            "native-binary-crossover", "quanteda-social-protection")
ROOT = Path(__file__).resolve().parents[1]


def git(*arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *arguments])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report: dict = {"acceptedSourceCommit": ACCEPTED, "archives": [],
                    "sourcePayloads": [], "readmeOverlays": [],
                    "freshDatabaseQualification": False}
    forbidden = {".exe", ".dll", ".pdb", ".key", ".pem", ".pfx", ".token"}
    for name in EXAMPLES:
        archive_path = ROOT / "examples/downloads" / f"axoldb-{name}-1.0.0.zip"
        archive_data = archive_path.read_bytes()
        expected = archive_path.with_suffix(".zip.sha256").read_text().split()[0]
        assert sha(archive_data) == expected, f"Archive checksum mismatch: {name}"
        count = 0
        seen: set[str] = set()
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.testzip() is None, f"Corrupt archive: {name}"
            for entry in archive.infolist():
                path = PurePosixPath(entry.filename)
                assert not path.is_absolute() and ".." not in path.parts
                assert "\\" not in entry.filename and ":" not in entry.filename
                assert path.parts[0] == name, f"Unexpected archive root: {name}"
                assert ((entry.external_attr >> 16) & 0o170000) != 0o120000
                assert entry.filename not in seen, f"Duplicate archive member: {name}"
                seen.add(entry.filename)
                if entry.is_dir():
                    continue
                assert path.suffix.lower() not in forbidden, f"Forbidden artifact: {path}"
                payload = archive.read(entry)
                original = git("show", f"{ACCEPTED}:examples/{path.as_posix()}")
                assert payload == original, f"Archive differs from accepted source: {path}"
                count += 1
        report["archives"].append({"example": name, "file": archive_path.name,
                                    "bytes": len(archive_data), "sha256": expected,
                                    "acceptedFilesMatched": count})
        paths = git("ls-tree", "-r", "--name-only", ACCEPTED, "--",
                    f"examples/{name}").decode().splitlines()
        for path in paths:
            original_blob = git("rev-parse", f"{ACCEPTED}:{path}").decode().strip()
            # Let Git normalize the checkout's line endings before comparing blobs.
            current_blob = git("hash-object", f"--path={path}", path).decode().strip()
            original = git("show", f"{ACCEPTED}:{path}")
            row = {"path": path, "acceptedGitBlob": original_blob,
                   "acceptedSha256": sha(original)}
            if current_blob != original_blob:
                assert path == f"examples/{name}/README.md", f"Accepted payload changed: {path}"
                assert "PUBLICATION-STATUS.md" in (ROOT / path).read_text(encoding="utf-8")
                report["readmeOverlays"].append(row)
            else:
                report["sourcePayloads"].append(row)
        assert (ROOT / f"examples/{name}/LICENSE").is_file()
        assert (ROOT / f"examples/{name}/THIRD-PARTY-NOTICES.md").is_file()
    findings = []
    text_suffixes = {".py", ".r", ".md", ".json", ".toml", ".lock", ".html"}
    paths = git("ls-tree", "-r", "--name-only", ACCEPTED, "--", "examples").decode().splitlines()
    for path in paths:
        if Path(path).suffix.lower() not in text_suffixes:
            continue
        text = (ROOT / path).read_text(encoding="utf-8")
        if re.search(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE" + r" KEY-----", text):
            findings.append({"path": path, "kind": "private key"})
        if re.search(r"(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}", text):
            findings.append({"path": path, "kind": "credential pattern"})
        if re.search(r"(?:/home/[^/\s]+/|[A-Za-z]:\\Users\\)", text):
            findings.append({"path": path, "kind": "private user path"})
    assert not findings, f"Public-data review required: {findings}"
    report.update(status="PASS", sensitivePatternFindings=findings,
                  notes="Only README publication overlays may differ. Algorithms, fixtures, locks, licenses, results and all five original ZIPs are preserved. This check does not execute database campaigns.")
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(json.dumps({"status": "PASS", "archives": len(report["archives"]),
                      "unchangedPayloadFiles": len(report["sourcePayloads"]),
                      "readmeOverlays": len(report["readmeOverlays"]),
                      "sensitivePatternFindings": len(findings)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
