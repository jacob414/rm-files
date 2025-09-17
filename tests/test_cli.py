from __future__ import annotations

import sys
from pathlib import Path

from rmfiles.cli import _cmd_inspect


class DummyArgs:
    def __init__(self, path: str | Path, verbose: bool = False):
        self.path = str(path)
        self.verbose = verbose


def test_cli_inspect_rmdoc_no_error_and_lists_layers_and_metadata(capsys):
    sample = Path("sample-files/Sample.rmdoc")
    assert sample.exists()

    rc = _cmd_inspect(DummyArgs(sample))
    assert rc == 0
    out = capsys.readouterr().out
    assert "-- ReMarkable .rmdoc file --" in out
    assert "Name: Sample" in out
    assert "Created time:" in out
    assert "Last modified:" in out
    assert "Size:" in out and "KiB" in out
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


def test_cli_inspect_rm_without_humanize(monkeypatch, tmp_path, capsys):
    sample = tmp_path / "sample.rm"
    sample.write_bytes(b"\x00" * 2048)

    # Force the CLI to take the fallback path by simulating a missing naturalsize.
    class _Stub:
        pass

    monkeypatch.setitem(sys.modules, "humanize", _Stub())
    monkeypatch.setattr("rmfiles.cli._inspect_with_rmscene", lambda _path: None)

    rc = _cmd_inspect(DummyArgs(sample))
    assert rc == 0
    out = capsys.readouterr().out
    assert "Size: 2.0 KiB" in out
