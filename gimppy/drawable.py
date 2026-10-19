"""
Drawable module — extracted from app/core/gimpdrawable.c,
app/core/gimpdrawable-edit.c, app/core/gimpdrawable-fill.c,
app/core/gimpdrawable-bucket-fill.c, app/core/gimpdrawable-gradient.c.
Provides pixel-level operations on layers and channels.
"""

import math
import numpy as np
from typing import Tuple, Optional

from .enums import (
    FillType, GradientType, BlendColorSpace, RepeatMode,
    BucketFillArea,
)
from .exceptions import GimpError


def drawable_fill(layer, fill_type: FillType,
                  color: Tuple[int, ...] = None,
                  pattern: np.ndarray = None) -> None:
    """
    Fill a drawable — extracted from gimpdrawable-fill.c.
    """
    if fill_type == FillType.TRANSPARENT:
        layer.pixels.fill(0)
        if layer.has_alpha:
            layer.pixels[:, :, -1] = 0
    elif fill_type == FillType.WHITE:
        layer.pixels.fill(255)
    elif fill_type == FillType.FOREGROUND:
        c = color or (0, 0, 0)
        for ch in range(min(len(c), layer.pixels.shape[2])):
            layer.pixels[:, :, ch] = c[ch]
        if layer.has_alpha:
            layer.pixels[:, :, -1] = 255
    elif fill_type == FillType.BACKGROUND:
        c = color or (255, 255, 255)
        for ch in range(min(len(c), layer.pixels.shape[2])):
            layer.pixels[:, :, ch] = c[ch]
        if layer.has_alpha:
            layer.pixels[:, :, -1] = 255
    elif fill_type == FillType.PATTERN and pattern is not None:
        ph, pw = pattern.shape[:2]
        if ph > 0 and pw > 0:
            for y in range(layer.height):
                for x in range(layer.width):
                    layer.pixels[y, x] = pattern[y % ph, x % pw]


def drawable_bucket_fill(layer, x: int, y: int,
                         fill_type: FillType = FillType.FOREGROUND,
                         color: Tuple[int, ...] = None,
                         threshold: int = 15,
                         antialias: bool = True,
                         fill_whole: bool = False,
                         sample_merged: bool = False,
                         line_art: bool = False) -> None:
    """
    Bucket fill — extracted from gimpdrawable-bucket-fill.c.
    Fills a region of similar color starting from (x, y).
    """
    if not (0 <= x < layer.width and 0 <= y < layer.height):
        raise GimpError(f"Position ({x}, {y}) out of bounds")

    if fill_whole:
        drawable_fill(layer, fill_type, color)
        return

    target = layer.pixels[y, x].astype(np.float32)
    channels = min(3, layer.pixels.shape[2])
    visited = np.zeros((layer.height, layer.width), dtype=bool)
    fill_color = _get_fill_color(fill_type, color, layer)

    stack = [(x, y)]
    while stack:
        cx, cy = stack.pop()
        if visited[cy, cx]:
            continue
        visited[cy, cx] = True
        diff = np.abs(layer.pixels[cy, cx, :channels].astype(np.float32) - target[:channels])
        if diff.max() <= threshold:
            layer.pixels[cy, cx] = fill_color
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = cx+dx, cy+dy
                if 0 <= nx < layer.width and 0 <= ny < layer.height and not visited[ny, nx]:
                    stack.append((nx, ny))


def _get_fill_color(fill_type, color, layer):
    channels = layer.pixels.shape[2]
    result = np.zeros(channels, dtype=np.uint8)
    if fill_type == FillType.FOREGROUND:
        c = color or (0, 0, 0, 255)
    elif fill_type == FillType.BACKGROUND:
        c = color or (255, 255, 255, 255)
    elif fill_type == FillType.WHITE:
        c = (255,) * channels
    elif fill_type == FillType.PATTERN:
        c = (128,) * channels
    else:
        c = (0,) * channels
    for i in range(min(len(c), channels)):
        result[i] = c[i]
    if layer.has_alpha:
        result[-1] = 255
    return result


