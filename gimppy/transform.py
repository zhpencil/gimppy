"""
Transform utilities — extracted from app/core/gimpdrawable-transform.c,
app/core/gimp-transform-utils.c, and libgimpmath/gimpmatrix.c.
Provides geometric transforms and pixel interpolation helpers.
"""

import math
import numpy as np
from typing import Tuple

from .enums import (
    FlipType, RotationType, InterpolationType, TransformResize,
)
from .exceptions import TransformError
from .math_utils import Matrix3


def _bilinear_sample(img: np.ndarray, x: float, y: float) -> np.ndarray:
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    x1, y1 = x0 + 1, y0 + 1
    h, w = img.shape[:2]
    x0c, y0c = max(0, min(x0, w-1)), max(0, min(y0, h-1))
    x1c, y1c = max(0, min(x1, w-1)), max(0, min(y1, h-1))
    dx, dy = x - math.floor(x), y - math.floor(y)
    top = img[y0c, x0c] * (1 - dx) + img[y0c, x1c] * dx
    bot = img[y1c, x0c] * (1 - dx) + img[y1c, x1c] * dx
    return top * (1 - dy) + bot * dy


def _bicubic_sample(img: np.ndarray, x: float, y: float) -> np.ndarray:
    return _bilinear_sample(img, x, y)


def _nearest_sample(img: np.ndarray, x: float, y: float) -> np.ndarray:
    h, w = img.shape[:2]
    ix, iy = int(round(x)), int(round(y))
    ix = max(0, min(ix, w - 1))
    iy = max(0, min(iy, h - 1))
    return img[iy, ix]


def _scale_array(img: np.ndarray, new_width: int, new_height: int,
                 interpolation: str = "cubic") -> np.ndarray:
    h, w = img.shape[:2]
    channels = img.shape[2] if img.ndim == 3 else 1
    result = np.zeros((new_height, new_width, channels), dtype=np.uint8)

    for y in range(new_height):
        for x in range(new_width):
            src_x = x * (w - 1) / max(1, new_width - 1)
            src_y = y * (h - 1) / max(1, new_height - 1)
            if interpolation == "none":
                result[y, x] = _nearest_sample(img, src_x, src_y)
            elif interpolation == "linear":
                result[y, x] = _bilinear_sample(img, src_x, src_y)
            else:
                result[y, x] = _bilinear_sample(img, src_x, src_y)

    return result


