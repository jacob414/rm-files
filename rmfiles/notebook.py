"""
ReMarkable notebook creation module.

This module provides functionality to create in-memory ReMarkable notebook objects
that can be used to build .rm files programmatically.
"""

# isort: skip_file

from uuid import UUID, uuid4

from rmscene import LwwValue, write_blocks
from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequenceItem
from rmscene.scene_stream import (
    Block,
    AuthorIdsBlock,
    MigrationInfoBlock,
    PageInfoBlock,
    SceneGroupItemBlock,
    SceneLineItemBlock,
    SceneGlyphItemBlock,
    SceneTreeBlock,
    TreeNodeBlock,
)
from rmscene.tagged_block_common import CrdtId


class NotebookIdGenerator:
    """Generator for unique CRDT IDs in a notebook."""

    def __init__(self, start_id: int = 2):
        self.current_id = start_id

    def next_id(self) -> CrdtId:
        """Generate the next unique CRDT ID."""
        crdt_id = CrdtId(0, self.current_id)
        self.current_id += 1
        return crdt_id


class NotebookLayer:
    """Represents a layer in a ReMarkable notebook."""

    def __init__(self, layer_id: CrdtId, label: str = "Layer", visible: bool = True):
        self.layer_id = layer_id
        self.label = label
        self.visible = visible
        self.lines: list[si.Line] = []
        self.line_ids: list[CrdtId] = []
        self.glyphs: list[si.GlyphRange] = []
        self.glyph_ids: list[CrdtId] = []

    def add_line(self, line: si.Line, line_id: CrdtId) -> None:
        """Add a line to this layer."""
        self.lines.append(line)
        self.line_ids.append(line_id)

    def add_glyph(self, glyph: si.GlyphRange, glyph_id: CrdtId) -> None:
        """Add a glyph highlight to this layer."""
        self.glyphs.append(glyph)
        self.glyph_ids.append(glyph_id)


