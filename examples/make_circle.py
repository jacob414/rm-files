from __future__ import annotations

import argparse
from pathlib import Path

from rmfiles.generate import create_circle_rm


def main() -> int:
    p = argparse.ArgumentParser(description="Create a circle .rm in ./output")
    p.add_argument("--out", default="output/circle.rm", help="Output .rm path")
    p.add_argument("--cx", type=float, default=200.0)
    p.add_argument("--cy", type=float, default=200.0)
    p.add_argument("--radius", type=float, default=150.0)
    p.add_argument("--segments", type=int, default=64)
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    create_circle_rm(
        str(out), cx=args.cx, cy=args.cy, radius=args.radius, segments=args.segments
    )
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
