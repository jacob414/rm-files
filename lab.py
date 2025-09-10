"""
Temporary experiment script to draw a simple rectangle into a .rm file
and then package it into a .rmdoc archive (without committing to repo).

Usage examples:

  # Create both .rm and .rmdoc with defaults
  python lab.py --rm-out output/rect.rm --rmdoc-out output/rect.rmdoc \
                --name "Rectangle Demo"

  # Customize rectangle position/size
  python lab.py --rm-out output/custom.rm --rmdoc-out output/custom.rmdoc \
                --x 200 --y 200 --width 600 --height 400
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

try:
    from uuid import uuid4

    from rmfiles.rmdoc import RmDoc, write_rmdoc
    from rmscene import LwwValue, write_blocks
    from rmscene import scene_items as si
    from rmscene.crdt_sequence import CrdtSequenceItem
    from rmscene.scene_stream import (
        AuthorIdsBlock,
        MigrationInfoBlock,
        PageInfoBlock,
        SceneGroupItemBlock,
        SceneLineItemBlock,
        SceneTreeBlock,
        TreeNodeBlock,
    )
    from rmscene.tagged_block_common import CrdtId
except ModuleNotFoundError as e:
    missing = str(e).split("'")[-2] if "'" in str(e) else str(e)
    print(
        "Dependency missing:",
        missing,
        "\nActivate your venv and install requirements, e.g.:\n"
        "  source .venv/bin/activate\n"
        "  pip install -r requirements.txt\n"
        "or install the package editable (installs deps):\n"
        "  pip install -e .\n",
    )
    raise


def rectangle_points(
    x: float, y: float, w: float, h: float, width: int = 10, pressure: int = 200
) -> list[si.Point]:
    # rectangle path: TL -> TR -> BR -> BL -> TL
    tl = si.Point(x=x, y=y, speed=0, direction=0, width=width, pressure=pressure)
    tr = si.Point(x=x + w, y=y, speed=0, direction=0, width=width, pressure=pressure)
    br = si.Point(
        x=x + w, y=y + h, speed=0, direction=0, width=width, pressure=pressure
    )
    bl = si.Point(x=x, y=y + h, speed=0, direction=0, width=width, pressure=pressure)
    return [tl, tr, br, bl, tl]


def main() -> int:
    p = argparse.ArgumentParser(
        description="Draw a rectangle .rm and package into .rmdoc (using rmscene API)"
    )
    p.add_argument(
        "--rm-out", type=Path, help="Output .rm path", default=Path("output/rect.rm")
    )
    p.add_argument(
        "--rmdoc-out",
        type=Path,
        help="Output .rmdoc path",
        default=Path("output/rect.rmdoc"),
    )
    p.add_argument(
        "--name", default="Rectangle", help="Visible name for the .rmdoc metadata"
    )
    p.add_argument("--x", type=float, default=100.0, help="Top-left X of rectangle")
    p.add_argument("--y", type=float, default=100.0, help="Top-left Y of rectangle")
    p.add_argument("--width", type=float, default=300.0, help="Rectangle width")
    p.add_argument("--height", type=float, default=200.0, help="Rectangle height")
    args = p.parse_args()

    # Build blocks directly via rmscene (mirroring device structure)
    author_uuid = uuid4()

    root_id = CrdtId(0, 1)
    layer_id = CrdtId(0, 11)
    label_ts = CrdtId(0, 12)
    link_item_id = CrdtId(0, 13)
    line_item_id = CrdtId(0, 20)
    line_link_item_id = CrdtId(0, 21)

    # Construct rectangle line
    pts = rectangle_points(args.x, args.y, args.width, args.height)
    line = si.Line(
        color=si.PenColor.BLACK,
        tool=si.Pen.MARKER_1,
        points=pts,
        thickness_scale=2.0,
        starting_length=0.0,
    )

    blocks = []
    # Meta blocks
    blocks.append(AuthorIdsBlock(author_uuids={1: author_uuid}))
    blocks.append(MigrationInfoBlock(migration_id=CrdtId(1, 1), is_device=True))
    blocks.append(
        PageInfoBlock(
            loads_count=1, merges_count=0, text_chars_count=0, text_lines_count=0
        )
    )

    # Scene tree: map layer under root
    blocks.append(
        SceneTreeBlock(
            tree_id=layer_id, node_id=CrdtId(0, 0), is_update=True, parent_id=root_id
        )
    )

    # Root and layer groups
    blocks.append(TreeNodeBlock(si.Group(node_id=root_id)))
    blocks.append(
        TreeNodeBlock(
            si.Group(
                node_id=layer_id, label=LwwValue(timestamp=label_ts, value="Layer 1")
            )
        )
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

    # Add line to layer
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

    # Ensure output dirs exist
    if args.rm_out:
        args.rm_out.parent.mkdir(parents=True, exist_ok=True)
    if args.rmdoc_out:
        args.rmdoc_out.parent.mkdir(parents=True, exist_ok=True)

    # Write .rm to disk (use version similar to lines tests)
    if args.rm_out:
        args.rm_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.rm_out, "wb") as f:
            write_blocks(f, blocks, options={"version": "3.1"})

    # Create .rmdoc from generated rm bytes
    if args.rmdoc_out:
        rm_bytes = Path(args.rm_out).read_bytes()
        doc_id = uuid4().hex
        page_id = uuid4().hex
        doc = RmDoc(doc_id=doc_id, visible_name=args.name, author_uuid=author_uuid)
        doc.add_page(page_id, rm_bytes)
        write_rmdoc(doc, str(args.rmdoc_out))

    print(f"Wrote RM: {args.rm_out}")
    print(f"Wrote RMDOC: {args.rmdoc_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
