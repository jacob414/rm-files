import struct
from io import BytesIO
from rmscene import (
    TaggedBlockWriter,
    SceneTreeBlock,
    SceneLineItemBlock,
    MigrationInfoBlock,
    PageInfoBlock,
    RootTextBlock,
    TreeNodeBlock,
    CrdtId,
    LwwValue,
    write_blocks,
)
from rmscene.tagged_block_common import HEADER_V6
from uuid import UUID
from rmscene.scene_items import Group, Text, ParagraphStyle, Line, Point

# Define a simple line with two points
def create_simple_line():
    return Line(
        points=[
            Point(x=0, y=0, speed=0, width=0, pressure=0.5),
            Point(x=100, y=100, speed=0, width=0, pressure=0.5)
        ],
        pen_type=1,  # Assuming pen type 1 is valid
        color=0,  # Assuming color 0 is black
        unknown_line_attribute=0  # Placeholder for any unknown or additional attributes
    )

def main():
    filename = 'sample-notebook.rm'
    line = create_simple_line()

    with open(filename, 'wb') as f:
        writer = TaggedBlockWriter(f)

        # Write the header
        f.write(HEADER_V6)

        # Create and write a simple scene with one line
        blocks = [
            MigrationInfoBlock(migration_id=CrdtId(1, 1), is_device=True),
            PageInfoBlock(loads_count=1, merges_count=0, text_chars_count=0, text_lines_count=1),
            SceneTreeBlock(
                tree_id=CrdtId(0, 1),
                node_id=CrdtId(0, 0),
                is_update=True,
                parent_id=CrdtId(0, 0),
            ),
            RootTextBlock(
                block_id=CrdtId(0, 0),
                value=Text(
                    items=[],
                    styles={},
                    pos_x=0,
                    pos_y=0,
                    width=0,
                ),
            ),
            TreeNodeBlock(
                group=Group(node_id=CrdtId(0, 0)),
            ),
            SceneLineItemBlock(
                parent_id=CrdtId(0, 0),
                item=line,
            ),
        ]

        # Write the blocks to the file
        write_blocks(f, blocks, options={"version": "3.0"})

if __name__ == '__main__':
    main()
