"""Simple primitive generator scratch pad."""

from __future__ import annotations

from pathlib import Path

from rmscene import Pen, Scene, Stroke


def build_rectangle_scene() -> Scene:
    scene = Scene()
    layer = scene.add_layer()
    pen = Pen()
    x1, y1 = 100, 100
    x2, y2 = 400, 300
    stroke = Stroke([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)], pen)
    layer.add_stroke(stroke)
    return scene


def main() -> None:
    scene = build_rectangle_scene()
    out = Path("sample-output.rm")
    scene.write(str(out))
    print(f"Wrote rectangle sample to {out}")


if __name__ == "__main__":
    main()