def drawable_gradient_fill(layer,
                           gradient_type: GradientType = GradientType.LINEAR,
                           x1: float = 0, y1: float = 0,
                           x2: float = 100, y2: float = 100,
                           color1: Tuple[int, ...] = (0, 0, 0, 255),
                           color2: Tuple[int, ...] = (255, 255, 255, 255),
                           repeat: RepeatMode = RepeatMode.NONE,
                           supersample: bool = False,
                           offset: float = 0.0) -> None:
    """
    Gradient fill — extracted from gimpdrawable-gradient.c.
    Fills the layer with a gradient between two colors.
    """
    c1 = np.array(color1, dtype=np.float32)
    c2 = np.array(color2, dtype=np.float32)
    channels = layer.pixels.shape[2]
    c1 = np.resize(c1, channels)
    c2 = np.resize(c2, channels)

    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx*dx + dy*dy
    if length_sq < 1e-10:
        return

    for py in range(layer.height):
        for px in range(layer.width):
            t = _gradient_factor(gradient_type, px, py, x1, y1, x2, y2)
            t = (t + offset) % 1.0
            if repeat == RepeatMode.TRIANGULAR:
                t = t * 2
                if t > 1:
                    t = 2 - t
            elif repeat == RepeatMode.SAWTOOTH:
                pass
            color = c1 * (1 - t) + c2 * t
            layer.pixels[py, px] = np.clip(color, 0, 255).astype(np.uint8)


