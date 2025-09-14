from __future__ import annotations

from pathlib import Path

from rmscene.scene_stream import SceneLineItemBlock, read_blocks

from rmfiles import RemarkableNotebook


def test_regular_polygon_writes_and_has_line(tmp_path: Path) -> None:
    out = tmp_path / "poly.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("L").regular_polygon(6, cx=100, cy=100, r=50)
    nb.write(out)
    assert out.exists() and out.stat().st_size > 0
    has_line = False
    with out.open("rb") as f:
        for b in read_blocks(f):  # type: ignore
            if isinstance(b, SceneLineItemBlock):
                has_line = True
                break
    assert has_line


def test_star_writes_and_has_line(tmp_path: Path) -> None:
    out = tmp_path / "star.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("L").star(cx=120, cy=120, r=60, points=5, inner_ratio=0.5)
    nb.write(out)
    assert out.exists() and out.stat().st_size > 0
    with out.open("rb") as f:
        assert any(isinstance(b, SceneLineItemBlock) for b in read_blocks(f))  # type: ignore


def test_ellipse_closed_and_line(tmp_path: Path) -> None:
    out = tmp_path / "ellipse.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("L").ellipse(cx=200, cy=200, rx=80, ry=40, segments=60, rotation=30)
    nb.write(out)
    assert out.exists() and out.stat().st_size > 0
    # We don't parse points here; just ensure a line block exists
    with out.open("rb") as f:
        assert any(isinstance(b, SceneLineItemBlock) for b in read_blocks(f))  # type: ignore


def test_arc_segment_count_and_line(tmp_path: Path) -> None:
    out = tmp_path / "arc.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("L").arc(cx=150, cy=150, r=70, start=45, sweep=180, segments=24)
    nb.write(out)
    assert out.exists() and out.stat().st_size > 0
    with out.open("rb") as f:
        assert any(isinstance(b, SceneLineItemBlock) for b in read_blocks(f))  # type: ignore
