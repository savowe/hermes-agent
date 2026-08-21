"""Regression tests for safe handling of divergent update histories."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from hermes_cli.update_cmd import _abort_diverged_update


def test_diverged_update_aborts_without_reset(capsys, tmp_path: Path):
    result = SimpleNamespace(
        stderr="fatal: Not possible to fast-forward, aborting.\n",
    )

    with pytest.raises(SystemExit) as exc_info:
        _abort_diverged_update("main", tmp_path, result)

    assert exc_info.value.code == 1
    output = capsys.readouterr().out
    assert "history diverged" in output
    assert "No local commits were changed or deleted" in output
    assert f"git -C {tmp_path} fetch origin" in output
    assert f"git -C {tmp_path} merge origin/main" in output
    assert "reset --hard" not in output
