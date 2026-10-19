"""
Resource module — extracted from app/core/:
  gimpbrush.c, gimppattern.c, gimpgradient.c,
  gimppalette.c, gimpdynamics.c.
Provides brush, pattern, gradient, palette, and dynamics resources.
"""

import math
import numpy as np
from typing import List, Tuple, Optional

from .enums import BrushShape, GradientType, RepeatMode
from .exceptions import ResourceError


class GimpBrush:
    """
    Brush resource — from gimpbrush.c, gimpbrushgenerated.c.
    Can be a raster brush (loaded from file) or a generated (parametric) brush.
    """

    def __init__(self, name: str = "Default Brush",
                 shape: BrushShape = BrushShape.CIRCLE,
                 radius: float = 5.0, hardness: float = 1.0,
                 spacing: float = 0.1, aspect_ratio: float = 1.0,
                 angle: float = 0.0):
        self.name = name
        self.shape = shape
        self.radius = radius
        self.hardness = hardness
        self.spacing = spacing
        self.aspect_ratio = aspect_ratio
        self.angle = angle
        self._pixels: Optional[np.ndarray] = None
        self._generated = True

    @property
    def is_generated(self) -> bool:
        return self._generated

    def get_mask(self) -> np.ndarray:
        if self._pixels is not None:
            return self._pixels
        d = int(self.radius * 2) + 1
        mask = np.zeros((d, d), dtype=np.float32)
        cx, cy = d // 2, d // 2
        for y in range(d):
            for x in range(d):
                dx = (x - cx) / max(self.radius, 0.01)
                dy = (y - cy) / max(self.radius, 0.01)
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
                        if dist <= self.hardness:
                            mask[y, x] = 1.0
                        else:
                            mask[y, x] = max(0, 1.0 - (dist - self.hardness) / (1.0 - self.hardness))
        self._pixels = mask
        return mask

    def get_info(self) -> dict:
        return {
            "name": self.name,
            "shape": self.shape.value,
            "radius": self.radius,
            "hardness": self.hardness,
            "spacing": self.spacing,
            "aspect_ratio": self.aspect_ratio,
            "angle": self.angle,
        }


class GimpPattern:
    """
    Pattern resource — from gimppattern.c.
    A small raster image used for tiling fills.
    """

    def __init__(self, name: str = "Default Pattern",
                 pixels: np.ndarray = None):
        self.name = name
        if pixels is None:
            self.pixels = np.full((10, 10, 3), 128, dtype=np.uint8)
        else:
            self.pixels = pixels.copy()

    @property
    def width(self) -> int:
        return self.pixels.shape[1]

    @property
    def height(self) -> int:
        return self.pixels.shape[0]


