"""
Command-line interface for rmfiles.

This CLI provides minimal commands for creating and inspecting
ReMarkable notebook files. It is intentionally small and will
grow as reading/writing capabilities mature.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
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
        from io import BytesIO  # noqa: I001
        from rmfiles.rmdoc import read_rmdoc  # noqa: I001
    except Exception:
        return None

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
    ) = imported  # type: ignore[misc]

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

    def _silence_rmscene_warnings():
        import logging

        loggers = [
            logging.getLogger("rmscene"),
            logging.getLogger("rmscene.tagged_block_reader"),
        ]
        levels = [lg.level for lg in loggers]
        for lg in loggers:
            lg.setLevel(logging.ERROR)

        class _Guard:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                for lg, level in zip(loggers, levels, strict=False):
                    lg.setLevel(level)
                return False

        return _Guard()

    try:
        bio = BytesIO(rm_bytes)
        with _silence_rmscene_warnings():
            for block in read_blocks(bio):  # type: ignore
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
    except Exception:
        return None


def _parse_rm_header_version(header: bytes) -> int | None:
    """Extract version from the .rm header if present."""
    try:
        s = header.decode("utf-8", errors="ignore")
    except Exception:
        return None
    marker = "reMarkable .lines file, version="
    if marker in s:
        try:
            part = s.split(marker, 1)[1].strip()
            # Version is first integer after marker
            ver_str = "".join(ch for ch in part if ch.isdigit())
            return int(ver_str) if ver_str else None
        except Exception:
            return None
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

    def _humanize_size(n: int) -> str:
        try:
            import humanize  # type: ignore

            return humanize.naturalsize(n, binary=True)
        except Exception:
            # Fallback implementation (binary)
            units = ["bytes", "KiB", "MiB", "GiB", "TiB"]
            size = float(n)
            u = 0
            while size >= 1024.0 and u < len(units) - 1:
                size /= 1024.0
                u += 1
        return f"{int(size)} bytes" if u == 0 else f"{size:.1f} {units[u]}"

    # Inspect .rm files with a focused summary
    if path.suffix.lower() == ".rm":
        humanized = _humanize_size(size)

        with path.open("rb") as f:
            header = f.read(64)
        version = _parse_rm_header_version(header)

        print("-- ReMarkable .rm file --")
        print(f"File: {path}")
        print(f"Size: {humanized}")
        if version is not None:
            print(f"Version: .lines file version {version}")

    else:
        # rmdoc summary with metadata and first-page info
        humanized = _humanize_size(size)

        print("-- ReMarkable .rmdoc file --")
        print(f"File: {path}")
        print(f"Size: {humanized}")

        # Read metadata from archive
        try:
            from rmfiles.rmdoc import read_rmdoc
        except Exception:
            read_rmdoc = None  # type: ignore[assignment]

        doc = None
        if read_rmdoc is not None:
            try:
                doc = read_rmdoc(path)
            except Exception:
                doc = None

        def _fmt_ms(v: object) -> str | None:
            try:
                if isinstance(v, str) and v.isdigit():
                    ms = int(v)
                elif isinstance(v, int | float):
                    ms = int(v)
                else:
                    return None
                dt = datetime.fromtimestamp(ms / 1000.0, tz=UTC)
                return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except Exception:
                return None

        if doc is not None:
            md = doc.metadata if isinstance(doc.metadata, dict) else {}
            name = md.get("visibleName")
            if isinstance(name, str) and name:
                print(f"Name: {name}")
            ct = _fmt_ms(md.get("createdTime"))
            if ct:
                print(f"Created time: {ct}")
            lm = _fmt_ms(md.get("lastModified"))
            if lm:
                print(f"Last modified: {lm}")

    # Block counts: handle .rm natively and .rmdoc via first page
    counts = _inspect_with_rmscene(path)
    if counts is None and path.suffix.lower() == ".rmdoc":
        counts = _rmdoc_counts(path)
    if counts:
        if path.suffix.lower() == ".rm":
            print(f"Blocks: {counts['blocks']}")
            print(f"TreeNodes: {counts['tree_nodes']}")
            print(f"GroupItems: {counts['group_items']}")
            print(f"LineItems: {counts['line_items']}")
            print(f"RootText: {counts['root_text']}")
        else:
            print(f"Blocks: {counts['blocks']}")
            print(f"TreeNodes: {counts['tree_nodes']}")
            print(f"GroupItems: {counts['group_items']}")
            print(f"LineItems: {counts['line_items']}")
            print(f"RootText: {counts['root_text']}")
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
                import logging  # noqa: I001
                from io import BytesIO  # noqa: I001

                # Silence rmscene warnings about unread data in newer formats
                rmscene_loggers = [
                    logging.getLogger("rmscene"),
                    logging.getLogger("rmscene.tagged_block_reader"),
                ]
                levels = [lg.level for lg in rmscene_loggers]
                for lg in rmscene_loggers:
                    lg.setLevel(logging.ERROR)
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
                except Exception as _:
                    # Non-fatal; keep base info
                    layer_names = []
                finally:
                    for lg, level in zip(rmscene_loggers, levels, strict=False):
                        lg.setLevel(level)
    except Exception as _:
        # Non-fatal; keep base info
        return 0

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
