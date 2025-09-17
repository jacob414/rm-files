from __future__ import annotations

# ruff: noqa: I001

import json
from pathlib import Path

from rmscene import scene_items as si
from rmscene.scene_stream import (
    read_blocks,
    RootTextBlock,
    SceneGlyphItemBlock,
    SceneLineItemBlock,
)


def test_turtle_square_and_text_and_highlight(tmp_path: Path) -> None:
    from rmfiles import RemarkableNotebook

    out = tmp_path / "turtle.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=si.Pen.MARKER_1, color=si.PenColor.BLACK, width=3)
    nb.move_to(10, 10).pen_down()
    for _ in range(4):
        nb.forward(20).rotate(90)
    nb.stroke()
    nb.text(5, 5, "Hello", width=200, style=si.ParagraphStyle.HEADING)
    nb.highlight("Hi", [(10.0, 10.0, 5.0, 2.0)], color=si.PenColor.YELLOW)
    nb.write(out)

    assert out.exists() and out.stat().st_size > 0

    # Inspect blocks for presence of line, root text, and glyph
    has_line = has_text = has_glyph = False
    with out.open("rb") as f:
        for b in read_blocks(f):  # type: ignore
            if isinstance(b, SceneLineItemBlock):
                has_line = True
            elif isinstance(b, RootTextBlock):
                has_text = True
            elif isinstance(b, SceneGlyphItemBlock):
                has_glyph = True

    assert has_line and has_text and has_glyph


def test_scene_to_json_emits_group_structure() -> None:
    from rmfiles import scene_to_json
    from rmscene.scene_stream import read_tree

    fixture = Path("fixtures/extracted_rm_file.rm")
    assert fixture.exists(), "Expected extracted RM fixture to exist"

    with fixture.open("rb") as handle:
        tree = read_tree(handle)

    payload = scene_to_json(tree, indent=2)
    data = json.loads(payload)

    assert data["type"] == "SceneTree"
    root = data["root"]
    assert root["type"] == "Group"
    assert root["children"], "Expected root to have child sequence items"


def test_remarkable_notebook_from_file_loads_layers() -> None:
    from rmfiles import RemarkableNotebook

    sample = Path("fixtures/extracted_rm_file.rm")
    nb = RemarkableNotebook.from_file(sample)

    blocks = nb.compile()
    assert any(isinstance(b, SceneLineItemBlock) for b in blocks)
