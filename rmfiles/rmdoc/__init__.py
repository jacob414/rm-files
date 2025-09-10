"""rmfiles.rmdoc: Read/write for .rmdoc archives.

Minimal support to parse and generate reMarkable `.rmdoc` archives.

The `.rmdoc` container is a ZIP file with structure:

- `<doc_id>.content` (JSON)
- `<doc_id>.metadata` (JSON)
- `<doc_id>/` directory containing one or more `<page_id>.rm` files

This module provides:

- `read_rmdoc(path) -> RmDoc` to read archives
- `write_rmdoc(doc, path)` to create archives
- `from_notebook(notebook, visible_name=...) -> RmDoc` convenience builder

It does not validate full reMarkable semantics; it targets simple
round-trips and local inspection for now.
"""

from __future__ import annotations

import json
import logging
import uuid
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass
class Page:
    """A single page entry in an `.rmdoc` archive."""

    page_id: str
    rm_bytes: bytes
    template: str | None = None
    layers: list[LayerInfo] = field(default_factory=list)


@dataclass
class LayerInfo:
    """Simplified layer information parsed from a page's .rm data.

    Only captures id, label, and visibility to keep the model light and
    independent of rmscene internals.
    """

    node_id: tuple[int, int]
    label: str
    visible: bool


@dataclass
class RmDoc:
    """In-memory representation of a `.rmdoc` archive."""

    doc_id: str
    visible_name: str = ""
    author_uuid: UUID | None = None
    content: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    pages: list[Page] = field(default_factory=list)

    def add_page(self, page_id: str, rm_bytes: bytes, template: str | None = None):
        self.pages.append(Page(page_id=page_id, rm_bytes=rm_bytes, template=template))


def _infer_doc_id_from_names(names: list[str]) -> str | None:
    """Return the leading `<doc_id>` from a list of zip names, if consistent."""
    ids: set[str] = set()
    for n in names:
        base = n.split("/", 1)[0]
        if base and (base.endswith(".content") or base.endswith(".metadata")):
            ids.add(base.split(".")[0])
        elif base:
            ids.add(base)
    return ids.pop() if len(ids) == 1 else None


def read_rmdoc(path: str | Path) -> RmDoc:
    """Read a `.rmdoc` zip archive into an `RmDoc` object."""
    zp = Path(path)
    with zipfile.ZipFile(zp, "r") as z:
        names = z.namelist()
        doc_id = _infer_doc_id_from_names(names) or ""

        # Load content and metadata JSON if present
        content_name = f"{doc_id}.content"
        metadata_name = f"{doc_id}.metadata"
        content: dict[str, Any] = {}
        metadata: dict[str, Any] = {}
        if content_name in names:
            content = json.loads(z.read(content_name).decode("utf-8"))
        if metadata_name in names:
            metadata = json.loads(z.read(metadata_name).decode("utf-8"))

        # Visible name from metadata if present
        visible_name = (
            metadata.get("visibleName", "") if isinstance(metadata, dict) else ""
        )

        # Discover pages: files under `<doc_id>/` ending with `.rm`
        pages: list[Page] = []
        prefix = f"{doc_id}/"
        for n in names:
            if not n.startswith(prefix):
                continue
            if not n.endswith(".rm"):
                continue
            page_id = Path(n).stem
            rm_bytes = z.read(n)
            # Attempt to pull template value from content
            template = None
            cp = content.get("cPages")
            if isinstance(cp, dict):
                entries = cp.get("pages")
                if isinstance(entries, list):
                    for e in entries:
                        if isinstance(e, dict) and e.get("id") == page_id:
                            t = e.get("template")
                            if isinstance(t, dict):
                                v = t.get("value")
                                if isinstance(v, str):
                                    template = v
                            break
            layers = _extract_layers_from_rm_bytes(rm_bytes)
            pages.append(
                Page(
                    page_id=page_id,
                    rm_bytes=rm_bytes,
                    template=template,
                    layers=layers,
                )
            )

        # Normalize pageCount if present
        if content and isinstance(content, dict):
            content.setdefault("pageCount", len(pages))

        return RmDoc(
            doc_id=doc_id,
            visible_name=visible_name,
            content=content,
            metadata=metadata,
            pages=pages,
        )


