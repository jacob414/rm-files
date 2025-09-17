from __future__ import annotations

import json
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from math import cos, sin, tau
from pathlib import Path
from typing import Any, BinaryIO

from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequence, CrdtSequenceItem
from rmscene.scene_stream import (
    AuthorIdsBlock,
    Block,
    MigrationInfoBlock,
    PageInfoBlock,
    RootTextBlock,
    SceneGlyphItemBlock,
    SceneLineItemBlock,
    SceneTreeBlock,
    TreeNodeBlock,
    read_blocks,
    read_tree,
)
from rmscene.scene_tree import SceneTree
from rmscene.tagged_block_common import CrdtId, LwwValue

from .generate import circle_points, rectangle_points, write_rm
from .notebook import NotebookLayer, ReMarkableNotebook


def _extract_lww(value: LwwValue[Any] | None) -> Any:
    if value is None:
        return None
    return getattr(value, "value", None)


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
        self._layer_visibility: dict[str, bool] = {}
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

        # Tool presets
        self._presets: dict[str, Tool] = {
            "ballpoint": Tool(
                pen=si.Pen.BALLPOINT_1,
                color=si.PenColor.BLACK,
                width=2,
                pressure=100,
                thickness_scale=1.0,
            ),
            "fineliner": Tool(
                pen=si.Pen.FINELINER_1,
                color=si.PenColor.BLACK,
                width=2,
                pressure=100,
                thickness_scale=1.0,
            ),
            "marker": Tool(
                pen=si.Pen.MARKER_1,
                color=si.PenColor.BLACK,
                width=4,
                pressure=120,
                thickness_scale=2.0,
            ),
            "pencil": Tool(
                pen=si.Pen.PENCIL_1,
                color=si.PenColor.BLACK,
                width=2,
                pressure=100,
                thickness_scale=1.0,
            ),
            "highlighter": Tool(
                pen=si.Pen.HIGHLIGHTER_1,
                color=si.PenColor.YELLOW,
                width=12,
                pressure=100,
                thickness_scale=2.0,
            ),
        }

    @classmethod
    def from_file(
        cls, path: str | Path, *, version: str = "3.1", deg: bool = True
    ) -> RemarkableNotebook:
        """Load a notebook from an existing `.rm` file."""

        notebook = cls(version=version, deg=deg)
        path = Path(path)
        try:
            with path.open("rb") as handle:
                tree = read_tree(handle)
            notebook._load_from_tree(tree)
        except ValueError:
            with path.open("rb") as handle:
                blocks = list(read_blocks(handle))
            notebook._load_from_blocks(blocks)
        return notebook

    def _load_from_tree(self, tree: SceneTree) -> None:
        self._lines.clear()
        self._highlights.clear()
        self._layer_visibility.clear()
        self._current_layer = "Layer 1"

        children = getattr(tree.root, "children", None)
        if children is None:
            return

        for item in children.sequence_items():
            group = item.value
            if not isinstance(group, si.Group):
                continue

            label = _extract_lww(group.label)
            name = label if isinstance(label, str) and label else "Layer"
            visible_lww = _extract_lww(group.visible)
            visible = True if visible_lww is None else bool(visible_lww)

            self.layer(name, visible=visible)
            lines_entry = self._lines.setdefault(name, [])
            highlights_entry = self._highlights.setdefault(name, [])
            lines_entry.clear()
            highlights_entry.clear()

            for child in group.children.sequence_items():
                value = child.value
                if isinstance(value, si.Line):
                    tool = Tool(
                        pen=value.tool,
                        color=value.color,
                        width=int(max((pt.width for pt in value.points), default=2)),
                        pressure=int(
                            max((pt.pressure for pt in value.points), default=100)
                        ),
                        thickness_scale=value.thickness_scale,
                    )
                    lines_entry.append((list(value.points), tool, self._affine))
                elif isinstance(value, si.GlyphRange):
                    rects = [
                        si.Rectangle(x=r.x, y=r.y, w=r.w, h=r.h)
                        for r in value.rectangles
                    ]
                    highlights_entry.append((value.text or "", value.color, rects))

    def _load_from_blocks(self, blocks: Iterable[Block]) -> None:
        self._lines.clear()
        self._highlights.clear()
        self._layer_visibility.clear()

        layer_data: dict[CrdtId, dict[str, Any]] = {}
        order: list[CrdtId] = []

        def entry(node_id: CrdtId) -> dict[str, Any]:
            if node_id not in layer_data:
                layer_data[node_id] = {
                    "name": "",
                    "visible": True,
                    "lines": [],
                    "highlights": [],
                }
                order.append(node_id)
            return layer_data[node_id]

        for block in blocks:
            if isinstance(block, SceneTreeBlock):
                entry(block.tree_id)
            elif isinstance(block, TreeNodeBlock):
                group = block.group
                if isinstance(group, si.Group):
                    data = entry(group.node_id)
                    name = _extract_lww(group.label)
                    if isinstance(name, str) and name:
                        data["name"] = name
                    visible = _extract_lww(group.visible)
                    if visible is not None:
                        data["visible"] = bool(visible)
            elif isinstance(block, SceneLineItemBlock):
                data = entry(block.parent_id)
                data["lines"].append(block.item.value)
            elif isinstance(block, SceneGlyphItemBlock):
                data = entry(block.parent_id)
                data["highlights"].append(block.item.value)

        for idx, node_id in enumerate(order, start=1):
            data = layer_data[node_id]
            if not data["lines"] and not data["highlights"]:
                continue
            name = data["name"] or f"Layer {idx}"
            visible = bool(data.get("visible", True))
            self.layer(name, visible=visible)
            lines_entry = self._lines.setdefault(name, [])
            highlights_entry = self._highlights.setdefault(name, [])
            lines_entry.clear()
            highlights_entry.clear()

            for line in data["lines"]:
                tool = Tool(
                    pen=line.tool,
                    color=line.color,
                    width=int(max((pt.width for pt in line.points), default=2)),
                    pressure=int(max((pt.pressure for pt in line.points), default=100)),
                    thickness_scale=line.thickness_scale,
                )
                lines_entry.append((list(line.points), tool, self._affine))

            for highlight in data["highlights"]:
                rects = [
                    si.Rectangle(x=r.x, y=r.y, w=r.w, h=r.h)
                    for r in highlight.rectangles
                ]
                highlights_entry.append((highlight.text or "", highlight.color, rects))

    # --- Layer management ---
    def layer(self, name: str, *, visible: bool = True) -> RemarkableNotebook:
        # visible is currently unused; reserved for future compile mapping
        self._current_layer = name
        self._layer_visibility[name] = visible
        self._lines.setdefault(name, [])
        self._highlights.setdefault(name, [])
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

    # --- Tool presets ---
    def define_preset(
        self,
        name: str,
        *,
        pen: si.Pen,
        color: si.PenColor = si.PenColor.BLACK,
        width: int = 2,
        pressure: int = 100,
        thickness_scale: float = 1.0,
    ) -> RemarkableNotebook:
        """Define or override a tool preset."""
        self._presets[name] = Tool(
            pen=pen,
            color=color,
            width=width,
            pressure=pressure,
            thickness_scale=thickness_scale,
        )
        return self

    def use_preset(self, name: str) -> RemarkableNotebook:
        """Activate a named preset as the current tool."""
        t = self._presets[name]
        self._tool = Tool(
            pen=t.pen,
            color=t.color,
            width=t.width,
            pressure=t.pressure,
            thickness_scale=t.thickness_scale,
        )
        return self

    @contextmanager
    def preset_scope(self, name: str):
        prev = self._tool
        self.use_preset(name)
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

    # --- Turtle aliases / ergonomics ---
    def goto(self, x: float, y: float) -> RemarkableNotebook:
        return self.move_to(x, y)

    def left(self, angle: float) -> RemarkableNotebook:
        return self.rotate(angle)

    def right(self, angle: float) -> RemarkableNotebook:
        return self.rotate(-angle)

    def setheading(self, angle: float) -> RemarkableNotebook:
        """Set absolute heading. Interprets `angle` in deg or rad per current mode."""
        self._heading = (angle * tau / 360 if self._deg else angle) % tau
        return self

    def home(self) -> RemarkableNotebook:
        """Return to origin (0,0) and reset heading to 0. Clears current path."""
        self._x, self._y = 0.0, 0.0
        self._heading = 0.0
        self._path.clear()
        return self

    def set_deg(self, flag: bool) -> RemarkableNotebook:
        """Toggle degree mode for turtle operations and heading display."""
        self._deg = bool(flag)
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
            eff = tool or self._tool
            self._lines.setdefault(self._current_layer, []).append(
                (pts, eff, self._affine)
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
        eff = tool or self._tool
        self._lines.setdefault(self._current_layer, []).append((pts, eff, self._affine))
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
        eff = tool or self._tool
        self._lines.setdefault(self._current_layer, []).append((pts, eff, self._affine))
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
        eff = tool or self._tool
        self._lines.setdefault(self._current_layer, []).append((pts, eff, self._affine))
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
        eff = tool or self._tool
        self._lines.setdefault(self._current_layer, []).append((pts, eff, self._affine))
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
        eff = tool or self._tool
        self._lines.setdefault(self._current_layer, []).append((pts, eff, self._affine))
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
        eff = tool or self._tool
        self._lines.setdefault(self._current_layer, []).append((pts, eff, self._affine))
        return self

    def filled_ellipse(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        *,
        rotation: float = 0.0,
        spacing_factor: float = 0.8,
        tool: Tool | None = None,
    ) -> RemarkableNotebook:
        """Approximate a filled ellipse using horizontal scanlines.

        Draws a set of parallel line segments inside the ellipse, spaced based
        on the effective stroke width times ``spacing_factor`` (default 0.8 to
        provide overlap and avoid gaps).
        """
        import math

        eff = tool or self._tool
        w = float(max(1, eff.width))
        step = max(1.0, w * float(spacing_factor))
        # Number of scanlines across 2*ry; include both ends for full coverage
        n = max(1, int(math.ceil((2.0 * ry) / step)))

        self.tf_push()
        # Apply rotation about center, then translate to (cx, cy)
        if rotation:
            self.tf_rotate(rotation)
        self.tf_translate(cx, cy)
        for i in range(n + 1):
            y = -ry + (2.0 * ry) * (i / n)
            # half-chord at height y inside ellipse: x = ± rx * sqrt(1 - (y/ry)^2)
            t = 1.0 - (y / ry) * (y / ry) if ry != 0 else 0.0
            if t < 0.0:
                continue
            half = rx * math.sqrt(max(0.0, t))
            self.polyline([(-half, y), (half, y)], tool=eff)
        self.tf_pop()
        return self

    def filled_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        spacing_factor: float = 0.25,
        tool: Tool | None = None,
        cross_hatch: bool = False,
    ) -> RemarkableNotebook:
        """Approximate a filled axis-aligned rectangle using scanlines.

        ``spacing_factor`` controls the distance between scanlines as a
        multiple of the effective tool width. Smaller values yield denser
        fills. When ``cross_hatch`` is True a second pass of vertical lines is
        drawn for better coverage.
        """

        import math

        if w <= 0 or h <= 0:
            return self
        eff = tool or self._tool
        sw = float(max(1, eff.width))
        step = max(1.0, sw * float(spacing_factor))

        rows = max(1, int(math.ceil(h / step)))
        for i in range(rows + 1):
            yy = y + (h * (i / rows))
            self.polyline([(x, yy), (x + w, yy)], tool=eff)

        if cross_hatch:
            cols = max(1, int(math.ceil(w / step)))
            for j in range(cols + 1):
                xx = x + (w * (j / cols))
                self.polyline([(xx, y), (xx, y + h)], tool=eff)

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
        eff = tool or self._tool
        self._lines.setdefault(self._current_layer, []).append((pts, eff, self._affine))
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
            layer_objs[name] = nb.create_layer(
                name, visible=self._layer_visibility.get(name, True)
            )
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
        # Reorder header/meta blocks to the front to match device expectations
        hdr: list[Block] = []
        rest: list[Block] = []
        for b in blocks:
            if isinstance(b, AuthorIdsBlock | MigrationInfoBlock | PageInfoBlock):
                hdr.append(b)
            else:
                rest.append(b)
        blocks = hdr + rest

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


