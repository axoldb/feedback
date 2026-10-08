import os
from pathlib import Path

import pytest

from mesa_axol.demo import run


@pytest.mark.skipif(os.environ.get("AXOLDB_E2E") != "1", reason="set AXOLDB_E2E=1 for real AxolDB")
def test_real_checkpoint_restore(tmp_path: Path) -> None:
    result = run(tmp_path)
    assert result["checks"]["uninterrupted_equals_restored"] is True
    assert result["checks"]["same_branch_start"] is True
