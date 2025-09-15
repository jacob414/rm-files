Adopt ``rmscene`` For .rm Read/Write (0005-rmscene-dependency)
==============================================================

Context
-------
Writing modern reMarkable ``.rm`` files (v6) involves a block-based format
with CRDT sequences and tagged blocks (TreeNode, SceneGroupItem, SceneLineItem,
RootText, etc.). Implementing a correct writer is non-trivial and requires a
robust encoder and stable schema knowledge. A prior exploration of a Go
codebase (``rm2pdf``) showed that while it parses v5, its v6 parsing and any
writing are not implemented, making it impractical to base a writer on it.

Decision
--------
Use the Python ``rmscene`` library as the canonical mechanism for reading and
writing ``.rm`` v6 files in this project.

- For generating notebooks/pages, ``rmfiles.notebook`` will build in-memory
  structures and call ``rmscene.write_blocks`` to produce ``.rm`` files.
- For inspection and future read flows, prefer ``rmscene.read_blocks`` and
  higher-level helpers.
- Keep local, minimal helpers only for convenience or data modeling; avoid
  re-implementing block encoders.

Consequences
------------
Positive
^^^^^^^^
- Leverages a maintained, specialized implementation for the v6 format.
- Reduces risk of subtle encoding bugs; faster path to working features.
- Aligns with existing tests and abstractions already using ``rmscene``.

Trade-offs
^^^^^^^^^^
- Introduces a runtime dependency, fetched from GitHub (network access needed).
- Upstream API or behavior changes can affect us if unpinned.
- Developers need a Python environment (already true for this repo).

Guidance For Development
------------------------
- Installation

  - Editable install: ``pip install -e .`` (installs ``rmscene`` from GitHub).
  - Network-restricted environments: pre-install ``rmscene`` from a wheel or
    pin a specific commit/tag in ``setup.py``/``requirements.txt`` as needed.

- Usage patterns

  - Write

    - Build blocks from our in-memory notebook and call
      ``rmscene.write_blocks(binary_io, blocks)``.

  - Read

    - Use ``rmscene.read_blocks(binary_io)`` to iterate blocks, or
      higher-level tree helpers if needed.

- Testing

  - Prefer golden tests using known-good ``.rm`` fixtures.
  - For generation tests, verify file presence, header bytes (``reMarkable``
    string), and basic structure via ``rmscene.read_blocks`` when available.

Follow-ups
----------
- We have pinned ``rmscene==0.7.0`` in ``setup.py`` and ``requirements.txt`` to
  ensure reproducible CI/local installs. Revisit the pin periodically to
  incorporate upstream fixes (consider pinning to a tag/commit if needed).
- Extend CLI with richer inspect commands powered by ``rmscene``.
- Document offline workflows (prebuilt wheels, internal mirrors) if needed.
