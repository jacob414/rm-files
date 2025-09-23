from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from rmscene import scene_items as si
from shapely.geometry import JOIN_STYLE, LineString, Polygon
from shapely.ops import unary_union

from rmfiles import RemarkableNotebook, scene_to_svg
from rmfiles.testing import SAMPLE_LINE_WIDTH, SAMPLE_TOOL

POINTS = [
    (80, 320),
    (200, 300),
    (240, 360),
    (200, 420),
    (80, 400),
]


def _svg_paths_to_union(svg_path: Path) -> Polygon:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = "{http://www.w3.org/2000/svg}"
    geoms = []
    paths = root.findall(f".//{ns}path")
    if len(paths) > len(POINTS):
        paths = paths[: -len(POINTS)]
        for path in paths:
            d = path.attrib.get("d", "")
            stroke_width = float(path.attrib.get("stroke-width", "1"))
            coords = _parse_coords(d)
            if len(coords) >= 2:
                line = LineString(coords)
                geoms.append(
                    line.buffer(stroke_width / 2.0, join_style=JOIN_STYLE.mitre)
                )
    if not geoms:
        return Polygon()
    return unary_union(geoms)


def _parse_coords(path_d: str) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    tokens = path_d.replace("M", " ").replace("L", " ").split()
    for token in tokens:
        if "," not in token:
            continue
        xs, ys = token.split(",", 1)
        try:
            coords.append((float(xs), float(ys)))
        except ValueError:
            continue
    return coords


def _shape_difference(
    actual, expected: Polygon, *, stroke_width: float
) -> tuple[float, float]:
    interior = expected.buffer(-stroke_width / 2.0, join_style=JOIN_STYLE.mitre)
    if interior.is_empty:
        interior = expected
    cap = expected.buffer(stroke_width / 2.0, join_style=JOIN_STYLE.mitre)
    clipped_actual = actual.intersection(cap)
    expected_area = max(interior.area, 1.0)
    missing = interior.difference(clipped_actual).area / expected_area
    excess = clipped_actual.difference(interior).area / expected_area
    return missing, excess
    missing = expected.difference(actual).area / expected_area
    excess = actual.difference(expected).area / expected_area
    return missing, excess


def _generate_svg(tmp_path, *, cross_hatch: bool) -> Path:
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.filled_polygon(
        POINTS,
        spacing_factor=0.2,
        cross_hatch=cross_hatch,
        edge_outline=True,
    )
    svg_path = tmp_path / (
        "filled_polygon_cross.svg" if cross_hatch else "filled_polygon.svg"
    )
    scene_to_svg(nb, svg_path, include_hidden_layers=True)
    return svg_path


def test_filled_polygon_matches_expected_shape(tmp_path):
    svg_path = _generate_svg(tmp_path, cross_hatch=False)
    actual = _svg_paths_to_union(svg_path)
    expected = Polygon(POINTS)
    missing, excess = _shape_difference(
        actual, expected, stroke_width=SAMPLE_LINE_WIDTH
    )
    assert missing < 0.25
    assert excess < 0.1


def test_filled_polygon_cross_hatch_matches_expected_shape(tmp_path):
    svg_path = _generate_svg(tmp_path, cross_hatch=True)
    actual = _svg_paths_to_union(svg_path)
    expected = Polygon(POINTS)
    missing, excess = _shape_difference(
        actual, expected, stroke_width=SAMPLE_LINE_WIDTH
    )
    assert missing < 0.1
    assert excess < 0.5
