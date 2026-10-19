# gimppy

> A Python class library extracted from [GIMP](https://www.gimp.org/) source code, providing programmatic image manipulation with an API modeled after GIMP's internal architecture.

<p align="center">
  <strong>Python >= 3.8</strong> &nbsp;|&nbsp; <strong>numpy</strong> &nbsp;|&nbsp; <strong>Pillow</strong> (optional) &nbsp;|&nbsp; <strong>GPL-3.0</strong>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Reference](#api-reference)
  - [GimpImage — Central Image Object](#gimpimage--central-image-object)
  - [Layers & Groups](#layers--groups)
  - [Selections](#selections)
  - [Channels](#channels)
  - [Color Adjustments](#color-adjustments)
  - [Geometric Transforms](#geometric-transforms)
  - [Paint Engine](#paint-engine)
  - [Vector Paths](#vector-paths)
  - [Text Rendering](#text-rendering)
  - [Resources](#resources)
  - [Filters](#filters)
  - [Undo System](#undo-system)
  - [Math Utilities](#math-utilities)
  - [File I/O](#file-io)
  - [Enumerations](#enumerations)
  - [Exceptions](#exceptions)
- [Examples](#examples)
- [Requirements](#requirements)
- [License](#license)
- [Credits](#credits)

---

## Overview

gimppy brings GIMP's powerful image processing capabilities to Python. Every major subsystem — layers, selections, paths, painting, color adjustments, transforms, filters, undo — is implemented as a Python class that mirrors the corresponding GIMP C structure.

Key design principles:

- **GIMP-faithful API** — Class names, method names, and behavior follow GIMP's internal architecture (`gimpimage.c`, `gimplayer.c`, `gimpselection.c`, etc.)
- **numpy-native** — All pixel data is stored as `numpy.ndarray` with `uint8` dtype in RGBA (4-channel) format
- **Pure Python** — Image processing algorithms implemented from scratch; no OpenCV dependency
- **Non-destructive** — Filter stacks and undo system allow reversible editing workflows
- **Pillow integration** — Optional Pillow dependency for TrueType text rendering and extended file format support (JPEG, BMP, TIFF, WebP, PSD, GIF)

---

## Installation

```bash
pip install gimppy
```

For text rendering and additional image format support (JPEG, BMP, TIFF, WebP, PSD, GIF):

```bash
pip install gimppy[pillow]
```

For development (includes test dependencies):

```bash
pip install gimppy[dev]
```

---

## Quick Start

```python
from gimppy import GimpImage
from gimppy.enums import ImageType, FillType, LayerMode

# Create a new 800x600 RGB image
img = GimpImage(800, 600, ImageType.RGB, name="My Image")

# Add layers
bg = img.new_layer("Background", FillType.WHITE)
fg = img.new_layer("Foreground")
fg.set_opacity(0.7)
fg.set_mode(LayerMode.MULTIPLY)

# Apply color adjustments
img.brightness_contrast(brightness=0.1, contrast=0.2)
img.adjust_hue_saturation(hue_offset=30, saturation=0.3)

# Save in multiple formats
img.save("output.png")
img.save("output.jpg", quality=95)
```

---

## Architecture

gimppy mirrors GIMP's internal object hierarchy:

```
GimpImage
├── layers[]              → GimpLayer / GimpGroupLayer
│   ├── pixels            → numpy ndarray (H x W x 4, RGBA uint8)
│   ├── mask              → GimpLayerMask
│   ├── opacity           → float (0.0 - 1.0)
│   └── mode              → LayerMode enum
├── channels[]            → GimpChannel
├── paths[]               → GimpPath
│   └── strokes[]         → Stroke
│       └── anchors[]     → Anchor
├── selection             → GimpSelection (extends GimpChannel)
├── guides[]              → {orientation, position}
├── grid                  → {spacing, offset, style}
── undo_stack            → UndoStack
│   ├── undo[]            → UndoStep / UndoGroup
│   └── redo[]            → UndoStep / UndoGroup
└── filter_stack          → FilterStack
    └── filters[]         → GimpFilter
```

All pixel operations work on 4-channel RGBA arrays. When loading 3-channel RGB images (e.g., JPEG), an alpha channel is automatically added.

---

## API Reference

### GimpImage — Central Image Object

The `GimpImage` class is the entry point for all operations. It manages layers, channels, paths, selection, guides, grid, color profile, metadata, and the undo stack.

```python
from gimppy import GimpImage
from gimppy.enums import ImageType, Precision

img = GimpImage(
    width=800,
    height=600,
    image_type=ImageType.RGB,        # RGB | GRAY | INDEXED
    precision=Precision.U8,          # U8 | U16 | U32 | HALF | FLOAT | DOUBLE
    name="Untitled"
)
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Image name |
| `width` | `int` | Image width in pixels |
| `height` | `int` | Image height in pixels |
| `image_type` | `ImageType` | Color mode (RGB/GRAY/INDEXED) |
| `precision` | `Precision` | Channel precision |
| `resolution_x` | `float` | Horizontal DPI |
| `resolution_y` | `float` | Vertical DPI |
| `unit` | `str` | Distance unit |
| `active_layer` | `GimpLayer` | Currently active layer |
| `active_channel` | `GimpChannel` | Currently active channel |
| `active_path` | `GimpPath` | Currently active path |
| `fg_color` | `tuple` | Foreground color (R, G, B, A) |
| `bg_color` | `tuple` | Background color (R, G, B, A) |
| `selection` | `GimpSelection` | Active selection |
| `layers` | `list` | All layers |
| `channels` | `list` | All channels |
| `paths` | `list` | All paths |
| `guides` | `list` | Guide lines |
| `undo_stack` | `UndoStack` | Undo history |
| `is_dirty` | `bool` | Whether image has unsaved changes |

**Layer Management:**

```python
# Create and add layers
layer = img.new_layer("Layer 1", fill_type=FillType.WHITE, opacity=1.0, mode=LayerMode.NORMAL)
group = img.new_group_layer("Group")
text_layer = img.new_text_layer("Hello", font="Sans-serif", size=24.0, color=(0, 0, 0))
visible_layer = img.new_layer_from_visible("Visible Composite")

img.add_layer(layer, position=-1)   # -1 = top of stack
img.remove_layer(layer)

# Layer ordering
img.raise_item(layer)
img.lower_item(layer)
img.raise_item_to_top(layer)
img.lower_item_to_bottom(layer)
img.get_item_position(layer)
```

**Image Operations:**

```python
# Duplicate / flatten / merge
dup = img.duplicate()
flat = img.flatten()                        # Returns flattened layer
merged = img.merge_visible_layers("Merged") # Merge all visible layers
img.merge_down(layer)                       # Merge layer with one below

# Resize / scale / crop
img.resize(1024, 768, offset_x=0, offset_y=0)
img.scale(1024, 768, interpolation=InterpolationType.CUBIC)
img.crop(10, 10, 200, 200)
img.autocrop()
img.resize_to_layers()

# Flip / rotate
from gimppy.enums import FlipType, RotationType
img.flip(FlipType.HORIZONTAL)
img.rotate(RotationType.ROTATE_90)

# Color mode conversion
img.convert_rgb()
img.convert_grayscale()
img.convert_indexed(max_colors=256, palette_type=ConvertPaletteType.GENERATE)
img.convert_precision(Precision.U16)
```

**Color Adjustments (operate on active layer):**

```python
img.brightness_contrast(brightness=0.1, contrast=0.2)
img.adjust_levels(input_black=0.0, input_white=1.0, gamma=1.0)
img.auto_levels()
img.adjust_curves(curve_points=[(0.0, 0.0), (0.5, 0.7), (1.0, 1.0)])
img.adjust_hue_saturation(hue_offset=30, saturation=0.3, lightness=0.0)
img.adjust_color_balance(cyan_red=0.1, magenta_green=0.0, yellow_blue=-0.1)
img.desaturate(mode=DesaturateMode.LUMINANCE)
img.colorize(color=(0.6, 0.2, 0.8), lightness=0.5)
img.posterize(levels=4)
img.threshold(value=127)
img.invert()
img.equalize()
img.shadows_highlights(shadows=0.3, highlights=0.2)
```

**Fill & Paint:**

```python
img.fill(FillType.FOREGROUND)
img.bucket_fill(x=100, y=100, fill_type=FillType.FOREGROUND, threshold=15)
img.gradient_fill(...)
img.stroke_selection(stroke_width=2.0, color=(255, 0, 0, 255))
img.offset(dx=10, dy=20, wrap=False)
```

**Pixel Access:**

```python
color = img.pick_color(x=50, y=50, sample_merged=False)
projection = img.get_projection()           # Composite of all visible layers
histogram = img.get_histogram(channel=HistogramChannel.VALUE)
```

**Metadata, Guides, Grid:**

```python
img.set_color_profile(profile)
img.set_metadata("Author", "gimppy")
author = img.get_metadata("Author", default="Unknown")

guide = img.add_guide(GuideOrientation.HORIZONTAL, 50.0)
img.remove_guide(0)

img.set_grid_spacing(x=10.0, y=10.0)
img.set_grid_offset(x=0.0, y=0.0)
img.set_resolution(x=72.0, y=72.0)
```

**Undo:**

```python
img.undo()
img.redo()
img.begin_undo_group("My Operation")
# ... operations ...
img.end_undo_group()
```

**File I/O:**

```python
img.load("input.png")
img.save("output.png")
img.save("output.jpg", quality=95)
img.clean_all()  # Clear undo history
```

---

### Layers & Groups

#### GimpLayer

```python
from gimppy import GimpLayer
from gimppy.enums import ImageType, FillType, LayerMode

layer = GimpLayer(
    width=800,
    height=600,
    name="My Layer",
    image_type=ImageType.RGB,
    has_alpha=True,
    fill_type=FillType.TRANSPARENT
)
```

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Layer name |
| `width` / `height` | `int` | Layer dimensions |
| `pixels` | `np.ndarray` | Pixel data (H x W x 4, RGBA uint8) |
| `opacity` | `float` | Layer opacity (0.0 - 1.0) |
| `mode` | `LayerMode` | Blend mode |
| `offset_x` / `offset_y` | `int` | Layer offset from image origin |
| `visible` | `bool` | Visibility flag |
| `lock_alpha` | `bool` | Lock alpha channel |
| `lock_content` | `bool` | Lock pixel content |
| `lock_position` | `bool` | Lock position |
| `mask` | `GimpLayerMask` | Attached layer mask |

**Methods:**

```python
layer.set_offsets(x=10, y=20)
layer.set_opacity(0.8)
layer.set_mode(LayerMode.MULTIPLY)

# Layer mask
mask = layer.create_mask(from_color=False)
layer.add_mask(mask)
layer.remove_mask(MaskApplyMode.APPLY)   # APPLY | DISCARD

# Alpha
layer.add_alpha()
layer.flatten()

# Transform
layer.scale(400, 300, interpolation="cubic")
layer.resize(1024, 768, offset_x=0, offset_y=0)
layer.resize_to_image_size(img.width, img.height)

# Pixel access
pixel = layer.get_pixel(x=50, y=50)
layer.set_pixel(x=50, y=50, color=(255, 0, 0, 255))

# Bounds
bounds = layer.bounds  # (x1, y1, x2, y2)

# Copy
clone = layer.copy()
```

#### GimpGroupLayer

```python
from gimppy import GimpGroupLayer

group = GimpGroupLayer(800, 600, name="My Group")
group.add_layer(child_layer, position=-1)
group.remove_layer(child_layer)
merged = group.merge()
all_layers = group.get_all_layers(recursive=True)
```

#### GimpLayerMask

```python
from gimppy import GimpLayerMask

mask = GimpLayerMask(800, 600, name="Mask")
mask.fill(255)          # Fill with value (0-255)
mask.invert()
mask.apply()            # Apply mask to parent layer
mask.discard()          # Remove without applying
mask.copy()
bounds = mask.bounds
```

---

### Selections

`GimpSelection` extends `GimpChannel` with shape-based selection operations and boolean algebra.

```python
from gimppy import GimpSelection
from gimppy.enums import SelectionOperation

sel = GimpSelection(800, 600)

# Shape selections
sel.select_all()
sel.select_none()
sel.select_invert()
sel.select_rectangle(x=10, y=10, width=100, height=100,
                     operation=SelectionOperation.REPLACE, antialias=True)
sel.select_ellipse(x=10, y=10, width=100, height=100,
                   operation=SelectionOperation.ADD, antialias=True)
sel.select_polygon(points=[(10,10), (100,10), (100,100), (10,100)],
                   operation=SelectionOperation.REPLACE, antialias=True)
sel.select_round_rectangle(x=10, y=10, width=100, height=100,
                           corner_radius=10, operation=SelectionOperation.REPLACE)

# Color-based selections
sel.select_by_color(image_pixels, x=50, y=50, threshold=15, antialias=True)
sel.select_contiguous_color(image_pixels, x=50, y=50, threshold=15)

# Modify selection
sel.feather(radius=5.0)
sel.sharpen()
sel.border(radius=3)
sel.grow(radius=5)
sel.shrink(radius=3)
sel.flood(x=50, y=50)
sel.translate(dx=10, dy=20)

# Suspend / resume (for batch operations)
sel.suspend()
# ... multiple operations ...
sel.resume()

# Query
bounds = sel.get_bounds()
boundary = sel.get_boundary()        # List of contour point lists
sel.save_to_channel(channel)         # Save selection to a channel
```

**SelectionOperation values:** `REPLACE`, `ADD`, `SUBTRACT`, `INTERSECT`

---

### Channels

```python
from gimppy import GimpChannel

ch = GimpChannel(800, 600, name="Alpha Copy", opacity=1.0, color=(255, 0, 0))

ch.fill(255)
ch.clear()
ch.invert()
ch.feather(radius=5.0)
ch.grow(radius=3)
ch.shrink(radius=3)
ch.combine(other_channel, operation="add")   # "add" | "subtract" | "intersect"
ch.scale(400, 300)
ch.resize(1024, 768, offset_x=0, offset_y=0)

val = ch.get_value(x=50, y=50)
ch.set_value(x=50, y=50, value=200)

is_empty = ch.is_empty
bounds = ch.bounds
clone = ch.copy()
```

---

### Color Adjustments

All color functions operate on `numpy.ndarray` pixel data and return a new array.

```python
from gimppy import color
from gimppy.enums import DesaturateMode, HistogramChannel

# Brightness / Contrast  (range: -1.0 to 1.0)
result = color.brightness_contrast(pixels, brightness=0.2, contrast=0.3)

# Levels
result = color.levels(pixels, input_black=0.0, input_white=1.0,
                      gamma=1.0, output_black=0.0, output_white=1.0, channel=-1)

# Auto levels (stretch histogram)
result = color.levels_stretch(pixels)

# Curves  (list of (input, output) control points, 0.0-1.0)
result = color.curves(pixels, curve_points=[(0.0, 0.0), (0.5, 0.7), (1.0, 1.0)], channel=-1)

# Hue / Saturation  (hue: -180 to 180, saturation/lightness: -1.0 to 1.0)
result = color.hue_saturation(pixels, hue_offset=90, saturation=0.5, lightness=0.0)

# Colorize  (color as HSL tuple, lightness: 0.0 to 1.0)
result = color.colorize(pixels, color=(0.6, 0.8, 0.4), lightness=0.5)

# Desaturate
result = color.desaturate(pixels, mode=DesaturateMode.LUMINANCE)
# DesaturateMode: LIGHTNESS | LUMINANCE | VALUE

# Posterize  (reduce to N levels)
result = color.posterize(pixels, levels=4)

# Threshold  (binary at value, 0-255)
result = color.threshold(pixels, value=128)

# Invert
result = color.invert(pixels)

# Equalize  (histogram equalization)
result = color.equalize(pixels)

# Color Balance  (range: -1.0 to 1.0)
result = color.color_balance(pixels, cyan_red=0.2, magenta_green=0.0, yellow_blue=-0.1,
                             shadows=True, midtones=True, highlights=True)

# Shadows / Highlights
result = color.shadows_highlights(pixels, shadows=0.3, highlights=0.2,
                                  white_point=0.0, radius=100.0, compress=0.5)

# Histogram  (returns 256-element array)
hist = color.compute_histogram(pixels, channel=HistogramChannel.VALUE)
# HistogramChannel: VALUE | RED | GREEN | BLUE | ALPHA
```

---

### Geometric Transforms

```python
from gimppy.transform import (
    transform_layer, flip_layer, rotate_layer, scale_layer,
    translate_layer, shear_layer, perspective_layer
)
from gimppy.enums import FlipType, InterpolationType, TransformResize
from gimppy import Matrix3

# Affine transform via 3x3 matrix
matrix = Matrix3.translate(50, 30) @ Matrix3.scale(1.5, 1.5) @ Matrix3.rotate(0.785)
transform_layer(layer, matrix, interpolation=InterpolationType.CUBIC,
                resize=TransformResize.ADJUST)

# Convenience transforms
flip_layer(layer, FlipType.HORIZONTAL)
rotate_layer(layer, angle_deg=45.0)
scale_layer(layer, new_width=400, new_height=300)
translate_layer(layer, dx=10, dy=20)
shear_layer(layer, shear_x=0.3, shear_y=0.0)

# Perspective transform  (4 source corners -> 4 destination corners)
perspective_layer(layer,
    src_corners=[(0,0), (100,0), (100,100), (0,100)],
    dst_corners=[(10,10), (90,0), (100,90), (0,100)])

# Coordinate transform
new_x, new_y = transform_image_coords(matrix, x=50, y=50)
```

**InterpolationType:** `NONE` (nearest), `LINEAR` (bilinear), `CUBIC` (bicubic), `NOHALO`, `LOHALO`

**TransformResize:** `ADJUST`, `CLIP`, `CROP`, `CROP_WITH_ASPECT`

---

### Paint Engine

#### Brush

```python
from gimppy import Brush
from gimppy.enums import BrushShape

brush = Brush(
    size=20.0,
    hardness=0.8,          # 0.0 (soft) to 1.0 (hard)
    shape=BrushShape.CIRCLE,  # CIRCLE | SQUARE | DIAMOND
    angle=0.0,             # Rotation angle in degrees
    aspect_ratio=1.0,      # Elliptical stretch
    spacing=0.1            # Spacing as fraction of size
)

mask = brush.get_mask()             # 2D float32 brush stamp
mask = brush.get_mask(size_override=30)  # Override size
```

#### PaintOptions

```python
from gimppy import PaintOptions

opts = PaintOptions()
opts.opacity = 0.8
opts.brush = Brush(size=15, hardness=0.7)
opts.flow = 1.0
opts.rate = 50
opts.pressure_opacity = True
opts.pressure_size = False
```

#### Stroke Functions

All stroke functions take a `GimpLayer` and a list of `(x, y)` control points.

```python
from gimppy import paint
from gimppy.enums import ConvolveType, DodgeBurnType

points = [(10, 10), (100, 50), (200, 30), (300, 80)]
color_rgba = (255, 0, 0, 255)

# Paintbrush — soft-edged brush stroke
paint.paintbrush_stroke(layer, points, color=color_rgba, options=opts)

# Pencil — hard-edged, aliased stroke
paint.pencil_stroke(layer, points, color=color_rgba, options=opts)

# Eraser — erase to transparent
paint.eraser_stroke(layer, points, options=opts)

# Airbrush — pressure-sensitive spray
paint.airbrush_stroke(layer, points, color=color_rgba, options=opts, pressure=1.0)

# Clone — copy pixels from source
paint.clone_stroke(layer, source_pixels=src_layer.pixels, points=points,
                   source_offset=(0, 0), options=opts)

# Heal — clone with color blending
paint.heal_stroke(layer, source_pixels=src_layer.pixels, points=points,
                  source_offset=(0, 0), options=opts)

# Smudge — smear existing pixels
paint.smudge_stroke(layer, points, rate=0.5, options=opts)

# Convolve — blur or sharpen
paint.convolve_stroke(layer, points, convolve_type=ConvolveType.BLUR, options=opts)
# ConvolveType: BLUR | SHARPEN

# Dodge / Burn — lighten or darken
paint.dodge_burn_stroke(layer, points, db_type=DodgeBurnType.DODGE,
                        intensity=0.5, options=opts)
# DodgeBurnType: DODGE | BURN
```

---

### Vector Paths

#### Stroke & Anchor

```python
from gimppy import Stroke, Anchor

s = Stroke(closed=False)

# Add anchors
s.moveto(10, 10)          # Move to starting point
s.lineto(100, 10)         # Straight line
s.conicto(50, 50, 100, 100)   # Quadratic Bezier
s.cubicto(30, 0, 70, 100, 100, 50)  # Cubic Bezier
s.close()                 # Close the path

# Query
length = s.get_length(precision=100)
point = s.get_point_at_distance(dist=50.0)
interpolated = s.interpolate(precision=100)  # List of (x, y)
bounds = s.get_bounds()

# Transforms
s.translate(dx=10, dy=20)
s.scale(sx=2.0, sy=1.5)
s.rotate(angle_rad=0.785)
s.flip(axis="horizontal", center=0.0)
s.reverse()

# Static constructors
s = Stroke.from_points([(10,10), (100,10), (100,100)], closed=True)
s = Stroke.ellipse(cx=100, cy=100, rx=50, ry=30)
```

#### GimpPath

```python
from gimppy import GimpPath

path = GimpPath("My Path")
path.add_stroke(stroke)
path.remove_stroke(0)
stroke = path.get_stroke(0)
count = path.stroke_count
bounds = path.get_bounds()

# Transforms
path.translate(dx=10, dy=20)
path.scale(sx=2.0, sy=1.5)
path.rotate(angle_rad=0.785)
clone = path.copy()

# Export
mask = path.to_selection_mask(width=800, height=600)  # 2D uint8 array
svg = path.to_svg()                                    # SVG path string
```

---

### Text Rendering

Text rendering uses Pillow's TrueType font engine with automatic font fallback.

```python
from gimppy import GimpText, GimpTextLayer
from gimppy.enums import TextJustification, TextDirection

# Create text object
text = GimpText(
    text="Hello, World!",
    font="Sans-serif",     # Font family name or file path
    size=24.0,             # Font size in points
    color=(0, 0, 0)        # RGB tuple
)

# Text properties
text.antialias = True
text.hint_style = "slight"
text.kerning = True
text.language = "en"
text.direction = TextDirection.LTR
text.justification = TextJustification.LEFT
text.indent = 0.0
text.line_spacing = 0.0
text.letter_spacing = 0.0
text.outline = False
text.outline_width = 1.0
text.outline_color = (0, 0, 0)

# Update text
text.set_text("New text")
text.set_markup("<b>Bold</b> text")
display = text.get_display_text()  # Strips markup tags

# Create text layer
tl = GimpTextLayer(text, name="Title")

# Properties
w = tl.width       # Actual rendered width
h = tl.height      # Actual rendered height
pixels = tl.pixels # RGBA numpy array
dynamic = tl.is_dynamic

# Operations
tl.set_text("Updated")
tl.set_markup("<i>Italic</i>")
tl.resize(400, 100)
tl.rasterize()     # Convert to static pixels
offsets = tl.get_layout_offsets()
clone = tl.copy()
```

**Font resolution order:** The specified font name is matched against system fonts in this order:
1. Windows: `C:\Windows\Fonts\`
2. macOS: `/Library/Fonts`, `/System/Library/Fonts`, `~/Library/Fonts`
3. Linux: `/usr/share/fonts`, `/usr/local/share/fonts`, `~/.fonts`

Common font family names: `"Sans-serif"`, `"Serif"`, `"Monospace"`

---

### Resources

#### GimpBrush

```python
from gimppy import GimpBrush
from gimppy.enums import BrushShape

brush = GimpBrush(
    name="My Brush",
    shape=BrushShape.CIRCLE,
    radius=10.0,
    hardness=0.8,
    spacing=0.1,
    aspect_ratio=1.0,
    angle=0.0
)

mask = brush.get_mask()
info = brush.get_info()
is_gen = brush.is_generated
```

#### GimpPattern

```python
from gimppy import GimpPattern
import numpy as np

pattern_pixels = np.tile(np.array([[255, 0, 0, 255], [0, 255, 0, 255]], dtype=np.uint8), (5, 5, 1))
pattern = GimpPattern(name="Checker", pixels=pattern_pixels)

w = pattern.width
h = pattern.height
```

#### GimpGradient

```python
from gimppy import GimpGradient
from gimppy.enums import GradientType

grad = GimpGradient("Sunset")
grad.add_segment(0.0, 0.5,
                 left_color=(255, 0, 0, 255),
                 right_color=(255, 255, 0, 255))
grad.add_segment(0.5, 1.0,
                 left_color=(255, 255, 0, 255),
                 right_color=(128, 0, 255, 255))

color = grad.get_color_at(0.3)          # RGBA tuple at position 0.0-1.0
grad.replicate(count=3)                 # Repeat gradient N times
grad.reverse()                          # Reverse gradient direction

# Render gradient to image
rendered = grad.render(800, 100, gradient_type=GradientType.LINEAR,
                       x1=0, y1=0, x2=800, y2=0)
```

**GradientType:** `LINEAR`, `BI_LINEAR`, `RADIAL`, `SQUARE`, `CONICAL_SYMMETRIC`, `CONICAL_ASYMMETRIC`, `SHAPEBURST_ANGULAR`, `SHAPEBURST_SPHERICAL`, `SHAPEBURST_DIMPLED`, `SPIRAL_CLOCKWISE`, `SPIRAL_COUNTERCLOCKWISE`

#### GimpPalette

```python
from gimppy import GimpPalette

pal = GimpPalette("Web Safe")
pal.add_color(255, 0, 0, "Red")
pal.add_color(0, 255, 0, "Green")
pal.add_color(0, 0, 255, "Blue")

count = pal.color_count
r, g, b, name = pal.get_color(0)
pal.remove_color(1)
index = pal.find_closest(200, 50, 50)
```

#### GimpDynamics

```python
from gimppy import GimpDynamics

dyn = GimpDynamics("Pressure Sensitive")
dyn.pressure_opacity = 1.0
dyn.pressure_size = 0.8
dyn.pressure_hardness = 0.5
dyn.velocity_opacity = 0.0
dyn.velocity_size = 0.0
dyn.random_opacity = 0.0
dyn.random_size = 0.0
dyn.fade_opacity = 0.0
dyn.fade_length = 0

result = dyn.apply(pressure=0.7, velocity=10.0, distance=50.0)
# Returns {"opacity": float, "size": float, "hardness": float}
```

---

### Filters

Non-destructive filter system with composable filter stacks.

```python
from gimppy import GimpFilter, FilterStack
from gimppy import color

# Create individual filters
f1 = GimpFilter("Brighten", lambda p: color.brightness_contrast(p, brightness=0.2))
f2 = GimpFilter("Sharpen", lambda p: color.levels_stretch(p))
f3 = GimpFilter("Invert", color.invert)

# Build a filter stack
stack = FilterStack()
stack.add(f1)
stack.add(f2)
stack.add(f3)

# Apply all filters in sequence
result = stack.apply_all(pixels)

# Manage filters
f = stack.get(0)
stack.remove(f1)
stack.clear()
print(len(stack))

# Filter with region restriction
f1.set_region(x=10, y=10, width=100, height=100)
f1.set_param("brightness", 0.3)
val = f1.get_param("brightness", default=0.0)

# Convenience filter functions
from gimppy.filter import (
    apply_brightness_contrast, apply_levels, apply_hue_saturation,
    apply_color_balance, apply_desaturate, apply_posterize,
    apply_threshold, apply_equalize, apply_invert,
    apply_shadows_highlights, create_filter
)

result = apply_brightness_contrast(pixels, brightness=0.1, contrast=0.2)
result = apply_hue_saturation(pixels, hue_offset=30, saturation=0.3)
f = create_filter("MyFilter", lambda p: color.invert(p), brightness=0.5)
```

---

### Undo System

Full undo/redo with grouping, freeze/thaw, and configurable depth.

```python
from gimppy import UndoStack, UndoStep, UndoType
from gimppy import UndoGroup

# Create undo stack
stack = UndoStack(max_steps=50)

# Push a step
def undo_fn():
    layer.pixels[:] = old_pixels

def redo_fn():
    layer.pixels[:] = new_pixels

step = UndoStep(UndoType.LAYER_PIXELS, "Paint Stroke", undo_fn, redo_fn)
stack.push(step)

# Undo / Redo
name = stack.undo()    # Returns step name
name = stack.redo()

# Query
can_undo = stack.can_undo
can_redo = stack.can_redo
print(stack.undo_count)
print(stack.redo_count)
print(stack.get_undo_names())
print(stack.get_redo_names())

# Group operations
stack.begin_group("Complex Operation")
stack.push(UndoStep(UndoType.LAYER_PIXELS, "Step 1", undo1, redo1))
stack.push(UndoStep(UndoType.LAYER_PIXELS, "Step 2", undo2, redo2))
stack.end_group()
# One undo() now undoes both steps

# Enable / Disable / Freeze / Thaw
stack.disable()        # Pushes are ignored
stack.enable()
stack.freeze()         # Pushes are queued but not executed
stack.thaw()
stack.clear()          # Clear all history
```

**UndoType values:** `LAYER_PIXELS`, `LAYER_PROPERTY`, `CHANNEL_PIXELS`, `CHANNEL_PROPERTY`, `IMAGE_PROPERTY`, `ITEM_ADD`, `ITEM_REMOVE`, `ITEM_REORDER`, `SELECTION`, `FILTER`, `GROUP`

---

### Math Utilities

#### Matrix3 — 3x3 Affine Transformation Matrix

```python
from gimppy import Matrix3

# Identity
m = Matrix3.identity()

# Factory methods
m = Matrix3.translate(tx=50, ty=30)
m = Matrix3.scale(sx=2.0, sy=1.5)
m = Matrix3.rotate(angle_rad=0.785)   # 45 degrees
m = Matrix3.shear(sx=0.3, sy=0.0)

# Perspective transform (4 source -> 4 destination corners)
m = Matrix3.perspective(
    0, 0, 100, 0, 100, 100, 0, 100,     # source corners
    10, 10, 90, 0, 100, 90, 0, 100       # destination corners
)

# Compose transforms (matrix multiplication)
m = Matrix3.translate(50, 30) @ Matrix3.scale(1.5, 1.5) @ Matrix3.rotate(0.785)

# Transform a point
new_x, new_y = m.transform_point(x=100, y=100)

# Matrix properties
det = m.determinant()
inv = m.inverse()
val = m[0]  # Access element by index (row-major)
```

#### Vector2 / Vector3

```python
from gimppy import Vector2, Vector3

v2 = Vector2(3.0, 4.0)
print(v2.length())        # 5.0
v2n = v2.normalize()
dot = v2.dot(Vector2(1.0, 0.0))
cross = v2.cross(Vector2(0.0, 1.0))
dist = v2.distance(Vector2(6.0, 8.0))

v3 = Vector3(1.0, 2.0, 3.0)
v3n = v3.normalize()
cross3 = v3.cross(Vector3(0.0, 1.0, 0.0))

# Arithmetic
v = Vector2(1, 2) + Vector2(3, 4)   # Vector2(4, 6)
v = Vector2(1, 2) - Vector2(3, 4)   # Vector2(-2, -2)
v = Vector2(1, 2) * 3.0             # Vector2(3, 6)
```

---

### File I/O

```python
from gimppy.fileio import load_image, save_image, get_supported_formats

# Load an image
data = load_image("photo.png")
# Returns: {
#     "width": int,
#     "height": int,
#     "image_type": ImageType,
#     "precision": Precision,
#     "layers": [{"pixels": ndarray, "name": str, "has_alpha": bool}, ...],
#     "channels": [...],
#     "source_format": str
# }

# Save an image
save_image("output.jpg", data, quality=95)
save_image("output.png", data, compress_level=6)

# Supported formats
formats = get_supported_formats()
# Always: .xcf, .bmp, .ico
# With Pillow: .png, .jpg, .jpeg, .tiff, .tif, .webp, .gif, .psd, .ppm, .pgm, .pbm
```

---

### Enumerations

gimppy provides 30+ enumeration classes covering all GIMP concepts. Import from `gimppy.enums`:

```python
from gimppy.enums import (
    # Image
    ImageType,          # RGB | GRAY | INDEXED
    Precision,          # U8 | U16 | U32 | HALF | FLOAT | DOUBLE

    # Layers
    LayerMode,          # NORMAL | MULTIPLY | SCREEN | OVERLAY | ... (40+ modes)
    FillType,           # FOREGROUND | BACKGROUND | WHITE | TRANSPARENT | PATTERN
    CompositeSpace,     # AUTO | RGB_LINEAR | RGB_PERCEPTUAL | LAB
    CompositeMode,      # AUTO | UNION | CLIP_TO_BACKDROP | CLIP_TO_LAYER | INTERSECTION
    MaskApplyMode,      # APPLY | DISCARD

    # Selection
    SelectionOperation, # REPLACE | ADD | SUBTRACT | INTERSECT

    # Color
    DesaturateMode,     # LIGHTNESS | LUMINANCE | VALUE
    HistogramChannel,   # VALUE | RED | GREEN | BLUE | ALPHA
    ConvertPaletteType, # GENERATE | MONO | CUSTOM | WEB
    ConvertDitherType,  # NONE | FS | FS_LOW_BLEED | POSITIONED

    # Transforms
    InterpolationType,  # NONE | LINEAR | CUBIC | NOHALO | LOHALO
    TransformResize,    # ADJUST | CLIP | CROP | CROP_WITH_ASPECT
    FlipType,           # HORIZONTAL | VERTICAL
    RotationType,       # ROTATE_90 | ROTATE_180 | ROTATE_270

    # Paint
    BrushShape,         # CIRCLE | SQUARE | DIAMOND
    PaintMode,          # NORMAL | BEHIND | ERASE
    ConvolveType,       # BLUR | SHARPEN
    DodgeBurnType,      # DODGE | BURN

    # Paths
    StrokeMethod,       # LINE | PAINT_TOOL
    LineCapStyle,       # BUTT | ROUND | SQUARE
    LineJoinStyle,      # MITER | ROUND | BEVEL

    # Gradients
    GradientType,       # LINEAR | RADIAL | CONICAL_SYMMETRIC | ... (11 types)
    RepeatMode,         # NONE | SAWTOOTH | TRIANGULAR
    BlendColorSpace,    # AUTO | RGB_LINEAR | RGB_PERCEPTUAL

    # Guides / Grid
    GuideOrientation,   # HORIZONTAL | VERTICAL
    GridStyle,          # DOTS | INTERSECTIONS | ON_OFF_DASH | SOLID

    # Text
    TextJustification,  # LEFT | CENTER | RIGHT | FILL
    TextDirection,      # LTR | RTL | TTB_RTL | ...

    # Channels
    ChannelType,        # RED | GREEN | BLUE | ALPHA

    # Misc
    BucketFillArea,     # SIMILAR_COLORS | BY_LINE_ART
    OrientationType,    # HORIZONTAL | VERTICAL
    InkBlobType,        # CIRCLE | SQUARE | DIAMOND
)
```

**LayerMode** includes 40+ blend modes: `NORMAL`, `DISSOLVE`, `BEHIND`, `ERASE`, `ANTI_ERASE`, `MERGE`, `SPLIT`, `PASS_THROUGH`, `REPLACE`, `OVERWRITE`, `ADDITION`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`, `SCREEN`, `OVERLAY`, `DARKEN_ONLY`, `LIGHTEN_ONLY`, `DIFFERENCE`, `EXCLUSION`, `SOFTLIGHT`, `GRAIN_EXTRACT`, `GRAIN_MERGE`, `COLOR_DODGE`, `COLOR_BURN`, `LINEAR_DODGE`, `LINEAR_BURN`, `VIVID_LIGHT`, `LINEAR_LIGHT`, `PIN_LIGHT`, `HARD_MIX`, `HSV_HUE`, `HSV_SATURATION`, `HSL_COLOR`, `HSV_VALUE`, `LCH_HUE`, `LCH_CHROMA`, `LCH_COLOR`, `LCH_LIGHTNESS`, plus 15 `LEGACY_*` variants.

---

### Exceptions

All exceptions inherit from `GimpError`:

```python
from gimppy.exceptions import (
    GimpError,          # Base exception
    ImageError,         # Image operation errors
    LayerError,         # Layer operation errors
    ChannelError,       # Channel operation errors
    SelectionError,     # Selection operation errors
    FileIOError,        # File read/write errors
    ColorError,         # Color adjustment errors
    TransformError,     # Transform operation errors
    PaintError,         # Paint engine errors
    FilterError,        # Filter operation errors
    PathError,          # Path operation errors
    TextError,          # Text rendering errors
    UndoError,          # Undo system errors
    ResourceError,      # Resource operation errors
    ValidationError,    # Parameter validation errors
)

try:
    img.undo()
except UndoError as e:
    print(f"Cannot undo: {e}")
```

---

## Examples

### Batch Image Processing

```python
from gimppy import GimpImage
from gimppy.fileio import load_image, save_image
import os

input_dir = "photos/"
output_dir = "processed/"
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if not filename.endswith((".jpg", ".png")):
        continue

    data = load_image(os.path.join(input_dir, filename))
    img = GimpImage(data["width"], data["height"], data["image_type"])

    for ld in data["layers"]:
        from gimppy import GimpLayer
        layer = GimpLayer(ld["pixels"].shape[1], ld["pixels"].shape[0],
                          ld.get("name", "Layer"), img.image_type)
        layer.pixels = ld["pixels"]
        img.add_layer(layer)

    # Apply adjustments
    img.brightness_contrast(brightness=0.1, contrast=0.15)
    img.adjust_hue_saturation(saturation=0.2)

    out_path = os.path.join(output_dir, filename.replace(".jpg", "_edited.png"))
    img.save(out_path)
    print(f"Processed: {filename}")
```

### Layer Compositing with Blend Modes

```python
from gimppy import GimpImage, GimpLayer
from gimppy.enums import ImageType, FillType, LayerMode
import numpy as np

img = GimpImage(512, 512, ImageType.RGB)

# Background: white
bg = img.new_layer("Background", FillType.WHITE)

# Red circle with Normal blend
red = img.new_layer("Red Circle")
red.set_mode(LayerMode.NORMAL)
red.set_opacity(0.8)
yy, xx = np.ogrid[:512, :512]
mask = (xx - 200)**2 + (yy - 200)**2 <= 150**2
red.pixels[mask, 0] = 255
red.pixels[mask, 3] = 204  # 80% opacity

# Blue circle with Multiply blend
blue = img.new_layer("Blue Circle")
blue.set_mode(LayerMode.MULTIPLY)
blue.set_opacity(0.6)
mask2 = (xx - 312)**2 + (yy - 312)**2 <= 150**2
blue.pixels[mask2, 2] = 255
blue.pixels[mask2, 3] = 153

img.save("composite.png")
```

### Non-Destructive Filter Workflow

```python
from gimppy import GimpImage, GimpFilter, FilterStack
from gimppy import color
from gimppy.fileio import load_image

data = load_image("photo.jpg")
img = GimpImage(data["width"], data["height"], data["image_type"])

from gimppy import GimpLayer
layer = GimpLayer(data["layers"][0]["pixels"].shape[1],
                  data["layers"][0]["pixels"].shape[0], "Photo", img.image_type)
layer.pixels = data["layers"][0]["pixels"]
img.add_layer(layer)

# Build a non-destructive filter stack
stack = FilterStack()
stack.add(GimpFilter("Warm", lambda p: color.color_balance(p, cyan_red=0.15)))
stack.add(GimpFilter("Contrast", lambda p: color.brightness_contrast(p, contrast=0.2)))
stack.add(GimpFilter("Vivid", lambda p: color.hue_saturation(p, saturation=0.3)))

# Apply
result = stack.apply_all(layer.pixels)
layer.pixels = result

img.save("filtered.png")
```

### Undo-Aware Editing

```python
from gimppy import GimpImage
from gimppy.enums import FillType

img = GimpImage(400, 400)
layer = img.new_layer("Canvas", FillType.WHITE)

# Group a series of operations as a single undo step
img.begin_undo_group("Artistic Effect")
img.invert()
img.brightness_contrast(brightness=0.2)
img.adjust_hue_saturation(hue_offset=45)
img.end_undo_group()

# One undo reverts the entire group
img.undo()   # Back to white canvas
img.redo()   # Re-apply the group
```

### Path to Selection

```python
from gimppy import GimpImage, GimpPath, Stroke
from gimppy.enums import FillType

img = GimpImage(400, 400)
layer = img.new_layer("Canvas", FillType.WHITE)

# Create a star-shaped path
path = GimpPath("Star")
s = Stroke(closed=True)
import math
for i in range(10):
    angle = math.pi * 2 * i / 10 - math.pi / 2
    r = 150 if i % 2 == 0 else 70
    x = 200 + r * math.cos(angle)
    y = 200 + r * math.sin(angle)
    if i == 0:
        s.moveto(x, y)
    else:
        s.lineto(x, y)
s.close()
path.add_stroke(s)

# Convert path to selection mask and fill
mask = path.to_selection_mask(400, 400)
layer.pixels[mask > 0] = [255, 200, 0, 255]

img.save("star.png")
```

---

## Requirements

| Dependency | Version | Required | Purpose |
|-----------|---------|----------|---------|
| Python | >= 3.8 | Yes | Runtime |
| numpy | >= 1.20 | Yes | Pixel data arrays |
| Pillow | >= 9.0 | Optional | Text rendering, JPEG/BMP/TIFF/WebP/PSD/GIF support |

---

## License

**GPL-3.0** — This library is derived from [GIMP](https://www.gimp.org/) source code and is distributed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for the full text.

---

## Credits

- **GIMP Team** — Original source code and architecture ([gimp.org](https://www.gimp.org/))
- **gimppy** — Python extraction and adaptation

<p align="center">
  <em>Powered by <a href="https://qoder.com">Qoder</a> (Qwen 3.8)</em>
</p>
