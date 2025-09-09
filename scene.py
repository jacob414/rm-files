from manim import (
    BLUE,
    GREEN,
    PI,
    RED,
    RIGHT,
    UP,
    WHITE,
    Circle,
    FadeOut,
    Rotate,
    Scene,
    Square,
    Text,
    Triangle,
    VGroup,
    Write,
)


class Scene(Scene):
    def construct(self):
        # Create a square
        square = Square(side_length=2, color=BLUE)
        self.add(square)

        # Create a circle
        circle = Circle(radius=1.5, color=RED)
        self.add(circle)

        # Create a triangle
        triangle = Triangle(color=GREEN)
        self.add(triangle)

        # Arrange the shapes
        VGroup(square, circle, triangle).arrange(RIGHT, buff=1)

        # Add text
        text = Text("Hello, World!", color=WHITE)
        self.add(text)

        # Animate the text
        self.play(Write(text))
        self.wait(1)
        self.play(FadeOut(text))

        # Animate the shapes
        self.play(Rotate(square, PI / 4))
        self.play(circle.animate.scale(0.5))
        self.play(triangle.animate.shift(UP))

        self.wait(2)
