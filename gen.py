from rmscene import Scene, Stroke, Pen

# Create a new scene
scene = Scene()

# Define the rectangle coordinates
x1, y1 = 100, 100
x2, y2 = 400, 300

# Create a new layer
layer = scene.add_layer()

# Create a pen with default settings
pen = Pen()

# Create a stroke for the rectangle
stroke = Stroke([
    (x1, y1),
    (x2, y1),
    (x2, y2),
    (x1, y2),
    (x1, y1)
], pen)

# Add the stroke to the layer
layer.add_stroke(stroke)

# Save the scene to a file named 'sample-output.rm'
scene.save('sample-output.rm')

