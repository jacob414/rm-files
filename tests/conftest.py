from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def ensure_rmscene_available() -> None:
    """Fail the run immediately when rmscene is missing."""
    try:
        __import__("rmscene")
    except ModuleNotFoundError as exc:  # pragma: no cover - guard path
        msg = (
            "Missing dependency: rmscene. Install with 'pip install -r requirements.txt' "
            "or 'pip install rmscene==0.7.0' before running QA."
        )
        raise pytest.UsageError(msg) from exc


@pytest.fixture(autouse=True, scope="session")
def ensure_sample_triangle() -> None:
    """Ensure sample-files/triangel.rm exists for CLI tests.

    The repository ignores *.rm files, so CI needs to generate this artifact
    on the fly before tests that expect it.
    """
    path = Path("sample-files/triangel.rm")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    # Try the generate helper first
    try:
        from rmfiles.generate import create_triangle_rm

        create_triangle_rm(str(path))
        return
    except Exception:
        pass
    # Fallback to notebook API
    try:
        from rmfiles.notebook import create

        nb = create()
        layer = nb.create_layer("Layer 1")
        nb.create_triangle(layer, center_x=150, center_y=150, size=100)
        nb.write(str(path))
    except Exception:
        # Leave creation to Makefile pre-step or fail in tests if still missing
        return
