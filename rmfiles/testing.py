"""Testing helpers and standard sample settings.

Exports constants for consistent sample generation and regression fixtures,
and houses regression tests reusable from the public ``rmfiles`` package.
"""

from __future__ import annotations

from pathlib import Path

from rmscene import scene_items as si
from rmscene.scene_stream import SceneLineItemBlock, read_blocks

from .remarkable import RemarkableNotebook

# Standardized sample settings
SAMPLE_LINE_WIDTH: int = 24
SAMPLE_TOOL: si.Pen = si.Pen.FINELINER_1


def canonical_lines(path: Path) -> list[tuple[int, int, list[tuple[float, float]]]]:
    """Return a canonicalized representation of lines in an .rm file.

    Produces a list of tuples: (tool_id, color_id, [(x,y), ...]) with points
    rounded to 4 decimals to avoid floating noise. Ignores header/meta blocks.
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


# --- Regression tests (imported by tests) ---


def test_regression_regular_polygon(tmp_path: Path) -> None:  # pragma: no cover
    fixture = Path("fixtures/polygon_fixture.rm")
    assert fixture.exists(), "Expected polygon fixture to exist"

    out = tmp_path / "poly.regression.rm"

    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.regular_polygon(6, cx=150, cy=120, r=60)
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)


def test_regression_rounded_rect(tmp_path: Path) -> None:  # pragma: no cover
    fixture = Path("fixtures/rounded_rect_fixture.rm")
    assert fixture.exists(), "Expected rounded rect fixture to exist"

    out = tmp_path / "rounded.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.rounded_rect(60, 320, 180, 110, radius=18, segments=6)
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)


def test_regression_star(tmp_path: Path) -> None:  # pragma: no cover
    fixture = Path("fixtures/star_fixture.rm")
    assert fixture.exists(), "Expected star fixture to exist"

    out = tmp_path / "star.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.star(cx=330, cy=120, r=60, points=5, inner_ratio=0.45)
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)


def test_regression_ellipse(tmp_path: Path) -> None:  # pragma: no cover
    fixture = Path("fixtures/ellipse_fixture.rm")
    assert fixture.exists(), "Expected ellipse fixture to exist"

    out = tmp_path / "ellipse.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.ellipse(cx=150, cy=260, rx=80, ry=40, rotation=20)
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)


def test_regression_arc(tmp_path: Path) -> None:  # pragma: no cover
    fixture = Path("fixtures/arc_fixture.rm")
    assert fixture.exists(), "Expected arc fixture to exist"

    out = tmp_path / "arc.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.arc(cx=330, cy=260, r=70, start=45, sweep=220)
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)
