"""
Paint engine — extracted from app/paint/:
  gimppaintcore.c, gimpbrushcore.c, gimppaintbrush.c,
  gimppencil.c, gimperaser.c, gimpairbrush.c,
  gimpclone.c, gimpheal.c, gimpsmudge.c,
  gimpconvolve.c, gimpdodgeburn.c, gimpink.c.
"""

import math
import numpy as np
from typing import Tuple, List, Optional

from .enums import (
    PaintMode, BrushShape, ConvolveType, DodgeBurnType,
    LayerMode,
)
from .exceptions import PaintError


class Brush:
    """
    Brush model — from gimpbrush.c.
    Defines the shape and size of the paint stamp.
    """

    def __init__(self, size: float = 10.0, hardness: float = 1.0,
                 shape: BrushShape = BrushShape.CIRCLE,
                 angle: float = 0.0, aspect_ratio: float = 1.0,
                 spacing: float = 0.1):
        self.size = size
        self.hardness = hardness
        self.shape = shape
        self.angle = angle
        self.aspect_ratio = aspect_ratio
        self.spacing = spacing
        self._mask_cache = {}

    def get_mask(self, size_override: float = None) -> np.ndarray:
        size = size_override or self.size
        radius = max(1, int(math.ceil(size / 2)))
        d = radius * 2 + 1
        key = (d, self.hardness, self.shape.value)
        if key in self._mask_cache:
            return self._mask_cache[key]
        mask = np.zeros((d, d), dtype=np.float32)
        cx, cy = radius, radius
        for y in range(d):
            for x in range(d):
                dx = (x - cx) / max(radius, 1)
                dy = (y - cy) / max(radius, 1)
                if self.shape == BrushShape.CIRCLE:
                    dist = math.sqrt(dx*dx + dy*dy)
                elif self.shape == BrushShape.SQUARE:
                    dist = max(abs(dx), abs(dy))
                else:
                    dist = abs(dx) + abs(dy)
                if dist <= 1.0:
                    if self.hardness >= 1.0:
                        mask[y, x] = 1.0
                    else:
                        t = dist
                        if t <= self.hardness:
                            mask[y, x] = 1.0
                        else:
                            mask[y, x] = max(0, 1.0 - (t - self.hardness) / (1.0 - self.hardness))
        self._mask_cache[key] = mask
        return mask


class PaintOptions:
    """
    Paint options — from gimppaintoptions.c.
    Controls opacity, flow, dynamics, etc.
    """

    def __init__(self):
        self.opacity = 1.0
        self.brush = Brush()
        self.mode = PaintMode.NORMAL
        self.flow = 1.0
        self.rate = 50.0
        self.pressure_opacity = False
        self.pressure_size = False
        self.fade_length = 0.0
        self.dynamics = None
        self.apply_jitter = 0.0
        self.sample_merged = False
        self.color_options = None


def paintbrush_stroke(layer, points: List[Tuple[float, float]],
                      color: Tuple[int, ...] = (0, 0, 0, 255),
                      options: PaintOptions = None) -> None:
    """
    Paintbrush — from gimppaintbrush.c.
    Paints a smooth stroke along the given points.
    """
    if options is None:
        options = PaintOptions()
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    radius = options.brush.size / 2
    paint_color = np.array(color, dtype=np.float32)
    channels = layer.pixels.shape[2]
    paint_color = np.resize(paint_color, channels)

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        spacing_px = max(1, options.brush.spacing * options.brush.size)
        steps = max(1, int(dist / spacing_px))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            _apply_brush_stamp(layer, px, py, brush_mask, paint_color,
                               options.opacity * options.flow)


