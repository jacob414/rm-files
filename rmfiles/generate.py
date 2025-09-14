"""
Utilities to programmatically generate simple .rm files.

This module exposes helpers to build a minimal reMarkable v6 scene with
stroke data using the `rmscene` library, suitable for experimentation and
further composition.
,"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from rmscene import LwwValue, write_blocks
from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequenceItem
from rmscene.scene_stream import (
    AuthorIdsBlock,
    Block,
    MigrationInfoBlock,
    PageInfoBlock,
    SceneGroupItemBlock,
    SceneLineItemBlock,
    SceneTreeBlock,
    TreeNodeBlock,
)
from rmscene.tagged_block_common import CrdtId


def circle_points(
    cx: float,
    cy: float,
    r: float,
    *,
    segments: int = 64,
    width: int = 10,
    pressure: int = 200,
) -> list[si.Point]:
    """Return a closed polyline approximating a circle.

    The first point is appended again to close the path.
    """
    import math

    pts: list[si.Point] = []
    for i in range(segments):
        ang = 2 * math.pi * i / segments
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        pts.append(
            si.Point(x=x, y=y, speed=0, direction=0, width=width, pressure=pressure)
        )
    # Close shape
    if pts:
        pts.append(pts[0])
    return pts


def triangle_points(
    cx: float,
    cy: float,
    size: float,
    *,
    width: int = 10,
    pressure: int = 200,
) -> list[si.Point]:
    """Return a closed triangle polyline (top→bottom-left→bottom-right→top)."""
    h = size
    p1 = si.Point(
        x=cx, y=cy - h / 2, speed=0, direction=0, width=width, pressure=pressure
    )
    p2 = si.Point(
        x=cx - h / 2, y=cy + h / 2, speed=0, direction=0, width=width, pressure=pressure
    )
    p3 = si.Point(
        x=cx + h / 2, y=cy + h / 2, speed=0, direction=0, width=width, pressure=pressure
    )
    return [p1, p2, p3, p1]


def build_line_blocks(
    points: list[si.Point],
    *,
    label: str = "Layer 1",
    author_uuid: UUID | None = None,
    color: si.PenColor = si.PenColor.BLACK,
    tool: si.Pen = si.Pen.MARKER_1,
    thickness_scale: float = 2.0,
) -> tuple[list[Block], UUID]:
    """Construct a minimal scene with a single line stroke from points.

    Returns (blocks, author_uuid).
    """
    if author_uuid is None:
        author_uuid = uuid4()

    root_id = CrdtId(0, 1)
    layer_id = CrdtId(0, 11)
    label_ts = CrdtId(0, 12)
    link_item_id = CrdtId(0, 13)
    line_item_id = CrdtId(0, 20)
    line_link_item_id = CrdtId(0, 21)

    line = si.Line(
        color=color,
        tool=tool,
        points=points,
        thickness_scale=thickness_scale,
        starting_length=0.0,
    )

    blocks: list[Block] = []
    blocks.append(AuthorIdsBlock(author_uuids={1: author_uuid}))
    blocks.append(MigrationInfoBlock(migration_id=CrdtId(1, 1), is_device=True))
    blocks.append(
        PageInfoBlock(
            loads_count=1, merges_count=0, text_chars_count=0, text_lines_count=0
        )
    )
    # Map layer under root in the scene tree
    blocks.append(
        SceneTreeBlock(
            tree_id=layer_id, node_id=CrdtId(0, 0), is_update=True, parent_id=root_id
        )
    )
    # Root and layer groups
    blocks.append(TreeNodeBlock(si.Group(node_id=root_id)))
    blocks.append(
        TreeNodeBlock(si.Group(node_id=layer_id, label=LwwValue(label_ts, label)))
    )
    # Link layer to root
    blocks.append(
        SceneGroupItemBlock(
            parent_id=root_id,
            item=CrdtSequenceItem(
                item_id=link_item_id,
                left_id=CrdtId(0, 0),
                right_id=CrdtId(0, 0),
                deleted_length=0,
                value=layer_id,
            ),
        )
    )
    # Line under layer
    blocks.append(
        SceneLineItemBlock(
            parent_id=layer_id,
            item=CrdtSequenceItem(
                item_id=line_item_id,
                left_id=CrdtId(0, 0),
                right_id=CrdtId(0, 0),
                deleted_length=0,
                value=line,
            ),
        )
    )
    # Link line id to layer's children
    blocks.append(
        SceneGroupItemBlock(
            parent_id=layer_id,
            item=CrdtSequenceItem(
                item_id=line_link_item_id,
                left_id=CrdtId(0, 0),
                right_id=CrdtId(0, 0),
                deleted_length=0,
                value=line_item_id,
            ),
        )
    )

    return blocks, author_uuid


def rectangle_points(
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    width: int = 10,
    pressure: int = 200,
) -> list[si.Point]:
    """Return a closed rectangle polyline (TL→TR→BR→BL→TL)."""
    tl = si.Point(x=x, y=y, speed=0, direction=0, width=width, pressure=pressure)
    tr = si.Point(x=x + w, y=y, speed=0, direction=0, width=width, pressure=pressure)
    br = si.Point(
        x=x + w, y=y + h, speed=0, direction=0, width=width, pressure=pressure
    )
    bl = si.Point(x=x, y=y + h, speed=0, direction=0, width=width, pressure=pressure)
    return [tl, tr, br, bl, tl]


def build_rectangle_blocks(
    *,
    x: float = 100.0,
    y: float = 100.0,
    width: float = 300.0,
    height: float = 200.0,
    label: str = "Layer 1",
    author_uuid: UUID | None = None,
    stroke_width: int = 10,
    stroke_pressure: int = 200,
) -> tuple[list[Block], UUID]:
    """Construct a minimal scene with a single rectangle stroke.

    Returns (blocks, author_uuid).
    """
    if author_uuid is None:
        author_uuid = uuid4()

    pts = rectangle_points(
        x, y, width, height, width=stroke_width, pressure=stroke_pressure
    )
    blocks, _ = build_line_blocks(
        pts,
        label=label,
        author_uuid=author_uuid,
        color=si.PenColor.BLACK,
        tool=si.Pen.MARKER_1,
        thickness_scale=2.0,
    )
    return blocks, author_uuid


def write_rm(path: str, blocks: Iterable[Block], *, version: str = "3.1") -> None:
    """Write the blocks to a .rm file using rmscene.write_blocks."""
    with open(path, "wb") as f:
        write_blocks(f, list(blocks), options={"version": version})


def create_rectangle_rm(
    path: str,
    *,
    x: float = 100.0,
    y: float = 100.0,
    width: float = 300.0,
    height: float = 200.0,
    label: str = "Layer 1",
    version: str = "3.1",
) -> None:
    """Convenience function to build and write a rectangle .rm file."""
    blocks, _ = build_rectangle_blocks(
        x=x, y=y, width=width, height=height, label=label
    )
    write_rm(path, blocks, version=version)


def create_triangle_rm(
    path: str,
    *,
    cx: float = 200.0,
    cy: float = 200.0,
    size: float = 300.0,
    label: str = "Layer 1",
    version: str = "3.1",
) -> None:
    """Convenience function to build and write a triangle .rm file."""
    pts = triangle_points(cx, cy, size)
    blocks, _ = build_line_blocks(pts, label=label)
    write_rm(path, blocks, version=version)


def create_circle_rm(
    path: str,
    *,
    cx: float = 200.0,
    cy: float = 200.0,
    radius: float = 150.0,
    segments: int = 64,
    label: str = "Layer 1",
    version: str = "3.1",
) -> None:
    """Convenience function to build and write a circle .rm file."""
    pts = circle_points(cx, cy, radius, segments=segments)
    blocks, _ = build_line_blocks(pts, label=label)
    write_rm(path, blocks, version=version)
