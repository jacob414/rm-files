from __future__ import annotations

import argparse
from pathlib import Path

from rmscene import scene_items as si

from rmfiles import RemarkableNotebook
from rmfiles.testing import SAMPLE_LINE_WIDTH, SAMPLE_TOOL


def regen_fixtures(fixtures_dir: Path, *, verbose: bool = False) -> None:
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    def write(nb: RemarkableNotebook, name: str) -> None:
        out = fixtures_dir / name
        nb.write(out)
        if verbose:
            print(f"Wrote {out}")

    # 1) Regular polygon (explicit tool, width 24)
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.regular_polygon(6, cx=150, cy=120, r=60)
    write(nb, "polygon_fixture.rm")

    # 2) Rounded rectangle (ballpoint tool, width 24)
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.rounded_rect(60, 320, 180, 110, radius=18, segments=6)
    write(nb, "rounded_rect_fixture.rm")

    # 3) Star (ballpoint tool, width 24)
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.star(cx=330, cy=120, r=60, points=5, inner_ratio=0.45)
    write(nb, "star_fixture.rm")

    # 4) Ellipse (ballpoint tool, width 24)
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.ellipse(cx=150, cy=260, rx=80, ry=40, rotation=20)
    write(nb, "ellipse_fixture.rm")

    # 5) Arc (ballpoint tool, width 24)
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(
        pen=SAMPLE_TOOL, color=si.PenColor.BLACK, width=SAMPLE_LINE_WIDTH
    )
    nb.arc(cx=330, cy=260, r=70, start=45, sweep=220)
    write(nb, "arc_fixture.rm")

    # 6) Path with quadratic and cubic (ballpoint tool, width 24)
    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=si.Pen.BALLPOINT_1, color=si.PenColor.BLACK, width=24)
    nb.move_to(280, 320)
    nb.begin_path().quad_to(360, 320, 360, 380, samples=12).cubic_to(
        360, 430, 300, 430, 280, 390, samples=18
    ).stroke()
    write(nb, "path_fixture.rm")


def main() -> int:
    p = argparse.ArgumentParser(
        description="Regenerate .rm fixtures used by regression tests"
    )
    p.add_argument(
        "--dir",
        default="fixtures",
        type=Path,
        help="Directory to write fixtures (default: fixtures)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = p.parse_args()

    regen_fixtures(args.dir, verbose=bool(args.verbose))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
