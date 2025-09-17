from __future__ import annotations

import xml.etree.ElementTree as ET

from rmscene import scene_items as si

from rmfiles import RemarkableNotebook, scene_to_svg


def _ns(tag: str) -> str:
    return f"{{http://www.w3.org/2000/svg}}{tag}"


def test_scene_to_svg_writes_paths_and_highlights(tmp_path):
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=si.Pen.MARKER_1, color=si.PenColor.BLUE)
    nb.move_to(10, 10).pen_down().line_to(40, 40)
    nb.stroke()
    nb.highlight("hi", [(12, 12, 10, 6)], color=si.PenColor.YELLOW)

    out = tmp_path / "export.svg"
    scene_to_svg(nb, out, background="#ffffff")

    tree = ET.parse(out)
    root = tree.getroot()

    groups = root.findall(_ns("g"))
    assert groups, "expected at least one layer group"
    first_group = groups[0]
    title = first_group.find(_ns("title"))
    assert title is not None and title.text == "Sketch"

    paths = first_group.findall(_ns("path"))
    assert paths and paths[0].attrib.get("stroke") == "#1976d2"

    rects = first_group.findall(_ns("rect"))
    assert rects and float(rects[0].attrib.get("opacity", "0")) > 0


def test_scene_to_svg_can_include_hidden_layers(tmp_path):
    from rmfiles.notebook import create

    nb = create()
    visible = nb.create_layer("Visible", visible=True)
    hidden = nb.create_layer("Hidden", visible=False)
    nb.add_line_to_layer(
        visible,
        [
            si.Point(x=0, y=0, speed=0, direction=0, width=2, pressure=100),
            si.Point(x=10, y=10, speed=0, direction=0, width=2, pressure=100),
        ],
    )
    nb.add_line_to_layer(
        hidden,
        [
            si.Point(x=5, y=5, speed=0, direction=0, width=2, pressure=100),
            si.Point(x=15, y=15, speed=0, direction=0, width=2, pressure=100),
        ],
    )

    out = tmp_path / "hidden.svg"
    scene_to_svg(nb.to_blocks(), out, include_hidden_layers=True)

    tree = ET.parse(out)
    root = tree.getroot()
    hidden_groups = [
        g for g in root.findall(_ns("g")) if g.attrib.get("style", "") == "display:none"
    ]
    assert hidden_groups, "expected hidden layer group when requested"
