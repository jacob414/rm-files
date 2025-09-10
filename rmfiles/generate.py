"""
Utilities to programmatically generate simple .rm files.

This module exposes helpers to build a minimal reMarkable v6 scene with
stroke data using the `rmscene` library, suitable for experimentation and
further composition.
"""

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

    root_id = CrdtId(0, 1)
    layer_id = CrdtId(0, 11)
    label_ts = CrdtId(0, 12)
    link_item_id = CrdtId(0, 13)
    line_item_id = CrdtId(0, 20)
    line_link_item_id = CrdtId(0, 21)

    pts = rectangle_points(
        x, y, width, height, width=stroke_width, pressure=stroke_pressure
    )
    line = si.Line(
        color=si.PenColor.BLACK,
        tool=si.Pen.MARKER_1,
        points=pts,
        thickness_scale=2.0,
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
