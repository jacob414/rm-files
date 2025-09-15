from __future__ import annotations

from pathlib import Path

from rmfiles import RemarkableNotebook
from rmfiles.testing import SAMPLE_LINE_WIDTH, SAMPLE_TOOL, canonical_lines


def test_regression_path_beziers(tmp_path: Path) -> None:
    """Recreate a mixed quadratic+cubic path and compare to golden fixture."""
    fixture = Path("fixtures/path_fixture.rm")
    assert fixture.exists(), "Expected path fixture to exist"

    out = tmp_path / "path.regression.rm"

    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=SAMPLE_TOOL, width=SAMPLE_LINE_WIDTH)
    # Start and draw: one quadratic followed by one cubic, then stroke
    nb.move_to(280, 320)
    nb.begin_path().quad_to(360, 320, 360, 380, samples=12).cubic_to(
        360, 430, 300, 430, 280, 390, samples=18
    ).stroke()
    nb.write(out)

    lines_new = canonical_lines(out)
    lines_fixture = canonical_lines(fixture)

    assert lines_new == lines_fixture
