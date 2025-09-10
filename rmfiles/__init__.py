"""rmfiles: helpers for ReMarkable .rm files.

Public API exports a minimal notebook builder.
"""

from .generate import (
    build_rectangle_blocks,
    create_rectangle_rm,
    rectangle_points,
    write_rm,
)
from .notebook import NotebookIdGenerator, NotebookLayer, ReMarkableNotebook, create

__all__ = [
    "create",
    "ReMarkableNotebook",
    "NotebookLayer",
    "NotebookIdGenerator",
    "rectangle_points",
    "build_rectangle_blocks",
    "write_rm",
    "create_rectangle_rm",
]

__version__ = "0.1.0"
