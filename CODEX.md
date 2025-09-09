** Project Overview**
- Purpose: Tools to create and manipulate ReMarkable “lines” (.rm v6) files.
- Approach: High-level API built on `rmscene` to assemble CRDT-based blocks and write `.rm` files programmatically.
- Status: Test suite passes (18 tests). Generates simple `.rm` pages (e.g., triangle) via `gen.py`.

**Repository Layout**
- `rmfiles/notebook.py`: High-level in-memory notebook builder.
  - `ReMarkableNotebook`, `NotebookLayer`, `NotebookIdGenerator`.
  - Builds scene tree blocks (groups, lines) and writes via `rmscene.write_blocks`.
- `tests/`: Unit and integration tests for the notebook API and write path.
- `gen.py`: Example script generating `triangle.rm` with a triangle shape and writing it via the notebook API.
- `parse_lines.py`: Quick loader/inspector using `rmscene.loads` for an existing `.rm`.
- `tree.py`: SSH-based helper (Paramiko) to list notebooks on device; filters out web-link entries.
- `rmfiles/deps/`: Vendored helpers (`scene_stream.py`, `scene_items.py`) mirroring `rmscene` internals; current code uses upstream `rmscene` imports instead.
- `doc/claude-*.org`, `CLAUDE.md`: Historical notes and prompts from earlier AI-assisted iterations.
- `pyproject.toml`, `requirements.txt`, `Makefile`: Formatting/test config and environment setup.

**Environment & Tooling**
- Python: 3.12 (Makefile uses `python3.12`).
- Setup: `make venv && source .venv/bin/activate && python -m pytest`.
- Formatting: Black (`pyproject.toml` configured, line-length 88).
- Key deps: `rmscene` (installed from GitHub), `numpy`, `manim`, `paramiko`, `pytest`, `black`.

**Notebook API (Summary)**
- IDs: `NotebookIdGenerator` yields `CrdtId(0, n)` starting at `n=2`.
- Structure: Root group `CrdtId(0, 1)`; each layer is a `Group` with label/visibility; lines added under layers.
- Shapes: `create_triangle(layer, center_x, center_y, size)` builds a closed path with `si.Point`s.
- Output: `to_blocks()` assembles `TreeNodeBlock`, `SceneGroupItemBlock`, `SceneLineItemBlock`; `write(filename)` serializes via `rmscene.write_blocks`.

**Tests (Key Expectations)**
- ID sequencing, layer creation, line insertion, triangle closure.
- Block typing/counts for non-empty notebooks.
- `write()` produces a non-empty `.rm` containing expected header bytes (asserts presence of "reMarkable").
- 18 tests pass locally.

**Notable Findings / Cleanup Opportunities**
- Packaging: `setup.py` has a syntax error (missing comma after `author='Jacob Oscarson'`). Not used in tests but should be fixed before packaging.
- Duplication: `tree.py` defines `is_web_link` twice; prefer a single implementation.
- Vendored deps: `rmfiles/deps/` duplicates pieces of `rmscene`; current project imports upstream `rmscene`. Keep vendored code only if you plan to decouple from upstream.
- Naming: `gen.py` writes `triangel.rm` (typo). Consider `triangle.rm` or `sample-notebook.rm` for clarity.

**Common Tasks**
- Run tests: `source .venv/bin/activate && pytest -q`.
- Format: `black .`.
- Generate triangle file: `python gen.py` (produces `triangel.rm`).

**Next Steps (Optional)**
- Add CLI entry point to generate shapes from parameters (size, position, color, tool).
- Add SVG-to-`.rm` conversion outline (stretch goal in README).
- Fix `setup.py`, consolidate `tree.py` helpers, and document device transfer workflow.
