# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an experimental project for working with ReMarkable tablet
line files (.rm format). The main goal is to convert SVG files to .rm
files and optionally insert them into the tablet's file system. This
project uses AI-assisted development, starting with Claude Code.

## Development Environment

### Setup
```bash
# Create and activate virtual environment
make venv
source .venv/bin/activate

# Or manually:
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Clean Environment
```bash
make clean  # Removes .venv directory
```

## Key Dependencies

- **rmscene**: Core library for ReMarkable scene manipulation (installed from GitHub)
- **numpy**: Numerical operations
- **manim**: Mathematical animation engine (used in scene.py)
- **paramiko**: SSH client for tablet communication
- **ipython/ipdb**: Interactive development and debugging

## Architecture

### Core Components

- **gen.py**: Main generator for creating .rm files from geometric shapes. Contains the core logic for:
  - Creating ReMarkable scene structures with proper CRDT (Conflict-free Replicated Data Type) IDs
  - Building scene trees with Groups and Lines
  - Converting geometric data to ReMarkable's internal format

- **scene.py**: Manim-based scene creator for generating mathematical animations and shapes

- **rmfiiles/**: Python package directory (currently empty but structured for future utilities)

### File Format Understanding

The project works with ReMarkable's proprietary .rm format which uses:
- CRDT-based data structures for conflict resolution
- Hierarchical scene trees (Groups containing Lines/Items)
- Specific data types for Points with pressure, speed, direction, and width
- Block-based file structure written with `write_blocks()`

## Testing

```bash
# Run tests (currently minimal - just a placeholder)
source .venv/bin/activate
python -m pytest tests/
```

Note: The test suite is currently minimal with just a placeholder test in `tests/test_tbd.py`.

## Common Development Patterns

### Creating ReMarkable Files
1. Generate unique CRDT IDs using the `get_next_id()` generator
2. Create root Group and layer Groups with proper hierarchy
3. Define geometric Points with required attributes (x, y, speed, direction, width, pressure)
4. Build Line objects with points, color, tool type, and styling
5. Wrap items in CrdtSequenceItem and appropriate Block types
6. Write blocks to .rm file using `write_blocks()`

### Coordinate System
ReMarkable uses a coordinate system where typical values range from 50-400 for visible content on the tablet screen.
