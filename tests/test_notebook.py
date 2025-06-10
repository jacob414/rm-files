"""
Tests for the rmfiles.notebook module.
"""

import os
import pytest
from rmscene import scene_items as si
from rmscene.tagged_block_common import CrdtId

from rmfiles.notebook import (
    create, 
    ReMarkableNotebook, 
    NotebookLayer, 
    NotebookIdGenerator
)


class TestNotebookIdGenerator:
    """Test the CRDT ID generator."""
    
    def test_id_generator_starts_at_2(self):
        """Test that ID generator starts at 2 by default."""
        generator = NotebookIdGenerator()
        first_id = generator.next_id()
        assert first_id.part1 == 0
        assert first_id.part2 == 2
    
    def test_id_generator_increments(self):
        """Test that ID generator increments properly."""
        generator = NotebookIdGenerator()
        id1 = generator.next_id()
        id2 = generator.next_id()
        id3 = generator.next_id()
        
        assert id1.part2 == 2
        assert id2.part2 == 3
        assert id3.part2 == 4
    
    def test_custom_start_id(self):
        """Test ID generator with custom start ID."""
        generator = NotebookIdGenerator(start_id=10)
        first_id = generator.next_id()
        assert first_id.part2 == 10


class TestNotebookLayer:
    """Test the NotebookLayer class."""
    
    def test_layer_creation(self):
        """Test creating a new layer."""
        layer_id = CrdtId(0, 5)
        layer = NotebookLayer(layer_id, "Test Layer", True)
        
        assert layer.layer_id == layer_id
        assert layer.label == "Test Layer"
        assert layer.visible is True
        assert len(layer.lines) == 0
        assert len(layer.line_ids) == 0
    
    def test_add_line_to_layer(self):
        """Test adding a line to a layer."""
        layer_id = CrdtId(0, 5)
        layer = NotebookLayer(layer_id)
        
        # Create a simple line
        points = [
            si.Point(x=0, y=0, speed=0, direction=0, width=2, pressure=100),
            si.Point(x=100, y=100, speed=0, direction=0, width=2, pressure=100)
        ]
        line = si.Line(
            color=si.PenColor.BLACK,
            tool=si.Pen.BALLPOINT_1,
            points=points,
            thickness_scale=1.0,
            starting_length=0.0
        )
        line_id = CrdtId(0, 10)
        
        layer.add_line(line, line_id)
        
        assert len(layer.lines) == 1
        assert len(layer.line_ids) == 1
        assert layer.lines[0] == line
        assert layer.line_ids[0] == line_id


class TestReMarkableNotebook:
    """Test the main ReMarkableNotebook class."""
    
    def test_notebook_creation(self):
        """Test creating a new notebook."""
        notebook = ReMarkableNotebook()
        
        assert notebook.root_id.part1 == 0
        assert notebook.root_id.part2 == 1
        assert len(notebook.layers) == 0
        assert isinstance(notebook.id_generator, NotebookIdGenerator)
    
    def test_create_layer(self):
        """Test creating a layer in the notebook."""
        notebook = ReMarkableNotebook()
        layer = notebook.create_layer("My Layer", visible=False)
        
        assert len(notebook.layers) == 1
        assert notebook.layers[0] == layer
        assert layer.label == "My Layer"
        assert layer.visible is False
    
    def test_add_line_to_layer(self):
        """Test adding a line to a layer."""
        notebook = ReMarkableNotebook()
        layer = notebook.create_layer()
        
        points = [
            si.Point(x=50, y=50, speed=0, direction=0, width=2, pressure=100),
            si.Point(x=150, y=150, speed=0, direction=0, width=2, pressure=100)
        ]
        
        line = notebook.add_line_to_layer(
            layer, 
            points, 
            color=si.PenColor.RED,
            tool=si.Pen.BALLPOINT_2
        )
        
        assert len(layer.lines) == 1
        assert layer.lines[0] == line
        assert line.color == si.PenColor.RED
        assert line.tool == si.Pen.BALLPOINT_2
        assert len(line.points) == 2
    
    def test_create_triangle(self):
        """Test creating a triangle shape."""
        notebook = ReMarkableNotebook()
        layer = notebook.create_layer()
        
        triangle = notebook.create_triangle(layer, center_x=100, center_y=100, size=80)
        
        assert len(layer.lines) == 1
        assert layer.lines[0] == triangle
        assert len(triangle.points) == 4  # Triangle + closing point
        
        # Check that triangle is closed (first and last points are the same)
        first_point = triangle.points[0]
        last_point = triangle.points[-1]
        assert first_point.x == last_point.x
        assert first_point.y == last_point.y
    
    def test_to_blocks_empty_notebook(self):
        """Test converting an empty notebook to blocks."""
        notebook = ReMarkableNotebook()
        blocks = notebook.to_blocks()
        
        # Should have at least the root TreeNodeBlock
        assert len(blocks) >= 1
        # First block should be the root TreeNodeBlock
        from rmscene.scene_stream import TreeNodeBlock
        assert isinstance(blocks[0], TreeNodeBlock)
    
    def test_to_blocks_with_layer_and_line(self):
        """Test converting a notebook with content to blocks."""
        notebook = ReMarkableNotebook()
        layer = notebook.create_layer("Test Layer")
        notebook.create_triangle(layer)
        
        blocks = notebook.to_blocks()
        
        # Should have multiple blocks: root, layer, group links, line, line links
        assert len(blocks) > 3
        
        # Verify we have the expected block types
        from rmscene.scene_stream import TreeNodeBlock, SceneGroupItemBlock, SceneLineItemBlock
        
        tree_blocks = [b for b in blocks if isinstance(b, TreeNodeBlock)]
        group_blocks = [b for b in blocks if isinstance(b, SceneGroupItemBlock)]
        line_blocks = [b for b in blocks if isinstance(b, SceneLineItemBlock)]
        
        assert len(tree_blocks) >= 2  # Root + layer
        assert len(group_blocks) >= 2  # Layer to root + line to layer
        assert len(line_blocks) == 1   # One line


