"""
Enumerations extracted from GIMP source code.
Maps directly to GIMP's core enums defined in libgimpbase/gimpbaseenums.h.
"""

from enum import Enum, IntEnum


class ImageType(Enum):
    RGB = "RGB"
    GRAY = "GRAY"
    INDEXED = "INDEXED"


class Precision(Enum):
    U8 = "u8"
    U16 = "u16"
    U32 = "u32"
    HALF = "half"
    FLOAT = "float"
    DOUBLE = "double"


class LayerMode(Enum):
    NORMAL = "normal"
    DISSOLVE = "dissolve"
    BEHIND = "behind"
    ERASE = "erase"
    ANTI_ERASE = "anti-erase"
    MERGE = "merge"
    SPLIT = "split"
    PASS_THROUGH = "pass-through"
    REPLACE = "replace"
    OVERWRITE = "overwrite"

    ADDITION = "addition"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN_ONLY = "darken-only"
    LIGHTEN_ONLY = "lighten-only"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"
    SOFTLIGHT = "softlight"
    GRAIN_EXTRACT = "grain-extract"
    GRAIN_MERGE = "grain-merge"
    COLOR_DODGE = "color-dodge"
    COLOR_BURN = "color-burn"
    LINEAR_DODGE = "linear-dodge"
    LINEAR_BURN = "linear-burn"
    VIVID_LIGHT = "vivid-light"
    LINEAR_LIGHT = "linear-light"
    PIN_LIGHT = "pin-light"
    HARD_MIX = "hard-mix"

    HSV_HUE = "hsv-hue"
    HSV_SATURATION = "hsv-saturation"
    HSL_COLOR = "hsl-color"
    HSV_VALUE = "hsv-value"
    LCH_HUE = "lch-hue"
    LCH_CHROMA = "lch-chroma"
    LCH_COLOR = "lch-color"
    LCH_LIGHTNESS = "lch-lightness"

    LEGACY_MULTIPLY = "multiply-legacy"
    LEGACY_SCREEN = "screen-legacy"
    LEGACY_DARKEN_ONLY = "darken-only-legacy"
    LEGACY_LIGHTEN_ONLY = "lighten-only-legacy"
    LEGACY_ADDITION = "addition-legacy"
    LEGACY_SUBTRACT = "subtract-legacy"
    LEGACY_DIFFERENCE = "difference-legacy"
    LEGACY_DODGE = "dodge-legacy"
    LEGACY_BURN = "burn-legacy"
    LEGACY_HARDLIGHT = "hardlight-legacy"
    LEGACY_SOFTLIGHT = "softlight-legacy"
    LEGACY_GRAIN_EXTRACT = "grain-extract-legacy"
    LEGACY_GRAIN_MERGE = "grain-merge-legacy"
    LEGACY_HSV_HUE = "hsv-hue-legacy"
    LEGACY_HSV_SATURATION = "hsv-saturation-legacy"
    LEGACY_HSL_COLOR = "hsl-color-legacy"
    LEGACY_HSV_VALUE = "hsv-value-legacy"


class CompositeSpace(Enum):
    AUTO = "auto"
    RGB_LINEAR = "rgb-linear"
    RGB_PERCEPTUAL = "rgb-perceptual"
    LAB = "lab"


class CompositeMode(Enum):
    AUTO = "auto"
    UNION = "union"
    CLIP_TO_BACKDROP = "clip-to-backdrop"
    CLIP_TO_LAYER = "clip-to-layer"
    INTERSECTION = "intersection"


class FillType(Enum):
    FOREGROUND = "foreground"
    BACKGROUND = "background"
    WHITE = "white"
    TRANSPARENT = "transparent"
    PATTERN = "pattern"


class StrokeMethod(Enum):
    LINE = "line"
    PAINT_TOOL = "paint-tool"


class LineCapStyle(Enum):
    BUTT = "butt"
    ROUND = "round"
    SQUARE = "square"


class LineJoinStyle(Enum):
    MITER = "miter"
    ROUND = "round"
    BEVEL = "bevel"


class InterpolationType(Enum):
    NONE = "none"
    LINEAR = "linear"
    CUBIC = "cubic"
    NOHALO = "nohalo"
    LOHALO = "lohalo"


class TransformResize(Enum):
    ADJUST = "adjust"
    CLIP = "clip"
    CROP = "crop"
    CROP_WITH_ASPECT = "crop-with-aspect"


class RotationType(Enum):
    ROTATE_90 = 90
    ROTATE_180 = 180
    ROTATE_270 = 270


class FlipType(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class ChannelType(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    ALPHA = "alpha"


class DesaturateMode(Enum):
    LIGHTNESS = "lightness"
    LUMINANCE = "luminance"
    VALUE = "value"


class HistogramChannel(Enum):
    VALUE = "value"
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    ALPHA = "alpha"


class GradientType(Enum):
    LINEAR = "linear"
    BI_LINEAR = "bi-linear"
    RADIAL = "radial"
    SQUARE = "square"
    CONICAL_SYMMETRIC = "conical-symmetric"
    CONICAL_ASYMMETRIC = "conical-asymmetric"
    SHAPEBURST_ANGULAR = "shapeburst-angular"
    SHAPEBURST_SPHERICAL = "shapeburst-spherical"
    SHAPEBURST_DIMPLED = "shapeburst-dimpled"
    SPIRAL_CLOCKWISE = "spiral-clockwise"
    SPIRAL_COUNTERCLOCKWISE = "spiral-counterclockwise"


class RepeatMode(Enum):
    NONE = "none"
    SAWTOOTH = "sawtooth"
    TRIANGULAR = "triangular"


class BlendColorSpace(Enum):
    AUTO = "auto"
    RGB_LINEAR = "rgb-linear"
    RGB_PERCEPTUAL = "rgb-perceptual"


class BrushShape(Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    DIAMOND = "diamond"


class PaintMode(Enum):
    NORMAL = "normal"
    BEHIND = "behind"
    ERASE = "erase"


class ConvertDitherType(Enum):
    NONE = "none"
    FS = "fs"
    FS_LOW_BLEED = "fs-low-bleed"
    POSITIONED = "positioned"


class ConvertPaletteType(Enum):
    GENERATE = "generate"
    MONO = "mono"
    CUSTOM = "custom"
    WEB = "web"


class GuideOrientation(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class GridStyle(Enum):
    DOTS = "dots"
    INTERSECTIONS = "intersections"
    ON_OFF_DASH = "on-off-dash"
    SOLID = "solid"


class SelectionOperation(Enum):
    REPLACE = "replace"
    ADD = "add"
    SUBTRACT = "subtract"
    INTERSECT = "intersect"


class MaskApplyMode(Enum):
    APPLY = "apply"
    DISCARD = "discard"


class InkBlobType(Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    DIAMOND = "diamond"


class ConvolveType(IntEnum):
    BLUR = 0
    SHARPEN = 1


class DodgeBurnType(IntEnum):
    DODGE = 0
    BURN = 1


class BucketFillArea(Enum):
    SIMILAR_COLORS = "similar-colors"
    BY_LINE_ART = "by-line-art"


class OrientationType(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class TextJustification(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    FILL = "fill"


class TextDirection(Enum):
    LTR = "ltr"
    RTL = "rtl"
    TTB_RTL = "ttb-rtl"
    TTB_RTL_UPRIGHT = "ttb-rtl-upright"
    TTB_LTR = "ttb-ltr"
    TTB_LTR_UPRIGHT = "ttb-ltr-upright"