class GimpGradient:
    """
    Gradient resource — from gimpgradient.c.
    A sequence of color segments for gradient fills.
    """

    def __init__(self, name: str = "Default Gradient"):
        self.name = name
        self.segments: List[dict] = []
        self._add_default_segments()

    def _add_default_segments(self):
        self.segments = [
            {
                "left_pos": 0.0,
                "right_pos": 1.0,
                "left_color": (0, 0, 0, 255),
                "right_color": (255, 255, 255, 255),
                "blend_func": "linear",
                "coloring_type": "rgb",
            }
        ]

    def add_segment(self, left_pos: float, right_pos: float,
                    left_color: Tuple[int, int, int, int],
                    right_color: Tuple[int, int, int, int],
                    blend_func: str = "linear") -> None:
        self.segments.append({
            "left_pos": left_pos,
            "right_pos": right_pos,
            "left_color": left_color,
            "right_color": right_color,
            "blend_func": blend_func,
            "coloring_type": "rgb",
        })

    def get_color_at(self, position: float) -> Tuple[int, int, int, int]:
        position = max(0.0, min(1.0, position))
        for seg in self.segments:
            if seg["left_pos"] <= position <= seg["right_pos"]:
                t = (position - seg["left_pos"]) / max(
                    seg["right_pos"] - seg["left_pos"], 1e-10
                )
                lc = seg["left_color"]
                rc = seg["right_color"]
                return tuple(int(lc[i] + (rc[i] - lc[i]) * t) for i in range(4))
        if self.segments:
            return self.segments[-1]["right_color"]
        return (0, 0, 0, 255)

    def replicate(self, count: int) -> None:
        if count < 2 or not self.segments:
            return
        new_segments = []
        seg_width = 1.0 / count
        for i in range(count):
            for seg in self.segments:
                new_seg = dict(seg)
                new_seg["left_pos"] = seg["left_pos"] * seg_width + i * seg_width
                new_seg["right_pos"] = seg["right_pos"] * seg_width + i * seg_width
                new_segments.append(new_seg)
        self.segments = new_segments

    def reverse(self) -> None:
        for seg in self.segments:
            seg["left_pos"], seg["right_pos"] = (
                1.0 - seg["right_pos"], 1.0 - seg["left_pos"]
            )
            seg["left_color"], seg["right_color"] = (
                seg["right_color"], seg["left_color"]
            )
        self.segments.reverse()

    def render(self, width: int, height: int,
               gradient_type: GradientType = GradientType.LINEAR,
               x1: float = 0, y1: float = 0,
               x2: float = 0, y2: float = 100) -> np.ndarray:
        result = np.zeros((height, width, 4), dtype=np.uint8)
        from .drawable import _gradient_factor
        for py in range(height):
            for px in range(width):
                t = _gradient_factor(gradient_type, px, py, x1, y1, x2, y2)
                result[py, px] = self.get_color_at(t)
        return result


class GimpPalette:
    """
    Palette resource — from gimppalette.c.
    A collection of named colors.
    """

    def __init__(self, name: str = "Default Palette"):
        self.name = name
        self.colors: List[Tuple[int, int, int, str]] = []

    def add_color(self, r: int, g: int, b: int, name: str = "") -> None:
        self.colors.append((r, g, b, name))

    def remove_color(self, index: int) -> None:
        if 0 <= index < len(self.colors):
            self.colors.pop(index)

    def get_color(self, index: int) -> Tuple[int, int, int, str]:
        if 0 <= index < len(self.colors):
            return self.colors[index]
        raise ResourceError(f"Palette index {index} out of range")

    @property
    def color_count(self) -> int:
        return len(self.colors)

    def find_closest(self, r: int, g: int, b: int) -> int:
        best_idx = 0
        best_dist = float('inf')
        for i, (cr, cg, cb, _) in enumerate(self.colors):
            dist = (r-cr)**2 + (g-cg)**2 + (b-cb)**2
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return best_idx


class GimpDynamics:
    """
    Brush dynamics — from gimpdynamics.c.
    Maps pen pressure, velocity, etc. to brush parameters.
    """

    def __init__(self, name: str = "Default Dynamics"):
        self.name = name
        self.pressure_opacity = True
        self.pressure_size = True
        self.pressure_hardness = False
        self.velocity_opacity = False
        self.velocity_size = False
        self.random_opacity = False
        self.random_size = False
        self.fade_opacity = False
        self.fade_length = 0.0

    def apply(self, pressure: float = 1.0, velocity: float = 0.0,
              distance: float = 0.0) -> dict:
        result = {"opacity": 1.0, "size": 1.0, "hardness": 1.0}
        if self.pressure_opacity:
            result["opacity"] *= pressure
        if self.pressure_size:
            result["size"] *= max(0.1, pressure)
        if self.pressure_hardness:
            result["hardness"] *= pressure
        if self.velocity_opacity:
            result["opacity"] *= (1.0 - min(velocity, 1.0) * 0.5)
        if self.fade_length > 0 and self.fade_opacity:
            fade = max(0, 1.0 - distance / self.fade_length)
            result["opacity"] *= fade
        return result
