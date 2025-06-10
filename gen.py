from rmscene import write_blocks, LwwValue
from rmscene import scene_items as si
from rmscene.crdt_sequence import CrdtSequenceItem
from rmscene.scene_stream import (
    SceneTreeBlock,
    TreeNodeBlock,
    SceneGroupItemBlock,
    SceneLineItemBlock,
)
from rmscene.tagged_block_common import CrdtId


# Funktion för att generera unika IDs
def get_next_id():
    n = 2  # Börja från 2 eftersom 1 används för root
    while True:
        yield CrdtId(0, n)
        n += 1


id_generator = get_next_id()

# Root node ID
root_id = CrdtId(0, 1)  # Root node ID

# Skapa root node som en Group
root_group = si.Group(node_id=root_id)

# Skapa ett lager (Group)
layer_id = next(id_generator)
layer_label_id = next(id_generator)
layer_label = LwwValue(timestamp=layer_label_id, value="Layer 1")
layer = si.Group(node_id=layer_id,
                 label=layer_label,
                 visible=LwwValue(timestamp=next(id_generator), value=True))

# Definiera punkterna för triangeln med värden inom rätt intervall och som heltal
points = [
    si.Point(
        x=200.0,
        y=50.0,
        speed=int(0),  # Speed som uint16 (0 - 65535)
        direction=int(0),  # Direction som uint16
        width=int(2),  # Width som uint8 (0 - 255)
        pressure=int(100)  # Pressure som uint8
    ),
    si.Point(x=50.0,
             y=350.0,
             speed=int(0),
             direction=int(0),
             width=int(2),
             pressure=int(100)),
    si.Point(x=350.0,
             y=350.0,
             speed=int(0),
             direction=int(0),
             width=int(2),
             pressure=int(100)),
    si.Point(x=200.0,
             y=50.0,
             speed=int(0),
             direction=int(0),
             width=int(2),
             pressure=int(100)),  # Återvänd till startpunkten
]

# Skapa en linje (stroke)
line_id = next(id_generator)
line_item = si.Line(
    color=si.PenColor.BLACK,
    tool=si.Pen.BALLPOINT_1,  # Använd BALLPOINT_1
    points=points,
    thickness_scale=1.0,
    starting_length=0.0,
)

# Skapa en CrdtSequenceItem för linjen
line_seq_item = CrdtSequenceItem(
    item_id=line_id,
    left_id=CrdtId(0, 0),  # Ingen vänster granne
    right_id=CrdtId(0, 0),  # Ingen höger granne
    deleted_length=0,
    value=line_item)

# Skapa en SceneLineItemBlock för linjen
line_block = SceneLineItemBlock(parent_id=layer_id, item=line_seq_item)

# Bygg upp blocken som ska skrivas
blocks = []

# Lägg till root node som TreeNodeBlock
blocks.append(TreeNodeBlock(root_group))

# Lägg till lagret som TreeNodeBlock
blocks.append(TreeNodeBlock(layer))

# Skapa en SceneGroupItemBlock för att länka lagret till root
group_item_id = next(id_generator)
group_item = CrdtSequenceItem(
    item_id=group_item_id,
    left_id=CrdtId(0, 0),  # Ingen vänster granne
    right_id=CrdtId(0, 0),  # Ingen höger granne
    deleted_length=0,
    value=layer_id)
group_block = SceneGroupItemBlock(parent_id=root_id, item=group_item)
blocks.append(group_block)

# Skapa en SceneGroupItemBlock för att länka linjen till lagret
line_group_item_id = next(id_generator)
line_group_item = CrdtSequenceItem(
    item_id=line_group_item_id,
    left_id=CrdtId(0, 0),  # Ingen vänster granne
    right_id=CrdtId(0, 0),  # Ingen höger granne
    deleted_length=0,
    value=line_id)
line_group_block = SceneGroupItemBlock(parent_id=layer_id,
                                       item=line_group_item)
blocks.append(line_group_block)

# Lägg till line_block
blocks.append(line_block)

# Skriv blocken till en fil
with open('triangel.rm', 'wb') as f:
    write_blocks(f, blocks)
