from __future__ import annotations

from pathlib import Path

from rmscene.scene_stream import SceneLineItemBlock, read_blocks

from rmfiles import RemarkableNotebook


def _canonical_lines(path: Path) -> list[tuple[int, int, list[tuple[float, float]]]]:
    """Return a canonicalized representation of lines in an .rm file.

    Produces a list of tuples: (tool_id, color_id, [(x,y), ...])
    Points are rounded to 4 decimals to avoid floating noise.
    Ignores header/meta and CRDT/link details.
    """

    def _round_pt(x: float, y: float) -> tuple[float, float]:
        return (round(x, 4), round(y, 4))

    lines: list[tuple[int, int, list[tuple[float, float]]]] = []
    with path.open("rb") as f:
        for b in read_blocks(f):  # type: ignore
            if isinstance(b, SceneLineItemBlock):
                line = b.item.value  # type: ignore[assignment]
                pts = [_round_pt(p.x, p.y) for p in line.points]
                lines.append((int(line.tool), int(line.color), pts))
    return lines


def test_regression_regular_polygon(tmp_path: Path) -> None:
    fixture = Path("fixtures/polygon_fixture.rm")
    assert fixture.exists(), "Expected polygon fixture to exist"

    out = tmp_path / "poly.regression.rm"
    from rmscene import scene_items as si

    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=si.Pen.MARKER_1, color=si.PenColor.BLACK, width=12)
    nb.regular_polygon(6, cx=150, cy=120, r=60)
    nb.write(out)

    lines_new = _canonical_lines(out)
    lines_fixture = _canonical_lines(fixture)

    assert lines_new == lines_fixture


def test_regression_rounded_rect(tmp_path: Path) -> None:
    fixture = Path("fixtures/rounded_rect_fixture.rm")
    assert fixture.exists(), "Expected rounded rect fixture to exist"

    out = tmp_path / "rounded.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").rounded_rect(60, 320, 180, 110, radius=18, segments=6)
    nb.write(out)

    lines_new = _canonical_lines(out)
    lines_fixture = _canonical_lines(fixture)

    assert lines_new == lines_fixture


def test_regression_star(tmp_path: Path) -> None:
    fixture = Path("fixtures/star_fixture.rm")
    assert fixture.exists(), "Expected star fixture to exist"

    out = tmp_path / "star.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").star(cx=330, cy=120, r=60, points=5, inner_ratio=0.45)
    nb.write(out)

    lines_new = _canonical_lines(out)
    lines_fixture = _canonical_lines(fixture)

    assert lines_new == lines_fixture


def test_regression_ellipse(tmp_path: Path) -> None:
    fixture = Path("fixtures/ellipse_fixture.rm")
    assert fixture.exists(), "Expected ellipse fixture to exist"

    out = tmp_path / "ellipse.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").ellipse(cx=150, cy=260, rx=80, ry=40, rotation=20)
    nb.write(out)

    lines_new = _canonical_lines(out)
    lines_fixture = _canonical_lines(fixture)

    assert lines_new == lines_fixture


def test_regression_arc(tmp_path: Path) -> None:
    fixture = Path("fixtures/arc_fixture.rm")
    assert fixture.exists(), "Expected arc fixture to exist"

    out = tmp_path / "arc.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").arc(cx=330, cy=260, r=70, start=45, sweep=220)
    nb.write(out)

    lines_new = _canonical_lines(out)
    lines_fixture = _canonical_lines(fixture)

    assert lines_new == lines_fixture
