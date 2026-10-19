"""
Layer module — extracted from app/core/gimplayer.c and app/core/gimpgrouplayer.c.
Provides GimpLayer, GimpGroupLayer, and GimpLayerMask classes.
"""

import numpy as np
from typing import Optional, List, Tuple

from .enums import (
    LayerMode, CompositeSpace, CompositeMode, ImageType, FillType,
    MaskApplyMode, BlendColorSpace,
)
from .exceptions import LayerError


class GimpLayerMask:
    """
    Layer mask — extracted from app/core/gimplayermask.c.
    A grayscale channel attached to a layer that controls transparency.
    """

    def __init__(self, width: int, height: int, name: str = "Layer Mask"):
        self.name = name
        self.width = width
        self.height = height
        self.pixels = np.full((height, width), 255, dtype=np.uint8)
        self.visible = True
        self._applied = False

    def apply(self) -> None:
        self._applied = True

    def discard(self) -> None:
        self._applied = False

    @property
    def is_applied(self) -> bool:
        return self._applied

    def invert(self) -> None:
        self.pixels = 255 - self.pixels

    def fill(self, value: int) -> None:
        self.pixels.fill(np.clip(value, 0, 255))

    def copy(self) -> 'GimpLayerMask':
        mask = GimpLayerMask(self.width, self.height, self.name)
        mask.pixels = self.pixels.copy()
        mask.visible = self.visible
        return mask

    def get_bounds(self) -> Tuple[int, int, int, int]:
        nonzero = np.nonzero(self.pixels)
        if len(nonzero[0]) == 0:
            return (0, 0, 0, 0)
        y_min, y_max = int(nonzero[0].min()), int(nonzero[0].max())
        x_min, x_max = int(nonzero[1].min()), int(nonzero[1].max())
        return (x_min, y_min, x_max + 1, y_max + 1)