# --- Scene inspection helpers ---

JSONPrimitive = str | int | float | bool | None
JSONValue = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]


def _cid_to_json(cid: CrdtId | None) -> JSONValue:
    if cid is None:
        return None
    return {"part1": cid.part1, "part2": cid.part2}


def _cid_to_key(cid: CrdtId | None) -> str:
    if cid is None:
        return "None"
    return f"{cid.part1}:{cid.part2}"


def _lww_to_json(value: LwwValue[Any] | None) -> JSONValue:
    if value is None:
        return None
    return {
        "timestamp": _cid_to_json(value.timestamp),
        "value": scene_to_data(value.value),
    }


def _dataclass_to_dict(obj: Any) -> dict[str, JSONValue]:
    data: dict[str, JSONValue] = {"type": type(obj).__name__}
    for field in fields(obj):
        data[field.name] = scene_to_data(getattr(obj, field.name))
    return data


def scene_to_data(obj: Any) -> JSONValue:
    """Convert a SceneTree or rmscene object into JSON-friendly data."""

    if isinstance(obj, SceneTree):
        return {
            "type": "SceneTree",
            "root": scene_to_data(obj.root),
            "root_text": scene_to_data(obj.root_text) if obj.root_text else None,
        }
    if isinstance(obj, si.Group):
        return {
            "type": "Group",
            "node_id": _cid_to_json(obj.node_id),
            "label": _lww_to_json(obj.label),
            "visible": _lww_to_json(obj.visible),
            "children": [scene_to_data(item) for item in obj.children.sequence_items()],
        }
    if isinstance(obj, CrdtSequenceItem):
        return {
            "type": "CrdtSequenceItem",
            "item_id": _cid_to_json(obj.item_id),
            "left_id": _cid_to_json(obj.left_id),
            "right_id": _cid_to_json(obj.right_id),
            "deleted_length": obj.deleted_length,
            "value": scene_to_data(obj.value),
        }
    if isinstance(obj, CrdtSequence):
        return [scene_to_data(item) for item in obj.sequence_items()]
    if isinstance(obj, si.Line):
        return {
            "type": "Line",
            "tool": obj.tool.name,
            "color": obj.color.name,
            "thickness_scale": obj.thickness_scale,
            "points": [scene_to_data(pt) for pt in obj.points],
        }
    if isinstance(obj, si.Point):
        return {
            "type": "Point",
            "x": obj.x,
            "y": obj.y,
            "speed": obj.speed,
            "direction": obj.direction,
            "width": obj.width,
            "pressure": obj.pressure,
        }
    if isinstance(obj, si.GlyphRange):
        return {
            "type": "GlyphRange",
            "start": obj.start,
            "length": obj.length,
            "text": obj.text,
            "color": obj.color.name,
            "rectangles": [scene_to_data(rect) for rect in obj.rectangles],
        }
    if isinstance(obj, si.Rectangle):
        return {
            "type": "Rectangle",
            "x": obj.x,
            "y": obj.y,
            "w": obj.w,
            "h": obj.h,
        }
    if isinstance(obj, si.Text):
        return {
            "type": "Text",
            "items": scene_to_data(obj.items),
            "styles": {_cid_to_key(k): scene_to_data(v) for k, v in obj.styles.items()},
            "pos_x": obj.pos_x,
            "pos_y": obj.pos_y,
            "width": obj.width,
        }
    if isinstance(obj, LwwValue):
        return _lww_to_json(obj)
    if isinstance(obj, CrdtId):
        return _cid_to_json(obj)
    if isinstance(obj, Enum):
        return obj.name
    if is_dataclass(obj):
        return _dataclass_to_dict(obj)
    if isinstance(obj, dict):
        return {str(key): scene_to_data(value) for key, value in obj.items()}
    if isinstance(obj, Iterable) and not isinstance(obj, str | bytes | bytearray):
        return [scene_to_data(item) for item in obj]
    if isinstance(obj, str | int | float | bool) or obj is None:
        return obj
    return repr(obj)


def scene_to_json(obj: Any, *, indent: int = 2) -> str:
    """Return a JSON string describing the given rmscene structure."""

    return json.dumps(scene_to_data(obj), indent=indent)
