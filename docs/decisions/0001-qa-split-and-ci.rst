0001: QA Split, CI, and Docs
===========================

Context
-------
- CI failed due to ``manim``'s system dependency (``pangocairo``) when installed from
  ``requirements.txt``. We also wanted a robust QA pipeline and auto-published docs.

Decision
--------
- Keep runtime dependencies lean in ``requirements.txt`` (no ``manim``).
- Add QA-only dependencies to ``requirements-qa.txt`` (ruff, mypy, pytest-cov, bandit,
  interrogate, pyupgrade, sphinx, myst-parser, RTD theme, pre-commit).
- Keep dev extras (including ``manim``) in ``requirements-dev.txt`` for local usage.
- Make Vulture optional (not in default audit) to avoid false positives early in the project.
- Add pre-commit with ruff+black hooks and run as part of ``make audit``.
- Add Sphinx docs and a GitHub Actions workflow to publish on GitHub Pages.

Consequences
------------
- CI is reliable across environments without needing system packages for manim.
- Developers can opt-in locally to ``manim`` by installing ``requirements-dev.txt``.
- QA is standardized via ``make qa`` and enforced pre-commit hooks.
- Documentation builds and deploys from the main branch.

