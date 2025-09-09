import rmscene


def main():
    with open("scribbles.rm", "rb") as f:
        data = f.read()

    scene = rmscene.loads(data)
    print(f"Scene version: {scene.version}")
    print(f"Number of layers: {len(scene.layers)}")

    for i, layer in enumerate(scene.layers):
        print(f"Layer {i}:")
        print(f"  Number of strokes: {len(layer.strokes)}")

        for j, stroke in enumerate(layer.strokes):
            print(f"  Stroke {j}:")
            print(f"    Number of points: {len(stroke.points)}")
            print(f"    Pen: {stroke.pen}")
            print(f"    Color: {stroke.color}")
            print(f"    Width: {stroke.width}")


if __name__ == "__main__":
    main()
