from __future__ import annotations

import argparse
from pathlib import Path

from rmfiles.generate import create_triangle_rm


def main() -> int:
    p = argparse.ArgumentParser(description="Create a triangle .rm in ./output")
    p.add_argument("--out", default="output/triangle.rm", help="Output .rm path")
    p.add_argument("--cx", type=float, default=200.0)
    p.add_argument("--cy", type=float, default=200.0)
    p.add_argument("--size", type=float, default=300.0)
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    create_triangle_rm(str(out), cx=args.cx, cy=args.cy, size=args.size)
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
