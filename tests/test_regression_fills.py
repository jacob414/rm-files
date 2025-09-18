from __future__ import annotations

from pathlib import Path

from rmfiles import RemarkableNotebook
from rmfiles.testing import SAMPLE_LINE_WIDTH, SAMPLE_TOOL, canonical_lines


def test_regression_filled_ellipse(tmp_path: Path) -> None:
    fixture = Path("fixtures/filled_ellipse_fixture.rm")
    assert fixture.exists(), "Expected filled ellipse fixture to exist"

    out = tmp_path / "filled_ellipse.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=SAMPLE_TOOL, width=SAMPLE_LINE_WIDTH)
    nb.filled_ellipse(cx=150, cy=260, rx=80, ry=40, rotation=20)
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)


def test_regression_filled_rect(tmp_path: Path) -> None:
    fixture = Path("fixtures/filled_rect_fixture.rm")
    assert fixture.exists(), "Expected filled rect fixture to exist"

    out = tmp_path / "filled_rect.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=SAMPLE_TOOL, width=SAMPLE_LINE_WIDTH)
    nb.filled_rect(60, 320, 180, 110)
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)


def test_regression_filled_rect_roundtrip(tmp_path: Path) -> None:
    fixture = Path("fixtures/filled_rect_edges_device.rm")
    assert fixture.exists(), "Expected filled rect device fixture to exist"

    nb = RemarkableNotebook.from_file(fixture)
    out = tmp_path / "filled_rect.roundtrip.rm"
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)


def test_regression_filled_polygon(tmp_path: Path) -> None:
    fixture = Path("fixtures/filled_polygon_fixture.rm")
    assert fixture.exists(), "Expected filled polygon fixture to exist"

    out = tmp_path / "filled_polygon.regression.rm"
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=SAMPLE_TOOL, width=SAMPLE_LINE_WIDTH)
    nb.filled_polygon(
        [
            (80, 320),
            (200, 300),
            (240, 360),
            (200, 420),
            (80, 400),
        ]
    )
    nb.write(out)

    assert canonical_lines(out) == canonical_lines(fixture)
