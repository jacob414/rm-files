from __future__ import annotations

from pathlib import Path

from rmfiles.cli import _cmd_inspect


class DummyArgs:
    def __init__(self, path: str | Path, verbose: bool = False):
        self.path = str(path)
        self.verbose = verbose


def test_cli_inspect_rmdoc_no_error_and_lists_layers(capsys):
    sample = Path("sample-files/Sample.rmdoc")
    assert sample.exists()

    rc = _cmd_inspect(DummyArgs(sample))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Pages:" in out
    assert "Page 1:" in out

