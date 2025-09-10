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


def test_cli_inspect_rm_humanized_and_no_header(capsys):
    rm = Path("sample-files/triangel.rm")
    assert rm.exists()

    rc = _cmd_inspect(DummyArgs(rm))
    assert rc == 0
    out = capsys.readouterr().out
    assert "-- ReMarkable .rm file --" in out
    assert "Version: .lines file version" in out
    assert "Blocks:" in out
    # Old header lines should not be present for .rm
    assert "Header (ascii):" not in out
    assert "Header (hex):" not in out
