"""Quick lab script for exploring rmfiles with rmscene."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequence, CrdtSequenceItem
from rmscene.scene_stream import read_tree
from rmscene.tagged_block_common import CrdtId, LwwValue

SAMPLE_PATH = Path("sample-files/Extracted_RM_file.rm")


def load_scene(path: Path):
    """Return the rmscene SceneTree parsed from `path`."""

    with path.open("rb") as handle:
        return read_tree(handle)


SCALAR_TYPES = (int, float, str, bool, type(None))


def _format_crdt_id(cid: CrdtId | None) -> str:
    if cid is None:
        return "None"
    return f"{cid.part1}:{cid.part2}"


def _format_lww(value: LwwValue[Any] | None) -> str:
    if value is None:
        return "None"
    return repr(value.value)


def _summarize(obj: Any) -> str:
    if isinstance(obj, si.Group):
        label = _format_lww(obj.label)
        visible = _format_lww(obj.visible)
        return (
            f"Group node_id={_format_crdt_id(obj.node_id)} label={label} "
            f"visible={visible}"
        )
    if isinstance(obj, si.Line):
        return (
            f"Line tool={obj.tool.name} color={obj.color.name} "
            f"points={len(obj.points)} thickness_scale={obj.thickness_scale}"
        )
    if isinstance(obj, si.Point):
        return f"Point x={obj.x:.1f} y={obj.y:.1f} w={obj.width} p={obj.pressure}"
    if isinstance(obj, CrdtSequenceItem):
        base = (
            "CrdtSequenceItem "
            f"id={_format_crdt_id(obj.item_id)} "
            f"left={_format_crdt_id(obj.left_id)} "
            f"right={_format_crdt_id(obj.right_id)} "
            f"value={type(obj.value).__name__}"
        )
        if obj.deleted_length:
            base += f" deleted={obj.deleted_length}"
        return base
    if isinstance(obj, CrdtSequence):
        count = sum(1 for _ in obj)
        return f"CrdtSequence(len={count})"
    if isinstance(obj, LwwValue):
        return f"LwwValue[{type(obj.value).__name__}]={obj.value!r}"
    if isinstance(obj, CrdtId):
        return f"CrdtId({_format_crdt_id(obj)})"
    if is_dataclass(obj):
        return type(obj).__name__
    return repr(obj)


def _iter_children(obj: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(obj, si.Group):
        for idx, item in enumerate(obj.children.sequence_items()):
            yield f"child[{idx}]", item
    elif isinstance(obj, CrdtSequence):
        for idx, item in enumerate(obj.sequence_items()):
            yield f"[{idx}]", item
    elif isinstance(obj, CrdtSequenceItem):
        yield "value", obj.value
    elif isinstance(obj, si.Line):
        for idx, point in enumerate(obj.points):
            yield f"point[{idx}]", point
    elif is_dataclass(obj):
        for field in fields(obj):
            val = getattr(obj, field.name)
            if isinstance(val, SCALAR_TYPES):
                continue
            yield field.name, val
    elif isinstance(obj, dict):
        for key, val in obj.items():
            yield f"{key!r}", val
    elif isinstance(obj, Iterable) and not isinstance(obj, str | bytes | bytearray):
        for idx, item in enumerate(obj):
            yield f"[{idx}]", item


def walk(scene_obj: Any, indent: int = 0, label: str | None = None) -> None:
    prefix = "  " * indent
    head = _summarize(scene_obj)
    if label:
        print(f"{prefix}{label}: {head}")
    else:
        print(f"{prefix}{head}")
    for child_label, child in _iter_children(scene_obj):
        if isinstance(child, SCALAR_TYPES):
            print(f"{prefix}  {child_label}: {child!r}")
            continue
        walk(child, indent + 1, child_label)


def main() -> None:
    tree = load_scene(SAMPLE_PATH)
    walk(tree.root)


if __name__ == "__main__":
    main()
