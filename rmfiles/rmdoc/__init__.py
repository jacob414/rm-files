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

from dataclasses import dataclass, field
from pathlib import Path
import io
import json
import uuid
import zipfile
from typing import Any


@dataclass
class Page:
    """A single page entry in an `.rmdoc` archive."""

    page_id: str
    rm_bytes: bytes
    template: str | None = None


@dataclass
class RmDoc:
    """In-memory representation of a `.rmdoc` archive."""

    doc_id: str
    visible_name: str = ""
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
        visible_name = metadata.get("visibleName", "") if isinstance(metadata, dict) else ""

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
            try:
                cp = content.get("cPages", {})
                entries = cp.get("pages", [])
                for e in entries:
                    if e.get("id") == page_id:
                        t = e.get("template", {}).get("value")
                        if isinstance(t, str):
                            template = t
                        break
            except Exception:
                pass
            pages.append(Page(page_id=page_id, rm_bytes=rm_bytes, template=template))

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
    for i, p in enumerate(doc.pages, start=1):
        entry = {"id": p.page_id}
        if p.template:
            entry["template"] = {"timestamp": "1:1", "value": p.template}
        # Fake an index structure similar to sample
        entry.setdefault("idx", {"timestamp": "1:2", "value": "ba"})
        pages_list.append(entry)
    cpages["pages"] = pages_list
    content["fileType"] = content.get("fileType", "notebook")
    content["formatVersion"] = content.get("formatVersion", 2)
    content["pageCount"] = len(doc.pages)

    metadata = dict(doc.metadata) if doc.metadata else {}
    if doc.visible_name:
        metadata["visibleName"] = doc.visible_name
    metadata.setdefault("type", "DocumentType")

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr(f"{doc_id}.content", json.dumps(content, indent=4))
        z.writestr(f"{doc_id}.metadata", json.dumps(metadata, indent=4))
        for p in doc.pages:
            z.writestr(f"{doc_id}/{p.page_id}.rm", p.rm_bytes)


def from_notebook(notebook: Any, visible_name: str = "") -> RmDoc:
    """Build an `RmDoc` with a single page from a rmfiles.notebook instance."""
    # Defer import to avoid hard dependency from rmdoc to notebook unless used
    try:
        from rmscene.tagged_block_common import CrdtId  # noqa: F401
    except Exception:
        # We don't actually need this import; keeping to signal optional nature
        pass

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

    doc = RmDoc(doc_id=doc_id, visible_name=visible_name)
    doc.add_page(page_id=page_id, rm_bytes=rm_bytes)
    return doc
