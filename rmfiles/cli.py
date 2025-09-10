"""
Command-line interface for rmfiles.

This CLI provides minimal commands for creating and inspecting
ReMarkable notebook files. It is intentionally small and will
grow as reading/writing capabilities mature.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _try_import_rmscene():
    """Try to import rmscene helpers needed by this CLI.

    Returns a tuple of imported symbols or None if not available.
    We keep this lazy to allow running non-writing commands without
    requiring optional deps.
    """

    try:
        # Preferred top-level exports
        from rmscene import read_blocks, write_blocks  # type: ignore

        # Classes for optional richer inspection
        from rmscene.scene_stream import (  # type: ignore
            RootTextBlock,
            SceneGroupItemBlock,
            SceneLineItemBlock,
            TreeNodeBlock,
        )

        return (
            read_blocks,
            write_blocks,
            TreeNodeBlock,
            SceneGroupItemBlock,
            SceneLineItemBlock,
            RootTextBlock,
        )
    except Exception:
        return None


def _cmd_new(args: argparse.Namespace) -> int:
    """Create a simple notebook and write it to a .rm file.

    Uses rmfiles.notebook high-level helpers to build a triangle
    on a single layer. More options can be added later.
    """

    try:
        from rmfiles.notebook import create
    except Exception as e:  # pragma: no cover - import error path
        print("Error: failed to import rmfiles.notebook:", e, file=sys.stderr)
        return 2

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    notebook = create()
    layer = notebook.create_layer(args.label, visible=not args.hidden)

    if args.shape == "triangle":
        notebook.create_triangle(
            layer,
            center_x=args.center_x,
            center_y=args.center_y,
            size=args.size,
        )
    else:
        # Future shapes
        pass

    notebook.write(str(out_path))

    if args.verbose:
        size = out_path.stat().st_size
        print(f"Wrote {out_path} ({size} bytes)")

    return 0


def _inspect_with_rmscene(path: Path) -> dict[str, int] | None:
    """If rmscene is available, return richer counts from block types."""

    imported = _try_import_rmscene()
    if not imported:
        return None

    (
        read_blocks,
        _write_blocks,
        TreeNodeBlock,
        SceneGroupItemBlock,
        SceneLineItemBlock,
        RootTextBlock,
    ) = (  # type: ignore
        imported
    )

    counts: dict[str, int] = {
        "blocks": 0,
        "tree_nodes": 0,
        "group_items": 0,
        "line_items": 0,
        "root_text": 0,
    }

    # Only valid for raw .rm files
    if path.suffix.lower() != ".rm":
        return None

    with path.open("rb") as f:
        for block in read_blocks(f):  # type: ignore
            counts["blocks"] += 1
            if isinstance(block, TreeNodeBlock):  # type: ignore
                counts["tree_nodes"] += 1
            elif isinstance(block, SceneGroupItemBlock):  # type: ignore
                counts["group_items"] += 1
            elif isinstance(block, SceneLineItemBlock):  # type: ignore
                counts["line_items"] += 1
            elif isinstance(block, RootTextBlock):  # type: ignore
                counts["root_text"] += 1

    return counts


def _rmdoc_counts(path: Path) -> dict[str, int] | None:
    """Return block counts for the first page inside a .rmdoc, if possible."""
    try:
        from io import BytesIO
        from rmfiles.rmdoc import read_rmdoc
    except Exception:
        return None

    imported = _try_import_rmscene()
    if not imported:
        return None

    read_blocks = imported[0]  # type: ignore[index]

    try:
        doc = read_rmdoc(path)
        if not doc.pages:
            return None
        rm_bytes = doc.pages[0].rm_bytes
    except Exception:
        return None

    counts: dict[str, int] = {
        "blocks": 0,
        "tree_nodes": 0,
        "group_items": 0,
        "line_items": 0,
        "root_text": 0,
    }

    try:
        bio = BytesIO(rm_bytes)
        for block in read_blocks(bio):  # type: ignore
            counts["blocks"] += 1
            # Types are not available here without importing; keep total blocks only
        return counts
    except Exception:
        return None


def _cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect a .rm file and print a small summary.

    If `rmscene` is installed, also print simple block counts.
    """

    path = Path(args.path).expanduser()
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2

    size = path.stat().st_size
    print(f"File: {path}")
    print(f"Size: {size} bytes")

    # Print header bytes for a quick visual check
    with path.open("rb") as f:
        header = f.read(64)
    # Render as ASCII best-effort
    try:
        header_ascii = header.decode("utf-8", errors="ignore")
    except Exception:
        header_ascii = ""
    if header_ascii:
        print(f"Header (ascii): {header_ascii!r}")
    print("Header (hex):", header.hex(" "))

    # Block counts: handle .rm natively and .rmdoc via first page
    counts = _inspect_with_rmscene(path)
    if counts is None and path.suffix.lower() == ".rmdoc":
        counts = _rmdoc_counts(path)
    if counts:
        print(
            "Blocks: {blocks}, TreeNodes: {tree_nodes}, GroupItems: {group_items}, "
            "LineItems: {line_items}, RootText: {root_text}".format(**counts)
        )
    else:
        if args.verbose:
            print(
                "Tip: install 'rmscene' to see parsed block counts.",
                file=sys.stderr,
            )

    # Layers: support both .rm and .rmdoc
    try:
        if path.suffix.lower() == ".rmdoc":
            from rmfiles.rmdoc import read_rmdoc  # lazy import

            doc = read_rmdoc(path)
            print(f"Pages: {len(doc.pages)}")
            for i, page in enumerate(doc.pages, start=1):
                names = [layer.label or "" for layer in page.layers]
                print(f"- Page {i}: layers={len(page.layers)}: {', '.join(names)}")
        elif path.suffix.lower() == ".rm":
            # Parse layers via rmscene if available
            try:
                from rmscene.scene_stream import read_tree  # type: ignore  # noqa: E402,I001
                from rmscene import scene_items as si  # type: ignore  # noqa: E402,I001
            except Exception:
                if args.verbose:
                    print(
                        "Tip: install 'rmscene' to see layer names.",
                        file=sys.stderr,
                    )
            else:
                from io import BytesIO

                try:
                    tree = read_tree(BytesIO(path.read_bytes()))  # type: ignore[arg-type]
                    root = getattr(tree, "root", None)
                    layer_names: list[str] = []
                    if root is not None:
                        for item in root.children.values():
                            if isinstance(item, si.Group):  # type: ignore[attr-defined]
                                label = getattr(item, "label", None)
                                layer_names.append(getattr(label, "value", ""))
                    print(f"Layers: {len(layer_names)}: {', '.join(layer_names)}")
                except Exception:
                    # Non-fatal; keep base info
                    pass
    except Exception:
        # Non-fatal; keep base info
        pass

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rmfiles",
        description=(
            "Small CLI for creating and inspecting ReMarkable .rm files. "
            "Reading/writing capabilities will expand over time."
        ),
    )

    parser.add_argument("--version", action="version", version="rmfiles CLI 0.1.0")

    sub = parser.add_subparsers(dest="command", required=True)

    # new
    p_new = sub.add_parser(
        "new",
        help="Create a simple notebook and write to a .rm file",
    )
    p_new.add_argument("-o", "--out", required=True, help="Output .rm file path")
    p_new.add_argument("--label", default="Layer", help="Layer label")
    p_new.add_argument(
        "--hidden", action="store_true", help="Create layer as hidden (not visible)"
    )
    p_new.add_argument(
        "--shape",
        choices=["triangle"],
        default="triangle",
        help="What to draw in the layer",
    )
    p_new.add_argument("--center-x", type=float, default=200.0)
    p_new.add_argument("--center-y", type=float, default=200.0)
    p_new.add_argument("--size", type=float, default=150.0)
    p_new.add_argument("-v", "--verbose", action="store_true")
    p_new.set_defaults(func=_cmd_new)

    # inspect
    p_inspect = sub.add_parser(
        "inspect", help="Print basic info about a .rm or .rmdoc file"
    )
    p_inspect.add_argument("path", help="Path to .rm file")
    p_inspect.add_argument("-v", "--verbose", action="store_true")
    p_inspect.set_defaults(func=_cmd_inspect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))  # type: ignore[arg-type]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
