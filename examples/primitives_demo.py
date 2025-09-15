from __future__ import annotations

import argparse
from pathlib import Path

from rmfiles import RemarkableNotebook


def main() -> int:
    p = argparse.ArgumentParser(
        description="Draw assorted primitives with transforms and presets"
    )
    p.add_argument("--out", default="output/primitives_demo.rm", help="Output .rm path")
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    nb = RemarkableNotebook(deg=True)

    # Base layer
    nb.layer("Sketch").use_preset("ballpoint")

    # Regular polygon and star
    nb.regular_polygon(6, cx=150, cy=120, r=60)
    nb.star(cx=330, cy=120, r=60, points=5, inner_ratio=0.45)

    # Ellipse and arc
    nb.ellipse(cx=150, cy=260, rx=80, ry=40, rotation=20)
    nb.arc(cx=330, cy=260, r=70, start=45, sweep=220)

    # Rounded rectangle
    nb.rounded_rect(60, 320, 180, 110, radius=18, segments=6)

    # Path with quadratic and cubic
    nb.move_to(280, 320)
    nb.begin_path().quad_to(360, 320, 360, 380, samples=12).cubic_to(
        360, 430, 300, 430, 280, 390, samples=18
    ).stroke()

    # Transform demo: draw rotated/scaled star copies using preset highlighter
    with nb.preset_scope("highlighter"):
        nb.tf_push().tf_translate(480, 180)
        for _i in range(5):
            nb.tf_rotate(18).tf_scale(0.9, 0.9)
            nb.star(cx=0, cy=0, r=90, points=5, inner_ratio=0.5)
        nb.tf_pop()

    nb.write(out)
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
