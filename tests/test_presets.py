from __future__ import annotations

from pathlib import Path

from rmscene import scene_items as si
from rmscene.scene_stream import SceneLineItemBlock, read_blocks

from rmfiles import RemarkableNotebook


def _first_line_block(path: Path) -> SceneLineItemBlock | None:
    with path.open("rb") as f:
        for b in read_blocks(f):  # type: ignore
            if isinstance(b, SceneLineItemBlock):
                return b  # type: ignore[return-value]
    return None


def test_use_preset_highlighter_affects_color_and_tool(tmp_path: Path) -> None:
    out = tmp_path / "hl.rm"
    nb = RemarkableNotebook(deg=True)
    with nb.preset_scope("highlighter"):
        nb.layer("L").circle(100, 100, 40)
    nb.write(out)
    block = _first_line_block(out)
    assert block is not None
    line = block.item.value  # type: ignore[assignment]
    assert line.tool == si.Pen.HIGHLIGHTER_1
    assert line.color == si.PenColor.YELLOW


def test_define_and_use_custom_preset_affects_point_width(tmp_path: Path) -> None:
    out = tmp_path / "bold.rm"
    nb = RemarkableNotebook(deg=True)
    nb.define_preset("bold", pen=si.Pen.MARKER_1, width=8)
    with nb.preset_scope("bold"):
        nb.layer("L").line(0, 0, 50, 0)
    nb.write(out)
    block = _first_line_block(out)
    assert block is not None
    points = block.item.value.points  # type: ignore[assignment]
    assert points[0].width == 8
