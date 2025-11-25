#!/usr/bin/env python3
"""
Image dithering algorithms for 1bpp conversion.

Inspired by Lopaka's image processing capabilities. Provides high-quality
conversion from grayscale/RGB images to 1-bit monochrome using dithering.
"""

from typing import Tuple, Optional
import sys


def floyd_steinberg_dither(
    pixels: list[list[int]], width: int, height: int, threshold: int = 128
) -> list[list[int]]:
    """
    Apply Floyd-Steinberg dithering to convert grayscale image to 1bpp.

    Floyd-Steinberg error diffusion distributes quantization error to
    neighboring pixels:
        [ ]  X   7/16
       3/16 5/16 1/16

    Args:
        pixels: 2D array of grayscale values (0-255)
        width: Image width
        height: Image height
        threshold: Threshold for black/white decision (default 128)

    Returns:
        2D array of binary values (0 or 255)
    """
    # Create a copy to avoid modifying input
    output = [[pixels[y][x] for x in range(width)] for y in range(height)]

    for y in range(height):
        for x in range(width):
            old_pixel = output[y][x]
            new_pixel = 255 if old_pixel >= threshold else 0
            output[y][x] = new_pixel
            quant_error = old_pixel - new_pixel

            # Distribute error to neighbors
            if x + 1 < width:
                output[y][x + 1] = _clamp(output[y][x + 1] + quant_error * 7 // 16)
            if y + 1 < height:
                if x > 0:
                    output[y + 1][x - 1] = _clamp(
                        output[y + 1][x - 1] + quant_error * 3 // 16
                    )
                output[y + 1][x] = _clamp(output[y + 1][x] + quant_error * 5 // 16)
                if x + 1 < width:
                    output[y + 1][x + 1] = _clamp(
                        output[y + 1][x + 1] + quant_error * 1 // 16
                    )

    return output


def atkinson_dither(
    pixels: list[list[int]], width: int, height: int, threshold: int = 128
) -> list[list[int]]:
    """
    Apply Atkinson dithering (1/8 error distribution, used in early Mac).

    Distributes error to 6 neighbors:
        [ ]  X   1   1
        1   1   1   [ ]

    Args:
        pixels: 2D array of grayscale values (0-255)
        width: Image width
        height: Image height
        threshold: Threshold for black/white decision

    Returns:
        2D array of binary values (0 or 255)
    """
    output = [[pixels[y][x] for x in range(width)] for y in range(height)]

    for y in range(height):
        for x in range(width):
            old_pixel = output[y][x]
            new_pixel = 255 if old_pixel >= threshold else 0
            output[y][x] = new_pixel
            quant_error = old_pixel - new_pixel

            # Distribute 6/8 of error (1/8 each), lose 2/8
            error_eighth = quant_error // 8

            if x + 1 < width:
                output[y][x + 1] = _clamp(output[y][x + 1] + error_eighth)
            if x + 2 < width:
                output[y][x + 2] = _clamp(output[y][x + 2] + error_eighth)

            if y + 1 < height:
                if x > 0:
                    output[y + 1][x - 1] = _clamp(
                        output[y + 1][x - 1] + error_eighth
                    )
                output[y + 1][x] = _clamp(output[y + 1][x] + error_eighth)
                if x + 1 < width:
                    output[y + 1][x + 1] = _clamp(
                        output[y + 1][x + 1] + error_eighth
                    )

            if y + 2 < height:
                output[y + 2][x] = _clamp(output[y + 2][x] + error_eighth)

    return output


def ordered_dither(
    pixels: list[list[int]], width: int, height: int, pattern_size: int = 4
) -> list[list[int]]:
    """
    Apply ordered (Bayer matrix) dithering.

    Uses a threshold matrix for fast, repeatable dithering pattern.
    Good for textures and patterns.

    Args:
        pixels: 2D array of grayscale values (0-255)
        width: Image width
        height: Image height
        pattern_size: Bayer matrix size (2, 4, or 8)

    Returns:
        2D array of binary values (0 or 255)
    """
    # Bayer matrices
    bayer_2x2 = [[0, 2], [3, 1]]

    bayer_4x4 = [
        [0, 8, 2, 10],
        [12, 4, 14, 6],
        [3, 11, 1, 9],
        [15, 7, 13, 5],
    ]

    bayer_8x8 = [
        [0, 32, 8, 40, 2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44, 4, 36, 14, 46, 6, 38],
        [60, 28, 52, 20, 62, 30, 54, 22],
        [3, 35, 11, 43, 1, 33, 9, 41],
        [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47, 7, 39, 13, 45, 5, 37],
        [63, 31, 55, 23, 61, 29, 53, 21],
    ]

    if pattern_size == 2:
        matrix = bayer_2x2
        scale = 4
    elif pattern_size == 8:
        matrix = bayer_8x8
        scale = 64
    else:  # default to 4x4
        matrix = bayer_4x4
        scale = 16

    output = [[0 for _ in range(width)] for _ in range(height)]

    for y in range(height):
        for x in range(width):
            threshold = (matrix[y % pattern_size][x % pattern_size] + 0.5) / scale
            output[y][x] = 255 if pixels[y][x] / 255.0 > threshold else 0

    return output


def rgb_to_grayscale(r: int, g: int, b: int) -> int:
    """
    Convert RGB to grayscale using luminance formula.

    Uses ITU-R BT.601 weights: Y = 0.299R + 0.587G + 0.114B

    Args:
        r, g, b: RGB components (0-255)

    Returns:
        Grayscale value (0-255)
    """
    return int(0.299 * r + 0.587 * g + 0.114 * b)


def image_to_xbm(
    pixels: list[list[int]],
    width: int,
    height: int,
    dither_method: str = "floyd-steinberg",
    threshold: int = 128,
) -> Tuple[int, int, bytes]:
    """
    Convert grayscale image to XBM format with dithering.

    Args:
        pixels: 2D array of grayscale values (0-255)
        width: Image width
        height: Image height
        dither_method: "floyd-steinberg", "atkinson", "ordered", or "threshold"
        threshold: Black/white threshold (default 128)

    Returns:
        Tuple of (width, height, bitmap_data)
    """
    # Apply dithering
    if dither_method == "floyd-steinberg":
        dithered = floyd_steinberg_dither(pixels, width, height, threshold)
    elif dither_method == "atkinson":
        dithered = atkinson_dither(pixels, width, height, threshold)
    elif dither_method == "ordered":
        dithered = ordered_dither(pixels, width, height)
    else:  # threshold
        dithered = [[255 if p >= threshold else 0 for p in row] for row in pixels]

    # Convert to XBM format (LSB first, rows packed)
    bitmap = bytearray()
    for y in range(height):
        for x in range(0, width, 8):
            byte = 0
            for bit in range(8):
                if x + bit < width and dithered[y][x + bit] > 0:
                    byte |= 1 << bit
            bitmap.append(byte)

    return (width, height, bytes(bitmap))


def _clamp(value: float) -> int:
    """Clamp value to 0-255 range."""
    return max(0, min(255, int(value)))


# Demo/test code
def _demo() -> None:
    """Demonstrate dithering with a gradient."""
    try:
        from PIL import Image
    except ImportError:
        print("PIL not available, skipping demo", file=sys.stderr)
        return

    # Create test gradient
    width, height = 64, 64
    pixels = [[x * 255 // (width - 1) for x in range(width)] for _ in range(height)]

    methods = ["threshold", "floyd-steinberg", "atkinson", "ordered"]
    for method in methods:
        print(f"\n{method.upper()} dithering:")
        dithered = (
            floyd_steinberg_dither(pixels, width, height)
            if method == "floyd-steinberg"
            else atkinson_dither(pixels, width, height)
            if method == "atkinson"
            else ordered_dither(pixels, width, height)
            if method == "ordered"
            else [[255 if p >= 128 else 0 for p in row] for row in pixels]
        )

        # Create PIL image and save
        img = Image.new("L", (width, height))
        for y in range(height):
            for x in range(width):
                img.putpixel((x, y), dithered[y][x])

        filename = f"gradient_{method}.png"
        img.save(filename)
        print(f"  Saved: {filename}")


if __name__ == "__main__":
    print("Image Dithering Module")
    print("=" * 50)
    _demo()
