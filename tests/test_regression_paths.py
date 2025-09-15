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


def test_regression_path_beziers(tmp_path: Path) -> None:
    """Recreate a mixed quadratic+cubic path and compare to golden fixture."""
    fixture = Path("fixtures/path_fixture.rm")
    assert fixture.exists(), "Expected path fixture to exist"

    out = tmp_path / "path.regression.rm"

    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch")
    # Start and draw: one quadratic followed by one cubic, then stroke
    nb.move_to(280, 320)
    nb.begin_path().quad_to(360, 320, 360, 380, samples=12).cubic_to(
        360, 430, 300, 430, 280, 390, samples=18
    ).stroke()
    nb.write(out)

    lines_new = _canonical_lines(out)
    lines_fixture = _canonical_lines(fixture)

    assert lines_new == lines_fixture
