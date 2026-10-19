"""
Demo script for gimppy — the Python class library extracted from GIMP.
Shows the main features: image creation, layers, selections, painting,
color adjustments, transforms, paths, filters, and file I/O.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gimppy import (
    GimpImage, GimpLayer, GimpGroupLayer, GimpChannel,
    GimpSelection, GimpPath, Stroke, GimpText, GimpTextLayer,
    GimpBrush, GimpGradient, GimpPalette,
    GimpFilter, FilterStack,
    Brush, PaintOptions, Matrix3,
)
from gimppy.enums import (
    ImageType, LayerMode, FillType, FlipType, RotationType,
    SelectionOperation, DesaturateMode, BrushShape,
    GradientType, GuideOrientation,
)
from gimppy import color, paint, drawable


def demo_basic_image():
    print("=== Basic Image Operations ===")
    img = GimpImage(800, 600, ImageType.RGB, name="Demo")
    print(f"Created: {img}")

    bg = img.new_layer("Background", FillType.WHITE)
    fg = img.new_layer("Foreground")
    fg.pixels[100:200, 100:200] = [255, 0, 0, 255]
    print(f"Layers: {[l.name for l in img.layers]}")

    img.add_guide(GuideOrientation.HORIZONTAL, 300.0)
    img.set_grid_spacing(50.0, 50.0)
    img.set_resolution(300.0, 300.0)
    print(f"Resolution: {img.resolution_x}x{img.resolution_y} DPI")
    print(f"Image dirty: {img.is_dirty}")
    print()


def demo_selections():
    print("=== Selection Operations ===")
    img = GimpImage(200, 200)
    layer = img.new_layer("BG", FillType.WHITE)

    img.selection.select_rectangle(20, 20, 60, 60, antialias=False)
    print(f"Rectangle selection bounds: {img.selection.get_bounds()}")

    img.selection.select_ellipse(100, 100, 80, 80,
                                 SelectionOperation.ADD, antialias=False)
    print(f"After adding ellipse: {img.selection.get_bounds()}")

    img.selection.feather(5.0)
    print(f"After feathering, center value: {img.selection.pixels[140, 140]}")

    img.selection.select_invert()
    print(f"After invert, corner value: {img.selection.pixels[0, 0]}")

    img.selection.select_none()
    print(f"After clear: is_empty={img.selection.is_empty}")
    print()


def demo_color_adjustments():
    print("=== Color Adjustments ===")
    img = GimpImage(100, 100)
    layer = img.new_layer("Test")
    layer.pixels[:] = [128, 64, 192, 255]

    img.brightness_contrast(brightness=0.2, contrast=0.1)
    print(f"After brightness/contrast: {tuple(layer.pixels[0, 0])}")

    img.invert()
    print(f"After invert: {tuple(layer.pixels[0, 0])}")

    img.undo()
    print(f"After undo: {tuple(layer.pixels[0, 0])}")

    img.desaturate()
    print(f"After desaturate: {tuple(layer.pixels[0, 0])}")

    layer.pixels[:] = [128, 128, 128, 255]
    img.posterize(4)
    unique = set()
    for y in range(100):
        for x in range(100):
            unique.add(layer.pixels[y, x, 0])
    print(f"After posterize(4): {len(unique)} unique values in R channel")

    img.threshold(127)
    print(f"After threshold: {tuple(layer.pixels[0, 0])}")
    print()


def demo_painting():
    print("=== Painting Operations ===")
    img = GimpImage(200, 200)
    layer = img.new_layer("Canvas", FillType.WHITE)

    opts = PaintOptions()
    opts.brush = Brush(size=15, hardness=0.8, shape=BrushShape.CIRCLE)
    opts.opacity = 0.8

    points = [(20, 100), (60, 50), (100, 150), (140, 50), (180, 100)]
    paint.paintbrush_stroke(layer, points, (255, 0, 0, 255), opts)
    print(f"Paintbrush stroke applied, pixel at (100,150): {tuple(layer.pixels[150, 100])}")

    opts2 = PaintOptions()
    opts2.brush = Brush(size=20, hardness=1.0)
    eraser_points = [(50, 100), (150, 100)]
    paint.eraser_stroke(layer, eraser_points, opts2)
    print(f"Eraser stroke applied, alpha at (100,100): {layer.pixels[100, 100, 3]}")
    print()


def demo_transforms():
    print("=== Transform Operations ===")
    img = GimpImage(100, 100)
    layer = img.new_layer("Test", FillType.WHITE)
    layer.pixels[10:90, 10:90] = [255, 0, 0, 255]

    img.flip(FlipType.HORIZONTAL)
    print(f"After horizontal flip: pixel at (0,50) = {tuple(layer.pixels[50, 0])}")

    img2 = GimpImage(100, 50)
    img2.new_layer("L", FillType.WHITE)
    img2.rotate(RotationType.ROTATE_90)
    print(f"After 90° rotation: {img2.width}x{img2.height}")

    m = Matrix3.translate(10, 20)
    x, y = m.transform_point(5, 5)
    print(f"Matrix translate(10,20) of (5,5) = ({x}, {y})")

    m2 = Matrix3.scale(2, 3)
    combined = m2 * m
    x, y = combined.transform_point(0, 0)
    print(f"Scale(2,3) * Translate(10,20) of (0,0) = ({x}, {y})")
    print()


def demo_paths():
    print("=== Path / Vector Operations ===")
    path = GimpPath("My Path")

    stroke = Stroke()
    stroke.moveto(10, 10)
    stroke.lineto(90, 10)
    stroke.lineto(90, 90)
    stroke.lineto(10, 90)
    stroke.close()
    path.add_stroke(stroke)

    ellipse = Stroke.ellipse(50, 50, 30, 20)
    path.add_stroke(ellipse)
    print(f"Path '{path.name}': {path.stroke_count} strokes")
    print(f"Bounds: {path.get_bounds()}")

    length = ellipse.get_length()
    print(f"Ellipse perimeter ≈ {length:.1f}")

    svg = path.to_svg()
    print(f"SVG output: {svg[:60]}...")
    print()


def demo_layers():
    print("=== Layer Operations ===")
    img = GimpImage(100, 100)
    bg = img.new_layer("Background", FillType.WHITE)
    fg = img.new_layer("Foreground")
    fg.pixels[20:80, 20:80] = [0, 0, 255, 128]

    fg.set_opacity(0.5)
    fg.set_mode(LayerMode.MULTIPLY)
    print(f"Layer mode: {fg.mode.value}, opacity: {fg.opacity}")

    mask = fg.create_mask()
    mask.pixels[30:70, 30:70] = 0
    fg.add_mask(mask)
    print(f"Layer mask added, mask center: {mask.pixels[50, 50]}")

    group = img.new_group_layer("Group")
    inner = GimpLayer(100, 100, "Inner", FillType.WHITE)
    group.add_layer(inner)
    print(f"Group has {len(group.children)} children")

    merged = img.merge_visible_layers()
    print(f"After merge: {len(img.layers)} layers")
    print()


def demo_filters():
    print("=== Non-destructive Filters ===")
    import numpy as np
    stack = FilterStack()

    f1 = GimpFilter("Brightness",
                    lambda p: color.brightness_contrast(p, brightness=0.2))
    f2 = GimpFilter("Invert", lambda p: color.invert(p))
    stack.add(f1)
    stack.add(f2)

    pixels = np.full((10, 10, 3), 100, dtype=np.uint8)
    result = stack.apply_all(pixels)
    print(f"Original: {pixels[0,0,0]}, After filters: {result[0,0,0]}")

    f2.visible = False
    result2 = stack.apply_all(pixels)
    print(f"With invert hidden: {result2[0,0,0]}")
    print()


def demo_resources():
    print("=== Resources ===")
    brush = GimpBrush("Hard Round", shape=BrushShape.CIRCLE,
                      radius=10, hardness=1.0)
    print(f"Brush: {brush.name}, mask size: {brush.get_mask().shape}")

    gradient = GimpGradient("Fire")
    gradient.segments.clear()
    gradient.add_segment(0.0, 0.5, (255, 0, 0, 255), (255, 255, 0, 255))
    gradient.add_segment(0.5, 1.0, (255, 255, 0, 255), (255, 255, 255, 255))
    print(f"Gradient at 0.25: {gradient.get_color_at(0.25)}")
    print(f"Gradient at 0.75: {gradient.get_color_at(0.75)}")

    palette = GimpPalette("Basic")
    palette.add_color(255, 0, 0, "Red")
    palette.add_color(0, 255, 0, "Green")
    palette.add_color(0, 0, 255, "Blue")
    print(f"Palette '{palette.name}': {palette.color_count} colors")
    print(f"Closest to (200,10,10): {palette.colors[palette.find_closest(200, 10, 10)][3]}")
    print()


def demo_text():
    print("=== Text Layer ===")
    text = GimpText("Hello GIMP!", font="Sans-serif", size=24,
                    color=(0, 0, 0))
    tl = GimpTextLayer(text, "Title")
    print(f"Text layer: {tl.width}x{tl.height}, dynamic: {tl.is_dynamic}")

    tl.set_text("Updated Text!")
    print(f"After update: {tl.width}x{tl.height}")

    tl.rasterize()
    print(f"After rasterize: dynamic={tl.is_dynamic}")
    print()


def demo_undo():
    print("=== Undo System ===")
    img = GimpImage(50, 50)
    layer = img.new_layer("L")
    layer.pixels[:] = [100, 100, 100, 255]

    img.invert()
    print(f"After invert: {layer.pixels[0,0,0]}")

    img.brightness_contrast(brightness=0.5)
    print(f"After brightness: {layer.pixels[0,0,0]}")

    img.undo()
    print(f"After 1st undo: {layer.pixels[0,0,0]}")

    img.undo()
    print(f"After 2nd undo: {layer.pixels[0,0,0]}")

    img.redo()
    print(f"After redo: {layer.pixels[0,0,0]}")
    print()


def demo_file_io():
    print("=== File I/O ===")
    from gimppy.fileio import get_supported_formats
    formats = get_supported_formats()
    print(f"Supported formats: {formats}")

    img = GimpImage(50, 50)
    img.new_layer("BG", FillType.WHITE)
    print(f"Image ready for save: {img}")
    print("(Actual save requires Pillow library)")
    print()


if __name__ == "__main__":
    print("gimppy Demo — Python class library extracted from GIMP source\n")
    demo_basic_image()
    demo_selections()
    demo_color_adjustments()
    demo_painting()
    demo_transforms()
    demo_paths()
    demo_layers()
    demo_filters()
    demo_resources()
    demo_text()
    demo_undo()
    demo_file_io()
    print("All demos completed successfully!")