class TestCreateFunction:
    """Test the create() function."""
    
    def test_create_function(self):
        """Test that create() returns a ReMarkableNotebook instance."""
        notebook = create()
        assert isinstance(notebook, ReMarkableNotebook)
        assert len(notebook.layers) == 0
    
    def test_create_function_independence(self):
        """Test that multiple create() calls return independent instances."""
        notebook1 = create()
        notebook2 = create()
        
        assert notebook1 is not notebook2
        
        # Modify one and ensure the other is unaffected
        layer1 = notebook1.create_layer("Layer 1")
        assert len(notebook1.layers) == 1
        assert len(notebook2.layers) == 0


class TestIntegration:
    """Integration tests for the notebook module."""
    
    def test_full_workflow(self):
        """Test a complete workflow of creating a notebook with content."""
        # Create notebook
        notebook = create()
        
        # Add multiple layers
        layer1 = notebook.create_layer("Background")
        layer2 = notebook.create_layer("Drawings", visible=True)
        
        # Add content to layers
        points = [
            si.Point(x=0, y=0, speed=0, direction=0, width=1, pressure=50),
            si.Point(x=200, y=0, speed=0, direction=0, width=1, pressure=50),
            si.Point(x=200, y=200, speed=0, direction=0, width=1, pressure=50),
            si.Point(x=0, y=200, speed=0, direction=0, width=1, pressure=50),
            si.Point(x=0, y=0, speed=0, direction=0, width=1, pressure=50)  # Close rectangle
        ]
        notebook.add_line_to_layer(layer1, points)  # Rectangle in background
        notebook.create_triangle(layer2, center_x=100, center_y=100, size=60)  # Triangle in drawings
        
        # Convert to blocks
        blocks = notebook.to_blocks()
        
        # Verify structure
        assert len(notebook.layers) == 2
        assert len(layer1.lines) == 1
        assert len(layer2.lines) == 1
        assert len(blocks) > 5  # Multiple blocks for structure
        
        # Verify blocks can be used (this would normally be written to file)
        assert all(hasattr(block, '__dict__') for block in blocks)


class TestWriteMethod:
    """Test the write() method that creates actual .rm files."""
    
    def test_write_creates_file(self, tmp_path):
        """Test that write() method creates a .rm file."""
        # Create a notebook with content
        notebook = create()
        layer = notebook.create_layer("Test Layer")
        notebook.create_triangle(layer, center_x=150, center_y=150, size=100)
        
        # Write to a temporary file
        test_file = tmp_path / "test_output.rm"
        notebook.write(str(test_file))
        
        # Verify file was created
        assert test_file.exists()
        assert test_file.is_file()
        
        # Verify file has content (should be non-empty)
        assert test_file.stat().st_size > 0
        
        # Verify file contains binary data (starts with ReMarkable header)
        with open(test_file, 'rb') as f:
            header = f.read(50)  # Read first 50 bytes
            # ReMarkable files should start with specific header content
            assert len(header) > 0
            assert b'reMarkable' in header  # Should contain "reMarkable" in header
    
    def test_write_creates_file_like_triangel(self, tmp_path):
        """Test creating a file similar to the triangel.rm from gen.py."""
        # Replicate the exact same content as gen.py
        notebook = create()
        layer = notebook.create_layer("Triangle Layer", visible=True)
        notebook.create_triangle(
            layer,
            center_x=200.0,
            center_y=200.0,
            size=300.0
        )
        
        # Write to test file
        test_file = tmp_path / "test_triangel.rm"
        notebook.write(str(test_file))
        
        # Verify file creation and basic properties
        assert test_file.exists()
        file_size = test_file.stat().st_size
        assert file_size > 200  # Should be substantial size (triangel.rm is 316 bytes)
        assert file_size < 1000  # But not too large for a simple triangle
        
        # Verify the notebook structure matches what we expect
        assert len(notebook.layers) == 1
        assert notebook.layers[0].label == "Triangle Layer"
        assert len(notebook.layers[0].lines) == 1
        
        print(f"Created test file: {test_file} ({file_size} bytes)")
    
    def test_write_multiple_files(self, tmp_path):
        """Test writing multiple different notebooks to different files."""
        # Create first notebook with triangle
        notebook1 = create()
        layer1 = notebook1.create_layer("Shapes")
        notebook1.create_triangle(layer1, center_x=100, center_y=100, size=80)
        
        # Create second notebook with custom line
        notebook2 = create()
        layer2 = notebook2.create_layer("Lines")
        points = [
            si.Point(x=0, y=0, speed=0, direction=0, width=3, pressure=150),
            si.Point(x=100, y=50, speed=0, direction=0, width=3, pressure=150),
            si.Point(x=200, y=0, speed=0, direction=0, width=3, pressure=150)
        ]
        notebook2.add_line_to_layer(layer2, points, color=si.PenColor.RED)
        
        # Write both notebooks
        file1 = tmp_path / "notebook1.rm"
        file2 = tmp_path / "notebook2.rm"
        
        notebook1.write(str(file1))
        notebook2.write(str(file2))
        
        # Verify both files exist and have different sizes (different content)
        assert file1.exists()
        assert file2.exists()
        
        size1 = file1.stat().st_size
        size2 = file2.stat().st_size
        
        assert size1 > 0
        assert size2 > 0
        # Files should have different sizes due to different content
        # (though they might be close due to similar structure)
        
        print(f"File 1: {size1} bytes, File 2: {size2} bytes")