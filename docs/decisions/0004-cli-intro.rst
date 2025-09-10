CLI Introduction (0003-cli-intro)
=================================

Context
-------
We need a small, future-proof command-line tool to create and inspect
ReMarkable ``.rm`` files as the project evolves towards full notebook
read/write support. Users reported difficulty discovering the CLI binary
after activating the project virtualenv.

Decision
--------
Introduce a minimal CLI with two subcommands:

- ``new``: create a simple notebook with a triangle on a single layer and write it to a ``.rm`` file.
- ``inspect``: print basic file info and, if ``rmscene`` is available, block-type counts.

Expose the CLI in two ways:

- Console script via ``setup.py`` entry point: ``rmfiles=rmfiles.cli:main`` (preferred)
- Module execution fallback: ``python -m rmfiles`` (works even without installing console scripts when run from repo root)

Consequences
------------
- Users can immediately run ``python -m rmfiles --help`` within the repo.
- Installing the package in editable mode (``pip install -e .``) provides the ``rmfiles`` binary on ``$PATH``.
- Documented troubleshooting: ensure venv's ``bin`` is first on ``$PATH``, then ``hash -r`` or open a new shell to refresh hashed commands.

