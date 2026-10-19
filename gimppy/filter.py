"""
Filter system — extracted from app/core/gimpdrawablefilter.c
and app/core/gimpfilterstack.c.
Provides non-destructive filter application on drawables.
"""

import numpy as np
from typing import Optional, List, Callable, Any

from .enums import LayerMode, BlendColorSpace
from .exceptions import FilterError


class GimpFilter:
    """
    Non-destructive filter — from gimpdrawablefilter.c.
    Wraps a pixel processing operation that can be toggled,
    adjusted, and stacked on a drawable without permanently modifying it.
    """

    def __init__(self, name: str, operation: Callable[[np.ndarray], np.ndarray]):
        self.name = name
        self.operation = operation
        self.visible = True
        self.opacity = 1.0
        self.mode = LayerMode.NORMAL
        self.region: Optional[tuple] = None
        self._params = {}

    def set_param(self, key: str, value: Any) -> None:
        self._params[key] = value

    def get_param(self, key: str, default: Any = None) -> Any:
        return self._params.get(key, default)

    def apply(self, pixels: np.ndarray) -> np.ndarray:
        if not self.visible:
            return pixels.copy()
        result = self.operation(pixels)
        if self.opacity < 1.0:
            result = (pixels.astype(np.float32) * (1 - self.opacity) +
                      result.astype(np.float32) * self.opacity).astype(np.uint8)
        return result

    def set_region(self, x: int, y: int, width: int, height: int) -> None:
        self.region = (x, y, width, height)


class FilterStack:
    """
    Filter stack — from gimpfilterstack.c.
    Manages an ordered list of filters applied to a drawable.
    """

    def __init__(self):
        self.filters: List[GimpFilter] = []

    def add(self, f: GimpFilter, position: int = -1) -> None:
        if position < 0 or position >= len(self.filters):
            self.filters.append(f)
        else:
            self.filters.insert(position, f)

    def remove(self, f: GimpFilter) -> None:
        if f in self.filters:
            self.filters.remove(f)

    def get(self, index: int) -> Optional[GimpFilter]:
        if 0 <= index < len(self.filters):
            return self.filters[index]
        return None

    def apply_all(self, pixels: np.ndarray) -> np.ndarray:
        result = pixels.copy()
        for f in self.filters:
            if f.visible:
                if f.region is not None:
                    x, y, w, h = f.region
                    region = result[y:y+h, x:x+w].copy()
                    filtered = f.apply(region)
                    result[y:y+h, x:x+w] = filtered
                else:
                    result = f.apply(result)
        return result

    def clear(self) -> None:
        self.filters.clear()

    def __len__(self) -> int:
        return len(self.filters)

    def __iter__(self):
        return iter(self.filters)


def apply_brightness_contrast(pixels: np.ndarray, brightness: float = 0,
                              contrast: float = 0) -> np.ndarray:
    from .color import brightness_contrast
    return brightness_contrast(pixels, brightness, contrast)


def apply_levels(pixels: np.ndarray, **kwargs) -> np.ndarray:
    from .color import levels
    return levels(pixels, **kwargs)


def apply_hue_saturation(pixels: np.ndarray, **kwargs) -> np.ndarray:
    from .color import hue_saturation
    return hue_saturation(pixels, **kwargs)


def apply_color_balance(pixels: np.ndarray, **kwargs) -> np.ndarray:
    from .color import color_balance
    return color_balance(pixels, **kwargs)


def apply_desaturate(pixels: np.ndarray, **kwargs) -> np.ndarray:
    from .color import desaturate
    return desaturate(pixels, **kwargs)


def apply_posterize(pixels: np.ndarray, levels: int = 4) -> np.ndarray:
    from .color import posterize
    return posterize(pixels, levels)


def apply_threshold(pixels: np.ndarray, value: int = 127) -> np.ndarray:
    from .color import threshold
    return threshold(pixels, value)


def apply_equalize(pixels: np.ndarray) -> np.ndarray:
    from .color import equalize
    return equalize(pixels)


def apply_invert(pixels: np.ndarray) -> np.ndarray:
    from .color import invert
    return invert(pixels)


def apply_shadows_highlights(pixels: np.ndarray, **kwargs) -> np.ndarray:
    from .color import shadows_highlights
    return shadows_highlights(pixels, **kwargs)


def create_filter(name: str, operation: Callable[[np.ndarray], np.ndarray],
                  **params) -> GimpFilter:
    f = GimpFilter(name, operation)
    for k, v in params.items():
        f.set_param(k, v)
    return f
