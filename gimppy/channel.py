"""
Channel module — extracted from app/core/gimpchannel.c.
Provides GimpChannel class for alpha channels and color masks.
"""

import numpy as np
from typing import Optional, Tuple

from .enums import ImageType
from .exceptions import ChannelError


class GimpChannel:
    """
    Channel — extracted from app/core/gimpchannel.c.
    A grayscale mask used for storing selections or custom alpha channels.
    """

    def __init__(self, width: int, height: int, name: str = "Channel",
                 opacity: float = 1.0, color: Tuple[int, int, int] = (255, 0, 0)):
        self.name = name
        self.width = width
        self.height = height
        self.opacity = opacity
        self.color = color
        self.pixels = np.zeros((height, width), dtype=np.uint8)
        self.visible = True
        self.lock_content = False
        self.lock_position = False
        self.lock_visibility = False
        self._tags: list = []
        self._parasites = {}

    def fill(self, value: int) -> None:
        self.pixels.fill(np.clip(value, 0, 255))

    def clear(self) -> None:
        self.pixels.fill(0)

    def invert(self) -> None:
        self.pixels = 255 - self.pixels

    @property
    def is_empty(self) -> bool:
        return not np.any(self.pixels)

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        nonzero = np.nonzero(self.pixels)
        if len(nonzero[0]) == 0:
            return (0, 0, 0, 0)
        y_min, y_max = int(nonzero[0].min()), int(nonzero[0].max())
        x_min, x_max = int(nonzero[1].min()), int(nonzero[1].max())
        return (x_min, y_min, x_max + 1, y_max + 1)

    def get_value(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.pixels[y, x])
        raise ChannelError(f"Position ({x}, {y}) out of bounds")

    def set_value(self, x: int, y: int, value: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y, x] = np.clip(value, 0, 255)
        else:
            raise ChannelError(f"Position ({x}, {y}) out of bounds")

    def combine(self, other: 'GimpChannel', operation: str = "add") -> None:
        a = self.pixels.astype(np.float32) / 255.0
        b = other.pixels.astype(np.float32) / 255.0
        if operation == "add":
            result = np.clip(a + b, 0, 1)
        elif operation == "subtract":
            result = np.clip(a - b, 0, 1)
        elif operation == "intersect":
            result = np.minimum(a, b)
        else:
            raise ChannelError(f"Unknown operation: {operation}")
        self.pixels = (result * 255).astype(np.uint8)

    def feather(self, radius: float) -> None:
        from .transform import _gaussian_blur_gray
        self.pixels = _gaussian_blur_gray(self.pixels, radius)

    def grow(self, radius: int) -> None:
        from .transform import _dilate_gray
        self.pixels = _dilate_gray(self.pixels, radius)

    def shrink(self, radius: int) -> None:
        from .transform import _erode_gray
        self.pixels = _erode_gray(self.pixels, radius)

    def copy(self) -> 'GimpChannel':
        ch = GimpChannel(self.width, self.height, self.name, self.opacity, self.color)
        ch.pixels = self.pixels.copy()
        ch.visible = self.visible
        ch.lock_content = self.lock_content
        ch.lock_position = self.lock_position
        ch.lock_visibility = self.lock_visibility
        ch._tags = list(self._tags)
        return ch

    def scale(self, new_width: int, new_height: int) -> None:
        from .transform import _scale_array
        scaled = _scale_array(
            self.pixels[:, :, np.newaxis], new_width, new_height, "linear"
        )
        self.pixels = scaled[:, :, 0]
        self.width = new_width
        self.height = new_height

    def resize(self, new_width: int, new_height: int,
               offset_x: int = 0, offset_y: int = 0) -> None:
        new_pixels = np.zeros((new_height, new_width), dtype=np.uint8)
        src_x = max(0, -offset_x)
        src_y = max(0, -offset_y)
        dst_x = max(0, offset_x)
        dst_y = max(0, offset_y)
        copy_w = min(self.width - src_x, new_width - dst_x)
        copy_h = min(self.height - src_y, new_height - dst_y)
        if copy_w > 0 and copy_h > 0:
            new_pixels[dst_y:dst_y+copy_h, dst_x:dst_x+copy_w] = \
                self.pixels[src_y:src_y+copy_h, src_x:src_x+copy_w]
        self.pixels = new_pixels
        self.width = new_width
        self.height = new_height
