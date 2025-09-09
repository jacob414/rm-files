"""
Triangle generator using the rmfiles.notebook module.

This script creates a ReMarkable file containing a triangle shape using the
high-level notebook API instead of low-level rmscene operations.
"""

import rmfiles.notebook


def main():
    """Generate a triangle in a ReMarkable file using the notebook API."""
    # Create a new notebook
    notebook = rmfiles.notebook.create()

    # Create a layer for our drawing
    layer = notebook.create_layer("Triangle Layer", visible=True)

    # Create a triangle in the center of the page
    # ReMarkable coordinates: typical visible area is roughly 0-400 range
    triangle = notebook.create_triangle(
        layer, center_x=200.0, center_y=200.0, size=300.0  # Make it a decent size
    )

    # Write notebook to file
    output_filename = "triangle.rm"
    notebook.write(output_filename)

    print(f"Generated ReMarkable file: {output_filename}")
    print(f"Notebook contains {len(notebook.layers)} layer(s)")
    print(f"Layer '{layer.label}' contains {len(layer.lines)} line(s)")


if __name__ == "__main__":
    main()
