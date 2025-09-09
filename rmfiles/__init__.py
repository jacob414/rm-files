"""rmfiles: helpers for ReMarkable .rm files.

Public API exports a minimal notebook builder.
"""

from .notebook import (
    NotebookIdGenerator,
    NotebookLayer,
    ReMarkableNotebook,
    create,
)

__all__ = [
    "create",
    "ReMarkableNotebook",
    "NotebookLayer",
    "NotebookIdGenerator",
]

__version__ = "0.1.0"
