"""Create the small deterministic image used by Lorna2's Moondream2 benchmark."""

from pathlib import Path

from PIL import Image, ImageDraw


output = Path(__file__).with_name("lorna_moondream_fixture.png")
image = Image.new("RGB", (512, 384), "#f4f7fb")
draw = ImageDraw.Draw(image)
draw.rectangle((30, 40, 260, 320), fill="#2674d9")
draw.ellipse((290, 60, 470, 240), fill="#3a9c5d")
draw.polygon([(300, 310), (470, 310), (385, 170)], fill="#d94747")
image.save(output, "PNG", optimize=True)
print(output)
