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
