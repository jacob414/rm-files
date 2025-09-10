from __future__ import annotations

import argparse
from pathlib import Path

from rmfiles.generate import create_rectangle_rm


def main() -> int:
    p = argparse.ArgumentParser(description="Create a rectangle .rm in ./output")
    p.add_argument("--out", default="output/rectangle.rm", help="Output .rm path")
    p.add_argument("--x", type=float, default=100.0)
    p.add_argument("--y", type=float, default=100.0)
    p.add_argument("--width", type=float, default=300.0)
    p.add_argument("--height", type=float, default=200.0)
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    create_rectangle_rm(str(out), x=args.x, y=args.y, width=args.width, height=args.height)
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

