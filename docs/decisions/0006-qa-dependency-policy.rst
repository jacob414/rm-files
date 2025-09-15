QA Dependency Policy (0006)
===========================

Context
-------

The project’s functionality and tests rely on the external ``rmscene`` package and
other runtime/QA dependencies. In previous iterations, tests could be run without
``rmscene`` by skipping most of the suite, which risks masking regressions.

Decision
--------

- All tests must fail fast if required dependencies are missing. No implicit skips.
- CI and local QA must always install both runtime and QA dependencies before running tests.
- The Makefile invokes a dependency check prior to running tests to ensure nothing is missing.

Consequences
------------

- Developers must run ``make venv && make install-dev`` (or the equivalent) before ``make test``.
- CI uses ``make ci`` which creates a venv, installs runtime deps (``requirements.txt``) and QA deps
  (``requirements-qa.txt``), verifies imports with ``make check-deps``, and then runs the test suite.
- If a dependency like ``rmscene`` is unavailable, tests will fail during collection, preventing
  partial runs that could hide issues.

Implementation Notes
--------------------

- ``Makefile`` provides:

  - ``venv``: create venv and install runtime deps.
  - ``install-dev``: install QA deps.
  - ``check-deps``: import-checks for key modules (``rmscene``, ``numpy``) before running tests.
  - ``test``/``test-quick``: depend on ``check-deps`` so failures surface early.

Testing Utilities
-----------------

- Centralize generalized test helpers in ``rmfiles.testing`` (e.g., canonical line diffing,
  common sample settings like ``SAMPLE_LINE_WIDTH`` and ``SAMPLE_TOOL``).
- Tests, examples, and fixture regeneration scripts should import from ``rmfiles.testing``
  to ensure consistency and avoid duplication.
