from __future__ import annotations

import argparse
from pathlib import Path
from uuid import uuid4

from rmscene import LwwValue, write_blocks
from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequenceItem
from rmscene.scene_stream import (
    AuthorIdsBlock,
    SceneGroupItemBlock,
    SceneLineItemBlock,
    SceneTreeBlock,
    TreeNodeBlock,
    MigrationInfoBlock,
    PageInfoBlock,
)
from rmscene.tagged_block_common import CrdtId


def triangle_points(cx: float, cy: float, size: float, *, width: int = 10, pressure: int = 200) -> list[si.Point]:
    h = size
    p1 = si.Point(x=cx, y=cy - h / 2, speed=0, direction=0, width=width, pressure=pressure)
    p2 = si.Point(x=cx - h / 2, y=cy + h / 2, speed=0, direction=0, width=width, pressure=pressure)
    p3 = si.Point(x=cx + h / 2, y=cy + h / 2, speed=0, direction=0, width=width, pressure=pressure)
    return [p1, p2, p3, p1]


def build_line_blocks(points: list[si.Point], *, label: str = "Layer 1"):
    author_uuid = uuid4()
    root_id = CrdtId(0, 1)
    layer_id = CrdtId(0, 11)
    label_ts = CrdtId(0, 12)
    link_item_id = CrdtId(0, 13)
    line_item_id = CrdtId(0, 20)
    line_link_item_id = CrdtId(0, 21)

    line = si.Line(
        color=si.PenColor.BLACK,
        tool=si.Pen.MARKER_1,
        points=points,
        thickness_scale=2.0,
        starting_length=0.0,
    )

    blocks = []
    blocks.append(AuthorIdsBlock(author_uuids={1: author_uuid}))
    blocks.append(MigrationInfoBlock(migration_id=CrdtId(1, 1), is_device=True))
    blocks.append(PageInfoBlock(loads_count=1, merges_count=0, text_chars_count=0, text_lines_count=0))
    blocks.append(SceneTreeBlock(tree_id=layer_id, node_id=CrdtId(0, 0), is_update=True, parent_id=root_id))
    blocks.append(TreeNodeBlock(si.Group(node_id=root_id)))
    blocks.append(TreeNodeBlock(si.Group(node_id=layer_id, label=LwwValue(label_ts, label))))
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
    return blocks


def main() -> int:
    p = argparse.ArgumentParser(description="Create a triangle .rm in ./output")
    p.add_argument("--out", default="output/triangle.rm", help="Output .rm path")
    p.add_argument("--cx", type=float, default=200.0)
    p.add_argument("--cy", type=float, default=200.0)
    p.add_argument("--size", type=float, default=300.0)
    args = p.parse_args()

    pts = triangle_points(args.cx, args.cy, args.size)
    blocks = build_line_blocks(pts)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        write_blocks(f, blocks, options={"version": "3.1"})
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

