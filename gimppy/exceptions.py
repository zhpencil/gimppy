"""
Exception classes for gimppy.
"""


class GimpError(Exception):
    """Base exception for all gimppy errors."""
    pass


class ImageError(GimpError):
    """Error related to image operations."""
    pass


class LayerError(GimpError):
    """Error related to layer operations."""
    pass


class ChannelError(GimpError):
    """Error related to channel operations."""
    pass


class SelectionError(GimpError):
    """Error related to selection operations."""
    pass


class FileIOError(GimpError):
    """Error related to file I/O operations."""
    pass


class ColorError(GimpError):
    """Error related to color operations."""
    pass


class TransformError(GimpError):
    """Error related to transform operations."""
    pass


class PaintError(GimpError):
    """Error related to paint operations."""
    pass


class FilterError(GimpError):
    """Error related to filter operations."""
    pass


class PathError(GimpError):
    """Error related to path/vector operations."""
    pass


class TextError(GimpError):
    """Error related to text operations."""
    pass


class UndoError(GimpError):
    """Error related to undo operations."""
    pass


class ResourceError(GimpError):
    """Error related to resource operations."""
    pass


class ValidationError(GimpError):
    """Error raised when input validation fails."""
    pass