def pencil_stroke(layer, points: List[Tuple[float, float]],
                  color: Tuple[int, ...] = (0, 0, 0, 255),
                  options: PaintOptions = None) -> None:
    """
    Pencil — from gimppencil.c.
    Hard-edge painting with no anti-aliasing.
    """
    if options is None:
        options = PaintOptions()
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    brush_mask = (brush_mask > 0.5).astype(np.float32)
    paint_color = np.resize(np.array(color, dtype=np.float32), layer.pixels.shape[2])

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        steps = max(1, int(dist))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            _apply_brush_stamp(layer, px, py, brush_mask, paint_color,
                               options.opacity)


def eraser_stroke(layer, points: List[Tuple[float, float]],
                  options: PaintOptions = None) -> None:
    """
    Eraser — from gimperaser.c.
    Removes pixel data along the stroke path.
    """
    if options is None:
        options = PaintOptions()
    if not layer.has_alpha:
        return
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    radius = options.brush.size / 2

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        spacing_px = max(1, options.brush.spacing * options.brush.size)
        steps = max(1, int(dist / spacing_px))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            bh, bw = brush_mask.shape
            for by in range(bh):
                for bx in range(bw):
                    ix = int(px - bw//2 + bx)
                    iy = int(py - bh//2 + by)
                    if 0 <= ix < layer.width and 0 <= iy < layer.height:
                        alpha_idx = layer.pixels.shape[2] - 1
                        current = layer.pixels[iy, ix, alpha_idx].astype(np.float32)
                        erase = brush_mask[by, bx] * options.opacity
                        layer.pixels[iy, ix, alpha_idx] = max(0, current * (1 - erase))


def airbrush_stroke(layer, points: List[Tuple[float, float]],
                    color: Tuple[int, ...] = (0, 0, 0, 255),
                    options: PaintOptions = None,
                    pressure: float = 1.0) -> None:
    """
    Airbrush — from gimpairbrush.c.
    Continuous spray with adjustable rate and pressure.
    """
    if options is None:
        options = PaintOptions()
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    paint_color = np.resize(np.array(color, dtype=np.float32), layer.pixels.shape[2])
    rate = options.rate / 100.0

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        spacing_px = max(1, options.brush.spacing * options.brush.size * 0.5)
        steps = max(1, int(dist / spacing_px))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            _apply_brush_stamp(layer, px, py, brush_mask, paint_color,
                               options.opacity * rate * pressure)


def clone_stroke(layer, source_pixels: np.ndarray,
                 points: List[Tuple[float, float]],
                 source_offset: Tuple[int, int] = (0, 0),
                 options: PaintOptions = None) -> None:
    """
    Clone tool — from gimpclone.c.
    Copies pixels from a source area to the destination.
    """
    if options is None:
        options = PaintOptions()
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    sx_off, sy_off = source_offset

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        steps = max(1, int(dist))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            _apply_clone_stamp(layer, source_pixels, px, py,
                               brush_mask, sx_off, sy_off, options.opacity)


def heal_stroke(layer, source_pixels: np.ndarray,
                points: List[Tuple[float, float]],
                source_offset: Tuple[int, int] = (0, 0),
                options: PaintOptions = None) -> None:
    """
    Heal tool — from gimpheal.c.
    Clone with blending to match surrounding texture and lighting.
    """
    if options is None:
        options = PaintOptions()
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    sx_off, sy_off = source_offset

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        steps = max(1, int(dist))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            _apply_heal_stamp(layer, source_pixels, px, py,
                              brush_mask, sx_off, sy_off, options.opacity)


def smudge_stroke(layer, points: List[Tuple[float, float]],
                  rate: float = 0.5,
                  options: PaintOptions = None) -> None:
    """
    Smudge — from gimpsmudge.c.
    Smears existing pixels along the stroke direction.
    """
    if options is None:
        options = PaintOptions()
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    bh, bw = brush_mask.shape
    accum = None

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        steps = max(1, int(dist))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            cx, cy = int(px), int(py)
            if accum is None:
                accum = np.zeros(layer.pixels.shape[2], dtype=np.float32)
                count = 0
                for by in range(bh):
                    for bx in range(bw):
                        if brush_mask[by, bx] > 0:
                            ix, iy = cx - bw//2 + bx, cy - bh//2 + by
                            if 0 <= ix < layer.width and 0 <= iy < layer.height:
                                accum += layer.pixels[iy, ix].astype(np.float32)
                                count += 1
                if count > 0:
                    accum /= count

            for by in range(bh):
                for bx in range(bw):
                    if brush_mask[by, bx] <= 0:
                        continue
                    ix, iy = cx - bw//2 + bx, cy - bh//2 + by
                    if 0 <= ix < layer.width and 0 <= iy < layer.height:
                        w = brush_mask[by, bx] * rate * options.opacity
                        layer.pixels[iy, ix] = (
                            layer.pixels[iy, ix].astype(np.float32) * (1 - w) +
                            accum * w
                        ).astype(np.uint8)
                        accum = accum * (1 - rate * 0.1) + \
                                layer.pixels[iy, ix].astype(np.float32) * (rate * 0.1)


def convolve_stroke(layer, points: List[Tuple[float, float]],
                    convolve_type: ConvolveType = ConvolveType.BLUR,
                    options: PaintOptions = None) -> None:
    """
    Convolve (Sharpen/Blur) — from gimpconvolve.c.
    Applies a convolution kernel by painting.
    """
    if options is None:
        options = PaintOptions()
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    bh, bw = brush_mask.shape
    kernel_size = 3

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        steps = max(1, int(dist))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            cx, cy = int(px), int(py)
            for by in range(bh):
                for bx in range(bw):
                    if brush_mask[by, bx] <= 0:
                        continue
                    ix, iy = cx - bw//2 + bx, cy - bh//2 + by
                    if not (0 <= ix < layer.width and 0 <= iy < layer.height):
                        continue
                    neighbors = []
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            nx, ny = ix + dx, iy + dy
                            if 0 <= nx < layer.width and 0 <= ny < layer.height:
                                neighbors.append(layer.pixels[ny, nx].astype(np.float32))
                    if not neighbors:
                        continue
                    avg = sum(neighbors) / len(neighbors)
                    center = layer.pixels[iy, ix].astype(np.float32)
                    if convolve_type == ConvolveType.BLUR:
                        new_val = center * (1 - 0.5) + avg * 0.5
                    else:
                        new_val = center + (center - avg) * 0.5
                    w = brush_mask[by, bx] * options.opacity
                    layer.pixels[iy, ix] = (
                        center * (1 - w) + np.clip(new_val, 0, 255) * w
                    ).astype(np.uint8)


def dodge_burn_stroke(layer, points: List[Tuple[float, float]],
                      db_type: DodgeBurnType = DodgeBurnType.DODGE,
                      intensity: float = 0.5,
                      options: PaintOptions = None) -> None:
    """
    Dodge/Burn — from gimpdodgeburntool.c.
    Lightens (dodge) or darkens (burn) the image.
    """
    if options is None:
        options = PaintOptions()
    if len(points) < 2:
        return
    brush_mask = options.brush.get_mask()
    bh, bw = brush_mask.shape

    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
        steps = max(1, int(dist))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            cx, cy = int(px), int(py)
            for by in range(bh):
                for bx in range(bw):
                    if brush_mask[by, bx] <= 0:
                        continue
                    ix, iy = cx - bw//2 + bx, cy - bh//2 + by
                    if not (0 <= ix < layer.width and 0 <= iy < layer.height):
                        continue
                    w = brush_mask[by, bx] * options.opacity * intensity
                    channels = min(3, layer.pixels.shape[2])
                    for c in range(channels):
                        val = layer.pixels[iy, ix, c].astype(np.float32)
                        if db_type == DodgeBurnType.DODGE:
                            val = val + w * 255
                        else:
                            val = val - w * 255
                        layer.pixels[iy, ix, c] = int(np.clip(val, 0, 255))


def _apply_brush_stamp(layer, cx: float, cy: float,
                       brush_mask: np.ndarray,
                       color: np.ndarray,
                       opacity: float) -> None:
    bh, bw = brush_mask.shape
    icx, icy = int(cx), int(cy)
    channels = layer.pixels.shape[2]
    color = np.resize(color, channels)

    for by in range(bh):
        for bx in range(bw):
            w = brush_mask[by, bx] * opacity
            if w <= 0:
                continue
            ix = icx - bw//2 + bx
            iy = icy - bh//2 + by
            if 0 <= ix < layer.width and 0 <= iy < layer.height:
                for c in range(channels):
                    old = layer.pixels[iy, ix, c].astype(np.float32)
                    layer.pixels[iy, ix, c] = int(old * (1 - w) + color[c] * w)


def _apply_clone_stamp(layer, source_pixels: np.ndarray,
                       cx: float, cy: float,
                       brush_mask: np.ndarray,
                       sx_off: int, sy_off: int,
                       opacity: float) -> None:
    bh, bw = brush_mask.shape
    icx, icy = int(cx), int(cy)
    channels = layer.pixels.shape[2]

    for by in range(bh):
        for bx in range(bw):
            w = brush_mask[by, bx] * opacity
            if w <= 0:
                continue
            ix = icx - bw//2 + bx
            iy = icy - bh//2 + by
            sx = ix + sx_off
            sy = iy + sy_off
            if 0 <= ix < layer.width and 0 <= iy < layer.height:
                if 0 <= sx < source_pixels.shape[1] and 0 <= sy < source_pixels.shape[0]:
                    src = source_pixels[sy, sx].astype(np.float32)
                    src = np.resize(src, channels)
                    for c in range(channels):
                        old = layer.pixels[iy, ix, c].astype(np.float32)
                        layer.pixels[iy, ix, c] = int(old * (1 - w) + src[c] * w)


def _apply_heal_stamp(layer, source_pixels: np.ndarray,
                      cx: float, cy: float,
                      brush_mask: np.ndarray,
                      sx_off: int, sy_off: int,
                      opacity: float) -> None:
    bh, bw = brush_mask.shape
    icx, icy = int(cx), int(cy)
    channels = layer.pixels.shape[2]

    src_lum_sum = 0.0
    dst_lum_sum = 0.0
    count = 0
    for by in range(bh):
        for bx in range(bw):
            if brush_mask[by, bx] <= 0:
                continue
            ix = icx - bw//2 + bx
            iy = icy - bh//2 + by
            sx = ix + sx_off
            sy = iy + sy_off
            if 0 <= ix < layer.width and 0 <= iy < layer.height and \
               0 <= sx < source_pixels.shape[1] and 0 <= sy < source_pixels.shape[0]:
                src_lum_sum += 0.299 * source_pixels[sy, sx, 0] + 0.587 * source_pixels[sy, sx, 1] + 0.114 * source_pixels[sy, sx, 2]
                dst_lum_sum += 0.299 * layer.pixels[iy, ix, 0] + 0.587 * layer.pixels[iy, ix, 1] + 0.114 * layer.pixels[iy, ix, 2]
                count += 1

    if count == 0:
        return
    lum_diff = (dst_lum_sum / count) - (src_lum_sum / count)

    for by in range(bh):
        for bx in range(bw):
            w = brush_mask[by, bx] * opacity
            if w <= 0:
                continue
            ix = icx - bw//2 + bx
            iy = icy - bh//2 + by
            sx = ix + sx_off
            sy = iy + sy_off
            if 0 <= ix < layer.width and 0 <= iy < layer.height and \
               0 <= sx < source_pixels.shape[1] and 0 <= sy < source_pixels.shape[0]:
                src = source_pixels[sy, sx].astype(np.float32)
                src = np.resize(src, channels)
                for c in range(min(3, channels)):
                    healed = np.clip(src[c] + lum_diff, 0, 255)
                    old = layer.pixels[iy, ix, c].astype(np.float32)
                    layer.pixels[iy, ix, c] = int(old * (1 - w) + healed * w)