class GimpLayer:
    """
    Layer object — extracted from app/core/gimplayer.c.
    Holds pixel data, opacity, blend mode, offsets, and optional layer mask.
    """

    def __init__(self, width: int, height: int, name: str = "Layer",
                 image_type: ImageType = ImageType.RGB,
                 has_alpha: bool = True, fill_type: FillType = FillType.TRANSPARENT):
        self.name = name
        self.width = width
        self.height = height
        self.image_type = image_type
        self.has_alpha = has_alpha

        channels = self._channel_count()
        if fill_type == FillType.TRANSPARENT:
            if has_alpha:
                self.pixels = np.zeros((height, width, channels), dtype=np.uint8)
            else:
                if image_type == ImageType.RGB:
                    self.pixels = np.full((height, width, channels), 255, dtype=np.uint8)
                else:
                    self.pixels = np.zeros((height, width, channels), dtype=np.uint8)
        elif fill_type == FillType.WHITE:
            self.pixels = np.full((height, width, channels), 255, dtype=np.uint8)
        elif fill_type == FillType.FOREGROUND:
            self.pixels = np.zeros((height, width, channels), dtype=np.uint8)
        elif fill_type == FillType.BACKGROUND:
            self.pixels = np.full((height, width, channels), 255, dtype=np.uint8)
        else:
            self.pixels = np.zeros((height, width, channels), dtype=np.uint8)

        if has_alpha and channels >= 4:
            if fill_type not in (FillType.TRANSPARENT,):
                self.pixels[:, :, 3] = 255

        self.opacity = 1.0
        self.mode = LayerMode.NORMAL
        self.blend_space = CompositeSpace.AUTO
        self.composite_space = CompositeSpace.AUTO
        self.composite_mode = CompositeMode.AUTO
        self.offset_x = 0
        self.offset_y = 0
        self.visible = True
        self.lock_alpha = False
        self.lock_content = False
        self.lock_position = False
        self.lock_visibility = False
        self.mask: Optional[GimpLayerMask] = None
        self.apply_mask = True
        self.show_mask = False
        self.edit_mask = False
        self.parent: Optional['GimpGroupLayer'] = None
        self._tags: List[str] = []
        self._parasites = {}

    def _channel_count(self) -> int:
        if self.image_type == ImageType.RGB:
            return 4 if self.has_alpha else 3
        elif self.image_type == ImageType.GRAY:
            return 2 if self.has_alpha else 1
        elif self.image_type == ImageType.INDEXED:
            return 2 if self.has_alpha else 1
        return 4

    def set_offsets(self, x: int, y: int) -> None:
        self.offset_x = x
        self.offset_y = y

    def set_opacity(self, opacity: float) -> None:
        if not 0.0 <= opacity <= 1.0:
            raise LayerError("Opacity must be between 0.0 and 1.0")
        self.opacity = opacity

    def set_mode(self, mode: LayerMode) -> None:
        self.mode = mode

    def create_mask(self, from_color: bool = False) -> GimpLayerMask:
        mask = GimpLayerMask(self.width, self.height, f"{self.name} Mask")
        if from_color and self.has_alpha:
            alpha = self.pixels[:, :, 3]
            mask.pixels = alpha.copy()
        else:
            mask.pixels.fill(255)
        return mask

    def add_mask(self, mask: GimpLayerMask) -> None:
        if mask.width != self.width or mask.height != self.height:
            raise LayerError("Mask dimensions must match layer dimensions")
        self.mask = mask

    def remove_mask(self, mode: MaskApplyMode = MaskApplyMode.APPLY) -> None:
        if self.mask is None:
            return
        if mode == MaskApplyMode.APPLY and self.has_alpha:
            mask_alpha = self.mask.pixels.astype(np.float32) / 255.0
            alpha_idx = self.pixels.shape[2] - 1
            self.pixels[:, :, alpha_idx] = (
                self.pixels[:, :, alpha_idx].astype(np.float32) * mask_alpha
            ).astype(np.uint8)
        self.mask = None

    def add_alpha(self) -> None:
        if self.has_alpha:
            return
        old = self.pixels
        self.has_alpha = True
        channels = self._channel_count()
        self.pixels = np.zeros((*old.shape[:2], channels), dtype=np.uint8)
        self.pixels[:, :, :old.shape[2]] = old
        self.pixels[:, :, -1] = 255

    def flatten(self) -> None:
        if not self.has_alpha:
            return
        self.pixels = self.pixels[:, :, :-1]
        self.has_alpha = False

    def scale(self, new_width: int, new_height: int,
              interpolation: str = "cubic") -> None:
        from .transform import _scale_array
        self.pixels = _scale_array(self.pixels, new_width, new_height, interpolation)
        self.width = new_width
        self.height = new_height
        if self.mask:
            self.mask.pixels = _scale_array(
                self.mask.pixels, new_width, new_height, interpolation
            )
            self.mask.width = new_width
            self.mask.height = new_height

    def resize(self, new_width: int, new_height: int,
               offset_x: int = 0, offset_y: int = 0) -> None:
        channels = self.pixels.shape[2] if self.pixels.ndim == 3 else 1
        new_pixels = np.zeros((new_height, new_width, channels), dtype=np.uint8)
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
        if self.mask:
            new_mask = np.zeros((new_height, new_width), dtype=np.uint8)
            if copy_w > 0 and copy_h > 0:
                new_mask[dst_y:dst_y+copy_h, dst_x:dst_x+copy_w] = \
                    self.mask.pixels[src_y:src_y+copy_h, src_x:src_x+copy_w]
            self.mask.pixels = new_mask
            self.mask.width = new_width
            self.mask.height = new_height

    def resize_to_image_size(self, image_width: int, image_height: int) -> None:
        self.resize(image_width, image_height, -self.offset_x, -self.offset_y)
        self.offset_x = 0
        self.offset_y = 0

    def copy(self) -> 'GimpLayer':
        new_layer = GimpLayer.__new__(GimpLayer)
        new_layer.name = self.name
        new_layer.width = self.width
        new_layer.height = self.height
        new_layer.image_type = self.image_type
        new_layer.has_alpha = self.has_alpha
        new_layer.pixels = self.pixels.copy()
        new_layer.opacity = self.opacity
        new_layer.mode = self.mode
        new_layer.blend_space = self.blend_space
        new_layer.composite_space = self.composite_space
        new_layer.composite_mode = self.composite_mode
        new_layer.offset_x = self.offset_x
        new_layer.offset_y = self.offset_y
        new_layer.visible = self.visible
        new_layer.lock_alpha = self.lock_alpha
        new_layer.lock_content = self.lock_content
        new_layer.lock_position = self.lock_position
        new_layer.lock_visibility = self.lock_visibility
        new_layer.mask = self.mask.copy() if self.mask else None
        new_layer.apply_mask = self.apply_mask
        new_layer.show_mask = self.show_mask
        new_layer.edit_mask = self.edit_mask
        new_layer.parent = None
        new_layer._tags = list(self._tags)
        new_layer._parasites = dict(self._parasites)
        return new_layer

    def get_pixel(self, x: int, y: int) -> Tuple[int, ...]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return tuple(self.pixels[y, x])
        raise LayerError(f"Pixel ({x}, {y}) out of bounds")

    def set_pixel(self, x: int, y: int, color: Tuple[int, ...]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            channels = min(len(color), self.pixels.shape[2])
            self.pixels[y, x, :channels] = color[:channels]
        else:
            raise LayerError(f"Pixel ({x}, {y}) out of bounds")

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        return (self.offset_x, self.offset_y,
                self.offset_x + self.width, self.offset_y + self.height)


class GimpGroupLayer(GimpLayer):
    """
    Layer group — extracted from app/core/gimpgrouplayer.c.
    A container that holds child layers and composites them.
    """

    def __init__(self, width: int, height: int, name: str = "Group",
                 image_type: ImageType = ImageType.RGB):
        super().__init__(width, height, name, image_type, has_alpha=True)
        self.children: List[GimpLayer] = []

    def add_layer(self, layer: GimpLayer, position: int = -1) -> None:
        layer.parent = self
        if position < 0 or position >= len(self.children):
            self.children.append(layer)
        else:
            self.children.insert(position, layer)

    def remove_layer(self, layer: GimpLayer) -> None:
        if layer in self.children:
            self.children.remove(layer)
            layer.parent = None

    def merge(self) -> GimpLayer:
        result = GimpLayer(self.width, self.height, f"{self.name} (merged)",
                           self.image_type, has_alpha=True)
        for layer in reversed(self.children):
            if not layer.visible:
                continue
            _composite_layer(result, layer)
        result.opacity = self.opacity
        result.mode = self.mode
        return result

    def get_all_layers(self, recursive: bool = True) -> List[GimpLayer]:
        layers = []
        for child in self.children:
            layers.append(child)
            if recursive and isinstance(child, GimpGroupLayer):
                layers.extend(child.get_all_layers(recursive=True))
        return layers


def _composite_layer(target: GimpLayer, source: GimpLayer) -> None:
    """Composite source onto target using alpha blending (simplified normal mode)."""
    sx = max(0, source.offset_x - target.offset_x)
    sy = max(0, source.offset_y - target.offset_y)
    dx = max(0, target.offset_x - source.offset_x)
    dy = max(0, target.offset_y - source.offset_y)
    w = min(source.width - dx, target.width - sx)
    h = min(source.height - dy, target.height - sy)
    if w <= 0 or h <= 0:
        return

    src = source.pixels[dy:dy+h, dx:dx+w].astype(np.float32)
    dst = target.pixels[sy:sy+h, sx:sx+w].astype(np.float32)

    src_channels = src.shape[2]
    dst_channels = dst.shape[2]

    if src_channels == 4:
        src_alpha = src[:, :, 3:4] / 255.0 * source.opacity
    else:
        src_alpha = np.full((*src.shape[:2], 1), source.opacity)

    if source.mask is not None and source.apply_mask:
        mask_alpha = source.mask.pixels[dy:dy+h, dx:dx+w].astype(np.float32) / 255.0
        src_alpha *= mask_alpha[:, :, np.newaxis]

    if dst_channels == 4:
        dst_alpha = dst[:, :, 3:4] / 255.0
    else:
        dst_alpha = np.ones((*dst.shape[:2], 1))

    out_alpha = src_alpha + dst_alpha * (1 - src_alpha)
    safe_alpha = np.where(out_alpha > 0, out_alpha, 1)

    src_rgb = src[:, :, :3]
    dst_rgb = dst[:, :, :3]
    out_rgb = (src_rgb * src_alpha + dst_rgb * dst_alpha * (1 - src_alpha)) / safe_alpha

    min_c = min(3, dst_channels)
    target.pixels[sy:sy+h, sx:sx+w, :min_c] = np.clip(out_rgb[:, :, :min_c], 0, 255).astype(np.uint8)
    if dst_channels == 4:
        target.pixels[sy:sy+h, sx:sx+w, 3] = np.clip(out_alpha[:, :, 0] * 255, 0, 255).astype(np.uint8)
