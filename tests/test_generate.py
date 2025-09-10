from __future__ import annotations

from pathlib import Path

from rmfiles.generate import build_rectangle_blocks, create_rectangle_rm, write_rm


def test_build_rectangle_blocks_and_write(tmp_path: Path):
    blocks, author_uuid = build_rectangle_blocks(x=120, y=140, width=160, height=100)
    assert blocks, "Expected some blocks"

    out = tmp_path / "rect.rm"
    write_rm(str(out), blocks, version="3.1")
    assert out.exists() and out.stat().st_size > 0

    # Verify header
    head = out.read_bytes()[:64]
    assert b"reMarkable .lines file" in head


def test_create_rectangle_rm(tmp_path: Path):
    out = tmp_path / "rect2.rm"
    create_rectangle_rm(str(out), x=100, y=100, width=200, height=150)
    assert out.exists()
    head = out.read_bytes()[:64]
    assert b"reMarkable .lines file" in head