def _gaussian_blur_gray(img: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0:
        return img.copy()
    size = int(math.ceil(radius * 3)) * 2 + 1
    sigma = radius / 2
    kernel = np.zeros(size)
    center = size // 2
    for i in range(size):
        kernel[i] = math.exp(-((i - center) ** 2) / (2 * sigma * sigma))
    kernel /= kernel.sum()

    h, w = img.shape
    fimg = img.astype(np.float32)
    temp = np.zeros_like(fimg)
    for y in range(h):
        for x in range(w):
            val = 0.0
            for k in range(size):
                sx = max(0, min(x + k - center, w - 1))
                val += fimg[y, sx] * kernel[k]
            temp[y, x] = val
    result = np.zeros_like(fimg)
    for y in range(h):
        for x in range(w):
            val = 0.0
            for k in range(size):
                sy = max(0, min(y + k - center, h - 1))
                val += temp[sy, x] * kernel[k]
            result[y, x] = val
    return np.clip(result, 0, 255).astype(np.uint8)


def _gaussian_blur_color(img: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0:
        return img.copy()
    channels = img.shape[2]
    result = np.zeros_like(img)
    for c in range(channels):
        result[:, :, c] = _gaussian_blur_gray(img[:, :, c], radius)
    return result


def _dilate_gray(img: np.ndarray, radius: int) -> np.ndarray:
    h, w = img.shape
    result = np.zeros_like(img)
    for y in range(h):
        for x in range(w):
            max_val = 0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx*dx + dy*dy <= radius*radius:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            max_val = max(max_val, int(img[ny, nx]))
            result[y, x] = max_val
    return result


def _erode_gray(img: np.ndarray, radius: int) -> np.ndarray:
    h, w = img.shape
    result = np.zeros_like(img)
    for y in range(h):
        for x in range(w):
            min_val = 255
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx*dx + dy*dy <= radius*radius:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            min_val = min(min_val, int(img[ny, nx]))
            result[y, x] = min_val
    return result


def transform_layer(layer, matrix: Matrix3,
                    interpolation: InterpolationType = InterpolationType.CUBIC,
                    resize: TransformResize = TransformResize.ADJUST) -> None:
    """Apply a 3x3 affine transform matrix to a layer's pixel data."""
    pixels = layer.pixels
    h, w = pixels.shape[:2]
    channels = pixels.shape[2] if pixels.ndim == 3 else 1

    inv = matrix.inverse()

    if resize == TransformResize.ADJUST:
        corners = [
            inv.transform_point(0, 0),
            inv.transform_point(w, 0),
            inv.transform_point(0, h),
            inv.transform_point(w, h),
        ]
        new_corners = [
            matrix.transform_point(0, 0),
            matrix.transform_point(w, 0),
            matrix.transform_point(0, h),
            matrix.transform_point(w, h),
        ]
        min_x = min(c[0] for c in new_corners)
        min_y = min(c[1] for c in new_corners)
        max_x = max(c[0] for c in new_corners)
        max_y = max(c[1] for c in new_corners)
        new_w = max(1, int(math.ceil(max_x - min_x)))
        new_h = max(1, int(math.ceil(max_y - min_y)))
        offset_x = -min_x
        offset_y = -min_y
    else:
        new_w, new_h = w, h
        offset_x, offset_y = 0, 0

    result = np.zeros((new_h, new_w, channels), dtype=np.uint8)
    if channels == 4:
        result[:, :, 3] = 0

    sample_fn = _bilinear_sample
    if interpolation == InterpolationType.NONE:
        sample_fn = _nearest_sample

    for dy in range(new_h):
        for dx in range(new_w):
            src_x, src_y = inv.transform_point(dx - offset_x, dy - offset_y)
            if 0 <= src_x < w and 0 <= src_y < h:
                result[dy, dx] = sample_fn(pixels, src_x, src_y)

    layer.pixels = result
    layer.width = new_w
    layer.height = new_h


def flip_layer(layer, flip_type: FlipType, axis: float = 0.0,
               clip: bool = True) -> None:
    if flip_type == FlipType.HORIZONTAL:
        layer.pixels = np.fliplr(layer.pixels).copy()
    else:
        layer.pixels = np.flipud(layer.pixels).copy()


def rotate_layer(layer, angle_deg: float,
                 interpolation: InterpolationType = InterpolationType.CUBIC) -> None:
    angle_rad = math.radians(angle_deg)
    matrix = Matrix3.rotate(angle_rad)
    transform_layer(layer, matrix, interpolation, TransformResize.ADJUST)


def scale_layer(layer, new_width: int, new_height: int,
                interpolation: InterpolationType = InterpolationType.CUBIC) -> None:
    layer.pixels = _scale_array(layer.pixels, new_width, new_height,
                                interpolation.value if hasattr(interpolation, 'value') else str(interpolation))
    layer.width = new_width
    layer.height = new_height


def translate_layer(layer, dx: int, dy: int) -> None:
    layer.offset_x += dx
    layer.offset_y += dy


def shear_layer(layer, shear_x: float, shear_y: float) -> None:
    matrix = Matrix3.shear(shear_x, shear_y)
    transform_layer(layer, matrix, InterpolationType.CUBIC, TransformResize.ADJUST)


def perspective_layer(layer, src_corners, dst_corners) -> None:
    matrix = Matrix3.perspective(
        *src_corners[0], *src_corners[1], *src_corners[2], *src_corners[3],
        *dst_corners[0], *dst_corners[1], *dst_corners[2], *dst_corners[3],
    )
    transform_layer(layer, matrix, InterpolationType.CUBIC, TransformResize.ADJUST)


def transform_image_coords(matrix: Matrix3, x: float, y: float) -> Tuple[float, float]:
    return matrix.transform_point(x, y)
