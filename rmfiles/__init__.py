"""rmfiles: helpers for ReMarkable .rm files.

Public API exports a minimal notebook builder.
"""

from .generate import (
    build_rectangle_blocks,
    circle_points,
    create_circle_rm,
    create_rectangle_rm,
    create_triangle_rm,
    rectangle_points,
    triangle_points,
    write_rm,
)
from .notebook import NotebookIdGenerator, NotebookLayer, ReMarkableNotebook, create
from .remarkable import RemarkableNotebook, scene_to_json

__all__ = [
    "create",
    "ReMarkableNotebook",
    "RemarkableNotebook",
    "scene_to_json",
    "NotebookLayer",
    "NotebookIdGenerator",
    "rectangle_points",
    "circle_points",
    "triangle_points",
    "build_rectangle_blocks",
    "write_rm",
    "create_rectangle_rm",
    "create_circle_rm",
    "create_triangle_rm",
]

__version__ = "0.1.0"
