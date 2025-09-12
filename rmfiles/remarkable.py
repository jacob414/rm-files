from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from math import cos, tau
from pathlib import Path
from typing import BinaryIO, Iterable

from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequence, CrdtSequenceItem
from rmscene.scene_stream import Block, RootTextBlock
from rmscene.tagged_block_common import CrdtId, LwwValue

from .generate import circle_points, rectangle_points, write_rm
from .notebook import ReMarkableNotebook


@dataclass
class Tool:
    pen: si.Pen
    color: si.PenColor = si.PenColor.BLACK
    width: int = 2
    pressure: int = 100
    thickness_scale: float = 1.0


class RemarkableNotebook:
    """Ergonomic, turtle-like API that compiles to a ReMarkable scene.

    This facade records drawing commands and compiles them to blocks using the
    existing ReMarkableNotebook implementation under the hood.
    """

    def __init__(
        self,
        output: str | Path | BinaryIO | None = None,
        *,
        version: str = "3.1",
        deg: bool = True,
    ) -> None:
        self._output = output
        self._version = version
        self._deg = deg

        # Turtle state
        self._x: float = 0.0
        self._y: float = 0.0
        self._heading: float = 0.0  # radians
        self._pen_down: bool = True
        # stack entries: (x, y, heading, pen_down, tool or None)
        self._stack: list[tuple[float, float, float, bool, Tool | None]] = []

        # Layers and content
        self._current_layer: str = "Layer 1"
        # lines[layer] = list[(points, Tool|None)]
        self._lines: dict[str, list[tuple[list[si.Point], Tool | None]]] = {}
        # highlights[layer] = list[(text, color, [rectangles])]
        self._highlights: dict[str, list[tuple[str, si.PenColor, list[si.Rectangle]]]] = {}
        # current path buffer
        self._path: list[si.Point] = []
        # current tool context
        self._tool: Tool = Tool(pen=si.Pen.BALLPOINT_1)

    # --- Layer management ---
    def layer(self, name: str, *, visible: bool = True) -> RemarkableNotebook:
        # visible is currently unused; reserved for future compile mapping
        self._current_layer = name
        self._lines.setdefault(name, [])
        return self

    # --- Tool management ---
    def tool(
        self,
        *,
        pen: si.Pen,
        color: si.PenColor = si.PenColor.BLACK,
        width: int = 2,
        pressure: int = 100,
        thickness_scale: float = 1.0,
    ) -> RemarkableNotebook:
        self._tool = Tool(
            pen=pen,
            color=color,
            width=width,
            pressure=pressure,
            thickness_scale=thickness_scale,
        )
        return self

    @contextmanager
    def tool_scope(self, **kwargs):
        prev = self._tool
        self.tool(**kwargs)
        try:
            yield self
        finally:
            self._tool = prev

    # --- Turtle state ---
    @property
    def position(self) -> tuple[float, float]:
        return (self._x, self._y)

    @position.setter
    def position(self, pos: tuple[float, float]) -> None:
        self._x, self._y = float(pos[0]), float(pos[1])

    @property
    def heading(self) -> float:
        return 360 * self._heading / tau if self._deg else self._heading

    def pen_down(self) -> RemarkableNotebook:
        self._pen_down = True
        # Start a new path at current position if empty
        if not self._path:
            self._path.append(
                si.Point(x=self._x, y=self._y, speed=0, direction=0, width=self._tool.width, pressure=self._tool.pressure)
            )
        return self

    def pen_up(self) -> RemarkableNotebook:
        self._pen_down = False
        return self

    def move_to(self, x: float, y: float) -> RemarkableNotebook:
        self._x, self._y = float(x), float(y)
        # Do not draw; reset path start for next pen down
        self._path.clear()
        return self

    def forward(self, distance: float) -> RemarkableNotebook:
        dx = distance * cos(self._heading)
        dy = distance * sin(self._heading)
        self._x += dx
        self._y += dy
        if self._pen_down:
            self._path.append(
                si.Point(
                    x=self._x,
                    y=self._y,
                    speed=0,
                    direction=0,
                    width=self._tool.width,
                    pressure=self._tool.pressure,
                )
            )
        return self

    def rotate(self, angle: float) -> RemarkableNotebook:
        dd = angle * tau / 360 if self._deg else angle
        # Keep heading within [0, 2π)
        self._heading = (self._heading + dd) % tau
        return self

    def push(self, *, include_tool: bool = False) -> RemarkableNotebook:
        self._stack.append(
            (self._x, self._y, self._heading, self._pen_down, self._tool if include_tool else None)
        )
        return self

    def pop(self, *, include_tool: bool = False) -> RemarkableNotebook:
        x, y, heading, pen_down, tool = self._stack.pop()
        self._x, self._y, self._heading, self._pen_down = x, y, heading, pen_down
        if include_tool and tool is not None:
            self._tool = tool
        # Path continuity is undefined after pop; do not implicitly connect
        self._path.clear()
        return self

    # --- Path and primitives ---
    def line_to(self, x: float, y: float) -> RemarkableNotebook:
        self._x, self._y = float(x), float(y)
        if self._pen_down:
            self._path.append(
                si.Point(
                    x=self._x,
                    y=self._y,
                    speed=0,
                    direction=0,
                    width=self._tool.width,
                    pressure=self._tool.pressure,
                )
            )
        return self

    def stroke(self, *, tool: Tool | None = None) -> RemarkableNotebook:
        pts = list(self._path)
        self._path.clear()
        if len(pts) >= 2:
            self._lines.setdefault(self._current_layer, []).append((pts, tool))
        return self

    def polyline(
        self,
        points: Iterable[tuple[float, float]],
        *,
        close: bool = False,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        pts: list[si.Point] = [
            si.Point(x=float(x), y=float(y), speed=0, direction=0, width=(tool or self._tool).width, pressure=(tool or self._tool).pressure)
            for (x, y) in points
        ]
        if close and pts:
            pts.append(pts[0])
        self._lines.setdefault(self._current_layer, []).append((pts, tool))
        return self

    def line(self, x1: float, y1: float, x2: float, y2: float, *, tool: Tool | None = None) -> RemarkableNotebook:
        return self.polyline([(x1, y1), (x2, y2)], tool=tool)

    def rect(self, x: float, y: float, w: float, h: float, *, tool: Tool | None = None) -> RemarkableNotebook:
        pts = rectangle_points(x, y, w, h, width=(tool or self._tool).width, pressure=(tool or self._tool).pressure)
        self._lines.setdefault(self._current_layer, []).append((pts, tool))
        return self

    def circle(self, cx: float, cy: float, r: float, *, segments: int | None = None, tool: Tool | None = None) -> RemarkableNotebook:
        pts = circle_points(cx, cy, r, segments=segments or 64, width=(tool or self._tool).width, pressure=(tool or self._tool).pressure)
        self._lines.setdefault(self._current_layer, []).append((pts, tool))
        return self

    # --- Text (stub: queued, not compiled yet) ---
    # --- Text (root-level block support) ---
    def text(
        self,
        x: float,
        y: float,
        text: str,
        *,
        width: float = 400.0,
        style: si.ParagraphStyle = si.ParagraphStyle.BASIC,
        color: si.PenColor = si.PenColor.BLACK,
    ) -> RemarkableNotebook:
        # Queue root text blocks for compile
        if not hasattr(self, "_root_texts"):
            self._root_texts: list[tuple[float, float, float, si.ParagraphStyle, si.PenColor, str]] = []
        self._root_texts.append((float(x), float(y), float(width), style, color, text))
        return self

    def highlight(
        self,
        text: str,
        rectangles: Iterable[tuple[float, float, float, float]],
        *,
        color: si.PenColor = si.PenColor.YELLOW,
    ) -> RemarkableNotebook:
        rects = [si.Rectangle(x=float(x), y=float(y), w=float(w), h=float(h)) for (x, y, w, h) in rectangles]
        self._highlights.setdefault(self._current_layer, []).append((text, color, rects))
        return self

    # --- Output ---
    def compile(self) -> list[Block]:
        # Materialize into the existing ReMarkableNotebook
        nb = ReMarkableNotebook()
        layer_objs: dict[str, object] = {}
        for name in self._lines.keys():
            layer_objs[name] = nb.create_layer(name)
        for name, lines in self._lines.items():
            layer = layer_objs[name]
            for pts, tool in lines:
                t = tool or self._tool
                line = si.Line(
                    color=t.color,
                    tool=t.pen,
                    points=pts,
                    thickness_scale=t.thickness_scale,
                    starting_length=0.0,
                )
                # add_line_to_layer will allocate CRDT IDs for us
                nb.add_line_to_layer(layer, line.points, color=line.color, tool=line.tool, thickness_scale=line.thickness_scale)
        # Add highlights
        for name, items in self._highlights.items():
            layer = layer_objs.get(name)
            if layer is None:
                layer = nb.create_layer(name)
                layer_objs[name] = layer
            for text, color, rects in items:
                nb.add_highlight_to_layer(layer, text=text, color=color, rectangles=rects)

        blocks = nb.to_blocks()

        # Append root text blocks if any
        for (x, y, width, style, color, text) in getattr(self, "_root_texts", []):
            # Build a minimal si.Text; style mapping is minimal PLAIN/selected style
            text_items = CrdtSequence(
                [
                    CrdtSequenceItem(
                        item_id=CrdtId(1, 16),
                        left_id=CrdtId(0, 0),
                        right_id=CrdtId(0, 0),
                        deleted_length=0,
                        value=text,
                    )
                ]
            )
            styles = {CrdtId(0, 0): LwwValue(timestamp=CrdtId(1, 15), value=style)}
            text_value = si.Text(items=text_items, styles=styles, pos_x=x, pos_y=y, width=width)
            blocks.append(RootTextBlock(block_id=CrdtId(0, 0), value=text_value))

        return blocks

    def write(self, dest: str | Path | BinaryIO | None = None) -> None:
        pathlike: str | Path | None
        buf: BinaryIO | None = None
        if dest is None:
            if isinstance(self._output, (str, Path)):
                pathlike = self._output
            else:
                buf = self._output  # may be None
                pathlike = None
        else:
            pathlike = dest if isinstance(dest, (str, Path)) else None
            buf = dest if hasattr(dest, "write") else None  # type: ignore[assignment]

        blocks = self.compile()
        if pathlike is not None:
            write_rm(str(pathlike), blocks, version=self._version)
        elif buf is not None:
            from rmscene.scene_stream import write_blocks

            write_blocks(buf, blocks, options={"version": self._version})
        else:
            raise ValueError("No output destination provided to write() or constructor")
