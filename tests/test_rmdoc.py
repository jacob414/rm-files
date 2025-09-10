"""Tests for the rmfiles.rmdoc subpackage."""

from __future__ import annotations

import zipfile
from pathlib import Path

from rmfiles.rmdoc import RmDoc, from_notebook, read_rmdoc, write_rmdoc


def test_read_sample_rmdoc():
    sample = Path("sample-files/Sample.rmdoc")
    assert sample.exists(), "Sample.rmdoc must exist for this test"

    doc = read_rmdoc(sample)

    # Basic structure
    assert isinstance(doc, RmDoc)
    assert doc.doc_id
    assert doc.visible_name == "Sample"
    assert isinstance(doc.content, dict)
    assert isinstance(doc.metadata, dict)

    # Pages parsed
    assert len(doc.pages) == 1
    p = doc.pages[0]
    assert p.page_id
    assert p.rm_bytes and isinstance(p.rm_bytes, bytes | bytearray)

    # Layers parsed (at least one layer expected)
    assert isinstance(p.layers, list)
    assert len(p.layers) >= 1
    first_layer = p.layers[0]
    assert hasattr(first_layer, "node_id")
    assert isinstance(first_layer.label, str)
    assert isinstance(first_layer.visible, bool)

    # .rm header contains "reMarkable"
    assert b"reMarkable" in p.rm_bytes[:64]

    # pageCount in content matches
    assert doc.content.get("pageCount") == len(doc.pages)


def test_write_single_page_rmdoc(tmp_path: Path):
    # Build a simple .rm page via notebook helper
    from rmfiles.notebook import create

    nb = create()
    layer = nb.create_layer("Test Layer")
    nb.create_triangle(layer, center_x=150, center_y=150, size=100)

    rmd = from_notebook(nb, visible_name="Triangle")
    out = tmp_path / "triangle.rmdoc"
    write_rmdoc(rmd, out)

    # Validate ZIP structure
    assert out.exists()
    with zipfile.ZipFile(out, "r") as z:
        names = z.namelist()
        assert f"{rmd.doc_id}.content" in names
        assert f"{rmd.doc_id}.metadata" in names
        # One page .rm under dir
        rm_names = [
            n for n in names if n.startswith(f"{rmd.doc_id}/") and n.endswith(".rm")
        ]
        assert len(rm_names) == 1

        # Read header
        rm_bytes = z.read(rm_names[0])
        assert b"reMarkable" in rm_bytes[:64]

    # Read back via API
    doc2 = read_rmdoc(out)
    assert doc2.visible_name == "Triangle"
    assert len(doc2.pages) == 1
    assert doc2.content.get("pageCount") == 1