class ReMarkableNotebook:
    """
    In-memory representation of a ReMarkable notebook.

    This class provides a high-level interface for creating and manipulating
    ReMarkable notebook content before writing to .rm files.
    """

    def __init__(self):
        self.id_generator = NotebookIdGenerator()
        self.root_id = CrdtId(0, 1)
        self.layers: list[NotebookLayer] = []
        # Keep a stable author UUID for this notebook instance so it
        # can be mirrored in .rmdoc metadata.
        self.author_uuid: UUID = uuid4()

    def create_layer(self, label: str = "Layer", visible: bool = True) -> NotebookLayer:
        """Create a new layer in the notebook."""
        layer_id = self.id_generator.next_id()
        layer = NotebookLayer(layer_id, label, visible)
        self.layers.append(layer)
        return layer

    def add_line_to_layer(
        self,
        layer: NotebookLayer,
        points: list[si.Point],
        color: si.PenColor = si.PenColor.BLACK,
        tool: si.Pen = si.Pen.BALLPOINT_1,
        thickness_scale: float = 1.0,
    ) -> si.Line:
        """Add a line to the specified layer."""
        line_id = self.id_generator.next_id()
        line = si.Line(
            color=color,
            tool=tool,
            points=points,
            thickness_scale=thickness_scale,
            starting_length=0.0,
        )
        layer.add_line(line, line_id)
        return line

    def add_highlight_to_layer(
        self,
        layer: NotebookLayer,
        *,
        text: str,
        color: si.PenColor = si.PenColor.YELLOW,
        rectangles: list[si.Rectangle] | None = None,
        start: int | None = None,
        length: int | None = None,
    ) -> si.GlyphRange:
        """Add a text highlight (GlyphRange) to a layer."""
        if rectangles is None:
            rectangles = []
        if length is None:
            length = len(text)
        glyph_id = self.id_generator.next_id()
        glyph = si.GlyphRange(
            start=start, length=length, text=text, color=color, rectangles=rectangles
        )
        layer.add_glyph(glyph, glyph_id)
        return glyph

    def create_triangle(
        self,
        layer: NotebookLayer,
        center_x: float = 200.0,
        center_y: float = 200.0,
        size: float = 150.0,
    ) -> si.Line:
        """Create a triangle shape in the specified layer."""
        # Calculate triangle points
        points = [
            si.Point(
                x=center_x,
                y=center_y - size / 2,
                speed=0,
                direction=0,
                width=2,
                pressure=100,
            ),
            si.Point(
                x=center_x - size / 2,
                y=center_y + size / 2,
                speed=0,
                direction=0,
                width=2,
                pressure=100,
            ),
            si.Point(
                x=center_x + size / 2,
                y=center_y + size / 2,
                speed=0,
                direction=0,
                width=2,
                pressure=100,
            ),
            si.Point(
                x=center_x,
                y=center_y - size / 2,
                speed=0,
                direction=0,
                width=2,
                pressure=100,
            ),  # Close the triangle
        ]
        return self.add_line_to_layer(layer, points)

    def to_blocks(self) -> list[Block]:
        """Convert the notebook to rmscene blocks for writing to .rm file."""
        blocks: list[Block] = []

        # Create root group (scene tree root)
        root_group = si.Group(node_id=self.root_id)
        blocks.append(TreeNodeBlock(root_group))

        # Header/meta blocks that real files typically include
        blocks.append(AuthorIdsBlock(author_uuids={1: self.author_uuid}))
        blocks.append(MigrationInfoBlock(migration_id=CrdtId(1, 1), is_device=True))
        blocks.append(
            PageInfoBlock(
                loads_count=1, merges_count=0, text_chars_count=0, text_lines_count=0
            )
        )

        # Process each layer
        for layer in self.layers:
            # Add tree mapping for this layer (parent: root)
            blocks.append(
                SceneTreeBlock(
                    tree_id=layer.layer_id,
                    node_id=CrdtId(0, 0),
                    is_update=True,
                    parent_id=self.root_id,
                )
            )
            # Create layer group with label and visibility
            layer_label_id = self.id_generator.next_id()
            layer_label = LwwValue(timestamp=layer_label_id, value=layer.label)
            visibility_id = self.id_generator.next_id()
            visible = LwwValue(timestamp=visibility_id, value=layer.visible)

            layer_group = si.Group(
                node_id=layer.layer_id, label=layer_label, visible=visible
            )
            blocks.append(TreeNodeBlock(layer_group))

            # Link layer to root
            group_item_id = self.id_generator.next_id()
            group_item = CrdtSequenceItem(
                item_id=group_item_id,
                left_id=CrdtId(0, 0),
                right_id=CrdtId(0, 0),
                deleted_length=0,
                value=layer.layer_id,
            )
            group_block = SceneGroupItemBlock(parent_id=self.root_id, item=group_item)
            blocks.append(group_block)

            # Add lines to layer
            for line, line_id in zip(layer.lines, layer.line_ids, strict=True):
                # Create line sequence item
                line_seq_item = CrdtSequenceItem(
                    item_id=line_id,
                    left_id=CrdtId(0, 0),
                    right_id=CrdtId(0, 0),
                    deleted_length=0,
                    value=line,
                )

                # Create line block
                line_block = SceneLineItemBlock(
                    parent_id=layer.layer_id, item=line_seq_item
                )
                blocks.append(line_block)

                # Link line to layer
                line_group_item_id = self.id_generator.next_id()
                line_group_item = CrdtSequenceItem(
                    item_id=line_group_item_id,
                    left_id=CrdtId(0, 0),
                    right_id=CrdtId(0, 0),
                    deleted_length=0,
                    value=line_id,
                )
                line_group_block = SceneGroupItemBlock(
                    parent_id=layer.layer_id, item=line_group_item
                )
                blocks.append(line_group_block)

            # Add glyphs (highlights) to layer
            for glyph, glyph_id in zip(layer.glyphs, layer.glyph_ids, strict=True):
                glyph_seq_item = CrdtSequenceItem(
                    item_id=glyph_id,
                    left_id=CrdtId(0, 0),
                    right_id=CrdtId(0, 0),
                    deleted_length=0,
                    value=glyph,
                )
                glyph_block = SceneGlyphItemBlock(
                    parent_id=layer.layer_id, item=glyph_seq_item
                )
                blocks.append(glyph_block)
                # Link glyph id to layer's children
                glyph_group_item_id = self.id_generator.next_id()
                glyph_group_item = CrdtSequenceItem(
                    item_id=glyph_group_item_id,
                    left_id=CrdtId(0, 0),
                    right_id=CrdtId(0, 0),
                    deleted_length=0,
                    value=glyph_id,
                )
                glyph_group_block = SceneGroupItemBlock(
                    parent_id=layer.layer_id, item=glyph_group_item
                )
                blocks.append(glyph_group_block)

        return blocks

    def write(self, filename: str) -> None:
        """
        Write the notebook to a ReMarkable .rm file.

        Args:
            filename: Path to the output .rm file

        Example:
            >>> notebook = create()
            >>> layer = notebook.create_layer("My Layer")
            >>> notebook.create_triangle(layer)
            >>> notebook.write("my_drawing.rm")
        """
        blocks = self.to_blocks()
        with open(filename, "wb") as f:
            write_blocks(f, blocks)


def create() -> ReMarkableNotebook:
    """
    Create a new ReMarkable notebook instance.

    Returns:
        ReMarkableNotebook: A new notebook instance ready for content creation.

    Example:
        >>> notebook = create()
        >>> layer = notebook.create_layer("Drawing Layer")
        >>> notebook.create_triangle(layer)
        >>> blocks = notebook.to_blocks()
    """
    return ReMarkableNotebook()
