from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from math import cos, sin, tau
from pathlib import Path
from typing import BinaryIO

from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequence, CrdtSequenceItem
from rmscene.scene_stream import Block, RootTextBlock
from rmscene.tagged_block_common import CrdtId, LwwValue

from .generate import circle_points, rectangle_points, write_rm
from .notebook import NotebookLayer, ReMarkableNotebook


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
        # lines[layer] = list[(points, Tool|None, affine)]
        # affine is a 2D transform matrix (a, b, c, d, tx, ty)
        self._lines: dict[
            str,
            list[
                tuple[
                    list[si.Point],
                    Tool | None,
                    tuple[float, float, float, float, float, float],
                ]
            ],
        ] = {}
        # highlights[layer] = list[(text, color, [rectangles])]
        self._highlights: dict[
            str, list[tuple[str, si.PenColor, list[si.Rectangle]]]
        ] = {}
        # current path buffer
        self._path: list[si.Point] = []
        # current tool context
        self._tool: Tool = Tool(pen=si.Pen.BALLPOINT_1)

        # Transform stack (applies only to geometry, not turtle heading)
        self._affine: tuple[float, float, float, float, float, float] = (
            1.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
        )
        self._affine_stack: list[tuple[float, float, float, float, float, float]] = []

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
            (
                self._x,
                self._y,
                self._heading,
                self._pen_down,
                self._tool if include_tool else None,
            )
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
    def begin_path(self) -> RemarkableNotebook:
        """Begin a new path at the current position.

        Does not depend on pen state; explicitly seeds the path buffer with a
        point at the current position using current tool width/pressure.
        """
        self._path.clear()
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

    def close_path(self) -> RemarkableNotebook:
        """Close the current path by repeating the first point, if present."""
        if self._path:
            first = self._path[0]
            last = self._path[-1]
            if first.x != last.x or first.y != last.y:
                self._path.append(
                    si.Point(
                        x=first.x,
                        y=first.y,
                        speed=0,
                        direction=0,
                        width=self._tool.width,
                        pressure=self._tool.pressure,
                    )
                )
        return self

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

    def quad_to(
        self, x1: float, y1: float, x2: float, y2: float, *, samples: int = 16
    ) -> RemarkableNotebook:
        """Append a quadratic Bezier segment to the current path.

        Uses the last point in the path as P0, (x1,y1) as control P1, and
        (x2,y2) as end P2. If the path is empty, it begins at current position.
        """
        if not self._path:
            self.begin_path()
        p0 = self._path[-1]
        w = self._tool.width
        p = self._tool.pressure
        s = max(1, int(samples))
        for i in range(1, s + 1):
            t = i / s
            mt = 1 - t
            x = mt * mt * p0.x + 2 * mt * t * x1 + t * t * x2
            y = mt * mt * p0.y + 2 * mt * t * y1 + t * t * y2
            self._path.append(
                si.Point(
                    x=float(x), y=float(y), speed=0, direction=0, width=w, pressure=p
                )
            )
        self._x, self._y = float(x2), float(y2)
        return self

    def cubic_to(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
        *,
        samples: int = 24,
    ) -> RemarkableNotebook:
        """Append a cubic Bezier segment to the current path.

        Uses the last point in the path as P0, (x1,y1) and (x2,y2) as control
        points, and (x3,y3) as end. If the path is empty, it begins at current
        position.
        """
        if not self._path:
            self.begin_path()
        p0 = self._path[-1]
        w = self._tool.width
        p = self._tool.pressure
        s = max(1, int(samples))
        for i in range(1, s + 1):
            t = i / s
            mt = 1 - t
            x = (
                mt * mt * mt * p0.x
                + 3 * mt * mt * t * x1
                + 3 * mt * t * t * x2
                + t * t * t * x3
            )
            y = (
                mt * mt * mt * p0.y
                + 3 * mt * mt * t * y1
                + 3 * mt * t * t * y2
                + t * t * t * y3
            )
            self._path.append(
                si.Point(
                    x=float(x), y=float(y), speed=0, direction=0, width=w, pressure=p
                )
            )
        self._x, self._y = float(x3), float(y3)
        return self

    def stroke(self, *, tool: Tool | None = None) -> RemarkableNotebook:
        pts = list(self._path)
        self._path.clear()
        if len(pts) >= 2:
            self._lines.setdefault(self._current_layer, []).append(
                (pts, tool, self._affine)
            )
        return self

    def polyline(
        self,
        points: Iterable[tuple[float, float]],
        *,
        close: bool = False,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        pts: list[si.Point] = [
            si.Point(
                x=float(x),
                y=float(y),
                speed=0,
                direction=0,
                width=(tool or self._tool).width,
                pressure=(tool or self._tool).pressure,
            )
            for (x, y) in points
        ]
        if close and pts:
            pts.append(pts[0])
        self._lines.setdefault(self._current_layer, []).append(
            (pts, tool, self._affine)
        )
        return self

    def line(
        self, x1: float, y1: float, x2: float, y2: float, *, tool: Tool | None = None
    ) -> RemarkableNotebook:
        return self.polyline([(x1, y1), (x2, y2)], tool=tool)

    def rect(
        self, x: float, y: float, w: float, h: float, *, tool: Tool | None = None
    ) -> RemarkableNotebook:
        pts = rectangle_points(
            x,
            y,
            w,
            h,
            width=(tool or self._tool).width,
            pressure=(tool or self._tool).pressure,
        )
        self._lines.setdefault(self._current_layer, []).append(
            (pts, tool, self._affine)
        )
        return self

    def circle(
        self,
        cx: float,
        cy: float,
        r: float,
        *,
        segments: int | None = None,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        pts = circle_points(
            cx,
            cy,
            r,
            segments=segments or 64,
            width=(tool or self._tool).width,
            pressure=(tool or self._tool).pressure,
        )
        self._lines.setdefault(self._current_layer, []).append(
            (pts, tool, self._affine)
        )
        return self

    def regular_polygon(
        self,
        n: int,
        cx: float,
        cy: float,
        r: float,
        *,
        rotation: float = 0.0,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        """Add a regular n-gon centered at (cx, cy) with radius r.

        The path is closed by repeating the first point.
        """
        if n < 3:
            return self
        ang0 = rotation * tau / 360 if self._deg else rotation
        pts: list[si.Point] = []
        w = (tool or self._tool).width
        p = (tool or self._tool).pressure
        for i in range(n):
            ang = ang0 + (tau * i / n)
            x = cx + r * cos(ang)
            y = cy + r * sin(ang)
            pts.append(
                si.Point(
                    x=float(x), y=float(y), speed=0, direction=0, width=w, pressure=p
                )
            )
        pts.append(pts[0])
        self._lines.setdefault(self._current_layer, []).append(
            (pts, tool, self._affine)
        )
        return self

    def star(
        self,
        cx: float,
        cy: float,
        r: float,
        *,
        points: int = 5,
        inner_ratio: float = 0.5,
        rotation: float = 0.0,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        """Add a star polygon with given points and inner radius ratio.

        The path alternates outer and inner vertices and is closed.
        """
        n = max(2, int(points))
        if n < 2:
            return self
        ang0 = rotation * tau / 360 if self._deg else rotation
        w = (tool or self._tool).width
        p = (tool or self._tool).pressure
        pts: list[si.Point] = []
        for i in range(n * 2):
            rr = r if i % 2 == 0 else r * inner_ratio
            ang = ang0 + (tau * i / (n * 2))
            x = cx + rr * cos(ang)
            y = cy + rr * sin(ang)
            pts.append(
                si.Point(
                    x=float(x), y=float(y), speed=0, direction=0, width=w, pressure=p
                )
            )
        pts.append(pts[0])
        self._lines.setdefault(self._current_layer, []).append(
            (pts, tool, self._affine)
        )
        return self

    def ellipse(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        *,
        segments: int = 96,
        rotation: float = 0.0,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        """Add an ellipse centered at (cx, cy) with radii rx, ry.

        The path is closed by repeating the first point. `rotation` rotates the
        ellipse around its center.
        """
        seg = max(8, int(segments))
        rot = rotation * tau / 360 if self._deg else rotation
        cr = cos(rot)
        sr = sin(rot)
        w = (tool or self._tool).width
        p = (tool or self._tool).pressure
        pts: list[si.Point] = []
        for i in range(seg):
            th = tau * i / seg
            x0 = rx * cos(th)
            y0 = ry * sin(th)
            x = cx + x0 * cr - y0 * sr
            y = cy + x0 * sr + y0 * cr
            pts.append(
                si.Point(
                    x=float(x), y=float(y), speed=0, direction=0, width=w, pressure=p
                )
            )
        if pts:
            pts.append(pts[0])
        self._lines.setdefault(self._current_layer, []).append(
            (pts, tool, self._affine)
        )
        return self

    def arc(
        self,
        cx: float,
        cy: float,
        r: float,
        *,
        start: float,
        sweep: float,
        segments: int = 32,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        """Add a circular arc with radius r from start by sweep.

        The arc is not closed; it consists of `segments + 1` points sampled
        uniformly along the angle.
        """
        seg = max(1, int(segments))
        s0 = start * tau / 360 if self._deg else start
        sw = sweep * tau / 360 if self._deg else sweep
        w = (tool or self._tool).width
        p = (tool or self._tool).pressure
        pts: list[si.Point] = []
        for i in range(seg + 1):
            th = s0 + sw * (i / seg)
            x = cx + r * cos(th)
            y = cy + r * sin(th)
            pts.append(
                si.Point(
                    x=float(x), y=float(y), speed=0, direction=0, width=w, pressure=p
                )
            )
        self._lines.setdefault(self._current_layer, []).append(
            (pts, tool, self._affine)
        )
        return self

    def rounded_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        radius: float = 10.0,
        segments: int = 8,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        """Add a rounded rectangle polyline (closed).

        `radius` is clamped to half of min(w, h). `segments` controls sampling
        for each quarter-arc corner.
        """
        if w <= 0 or h <= 0:
            return self
        r = float(max(0.0, min(radius, w / 2.0, h / 2.0)))
        k = max(1, int(segments))
        wtool = (tool or self._tool).width
        ptool = (tool or self._tool).pressure

        def pt(px: float, py: float) -> si.Point:
            return si.Point(
                x=float(px),
                y=float(py),
                speed=0,
                direction=0,
                width=wtool,
                pressure=ptool,
            )

        pts: list[si.Point] = []
        # Start at top edge, left of top-right corner
        pts.append(pt(x + r, y))
        # Top edge
        pts.append(pt(x + w - r, y))
        # Top-right corner (center cx,cy = x+w-r, y+r), angles -90 -> 0
        cx_tr, cy_tr = x + w - r, y + r
        for i in range(1, k + 1):
            ang = -tau / 4 + (tau / 4) * (i / k)
            px = cx_tr + r * cos(ang)
            py = cy_tr + r * sin(ang)
            pts.append(pt(px, py))
        # Right edge down to bottom-right corner start
        pts.append(pt(x + w, y + h - r))
        # Bottom-right corner 0 -> 90
        cx_br, cy_br = x + w - r, y + h - r
        for i in range(1, k + 1):
            ang = 0.0 + (tau / 4) * (i / k)
            px = cx_br + r * cos(ang)
            py = cy_br + r * sin(ang)
            pts.append(pt(px, py))
        # Bottom edge to bottom-left
        pts.append(pt(x + r, y + h))
        # Bottom-left corner 90 -> 180
        cx_bl, cy_bl = x + r, y + h - r
        for i in range(1, k + 1):
            ang = tau / 4 + (tau / 4) * (i / k)
            px = cx_bl + r * cos(ang)
            py = cy_bl + r * sin(ang)
            pts.append(pt(px, py))
        # Left edge up to top-left
        pts.append(pt(x, y + r))
        # Top-left corner 180 -> 270
        cx_tl, cy_tl = x + r, y + r
        for i in range(1, k + 1):
            ang = tau / 2 + (tau / 4) * (i / k)
            px = cx_tl + r * cos(ang)
            py = cy_tl + r * sin(ang)
            pts.append(pt(px, py))
        # Close
        pts.append(pt(x + r, y))

        self._lines.setdefault(self._current_layer, []).append(
            (pts, tool, self._affine)
        )
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
            self._root_texts: list[
                tuple[float, float, float, si.ParagraphStyle, si.PenColor, str]
            ] = []
        self._root_texts.append((float(x), float(y), float(width), style, color, text))
        return self

    def highlight(
        self,
        text: str,
        rectangles: Iterable[tuple[float, float, float, float]],
        *,
        color: si.PenColor = si.PenColor.YELLOW,
    ) -> RemarkableNotebook:
        rects = [
            si.Rectangle(x=float(x), y=float(y), w=float(w), h=float(h))
            for (x, y, w, h) in rectangles
        ]
        self._highlights.setdefault(self._current_layer, []).append(
            (text, color, rects)
        )
        return self

    # --- Output ---
    def compile(self) -> list[Block]:
        # Materialize into the existing ReMarkableNotebook
        nb = ReMarkableNotebook()
        layer_objs: dict[str, NotebookLayer] = {}
        for name in self._lines.keys():
            layer_objs[name] = nb.create_layer(name)
        for name, lines in self._lines.items():
            layer = layer_objs[name]
            for pts, tool, aff in lines:
                t = tool or self._tool
                # Apply affine to points (geometry only)
                tx_pts = [
                    si.Point(
                        x=self._aff_apply(p.x, p.y, aff)[0],
                        y=self._aff_apply(p.x, p.y, aff)[1],
                        speed=p.speed,
                        direction=p.direction,
                        width=p.width,
                        pressure=p.pressure,
                    )
                    for p in pts
                ]
                line = si.Line(
                    color=t.color,
                    tool=t.pen,
                    points=tx_pts,
                    thickness_scale=t.thickness_scale,
                    starting_length=0.0,
                )
                # add_line_to_layer will allocate CRDT IDs for us
                nb.add_line_to_layer(
                    layer,
                    line.points,
                    color=line.color,
                    tool=line.tool,
                    thickness_scale=line.thickness_scale,
                )
        # Add highlights
        for name, items in self._highlights.items():
            existing = layer_objs.get(name)
            layer = existing if existing is not None else nb.create_layer(name)
            if existing is None:
                layer_objs[name] = layer
            for text, color, rects in items:
                nb.add_highlight_to_layer(
                    layer, text=text, color=color, rectangles=rects
                )

        blocks = nb.to_blocks()

        # Append root text blocks if any
        for x, y, width, style, _color, text in getattr(self, "_root_texts", []):
            # Build a minimal si.Text; style mapping is minimal PLAIN/selected style
            text_items: CrdtSequence = CrdtSequence(
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
            text_value = si.Text(
                items=text_items, styles=styles, pos_x=x, pos_y=y, width=width
            )
            blocks.append(RootTextBlock(block_id=CrdtId(0, 0), value=text_value))

        return blocks

    # --- Transform helpers (geometry only) ---
    @staticmethod
    def _aff_mul(
        m1: tuple[float, float, float, float, float, float],
        m2: tuple[float, float, float, float, float, float],
    ) -> tuple[float, float, float, float, float, float]:
        a1, b1, c1, d1, tx1, ty1 = m1
        a2, b2, c2, d2, tx2, ty2 = m2
        return (
            a1 * a2 + c1 * b2,
            b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2,
            b1 * c2 + d1 * d2,
            a1 * tx2 + c1 * ty2 + tx1,
            b1 * tx2 + d1 * ty2 + ty1,
        )

    @staticmethod
    def _aff_apply(
        x: float,
        y: float,
        m: tuple[float, float, float, float, float, float],
    ) -> tuple[float, float]:
        a, b, c, d, tx, ty = m
        return (a * x + c * y + tx, b * x + d * y + ty)

    def tf_translate(self, dx: float, dy: float) -> RemarkableNotebook:
        t = (1.0, 0.0, 0.0, 1.0, float(dx), float(dy))
        self._affine = self._aff_mul(self._affine, t)
        return self

    def tf_scale(self, sx: float, sy: float) -> RemarkableNotebook:
        s = (float(sx), 0.0, 0.0, float(sy), 0.0, 0.0)
        self._affine = self._aff_mul(self._affine, s)
        return self

    def tf_rotate(self, angle: float) -> RemarkableNotebook:
        from math import cos as _cos
        from math import sin as _sin
        from math import tau as _tau

        ang = angle * _tau / 360 if self._deg else angle
        ca = _cos(ang)
        sa = _sin(ang)
        r = (ca, sa, -sa, ca, 0.0, 0.0)
        self._affine = self._aff_mul(self._affine, r)
        return self

    def tf_push(self) -> RemarkableNotebook:
        self._affine_stack.append(self._affine)
        return self

    def tf_pop(self) -> RemarkableNotebook:
        self._affine = self._affine_stack.pop()
        return self

    def write(self, dest: str | Path | BinaryIO | None = None) -> None:
        pathlike: str | Path | None
        buf: BinaryIO | None = None
        if dest is None:
            if isinstance(self._output, str | Path):
                pathlike = self._output
            else:
                buf = self._output  # may be None
                pathlike = None
        else:
            pathlike = dest if isinstance(dest, str | Path) else None
            buf = dest if hasattr(dest, "write") else None  # type: ignore[assignment]

        blocks = self.compile()
        if pathlike is not None:
            write_rm(str(pathlike), blocks, version=self._version)
        elif buf is not None:
            from rmscene.scene_stream import write_blocks

            write_blocks(buf, blocks, options={"version": self._version})
        else:
            raise ValueError("No output destination provided to write() or constructor")
