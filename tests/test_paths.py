from __future__ import annotations

from pathlib import Path

from rmscene.scene_stream import SceneLineItemBlock, read_blocks

from rmfiles import RemarkableNotebook


def test_quad_to_close_and_stroke(tmp_path: Path) -> None:
    out = tmp_path / "quad.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("L")
    nb.move_to(10, 10)
    nb.begin_path().quad_to(60, 10, 60, 60, samples=12).close_path().stroke()
    nb.write(out)
    assert out.exists() and out.stat().st_size > 0
    with out.open("rb") as f:
        assert any(isinstance(b, SceneLineItemBlock) for b in read_blocks(f))  # type: ignore


def test_cubic_to_stroke(tmp_path: Path) -> None:
    out = tmp_path / "cubic.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("L")
    nb.move_to(20, 20)
    nb.begin_path().cubic_to(40, 0, 80, 40, 100, 20, samples=20).stroke()
    nb.write(out)
    assert out.exists() and out.stat().st_size > 0
    with out.open("rb") as f:
        assert any(isinstance(b, SceneLineItemBlock) for b in read_blocks(f))  # type: ignore