def write_rmdoc(doc: RmDoc, path: str | Path) -> None:
    """Write an `RmDoc` to `.rmdoc` archive at `path`."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc_id = doc.doc_id or str(uuid.uuid4())

    # Prepare JSON content/metadata with minimal fields
    content = dict(doc.content) if doc.content else {}
    cpages = content.setdefault("cPages", {})
    pages_list = []
    total_rm_bytes = 0
    for _i, p in enumerate(doc.pages, start=1):
        entry: dict[str, Any] = {"id": p.page_id}
        # Template: default to "Blank" if not provided, match drawj2d shape
        template_value = p.template if p.template else "Blank"
        entry["template"] = {"timestamp": "1:2", "value": template_value}
        # Fake an index structure similar to sample
        entry.setdefault("idx", {"timestamp": "1:2", "value": "ba"})
        pages_list.append(entry)
        total_rm_bytes += len(p.rm_bytes)
    cpages["pages"] = pages_list
    # Set lastOpened to the first page if missing
    if pages_list:
        cpages.setdefault(
            "lastOpened", {"timestamp": "1:1", "value": pages_list[0]["id"]}
        )
    # Original (-1) like in sample
    cpages.setdefault("original", {"timestamp": "0:0", "value": -1})
    # Map author UUID to id 1 like in sample
    if doc.author_uuid:
        cpages.setdefault(
            "uuids",
            [
                {
                    "first": str(doc.author_uuid),
                    "second": 1,
                }
            ],
        )
    # Provide defaults for fields commonly present
    content.setdefault("coverPageNumber", -1)
    content["fileType"] = content.get("fileType", "notebook")
    content["formatVersion"] = content.get("formatVersion", 2)
    content["pageCount"] = len(doc.pages)
    # Total size in bytes for all page .rm files (string), as seen in samples
    content["sizeInBytes"] = str(total_rm_bytes)
    # Common default layout fields mirrored from sample; safe fallbacks
    content.setdefault("orientation", "portrait")
    content.setdefault("textScale", 1)
    content.setdefault("lineHeight", -1)
    content.setdefault("margins", 125)
    content.setdefault("textAlignment", "justify")
    content.setdefault("zoomMode", "bestFit")
    content.setdefault("pageTags", [])
    content.setdefault("tags", [])
    # Custom zoom defaults
    content.setdefault("customZoomCenterX", 0)
    content.setdefault("customZoomCenterY", 936)
    content.setdefault("customZoomOrientation", "portrait")
    content.setdefault("customZoomPageHeight", 1872)
    content.setdefault("customZoomPageWidth", 1404)
    content.setdefault("customZoomScale", 1)

    metadata = dict(doc.metadata) if doc.metadata else {}
    if doc.visible_name:
        metadata["visibleName"] = doc.visible_name
    metadata.setdefault("type", "DocumentType")
    # Timestamps in milliseconds since epoch
    import time

    now_ms = int(time.time() * 1000)
    metadata.setdefault("createdTime", str(now_ms))
    metadata.setdefault("lastModified", str(now_ms))
    metadata.setdefault("lastOpenedPage", 0)
    metadata.setdefault("lastOpened", str(now_ms))
    metadata.setdefault("new", False)
    metadata.setdefault("parent", "")
    metadata.setdefault("pinned", False)
    metadata.setdefault("source", "")

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr(f"{doc_id}.content", json.dumps(content, indent=4))
        z.writestr(f"{doc_id}.metadata", json.dumps(metadata, indent=4))
        for p in doc.pages:
            z.writestr(f"{doc_id}/{p.page_id}.rm", p.rm_bytes)


def from_notebook(notebook: Any, visible_name: str = "") -> RmDoc:
    """Build an `RmDoc` with a single page from a rmfiles.notebook instance."""
    # Note: avoid importing ``rmscene`` here to keep the dependency optional

    # Render notebook to .rm bytes
    from io import BytesIO

    buf = BytesIO()
    # notebook.write only writes to filename; to avoid fs, we mimic its behavior
    # by calling its public to_blocks and use rmscene.write_blocks directly.
    try:
        blocks = notebook.to_blocks()
        from rmscene import write_blocks  # type: ignore

        write_blocks(buf, blocks)
        rm_bytes = buf.getvalue()
    finally:
        buf.close()

    # Generate ids
    doc_id = str(uuid.uuid4())
    page_id = str(uuid.uuid4())

    # If notebook provides an author uuid, preserve it for .rmdoc content
    author_uuid = getattr(notebook, "author_uuid", None)
    doc = RmDoc(doc_id=doc_id, visible_name=visible_name, author_uuid=author_uuid)
    doc.add_page(page_id=page_id, rm_bytes=rm_bytes)
    return doc


def _extract_layers_from_rm_bytes(rm_bytes: bytes) -> list[LayerInfo]:
    """Parse `.rm` data and return a list of top-level layers.

    Returns an empty list if parsing fails.
    """
    from io import BytesIO

    try:
        from rmscene.scene_stream import read_tree  # type: ignore  # noqa: E402,I001
        from rmscene import scene_items as si  # type: ignore  # noqa: E402,I001
    except Exception:
        # rmscene not available; can't parse layers
        return []

    @contextmanager
    def _silence_rmscene_warnings():
        loggers = [
            logging.getLogger("rmscene"),
            logging.getLogger("rmscene.tagged_block_reader"),
        ]
        levels = [lg.level for lg in loggers]
        for lg in loggers:
            lg.setLevel(logging.ERROR)
        try:
            yield
        finally:
            for lg, level in zip(loggers, levels, strict=False):
                lg.setLevel(level)

    try:
        with _silence_rmscene_warnings():
            tree = read_tree(BytesIO(rm_bytes))
    except Exception:
        return []

    infos: list[LayerInfo] = []
    root = getattr(tree, "root", None)
    if root is None:
        return []

    for item in root.children.values():
        if isinstance(item, si.Group):  # type: ignore[attr-defined]
            node_id = getattr(item, "node_id", None)
            label = getattr(item, "label", None)
            visible = getattr(item, "visible", None)

            # Extract values safely
            label_value = getattr(label, "value", "") if label is not None else ""
            visible_value = (
                getattr(visible, "value", True) if visible is not None else True
            )
            nid = (getattr(node_id, "part1", 0), getattr(node_id, "part2", 0))
            infos.append(
                LayerInfo(node_id=nid, label=label_value, visible=visible_value)
            )

    return infos
