"""Scratch pad for constructing raw rmscene stroke objects."""

from __future__ import annotations

from rmscene import scene_items as si


def build_sample_line() -> si.Line:
    start = si.Point(x=100, y=100, speed=100, direction=1, width=48, pressure=50)
    stop = si.Point(x=100, y=200, speed=100, direction=1, width=48, pressure=50)
    return si.Line(
        color=si.PenColor.BLACK,
        tool=si.Pen.FINELINER_1,
        points=[start, stop],
        thickness_scale=100.0,
        starting_length=100.0,
    )


if __name__ == "__main__":
    line = build_sample_line()
    print(f"Created sample line with {len(line.points)} points")
