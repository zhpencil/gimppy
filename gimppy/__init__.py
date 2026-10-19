"""
gimppy — A Python class library extracted from GIMP source code.

Provides core image manipulation functionality modeled after GIMP's
architecture: layers, channels, selections, paths, painting, filters,
color adjustments, transforms, text, and file I/O.

Usage:
    from gimppy import GimpImage, GimpLayer, GimpSelection
    from gimppy.enums import ImageType, LayerMode, FillType

    img = GimpImage(800, 600, ImageType.RGB)
    layer = img.new_layer("Background", FillType.WHITE)
    img.brightness_contrast(brightness=0.1, contrast=0.2)
    img.save("output.png")
"""

__version__ = "1.0.0"
__all__ = [
    "GimpImage",
    "GimpLayer",
    "GimpGroupLayer",
    "GimpLayerMask",
    "GimpChannel",
    "GimpSelection",
    "GimpPath",
    "Stroke",
    "Anchor",
    "GimpText",
    "GimpTextLayer",
    "GimpBrush",
    "GimpPattern",
    "GimpGradient",
    "GimpPalette",
    "GimpDynamics",
    "GimpFilter",
    "FilterStack",
    "UndoStack",
    "UndoStep",
    "UndoType",
    "Brush",
    "PaintOptions",
    "Matrix3",
    "Vector2",
    "Vector3",
]

from .image import GimpImage
from .layer import GimpLayer, GimpGroupLayer, GimpLayerMask
from .channel import GimpChannel
from .selection import GimpSelection
from .path import GimpPath, Stroke, Anchor
from .text import GimpText, GimpTextLayer
from .resource import GimpBrush, GimpPattern, GimpGradient, GimpPalette, GimpDynamics
from .filter import GimpFilter, FilterStack
from .undo import UndoStack, UndoStep, UndoType
from .paint import Brush, PaintOptions
from .math_utils import Matrix3, Vector2, Vector3
from .exceptions import (
    GimpError, ImageError, LayerError, ChannelError,
    SelectionError, FileIOError, ColorError, TransformError,
    PaintError, FilterError, PathError, TextError, UndoError,
    ResourceError, ValidationError,
)
