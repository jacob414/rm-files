---
title: Regression Tests
---

# Regression Tests

This project uses golden-file regression tests to ensure the geometry emitted by `rmfiles.RemarkableNotebook` stays stable over time.

- Fixtures live in `fixtures/*.rm` and represent known-good `.rm` pages.
- Tests regenerate shapes using the public API, then canonicalize both the new output and the fixture for a stable comparison.
- Canonicalization reduces each line to `(tool_id, color_id, [(x, y), ...])` with points rounded to 4 decimals to avoid floating-point noise.

## Where to look

- Primitive shape regression tests: `tests/test_regression_primitives.py`
- Path (Bezier) regression test: `tests/test_regression_paths.py`
- Fixtures: `fixtures/`

## Running tests

```bash
make venv
source .venv/bin/activate
pytest -q
```

Dependency note:

- The regression tests require the `rmscene` package. If `rmscene` is not installed, the test suite fails during collection. Install all dependencies first using the commands above.

## Updating fixtures

Only update fixtures when a deliberate, vetted change modifies the intended geometry. Steps:

1) Recreate the output using the test’s parameters and write to a temp file (e.g., by locally adjusting the test to write next to the fixture or by running an example script like `examples/primitives_demo.py`).
2) Inspect the difference by opening both `.rm` files in a viewer and/or by using the canonical diff helpers from tests.
3) If the change is intentional, replace the corresponding file in `fixtures/` and commit with a clear message (include rationale in the PR).

Guidelines:

- Do not update fixtures to paper over bugs; fix the code instead.
- Keep the scene tool and color consistent across fixture and test (tests usually rely on defaults or explicitly set a preset/tool for determinism).
- This project standardizes on a stroke width of 24 for regression fixtures to keep shapes visually clear and to avoid ambiguity. The regeneration script and example code use `width=24` accordingly.

## Regenerating all fixtures

- Use the helper script to regenerate the exact fixtures used by tests:

```bash
make fixtures-rebuild
```

This runs `scripts/regenerate_regression_fixtures.py` and writes the golden `.rm` files into `fixtures/`.

## Adding a new regression test

1) Create a fixture: generate the `.rm` you expect via the public API and save it under `fixtures/<name>_fixture.rm`.
2) Write a test in `tests/` that regenerates the same content and compares canonicalized lines from the new file vs. the fixture.
3) Keep inputs explicit (e.g., set `deg=True`, sample counts, and tool/preset when relevant) to avoid accidental changes.
