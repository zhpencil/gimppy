"""
GimpImage — the central image object, extracted from app/core/gimpimage.c.
Manages layers, channels, paths, selection, color profile, metadata,
guides, grid, and all image-level operations.
"""

import numpy as np
from typing import Optional, List, Tuple

from .enums import (
    ImageType, Precision, LayerMode, FillType, FlipType,
    RotationType, CompositeSpace, CompositeMode,
    InterpolationType, TransformResize, SelectionOperation,
    ConvertPaletteType, ConvertDitherType, GuideOrientation,
    GridStyle, MaskApplyMode,
)
from .exceptions import ImageError, LayerError
from .layer import GimpLayer, GimpGroupLayer, GimpLayerMask, _composite_layer
from .channel import GimpChannel
from .selection import GimpSelection
from .path import GimpPath
from .text import GimpText, GimpTextLayer
from .undo import UndoStack, UndoStep, UndoType
from . import color as _color
from . import drawable as _drawable
from . import transform as _transform


class GimpImage:
    """
    The central image document — from gimpimage.c.
    Holds all layers, channels, paths, selection, guides, grid,
    color profile, metadata, and undo history.
    """

    def __init__(self, width: int, height: int,
                 image_type: ImageType = ImageType.RGB,
                 precision: Precision = Precision.U8,
                 name: str = "Untitled"):
        if width <= 0 or height <= 0:
            raise ImageError("Image dimensions must be positive")
        self.name = name
        self.width = width
        self.height = height
        self.image_type = image_type
        self.precision = precision
        self.resolution_x = 72.0
        self.resolution_y = 72.0
        self.unit = "inch"

        self.layers: List[GimpLayer] = []
        self.channels: List[GimpChannel] = []
        self.paths: List[GimpPath] = []
        self.selection = GimpSelection(width, height)
        self.active_layer: Optional[GimpLayer] = None
        self.active_channel: Optional[GimpChannel] = None
        self.active_path: Optional[GimpPath] = None

        self.fg_color = (0, 0, 0)
        self.bg_color = (255, 255, 255)

        self.guides: List[dict] = []
        self.grid_spacing_x = 10.0
        self.grid_spacing_y = 10.0
        self.grid_offset_x = 0.0
        self.grid_offset_y = 0.0
        self.grid_style = GridStyle.INTERSECTIONS
        self.grid_fg_color = (255, 255, 255)
        self.grid_bg_color = (128, 128, 128)

        self.color_profile = None
        self.simulation_profile = None
        self.metadata: dict = {}

        self.undo_stack = UndoStack()
        self._dirty = False
        self._colormap: Optional[np.ndarray] = None

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def clean_all(self) -> None:
        self._dirty = False

    @property
    def base_type(self) -> ImageType:
        return self.image_type

    def get_layers(self) -> List[GimpLayer]:
        return list(self.layers)

    def get_channels(self) -> List[GimpChannel]:
        return list(self.channels)

    def get_paths(self) -> List[GimpPath]:
        return list(self.paths)

    def add_layer(self, layer: GimpLayer, position: int = -1) -> None:
        if position < 0 or position >= len(self.layers):
            self.layers.append(layer)
        else:
            self.layers.insert(position, layer)
        if self.active_layer is None:
            self.active_layer = layer
        self._dirty = True

    def remove_layer(self, layer: GimpLayer) -> None:
        if layer in self.layers:
            self.layers.remove(layer)
            if self.active_layer is layer:
                self.active_layer = self.layers[0] if self.layers else None
            self._dirty = True
        else:
            raise ImageError("Layer not found in image")

    def add_channel(self, channel: GimpChannel) -> None:
        self.channels.append(channel)
        self._dirty = True

    def remove_channel(self, channel: GimpChannel) -> None:
        if channel in self.channels:
            self.channels.remove(channel)
            self._dirty = True

    def add_path(self, path: GimpPath) -> None:
        self.paths.append(path)
        self._dirty = True

    def remove_path(self, path: GimpPath) -> None:
        if path in self.paths:
            self.paths.remove(path)
            self._dirty = True

    def get_item_position(self, item) -> int:
        if isinstance(item, GimpLayer):
            if item in self.layers:
                return self.layers.index(item)
        elif isinstance(item, GimpChannel):
            if item in self.channels:
                return self.channels.index(item)
        elif isinstance(item, GimpPath):
            if item in self.paths:
                return self.paths.index(item)
        raise ImageError("Item not found in image")

    def raise_item(self, item) -> None:
        if isinstance(item, GimpLayer) and item in self.layers:
            idx = self.layers.index(item)
            if idx < len(self.layers) - 1:
                self.layers[idx], self.layers[idx+1] = self.layers[idx+1], self.layers[idx]
                self._dirty = True

    def lower_item(self, item) -> None:
        if isinstance(item, GimpLayer) and item in self.layers:
            idx = self.layers.index(item)
            if idx > 0:
                self.layers[idx], self.layers[idx-1] = self.layers[idx-1], self.layers[idx]
                self._dirty = True

    def raise_item_to_top(self, item) -> None:
        if isinstance(item, GimpLayer) and item in self.layers:
            self.layers.remove(item)
            self.layers.append(item)
            self._dirty = True

    def lower_item_to_bottom(self, item) -> None:
        if isinstance(item, GimpLayer) and item in self.layers:
            self.layers.remove(item)
            self.layers.insert(0, item)
            self._dirty = True

    def new_layer(self, name: str = "Layer",
                  fill_type: FillType = FillType.TRANSPARENT,
                  opacity: float = 1.0,
                  mode: LayerMode = LayerMode.NORMAL) -> GimpLayer:
        layer = GimpLayer(self.width, self.height, name,
                          self.image_type, has_alpha=True, fill_type=fill_type)
        layer.opacity = opacity
        layer.mode = mode
        self.add_layer(layer)
        return layer

    def new_layer_from_visible(self, name: str = "Visible") -> GimpLayer:
        result = GimpLayer(self.width, self.height, name,
                           self.image_type, has_alpha=True)
        for layer in self.layers:
            if layer.visible:
                _composite_layer(result, layer)
        self.add_layer(result)
        return result

    def new_group_layer(self, name: str = "Group") -> GimpGroupLayer:
        group = GimpGroupLayer(self.width, self.height, name, self.image_type)
        self.add_layer(group)
        return group

    def new_text_layer(self, text: str = "Text",
                       font: str = "Sans-serif",
                       size: float = 12.0,
                       color: Tuple[int, int, int] = (0, 0, 0),
                       name: str = "Text") -> GimpTextLayer:
        text_obj = GimpText(text, font, size, color)
        text_layer = GimpTextLayer(text_obj, name)
        layer = GimpLayer(text_layer.width, text_layer.height, name,
                          self.image_type, has_alpha=True)
        layer.pixels = text_layer.pixels.copy()
        self.add_layer(layer)
        return text_layer

    def duplicate(self) -> 'GimpImage':
        new_img = GimpImage(self.width, self.height, self.image_type,
                            self.precision, self.name + " copy")
        new_img.resolution_x = self.resolution_x
        new_img.resolution_y = self.resolution_y
        for layer in self.layers:
            new_img.add_layer(layer.copy())
        for channel in self.channels:
            new_img.add_channel(channel.copy())
        for path in self.paths:
            new_img.add_path(path.copy())
        new_img.selection.pixels = self.selection.pixels.copy()
        new_img.fg_color = self.fg_color
        new_img.bg_color = self.bg_color
        new_img.color_profile = self.color_profile
        new_img.metadata = dict(self.metadata)
        new_img._dirty = False
        return new_img

    def flatten(self) -> GimpLayer:
        result = GimpLayer(self.width, self.height, "Flattened",
                           self.image_type, has_alpha=False)
        result.pixels = result.pixels
        for layer in reversed(self.layers):
            if not layer.visible:
                continue
            _composite_layer(result, layer)
        self.layers.clear()
        self.add_layer(result)
        self._dirty = True
        return result

    def merge_visible_layers(self, name: str = "Merged") -> GimpLayer:
        result = GimpLayer(self.width, self.height, name,
                           self.image_type, has_alpha=True)
        visible = [l for l in self.layers if l.visible]
        for layer in reversed(visible):
            _composite_layer(result, layer)
        for layer in visible:
            self.layers.remove(layer)
        self.add_layer(result)
        self._dirty = True
        return result

    def merge_down(self, layer: GimpLayer) -> Optional[GimpLayer]:
        if layer not in self.layers:
            raise ImageError("Layer not in image")
        idx = self.layers.index(layer)
        if idx == 0:
            return None
        below = self.layers[idx - 1]
        _composite_layer(below, layer)
        self.remove_layer(layer)
        return below

    def has_transparency(self) -> bool:
        for layer in self.layers:
            if layer.has_alpha:
                alpha = layer.pixels[:, :, -1]
                if np.any(alpha < 255):
                    return True
        return False

    def resize(self, new_width: int, new_height: int,
               offset_x: int = 0, offset_y: int = 0) -> None:
        if new_width <= 0 or new_height <= 0:
            raise ImageError("Dimensions must be positive")
        for layer in self.layers:
            layer.resize(new_width, new_height,
                         layer.offset_x - offset_x, layer.offset_y - offset_y)
        for channel in self.channels:
            channel.resize(new_width, new_height, -offset_x, -offset_y)
        self.selection.resize(new_width, new_height, -offset_x, -offset_y)
        self.width = new_width
        self.height = new_height
        self._dirty = True

    def resize_to_layers(self) -> None:
        if not self.layers:
            return
        min_x = min(l.offset_x for l in self.layers)
        min_y = min(l.offset_y for l in self.layers)
        max_x = max(l.offset_x + l.width for l in self.layers)
        max_y = max(l.offset_y + l.height for l in self.layers)
        new_w = max_x - min_x
        new_h = max_y - min_y
        self.resize(new_w, new_h, min_x, min_y)

    def scale(self, new_width: int, new_height: int,
              interpolation: InterpolationType = InterpolationType.CUBIC) -> None:
        if new_width <= 0 or new_height <= 0:
            raise ImageError("Dimensions must be positive")
        for layer in self.layers:
            layer.scale(new_width, new_height, interpolation.value)
        for channel in self.channels:
            channel.scale(new_width, new_height)
        self.selection.scale(new_width, new_height)
        self.width = new_width
        self.height = new_height
        self._dirty = True

    def crop(self, x: int, y: int, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ImageError("Crop dimensions must be positive")
        for layer in self.layers:
            new_pixels = np.zeros((height, width, *layer.pixels.shape[2:]),
                                  dtype=np.uint8)
            src_x = max(0, x - layer.offset_x)
            src_y = max(0, y - layer.offset_y)
            dst_x = max(0, layer.offset_x - x)
            dst_y = max(0, layer.offset_y - y)
            copy_w = min(layer.width - src_x, width - dst_x)
            copy_h = min(layer.height - src_y, height - dst_y)
            if copy_w > 0 and copy_h > 0:
                new_pixels[dst_y:dst_y+copy_h, dst_x:dst_x+copy_w] = \
                    layer.pixels[src_y:src_y+copy_h, src_x:src_x+copy_w]
            layer.pixels = new_pixels
            layer.width = width
            layer.height = height
            layer.offset_x = max(0, layer.offset_x - x)
            layer.offset_y = max(0, layer.offset_y - y)
        self.selection.pixels = self.selection.pixels[
            max(0,y):min(self.height,y+height),
            max(0,x):min(self.width,x+width)
        ].copy()
        self.selection.width = width
        self.selection.height = height
        self.width = width
        self.height = height
        self._dirty = True

    def autocrop(self) -> None:
        if not self.layers:
            return
        min_x, min_y = self.width, self.height
        max_x, max_y = 0, 0
        for layer in self.layers:
            if not layer.visible:
                continue
            if layer.has_alpha:
                alpha = layer.pixels[:, :, -1]
                nonzero = np.nonzero(alpha)
                if len(nonzero[0]) == 0:
                    continue
                ly_min = int(nonzero[0].min()) + layer.offset_y
                lx_min = int(nonzero[1].min()) + layer.offset_x
                ly_max = int(nonzero[0].max()) + 1 + layer.offset_y
                lx_max = int(nonzero[1].max()) + 1 + layer.offset_x
            else:
                lx_min, ly_min = layer.offset_x, layer.offset_y
                lx_max = layer.offset_x + layer.width
                ly_max = layer.offset_y + layer.height
            min_x = min(min_x, lx_min)
            min_y = min(min_y, ly_min)
            max_x = max(max_x, lx_max)
            max_y = max(max_y, ly_max)
        if max_x > min_x and max_y > min_y:
            self.crop(min_x, min_y, max_x - min_x, max_y - min_y)

    def flip(self, flip_type: FlipType) -> None:
        for layer in self.layers:
            _transform.flip_layer(layer, flip_type)
        self.selection.pixels = np.flip(
            self.selection.pixels,
            axis=1 if flip_type == FlipType.HORIZONTAL else 0
        ).copy()
        self._dirty = True

    def rotate(self, rotation_type: RotationType) -> None:
        angle = rotation_type.value
        for layer in self.layers:
            _transform.rotate_layer(layer, float(angle))
        if angle in (90, 270):
            self.width, self.height = self.height, self.width
            self.selection.pixels = np.rot90(self.selection.pixels,
                                             k=1 if angle == 90 else 3)
        else:
            self.selection.pixels = np.rot90(self.selection.pixels, k=2)
        self.selection.width = self.width
        self.selection.height = self.height
        self._dirty = True

    def convert_rgb(self) -> None:
        if self.image_type == ImageType.RGB:
            return
        for layer in self.layers:
            if layer.image_type == ImageType.GRAY:
                gray = layer.pixels[:, :, 0]
                actual_channels = layer.pixels.shape[2] if layer.pixels.ndim == 3 else 1
                has_alpha = layer.has_alpha and actual_channels >= 2
                new_channels = 4 if has_alpha else 3
                new_pixels = np.zeros((*gray.shape, new_channels), dtype=np.uint8)
                new_pixels[:, :, 0] = gray
                new_pixels[:, :, 1] = gray
                new_pixels[:, :, 2] = gray
                if has_alpha:
                    new_pixels[:, :, 3] = layer.pixels[:, :, 1]
                else:
                    layer.has_alpha = False
                layer.pixels = new_pixels
                layer.image_type = ImageType.RGB
        self.image_type = ImageType.RGB
        self._dirty = True

    def convert_grayscale(self) -> None:
        if self.image_type == ImageType.GRAY:
            return
        for layer in self.layers:
            if layer.image_type == ImageType.RGB:
                gray = _color.desaturate(layer.pixels)[:, :, 0]
                actual_channels = layer.pixels.shape[2] if layer.pixels.ndim == 3 else 1
                has_alpha = layer.has_alpha and actual_channels >= 4
                if has_alpha:
                    new_pixels = np.zeros((*gray.shape, 2), dtype=np.uint8)
                    new_pixels[:, :, 0] = gray
                    new_pixels[:, :, 1] = layer.pixels[:, :, 3]
                else:
                    new_pixels = gray[:, :, np.newaxis]
                    layer.has_alpha = False
                layer.pixels = new_pixels
                layer.image_type = ImageType.GRAY
        self.image_type = ImageType.GRAY
        self._dirty = True

    def convert_indexed(self, max_colors: int = 256,
                        palette_type: ConvertPaletteType = ConvertPaletteType.GENERATE,
                        dither: ConvertDitherType = ConvertDitherType.NONE) -> None:
        if self.image_type == ImageType.INDEXED:
            return
        self.convert_rgb()
        all_pixels = np.vstack([l.pixels[:, :, :3].reshape(-1, 3)
                                for l in self.layers if l.pixels.size > 0])
        unique = np.unique(all_pixels, axis=0)
        if len(unique) <= max_colors:
            self._colormap = unique
        else:
            indices = np.random.choice(len(unique), max_colors, replace=False)
            self._colormap = unique[indices]
        self.image_type = ImageType.INDEXED
        self._dirty = True

    def convert_precision(self, new_precision: Precision) -> None:
        self.precision = new_precision
        self._dirty = True

    def set_color_profile(self, profile) -> None:
        self.color_profile = profile
        self._dirty = True

    def set_metadata(self, key: str, value) -> None:
        self.metadata[key] = value
        self._dirty = True

    def get_metadata(self, key: str, default=None):
        return self.metadata.get(key, default)

    def add_guide(self, orientation: GuideOrientation, position: float) -> dict:
        guide = {"orientation": orientation, "position": position}
        self.guides.append(guide)
        return guide

    def remove_guide(self, index: int) -> None:
        if 0 <= index < len(self.guides):
            self.guides.pop(index)

    def set_grid_spacing(self, x: float, y: float) -> None:
        self.grid_spacing_x = x
        self.grid_spacing_y = y

    def set_grid_offset(self, x: float, y: float) -> None:
        self.grid_offset_x = x
        self.grid_offset_y = y

    def set_resolution(self, x: float, y: float) -> None:
        self.resolution_x = x
        self.resolution_y = y

    def pick_color(self, x: int, y: int,
                   sample_merged: bool = False) -> Tuple[int, ...]:
        if sample_merged:
            composite = self.get_projection()
            if 0 <= x < self.width and 0 <= y < self.height:
                return tuple(composite[y, x])
        else:
            layer = self.active_layer
            if layer:
                lx = x - layer.offset_x
                ly = y - layer.offset_y
                if 0 <= lx < layer.width and 0 <= ly < layer.height:
                    return tuple(layer.pixels[ly, lx])
        raise ImageError(f"Cannot pick color at ({x}, {y})")

    def get_projection(self) -> np.ndarray:
        result = GimpLayer(self.width, self.height, "Projection",
                           self.image_type, has_alpha=True)
        for layer in self.layers:
            if layer.visible:
                _composite_layer(result, layer)
        return result.pixels

    def get_histogram(self, channel=None):
        from .enums import HistogramChannel
        from .color import compute_histogram
        if self.active_layer is None:
            raise ImageError("No active layer")
        ch = channel or HistogramChannel.VALUE
        return compute_histogram(self.active_layer.pixels, ch)

    def brightness_contrast(self, brightness: float = 0, contrast: float = 0) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.brightness_contrast(
            self.active_layer.pixels, brightness, contrast
        )
        self._push_layer_undo("Brightness-Contrast", old)

    def adjust_levels(self, **kwargs) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.levels(self.active_layer.pixels, **kwargs)
        self._push_layer_undo("Levels", old)

    def auto_levels(self) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.levels_stretch(self.active_layer.pixels)
        self._push_layer_undo("Auto Levels", old)

    def adjust_curves(self, curve_points, channel: int = -1) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.curves(
            self.active_layer.pixels, curve_points, channel
        )
        self._push_layer_undo("Curves", old)

    def adjust_hue_saturation(self, hue_offset=0, saturation=0, lightness=0) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.hue_saturation(
            self.active_layer.pixels, hue_offset, saturation, lightness
        )
        self._push_layer_undo("Hue-Saturation", old)

    def adjust_color_balance(self, **kwargs) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.color_balance(self.active_layer.pixels, **kwargs)
        self._push_layer_undo("Color Balance", old)

    def desaturate(self, mode=None) -> None:
        from .enums import DesaturateMode
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.desaturate(
            self.active_layer.pixels, mode or DesaturateMode.LUMINANCE
        )
        self._push_layer_undo("Desaturate", old)

    def colorize(self, color, lightness=0.5) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.colorize(self.active_layer.pixels, color, lightness)
        self._push_layer_undo("Colorize", old)

    def posterize(self, levels: int = 4) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.posterize(self.active_layer.pixels, levels)
        self._push_layer_undo("Posterize", old)

    def threshold(self, value: int = 127) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.threshold(self.active_layer.pixels, value)
        self._push_layer_undo("Threshold", old)

    def invert(self) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.invert(self.active_layer.pixels)
        self._push_layer_undo("Invert", old)

    def equalize(self) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.equalize(self.active_layer.pixels)
        self._push_layer_undo("Equalize", old)

    def shadows_highlights(self, **kwargs) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        self.active_layer.pixels = _color.shadows_highlights(self.active_layer.pixels, **kwargs)
        self._push_layer_undo("Shadows-Highlights", old)

    def fill(self, fill_type: FillType = FillType.FOREGROUND) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        color = self.fg_color if fill_type == FillType.FOREGROUND else self.bg_color
        _drawable.drawable_fill(self.active_layer, fill_type, color)
        self._push_layer_undo("Fill", old)

    def bucket_fill(self, x: int, y: int,
                    fill_type: FillType = FillType.FOREGROUND,
                    threshold: int = 15) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        color = self.fg_color if fill_type == FillType.FOREGROUND else self.bg_color
        _drawable.drawable_bucket_fill(
            self.active_layer, x, y, fill_type, color, threshold
        )
        self._push_layer_undo("Bucket Fill", old)

    def gradient_fill(self, **kwargs) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        _drawable.drawable_gradient_fill(self.active_layer, **kwargs)
        self._push_layer_undo("Gradient Fill", old)

    def stroke_selection(self, stroke_width: float = 1.0,
                         color: Tuple[int, ...] = None) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        c = color or self.fg_color + (255,)
        _drawable.drawable_edit_stroke_selection(
            self.active_layer, self.selection.pixels, stroke_width, c
        )
        self._push_layer_undo("Stroke Selection", old)

    def offset(self, dx: int, dy: int, wrap: bool = False) -> None:
        if self.active_layer is None:
            raise ImageError("No active layer")
        old = self.active_layer.pixels.copy()
        _drawable.drawable_offset(self.active_layer, dx, dy, wrap)
        self._push_layer_undo("Offset", old)

    def undo(self) -> Optional[str]:
        return self.undo_stack.undo()

    def redo(self) -> Optional[str]:
        return self.undo_stack.redo()

    def begin_undo_group(self, name: str) -> None:
        self.undo_stack.begin_group(name)

    def end_undo_group(self) -> None:
        self.undo_stack.end_group()

    def _push_layer_undo(self, name: str, old_pixels: np.ndarray) -> None:
        layer = self.active_layer
        new_pixels = layer.pixels.copy()

        def undo_fn():
            layer.pixels = old_pixels.copy()

        def redo_fn():
            layer.pixels = new_pixels.copy()

        step = UndoStep(UndoType.LAYER_PIXELS, name, undo_fn, redo_fn)
        self.undo_stack.push(step)
        self._dirty = True

    def load(self, filepath: str) -> None:
        from .fileio import load_image
        data = load_image(filepath)
        self.width = data["width"]
        self.height = data["height"]
        self.image_type = data["image_type"]
        self.selection = GimpSelection(self.width, self.height)
        self.layers.clear()
        for ld in data.get("layers", []):
            pixels = ld["pixels"]
            has_alpha = ld.get("has_alpha", pixels.shape[2] == 4 if pixels.ndim == 3 else False)
            layer = GimpLayer(
                pixels.shape[1], pixels.shape[0],
                ld.get("name", "Layer"),
                self.image_type, has_alpha=has_alpha
            )
            layer.pixels = pixels
            self.add_layer(layer)

    def save(self, filepath: str, **kwargs) -> None:
        from .fileio import save_image
        data = {
            "width": self.width,
            "height": self.height,
            "image_type": self.image_type,
            "layers": [{"pixels": l.pixels, "name": l.name,
                        "has_alpha": l.has_alpha,
                        "offset_x": l.offset_x, "offset_y": l.offset_y,
                        "opacity": l.opacity} for l in self.layers],
        }
        save_image(filepath, data, **kwargs)
        self._dirty = False

    def __repr__(self):
        return (f"GimpImage({self.width}x{self.height}, "
                f"{self.image_type.value}, "
                f"{len(self.layers)} layers)")
