"""Failed historical RGB888 format, retained only for reproducing that result."""

def reference_rgb_frame(pixels: bytes, *, width: int, height: int) -> bytes:
    """The exact 64x16 live RGB888 format from mx2rel/matrix.js.

    Other sizes are deliberately rejected: the fixed header's individual fields
    have not been experimentally varied. This path did not render the diagnostic
    image on the owner's unit; use the verified PNG path for static images.
    """
    if (width, height) != (64, 16):
        raise ValueError("The reference live-frame format is limited to 64x16.")
    if len(pixels) != 64 * 16 * 3:
        raise ValueError("Expected exactly 3072 row-major RGB888 bytes.")
    return bytes.fromhex("090c000000000c0000") + bytes(pixels)
