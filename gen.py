from rmscene import Scene, Notebook
import numpy as np

# Create a new scene
scene = Scene(1404, 1872)

# Create a simple geometric figure (e.g., a square)
square_points = np.array([
    [100, 100],
    [100, 200],
    [200, 200],
    [200, 100],
    [100, 100]
])

# Add the square to the scene
scene.add_stroke(square_points, 0, 2)

# Create a new notebook with the scene
notebook = Notebook()
notebook.add_scene(scene)

# Save the notebook to a file
notebook.save("sample-notebook.rm")
