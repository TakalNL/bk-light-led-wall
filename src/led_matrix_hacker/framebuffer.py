"""Pillow image preparation independent of Bluetooth and packet framing."""

from PIL import Image, ImageDraw, ImageFont


def to_rgb_bytes(image: Image.Image, *, width: int, height: int) -> bytes:
    """Composite transparency onto black and emit row-major RGB888, without resizing."""
    if image.size != (width, height):
        raise ValueError(f"Expected image dimensions {width}x{height}; got {image.width}x{image.height}.")
    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
    return Image.alpha_composite(background, rgba).convert("RGB").tobytes()


def diagnostic_image(width: int = 64, height: int = 16, *, label: str = "64x16") -> Image.Image:
    """Generate an asymmetric border/label/RGB-bar pattern for the verified grid."""
    if (width, height) != (64, 16):
        raise ValueError("This diagnostic layout is designed for the verified 64x16 grid.")
    if not label or len(label) > 5 or not all(c.isascii() and (c.isalnum() or c == " ") for c in label):
        raise ValueError("Diagnostic label must contain 1..5 ASCII letters, digits or spaces.")
    image = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, height - 1), outline=(96, 96, 96))
    draw.rectangle((0, 0, 2, 2), fill="red")
    draw.rectangle((width - 3, 0, width - 1, 2), fill=(0, 255, 0))
    draw.rectangle((0, height - 3, 2, height - 1), fill="blue")
    draw.rectangle((width - 3, height - 3, width - 1, height - 1), fill="yellow")
    draw.text((5, 2), label, font=ImageFont.load_default(size=10), fill="white")
    for index, color in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255))):
        left = 46 + index * 4
        draw.rectangle((left, 4, left + 2, 11), fill=color)
    return image