def _gradient_factor(gradient_type, px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx*dx + dy*dy

    if gradient_type == GradientType.LINEAR:
        if length_sq < 1e-10:
            return 0
        t = ((px - x1) * dx + (py - y1) * dy) / length_sq
        return max(0, min(1, t))
    elif gradient_type == GradientType.RADIAL:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        max_r = math.sqrt((x2-x1)**2 + (y2-y1)**2) / 2
        if max_r < 1e-10:
            return 0
        dist = math.sqrt((px - cx)**2 + (py - cy)**2)
        return max(0, min(1, dist / max_r))
    elif gradient_type == GradientType.SQUARE:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        half_w = abs(x2 - x1) / 2
        half_h = abs(y2 - y1) / 2
        if half_w < 1e-10 or half_h < 1e-10:
            return 0
        return max(0, min(1, max(abs(px - cx) / half_w, abs(py - cy) / half_h)))
    elif gradient_type == GradientType.CONICAL_SYMMETRIC:
        angle = math.atan2(py - y1, px - x1) / math.pi
        return abs(angle)
    elif gradient_type == GradientType.CONICAL_ASYMMETRIC:
        angle = math.atan2(py - y1, px - x1) / (2 * math.pi) + 0.5
        return angle % 1.0
    elif gradient_type == GradientType.SHAPEBURST_ANGULAR:
        return 0.5
    elif gradient_type == GradientType.SHAPEBURST_SPHERICAL:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        max_r = math.sqrt((x2-x1)**2 + (y2-y1)**2) / 2
        if max_r < 1e-10:
            return 0
        dist = math.sqrt((px-cx)**2 + (py-cy)**2) / max_r
        return max(0, min(1, dist))
    elif gradient_type == GradientType.SPIRAL_CLOCKWISE:
        angle = math.atan2(py - y1, px - x1) / (2 * math.pi) + 0.5
        dist = math.sqrt((px-x1)**2 + (py-y1)**2) / 100
        return (angle + dist) % 1.0
    elif gradient_type == GradientType.SPIRAL_COUNTERCLOCKWISE:
        angle = math.atan2(py - y1, px - x1) / (2 * math.pi) + 0.5
        dist = math.sqrt((px-x1)**2 + (py-y1)**2) / 100
        return (angle - dist) % 1.0
    else:
        if length_sq < 1e-10:
            return 0
        t = ((px - x1) * dx + (py - y1) * dy) / length_sq
        return max(0, min(1, t))


def drawable_edit_clear(layer, selection_mask: np.ndarray = None) -> None:
    """
    Clear — extracted from gimpdrawable-edit.c.
    Clears the drawable (or selected region) to transparent.
    """
    if not layer.has_alpha:
        layer.pixels.fill(0)
        return
    if selection_mask is not None:
        alpha = selection_mask.astype(np.float32) / 255.0
        for c in range(layer.pixels.shape[2]):
            layer.pixels[:, :, c] = (
                layer.pixels[:, :, c].astype(np.float32) * (1 - alpha)
            ).astype(np.uint8)
    else:
        layer.pixels.fill(0)


def drawable_edit_stroke_selection(layer, selection_mask: np.ndarray,
                                   stroke_width: float = 1.0,
                                   color: Tuple[int, ...] = (0, 0, 0, 255)) -> None:
    """
    Stroke selection — extracted from gimpdrawable-stroke.c.
    Draws the outline of the selection mask.
    """
    from .transform import _dilate_gray, _erode_gray
    radius = max(1, int(stroke_width / 2))
    outer = _dilate_gray(selection_mask, radius)
    inner = _erode_gray(selection_mask, radius)
    border = np.clip(outer.astype(np.int16) - inner.astype(np.int16), 0, 255).astype(np.uint8)

    stroke_color = np.array(color, dtype=np.uint8)
    channels = layer.pixels.shape[2]
    stroke_color = np.resize(stroke_color, channels)

    mask = border > 0
    for c in range(channels):
        layer.pixels[:, :, c][mask] = stroke_color[c]


def drawable_get_pixel(layer, x: int, y: int) -> Tuple[int, ...]:
    if 0 <= x < layer.width and 0 <= y < layer.height:
        return tuple(layer.pixels[y, x])
    raise GimpError(f"Pixel ({x}, {y}) out of bounds")


def drawable_set_pixel(layer, x: int, y: int, color: Tuple[int, ...]) -> None:
    if 0 <= x < layer.width and 0 <= y < layer.height:
        channels = min(len(color), layer.pixels.shape[2])
        layer.pixels[y, x, :channels] = color[:channels]
    else:
        raise GimpError(f"Pixel ({x}, {y}) out of bounds")


def drawable_offset(layer, offset_x: int, offset_y: int,
                    wrap: bool = False) -> None:
    """
    Offset — extracted from gimpdrawable-offset.c.
    Shifts the drawable content by the given amount.
    """
    pixels = layer.pixels
    h, w = pixels.shape[:2]
    if wrap:
        layer.pixels = np.roll(np.roll(pixels, offset_y, axis=0), offset_x, axis=1)
    else:
        new_pixels = np.zeros_like(pixels)
        src_x = max(0, -offset_x)
        src_y = max(0, -offset_y)
        dst_x = max(0, offset_x)
        dst_y = max(0, offset_y)
        copy_w = min(w - src_x, w - dst_x)
        copy_h = min(h - src_y, h - dst_y)
        if copy_w > 0 and copy_h > 0:
            new_pixels[dst_y:dst_y+copy_h, dst_x:dst_x+copy_w] = \
                pixels[src_y:src_y+copy_h, src_x:src_x+copy_w]
        layer.pixels = new_pixels


def drawable_foreground_extract(layer, mask_pixels: np.ndarray) -> np.ndarray:
    """
    Foreground extraction — extracted from gimpdrawable-foreground-extract.c.
    Simplified matting algorithm.
    """
    result = layer.pixels.copy()
    if layer.has_alpha:
        alpha = mask_pixels.astype(np.float32) / 255.0
        result[:, :, -1] = (result[:, :, -1].astype(np.float32) * alpha).astype(np.uint8)
    return result
