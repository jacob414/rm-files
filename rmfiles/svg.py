"""SVG export helpers for rmfiles scenes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import svgwrite
from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequenceItem
from rmscene.scene_stream import (
    Block,
    SceneGlyphItemBlock,
    SceneLineItemBlock,
    SceneTreeBlock,
    TreeNodeBlock,
    read_tree,
)
from rmscene.scene_tree import SceneTree
from rmscene.tagged_block_common import LwwValue

from .remarkable import RemarkableNotebook

DEFAULT_PAGE_SIZE = (1404, 1872)


@dataclass
class _LayerExport:
    name: str
    visible: bool
    strokes: list[si.Line]
    highlights: list[si.GlyphRange]


_COLOR_MAP: dict[si.PenColor, str] = {
    si.PenColor.BLACK: "#000000",
    si.PenColor.GRAY: "#7f7f7f",
    si.PenColor.WHITE: "#ffffff",
    si.PenColor.YELLOW: "#f5d90a",
    si.PenColor.GREEN: "#2e7d32",
    si.PenColor.GREEN_2: "#66bb6a",
    si.PenColor.PINK: "#ec407a",
    si.PenColor.RED: "#d32f2f",
    si.PenColor.BLUE: "#1976d2",
    si.PenColor.CYAN: "#00acc1",
    si.PenColor.MAGENTA: "#8e24aa",
    si.PenColor.YELLOW_2: "#fff59d",
    si.PenColor.GRAY_OVERLAP: "#9e9e9e",
    si.PenColor.HIGHLIGHT: "#fff59d",
}


def scene_to_svg(
    obj: Any,
    dest: str | Path,
    *,
    page_size: tuple[float, float] | None = None,
    background: str | None = None,
    include_hidden_layers: bool = False,
    color_map: dict[si.PenColor, str] | None = None,
    stroke_width_scale: float = 0.2,
    highlight_opacity: float = 0.28,
) -> None:
    """Write an SVG representation of *obj*.

    Parameters
    ----------
    obj:
        A `SceneTree`, list of rmscene `Block` objects, or a
        `RemarkableNotebook`.
    dest:
        Output file path.
    page_size:
        Optional `(width, height)` in SVG units. Defaults to the ReMarkable
        page size (1404 x 1872) when not provided.
    background:
        Optional background fill color (CSS value). No background rectangle is
        emitted when omitted.
    include_hidden_layers:
        When false (default) layers marked invisible on the tablet are skipped.
        When true they are kept with `display:none` styling.
    color_map:
        Overrides the default pen color palette.
    stroke_width_scale:
        Multiplier applied to the widest point width within a stroke to derive
        the SVG `stroke-width`.
    highlight_opacity:
        Opacity used for rendered text highlights.
    """

    if isinstance(obj, RemarkableNotebook):
        layers = _collect_layers_from_blocks(obj.compile())
    elif isinstance(obj, Iterable) and not isinstance(
        obj, str | Path | bytes | bytearray
    ):
        blocks = list(obj)
        if blocks and all(isinstance(b, Block) for b in blocks):
            layers = _collect_layers_from_blocks(blocks)
        else:
            tree = _coerce_scene_tree(obj)
            layers = _collect_layers_from_tree(tree)
    else:
        tree = _coerce_scene_tree(obj)
        layers = _collect_layers_from_tree(tree)

    width, height = page_size or DEFAULT_PAGE_SIZE
    palette = {**_COLOR_MAP, **(color_map or {})}

    drawing = svgwrite.Drawing(str(dest), size=(width, height))

    bounds = _compute_bounds(layers)
    if bounds is not None:
        min_x, min_y, max_x, max_y = bounds
        pad = 8.0
        min_x -= pad
        min_y -= pad
        max_x += pad
        max_y += pad
        view_w = max(max_x - min_x, 1.0)
        view_h = max(max_y - min_y, 1.0)
        drawing.viewbox(min_x, min_y, view_w, view_h)
    else:
        drawing.viewbox(0, 0, width, height)

    if background:
        drawing.add(drawing.rect(insert=(0, 0), size=(width, height), fill=background))

    for index, layer in enumerate(layers):
        if not layer.visible and not include_hidden_layers:
            continue

        group_attribs: dict[str, Any] = {"id": f"layer-{index}"}
        if not layer.visible:
            group_attribs["style"] = "display:none"

        svg_group = drawing.g(**group_attribs)
        if layer.name:
            svg_group.set_desc(title=layer.name)

        for line in layer.strokes:
            _add_line(svg_group, drawing, line, palette, stroke_width_scale)

        for highlight in layer.highlights:
            _add_highlight(svg_group, drawing, highlight, palette, highlight_opacity)

        if svg_group.elements:
            drawing.add(svg_group)

    drawing.save()


def _coerce_scene_tree(obj: Any) -> SceneTree:
    if isinstance(obj, SceneTree):
        return obj

    if isinstance(obj, str | Path):
        path = Path(obj)
        with path.open("rb") as handle:
            return read_tree(handle)

    raise TypeError(
        f"Unsupported scene object type for SceneTree conversion: {type(obj)!r}"
    )


def _collect_layers_from_tree(tree: SceneTree) -> list[_LayerExport]:
    layers: list[_LayerExport] = []

    for item in tree.root.children.sequence_items():
        if not isinstance(item, CrdtSequenceItem):
            continue
        group = item.value
        if not isinstance(group, si.Group):
            continue

        name = _lww_value(group.label)
        visible_lww = group.visible
        visible = True if visible_lww is None else bool(_lww_value(visible_lww))

        strokes: list[si.Line] = []
        highlights: list[si.GlyphRange] = []

        for child in group.children.sequence_items():
            value = child.value
            if isinstance(value, si.Line):
                strokes.append(value)
            elif isinstance(value, si.GlyphRange):
                highlights.append(value)

        layers.append(
            _LayerExport(
                name=name if isinstance(name, str) else "",
                visible=visible,
                strokes=strokes,
                highlights=highlights,
            )
        )

    return layers


def _collect_layers_from_blocks(blocks: Iterable[Block]) -> list[_LayerExport]:
    layers_by_id: dict[Any, _LayerExport] = {}
    order: list[Any] = []

    def ensure_layer(node_id: Any) -> _LayerExport:
        if node_id not in layers_by_id:
            layers_by_id[node_id] = _LayerExport("", True, [], [])
            order.append(node_id)
        return layers_by_id[node_id]

    for block in blocks:
        if isinstance(block, SceneTreeBlock):
            ensure_layer(block.tree_id)
        elif isinstance(block, TreeNodeBlock):
            group = block.group
            if isinstance(group, si.Group):
                layer = ensure_layer(group.node_id)
                name = _lww_value(group.label)
                if isinstance(name, str):
                    layer.name = name
                visible = _lww_value(group.visible)
                if visible is not None:
                    layer.visible = bool(visible)
        elif isinstance(block, SceneLineItemBlock):
            target = layers_by_id.get(block.parent_id)
            if target is None:
                target = ensure_layer(block.parent_id)
            target.strokes.append(block.item.value)
        elif isinstance(block, SceneGlyphItemBlock):
            target = layers_by_id.get(block.parent_id)
            if target is None:
                target = ensure_layer(block.parent_id)
            target.highlights.append(block.item.value)

    return [
        layers_by_id[node_id]
        for node_id in order
        if layers_by_id[node_id].strokes or layers_by_id[node_id].highlights
    ]


def _lww_value(value: LwwValue[Any] | None) -> Any:
    if value is None:
        return None
    return getattr(value, "value", None)


def _add_line(
    group: svgwrite.container.Group,
    drawing: svgwrite.Drawing,
    line: si.Line,
    palette: dict[si.PenColor, str],
    stroke_scale: float,
) -> None:
    points = [(pt.x, pt.y) for pt in line.points]
    if len(points) < 2:
        return

    path = drawing.path(fill="none")
    path.push(f"M {points[0][0]:.2f},{points[0][1]:.2f}")
    for x, y in points[1:]:
        path.push(f"L {x:.2f},{y:.2f}")

    color = palette.get(line.color, "#000000")
    path.stroke(color=color, width=_stroke_width(line, stroke_scale))
    path.attribs["stroke-linecap"] = "round"
    path.attribs["stroke-linejoin"] = "round"
    group.add(path)


def _stroke_width(line: si.Line, scale: float) -> float:
    widths = [max(pt.width, 1) for pt in line.points if hasattr(pt, "width")]
    if not widths:
        return 1.0
    return max(widths) * max(scale, 0.01)


def _add_highlight(
    group: svgwrite.container.Group,
    drawing: svgwrite.Drawing,
    highlight: si.GlyphRange,
    palette: dict[si.PenColor, str],
    opacity: float,
) -> None:
    color = palette.get(highlight.color, "#fff59d")
    for rect in highlight.rectangles:
        group.add(
            drawing.rect(
                insert=(rect.x, rect.y),
                size=(rect.w, rect.h),
                fill=color,
                opacity=opacity,
                stroke="none",
            )
        )


def _compute_bounds(
    layers: list[_LayerExport],
) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    for layer in layers:
        for line in layer.strokes:
            for pt in line.points:
                xs.append(pt.x)
                ys.append(pt.y)
        for highlight in layer.highlights:
            for rect in highlight.rectangles:
                xs.extend([rect.x, rect.x + rect.w])
                ys.extend([rect.y, rect.y + rect.h])

    if not xs or not ys:
        return None

    return (min(xs), min(ys), max(xs), max(ys))
