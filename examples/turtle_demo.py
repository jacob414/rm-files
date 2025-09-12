from __future__ import annotations

import argparse
from pathlib import Path

from rmfiles import RemarkableNotebook
from rmscene import scene_items as si


def main() -> int:
    p = argparse.ArgumentParser(description="Draw a simple scene with the turtle-like API")
    p.add_argument("--out", default="output/turtle_demo.rm", help="Output .rm path")
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    nb = RemarkableNotebook(deg=True)
    nb.layer("Sketch").tool(pen=si.Pen.MARKER_1, color=si.PenColor.BLACK, width=3)

    # Draw a square using turtle forward/rotate
    nb.move_to(100, 100).pen_down()
    for _ in range(4):
        nb.forward(150).rotate(90)
    nb.stroke()

    # Draw a circle with a different tool
    with nb.tool_scope(pen=si.Pen.HIGHLIGHTER_1, color=si.PenColor.YELLOW, width=10):
        nb.circle(260, 175, 60)

    # Add a root text block
    nb.text(80, 60, "Turtle Demo", width=400, style=si.ParagraphStyle.HEADING)

    nb.write(out)
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

