"""
Tests for gimppy — the Python class library extracted from GIMP source.
Run with: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from gimppy import (
    GimpImage, GimpLayer, GimpGroupLayer, GimpLayerMask,
    GimpChannel, GimpSelection, GimpPath, Stroke, Anchor,
    GimpText, GimpTextLayer, GimpBrush, GimpPattern,
    GimpGradient, GimpPalette, GimpDynamics,
    GimpFilter, FilterStack, UndoStack, UndoStep, UndoType,
    Brush, PaintOptions, Matrix3, Vector2, Vector3,
)
from gimppy.enums import (
    ImageType, LayerMode, FillType, FlipType, RotationType,
    SelectionOperation, DesaturateMode, BrushShape,
    GradientType, RepeatMode, GuideOrientation, GridStyle,
    InterpolationType, TransformResize,
)
from gimppy.exceptions import (
    ImageError, LayerError, SelectionError, GimpError, UndoError,
)
from gimppy import color, drawable, transform, paint


class TestGimpImage:
    def test_create_image(self):
        img = GimpImage(800, 600)
        assert img.width == 800
        assert img.height == 600
        assert img.image_type == ImageType.RGB
        assert len(img.layers) == 0

    def test_create_image_invalid_size(self):
        try:
            GimpImage(0, 100)
            assert False, "Should raise ImageError"
        except ImageError:
            pass

    def test_new_layer(self):
        img = GimpImage(100, 100)
        layer = img.new_layer("Test", FillType.WHITE)
        assert layer.name == "Test"
        assert layer.width == 100
        assert layer.height == 100
        assert len(img.layers) == 1
        assert img.active_layer is layer
        assert np.all(layer.pixels[:, :, :3] == 255)

    def test_add_remove_layer(self):
        img = GimpImage(50, 50)
        l1 = img.new_layer("L1")
        l2 = img.new_layer("L2")
        assert len(img.layers) == 2
        img.remove_layer(l1)
        assert len(img.layers) == 1
        assert img.layers[0] is l2

    def test_duplicate(self):
        img = GimpImage(100, 100, name="Original")
        img.new_layer("L1", FillType.WHITE)
        dup = img.duplicate()
        assert dup.width == 100
        assert len(dup.layers) == 1
        assert dup.layers[0].name == "L1"
        assert dup is not img
        assert dup.layers[0] is not img.layers[0]

    def test_resize(self):
        img = GimpImage(100, 100)
        layer = img.new_layer("L", FillType.WHITE)
        img.resize(200, 150)
        assert img.width == 200
        assert img.height == 150

    def test_scale(self):
        img = GimpImage(100, 100)
        img.new_layer("L", FillType.WHITE)
        img.scale(50, 50)
        assert img.width == 50
        assert img.height == 50

    def test_crop(self):
        img = GimpImage(100, 100)
        img.new_layer("L", FillType.WHITE)
        img.crop(10, 10, 50, 50)
        assert img.width == 50
        assert img.height == 50

    def test_flip(self):
        img = GimpImage(100, 100)
        layer = img.new_layer("L", FillType.WHITE)
        layer.pixels[0, 0, 0] = 128
        img.flip(FlipType.HORIZONTAL)
        assert layer.pixels[0, 99, 0] == 128

    def test_rotate(self):
        img = GimpImage(100, 50)
        img.new_layer("L", FillType.WHITE)
        img.rotate(RotationType.ROTATE_90)
        assert img.width == 50
        assert img.height == 100

    def test_convert_grayscale(self):
        img = GimpImage(10, 10)
        img.new_layer("L", FillType.WHITE)
        img.convert_grayscale()
        assert img.image_type == ImageType.GRAY

    def test_flatten(self):
        img = GimpImage(50, 50)
        l1 = img.new_layer("BG", FillType.WHITE)
        l2 = img.new_layer("FG")
        l2.pixels[10:20, 10:20] = [255, 0, 0, 255]
        result = img.flatten()
        assert len(img.layers) == 1
        assert not result.has_alpha

    def test_merge_visible(self):
        img = GimpImage(50, 50)
        l1 = img.new_layer("BG", FillType.WHITE)
        l2 = img.new_layer("FG")
        l2.visible = False
        result = img.merge_visible_layers()
        assert len(img.layers) == 2

    def test_pick_color(self):
        img = GimpImage(100, 100)
        layer = img.new_layer("L", FillType.WHITE)
        layer.pixels[10, 20] = [128, 64, 32, 255]
        c = img.pick_color(20, 10)
        assert c == (128, 64, 32, 255)

    def test_guides(self):
        img = GimpImage(100, 100)
        g = img.add_guide(GuideOrientation.HORIZONTAL, 50.0)
        assert len(img.guides) == 1
        img.remove_guide(0)
        assert len(img.guides) == 0

    def test_grid(self):
        img = GimpImage(100, 100)
        img.set_grid_spacing(20.0, 20.0)
        assert img.grid_spacing_x == 20.0

    def test_resolution(self):
        img = GimpImage(100, 100)
        img.set_resolution(300.0, 300.0)
        assert img.resolution_x == 300.0

    def test_dirty_flag(self):
        img = GimpImage(100, 100)
        assert not img.is_dirty
        img.new_layer("L")
        assert img.is_dirty
        img.clean_all()
        assert not img.is_dirty

    def test_repr(self):
        img = GimpImage(100, 100)
        assert "100x100" in repr(img)


class TestGimpLayer:
    def test_create_layer(self):
        layer = GimpLayer(100, 100, "Test")
        assert layer.width == 100
        assert layer.height == 100
        assert layer.opacity == 1.0
        assert layer.mode == LayerMode.NORMAL

    def test_set_opacity(self):
        layer = GimpLayer(10, 10)
        layer.set_opacity(0.5)
        assert layer.opacity == 0.5

    def test_set_opacity_invalid(self):
        layer = GimpLayer(10, 10)
        try:
            layer.set_opacity(1.5)
            assert False
        except LayerError:
            pass

    def test_pixel_access(self):
        layer = GimpLayer(10, 10, has_alpha=True)
        layer.set_pixel(5, 5, (128, 64, 32, 255))
        assert layer.get_pixel(5, 5) == (128, 64, 32, 255)

    def test_layer_mask(self):
        layer = GimpLayer(50, 50)
        mask = layer.create_mask()
        layer.add_mask(mask)
        assert layer.mask is not None
        layer.remove_mask()
        assert layer.mask is None

    def test_add_alpha(self):
        layer = GimpLayer(10, 10, has_alpha=False)
        assert not layer.has_alpha
        layer.add_alpha()
        assert layer.has_alpha

    def test_flatten(self):
        layer = GimpLayer(10, 10, has_alpha=True)
        layer.flatten()
        assert not layer.has_alpha

    def test_copy(self):
        layer = GimpLayer(10, 10, "Original")
        layer.pixels[5, 5] = [128, 64, 32, 255]
        copy = layer.copy()
        assert copy.name == "Original"
        assert tuple(copy.pixels[5, 5]) == (128, 64, 32, 255)
        copy.pixels[5, 5] = [0, 0, 0, 0]
        assert tuple(layer.pixels[5, 5]) == (128, 64, 32, 255)

    def test_scale(self):
        layer = GimpLayer(100, 100, FillType.WHITE)
        layer.scale(50, 50)
        assert layer.width == 50
        assert layer.height == 50

    def test_resize(self):
        layer = GimpLayer(50, 50, FillType.WHITE)
        layer.resize(100, 100, 25, 25)
        assert layer.width == 100
        assert layer.height == 100


class TestGimpGroupLayer:
    def test_group_layer(self):
        group = GimpGroupLayer(100, 100, "Group")
        l1 = GimpLayer(100, 100, "Child1", FillType.WHITE)
        l2 = GimpLayer(100, 100, "Child2")
        group.add_layer(l1)
        group.add_layer(l2)
        assert len(group.children) == 2

    def test_merge_group(self):
        group = GimpGroupLayer(50, 50)
        l1 = GimpLayer(50, 50, "BG", FillType.WHITE)
        group.add_layer(l1)
        merged = group.merge()
        assert merged.width == 50


class TestGimpChannel:
    def test_create_channel(self):
        ch = GimpChannel(100, 100, "Alpha")
        assert ch.width == 100
        assert ch.is_empty

    def test_fill_and_clear(self):
        ch = GimpChannel(10, 10)
        ch.fill(255)
        assert not ch.is_empty
        ch.clear()
        assert ch.is_empty

    def test_invert(self):
        ch = GimpChannel(10, 10)
        ch.fill(255)
        ch.invert()
        assert ch.pixels[0, 0] == 0

    def test_combine(self):
        ch1 = GimpChannel(10, 10)
        ch1.fill(128)
        ch2 = GimpChannel(10, 10)
        ch2.fill(200)
        ch1.combine(ch2, "add")
        assert ch1.pixels[0, 0] == 255

    def test_copy(self):
        ch = GimpChannel(10, 10, "Test")
        ch.fill(128)
        copy = ch.copy()
        assert copy.name == "Test"
        assert copy.pixels[0, 0] == 128


class TestGimpSelection:
    def test_select_all_none(self):
        sel = GimpSelection(100, 100)
        sel.select_all()
        assert sel.pixels[50, 50] == 255
        sel.select_none()
        assert sel.pixels[50, 50] == 0

    def test_select_rectangle(self):
        sel = GimpSelection(100, 100)
        sel.select_rectangle(10, 10, 30, 30, antialias=False)
        assert sel.pixels[20, 20] == 255
        assert sel.pixels[0, 0] == 0

    def test_select_ellipse(self):
        sel = GimpSelection(100, 100)
        sel.select_ellipse(20, 20, 60, 60, antialias=False)
        assert sel.pixels[50, 50] == 255

    def test_select_polygon(self):
        sel = GimpSelection(100, 100)
        points = [(10, 10), (90, 10), (90, 90), (10, 90)]
        sel.select_polygon(points, antialias=False)
        assert sel.pixels[50, 50] == 255
        assert sel.pixels[0, 0] == 0

    def test_invert(self):
        sel = GimpSelection(10, 10)
        sel.select_all()
        sel.select_invert()
        assert sel.pixels[5, 5] == 0

    def test_feather(self):
        sel = GimpSelection(50, 50)
        sel.select_rectangle(10, 10, 30, 30, antialias=False)
        sel.feather(3.0)
        assert sel.pixels[25, 25] > 0

    def test_grow_shrink(self):
        sel = GimpSelection(50, 50)
        sel.select_rectangle(15, 15, 20, 20, antialias=False)
        original_sum = sel.pixels.sum()
        sel.grow(3)
        grown_sum = sel.pixels.sum()
        assert grown_sum > original_sum

    def test_translate(self):
        sel = GimpSelection(50, 50)
        sel.select_rectangle(0, 0, 10, 10, antialias=False)
        sel.translate(5, 5)
        assert sel.pixels[0, 0] == 0

    def test_boundary(self):
        sel = GimpSelection(20, 20)
        sel.select_rectangle(5, 5, 10, 10, antialias=False)
        contours = sel.get_boundary()
        assert len(contours) > 0

    def test_operations(self):
        sel = GimpSelection(50, 50)
        sel.select_rectangle(0, 0, 20, 20, antialias=False)
        sel.select_rectangle(10, 10, 20, 20, SelectionOperation.ADD, antialias=False)
        assert sel.pixels[25, 25] == 255
        sel.select_rectangle(0, 0, 5, 5, SelectionOperation.SUBTRACT, antialias=False)
        assert sel.pixels[2, 2] == 0


class TestGimpPath:
    def test_create_path(self):
        path = GimpPath("Test Path")
        stroke = Stroke()
        stroke.moveto(10, 10)
        stroke.lineto(90, 90)
        path.add_stroke(stroke)
        assert path.stroke_count == 1

    def test_stroke_interpolate(self):
        stroke = Stroke()
        stroke.moveto(0, 0)
        stroke.lineto(100, 100)
        points = stroke.interpolate()
        assert len(points) > 0
        assert points[0] == (0, 0)

    def test_stroke_transforms(self):
        stroke = Stroke()
        stroke.moveto(10, 10)
        stroke.lineto(20, 20)
        stroke.translate(5, 5)
        assert stroke.anchors[0].x == 15
        stroke.scale(2, 2)
        assert stroke.anchors[0].x == 30

    def test_ellipse_stroke(self):
        stroke = Stroke.ellipse(50, 50, 30, 20)
        assert stroke.closed
        points = stroke.interpolate()
        assert len(points) > 0

    def test_path_bounds(self):
        path = GimpPath()
        stroke = Stroke()
        stroke.moveto(10, 20)
        stroke.lineto(80, 90)
        path.add_stroke(stroke)
        bounds = path.get_bounds()
        assert bounds[0] <= 10
        assert bounds[1] <= 20

    def test_path_to_svg(self):
        path = GimpPath()
        stroke = Stroke()
        stroke.moveto(10, 10)
        stroke.lineto(50, 50)
        path.add_stroke(stroke)
        svg = path.to_svg()
        assert '<path' in svg


class TestColorOperations:
    def test_brightness_contrast(self):
        pixels = np.full((10, 10, 3), 128, dtype=np.uint8)
        result = color.brightness_contrast(pixels, brightness=0.5)
        assert result[0, 0, 0] > 128

    def test_levels(self):
        pixels = np.full((10, 10, 3), 128, dtype=np.uint8)
        result = color.levels(pixels, input_black=0.0, input_white=0.8)
        assert result[0, 0, 0] > 128

    def test_hue_saturation(self):
        pixels = np.full((10, 10, 3), 128, dtype=np.uint8)
        result = color.hue_saturation(pixels, hue_offset=90)
        assert result.shape == pixels.shape

    def test_desaturate(self):
        pixels = np.zeros((10, 10, 3), dtype=np.uint8)
        pixels[:, :, 0] = 255
        result = color.desaturate(pixels)
        assert result[0, 0, 0] == result[0, 0, 1] == result[0, 0, 2]

    def test_posterize(self):
        pixels = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
        result = color.posterize(pixels, levels=4)
        unique_vals = np.unique(result[:, :, 0])
        assert len(unique_vals) <= 4

    def test_threshold(self):
        pixels = np.full((10, 10, 3), 128, dtype=np.uint8)
        pixels[5:, :, :] = 200
        result = color.threshold(pixels, 150)
        assert result[0, 0, 0] == 0
        assert result[5, 0, 0] == 255

    def test_invert(self):
        pixels = np.full((10, 10, 3), 100, dtype=np.uint8)
        result = color.invert(pixels)
        assert result[0, 0, 0] == 155

    def test_equalize(self):
        pixels = np.random.randint(50, 200, (10, 10, 3), dtype=np.uint8)
        result = color.equalize(pixels)
        assert result.shape == pixels.shape

    def test_color_balance(self):
        pixels = np.full((10, 10, 3), 128, dtype=np.uint8)
        result = color.color_balance(pixels, cyan_red=0.5)
        assert result[0, 0, 0] > 128

    def test_histogram(self):
        pixels = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        hist = color.compute_histogram(pixels)
        assert len(hist) == 256
        assert hist.sum() == 100 * 100


class TestTransformOperations:
    def test_matrix_identity(self):
        m = Matrix3.identity()
        x, y = m.transform_point(10, 20)
        assert x == 10 and y == 20

    def test_matrix_translate(self):
        m = Matrix3.translate(5, 10)
        x, y = m.transform_point(0, 0)
        assert x == 5 and y == 10

    def test_matrix_scale(self):
        m = Matrix3.scale(2, 3)
        x, y = m.transform_point(10, 10)
        assert x == 20 and y == 30

    def test_matrix_rotate(self):
        import math
        m = Matrix3.rotate(math.pi / 2)
        x, y = m.transform_point(1, 0)
        assert abs(x) < 1e-10
        assert abs(y - 1) < 1e-10

    def test_matrix_inverse(self):
        m = Matrix3.translate(5, 10)
        inv = m.inverse()
        x, y = inv.transform_point(5, 10)
        assert abs(x) < 1e-10 and abs(y) < 1e-10

    def test_matrix_multiply(self):
        t = Matrix3.translate(5, 0)
        s = Matrix3.scale(2, 2)
        combined = s * t
        x, y = combined.transform_point(0, 0)
        assert abs(x - 10) < 1e-10

    def test_vector2(self):
        v = Vector2(3, 4)
        assert abs(v.length() - 5.0) < 1e-10
        n = v.normalize()
        assert abs(n.length() - 1.0) < 1e-10

    def test_vector3(self):
        v1 = Vector3(1, 0, 0)
        v2 = Vector3(0, 1, 0)
        cross = v1.cross(v2)
        assert cross.z == 1.0


class TestDrawableOperations:
    def test_fill(self):
        layer = GimpLayer(10, 10, has_alpha=True)
        drawable.drawable_fill(layer, FillType.WHITE)
        assert np.all(layer.pixels[:, :, :3] == 255)

    def test_fill_transparent(self):
        layer = GimpLayer(10, 10, FillType.WHITE, has_alpha=True)
        drawable.drawable_fill(layer, FillType.TRANSPARENT)
        assert np.all(layer.pixels == 0)

    def test_clear(self):
        layer = GimpLayer(10, 10, FillType.WHITE, has_alpha=True)
        drawable.drawable_edit_clear(layer)
        assert np.all(layer.pixels == 0)

    def test_offset(self):
        layer = GimpLayer(10, 10, has_alpha=True)
        layer.pixels[0, 0] = [255, 0, 0, 255]
        drawable.drawable_offset(layer, 5, 5)
        assert layer.pixels[5, 5, 0] == 255
        assert layer.pixels[0, 0, 0] == 0

    def test_offset_wrap(self):
        layer = GimpLayer(10, 10, has_alpha=True)
        layer.pixels[0, 0] = [255, 0, 0, 255]
        drawable.drawable_offset(layer, -1, -1, wrap=True)
        assert layer.pixels[9, 9, 0] == 255


class TestPaintEngine:
    def test_paintbrush(self):
        layer = GimpLayer(100, 100, FillType.WHITE, has_alpha=True)
        points = [(10, 10), (50, 50), (90, 90)]
        paint.paintbrush_stroke(layer, points, (255, 0, 0, 255))
        assert layer.pixels[50, 50, 0] > 0

    def test_pencil(self):
        layer = GimpLayer(100, 100, FillType.WHITE, has_alpha=True)
        points = [(10, 50), (90, 50)]
        paint.pencil_stroke(layer, points, (0, 0, 0, 255))

    def test_eraser(self):
        layer = GimpLayer(100, 100, FillType.WHITE, has_alpha=True)
        points = [(10, 50), (90, 50)]
        paint.eraser_stroke(layer, points)
        assert layer.pixels[50, 50, 3] < 255

    def test_brush_mask(self):
        brush = Brush(size=10, hardness=1.0, shape=BrushShape.CIRCLE)
        mask = brush.get_mask()
        assert mask.shape[0] > 0
        assert mask[mask.shape[0]//2, mask.shape[1]//2] == 1.0


class TestResources:
    def test_brush(self):
        brush = GimpBrush("Test", radius=10, hardness=0.5)
        mask = brush.get_mask()
        assert mask.shape[0] > 0
        info = brush.get_info()
        assert info["name"] == "Test"

    def test_pattern(self):
        pat = GimpPattern("Test", np.full((5, 5, 3), 128, dtype=np.uint8))
        assert pat.width == 5
        assert pat.height == 5

    def test_gradient(self):
        grad = GimpGradient("Test")
        c = grad.get_color_at(0.0)
        assert c[0] == 0
        c = grad.get_color_at(1.0)
        assert c[0] == 255

    def test_gradient_reverse(self):
        grad = GimpGradient("Test")
        grad.reverse()
        c = grad.get_color_at(0.0)
        assert c[0] == 255

    def test_palette(self):
        pal = GimpPalette("Test")
        pal.add_color(255, 0, 0, "Red")
        pal.add_color(0, 255, 0, "Green")
        assert pal.color_count == 2
        assert pal.find_closest(200, 0, 0) == 0

    def test_dynamics(self):
        dyn = GimpDynamics("Test")
        result = dyn.apply(pressure=0.5)
        assert result["opacity"] == 0.5


class TestFilterSystem:
    def test_filter(self):
        f = GimpFilter("test", lambda p: color.invert(p))
        pixels = np.full((10, 10, 3), 100, dtype=np.uint8)
        result = f.apply(pixels)
        assert result[0, 0, 0] == 155

    def test_filter_stack(self):
        stack = FilterStack()
        f1 = GimpFilter("f1", lambda p: color.brightness_contrast(p, brightness=0.1))
        f2 = GimpFilter("f2", lambda p: color.invert(p))
        stack.add(f1)
        stack.add(f2)
        assert len(stack) == 2
        pixels = np.full((10, 10, 3), 128, dtype=np.uint8)
        result = stack.apply_all(pixels)
        assert result.shape == pixels.shape

    def test_filter_visibility(self):
        f = GimpFilter("test", lambda p: color.invert(p))
        f.visible = False
        pixels = np.full((10, 10, 3), 100, dtype=np.uint8)
        result = f.apply(pixels)
        assert result[0, 0, 0] == 100

    def test_filter_opacity(self):
        f = GimpFilter("test", lambda p: color.invert(p))
        f.opacity = 0.5
        pixels = np.full((10, 10, 3), 100, dtype=np.uint8)
        result = f.apply(pixels)
        assert 100 < result[0, 0, 0] < 155


class TestUndoSystem:
    def test_undo_redo(self):
        stack = UndoStack()
        data = [0]

        def undo_fn():
            data[0] = 0

        def redo_fn():
            data[0] = 1

        data[0] = 1
        step = UndoStep(UndoType.LAYER_PIXELS, "test", undo_fn, redo_fn)
        stack.push(step)
        assert stack.can_undo
        stack.undo()
        assert data[0] == 0
        assert stack.can_redo
        stack.redo()
        assert data[0] == 1

    def test_undo_group(self):
        stack = UndoStack()
        data = [0, 0]
        stack.begin_group("group")
        stack.push(UndoStep(UndoType.LAYER_PIXELS, "s1",
                            lambda: data.__setitem__(0, 0),
                            lambda: data.__setitem__(0, 1)))
        stack.push(UndoStep(UndoType.LAYER_PIXELS, "s2",
                            lambda: data.__setitem__(1, 0),
                            lambda: data.__setitem__(1, 1)))
        stack.end_group()
        data[0] = 1
        data[1] = 1
        stack.undo()
        assert data[0] == 0 and data[1] == 0

    def test_undo_disabled(self):
        stack = UndoStack()
        stack.disable()
        step = UndoStep(UndoType.LAYER_PIXELS, "test", lambda: None, lambda: None)
        stack.push(step)
        assert not stack.can_undo

    def test_undo_empty_raises(self):
        stack = UndoStack()
        try:
            stack.undo()
            assert False
        except UndoError:
            pass


class TestTextLayer:
    def test_text_layer(self):
        text = GimpText("Hello", size=20, color=(255, 0, 0))
        tl = GimpTextLayer(text)
        assert tl.width > 0
        assert tl.height > 0
        assert tl.is_dynamic

    def test_text_rasterize(self):
        text = GimpText("Test")
        tl = GimpTextLayer(text)
        tl.rasterize()
        assert not tl.is_dynamic

    def test_text_set(self):
        text = GimpText("Hello")
        tl = GimpTextLayer(text)
        old_w = tl.width
        tl.set_text("Hello World!")
        assert tl.width >= old_w


class TestImageAdjustments:
    def test_brightness_contrast(self):
        img = GimpImage(50, 50)
        layer = img.new_layer("L", FillType.WHITE)
        layer.pixels[:] = [128, 128, 128, 255]
        img.brightness_contrast(brightness=0.5)
        assert layer.pixels[0, 0, 0] > 128

    def test_invert(self):
        img = GimpImage(10, 10)
        layer = img.new_layer("L")
        layer.pixels[:] = [100, 100, 100, 255]
        img.invert()
        assert layer.pixels[0, 0, 0] == 155

    def test_desaturate(self):
        img = GimpImage(10, 10)
        layer = img.new_layer("L")
        layer.pixels[:] = [255, 0, 0, 255]
        img.desaturate()
        assert layer.pixels[0, 0, 0] == layer.pixels[0, 0, 1]

    def test_threshold(self):
        img = GimpImage(10, 10)
        layer = img.new_layer("L")
        layer.pixels[:5, :] = [200, 200, 200, 255]
        layer.pixels[5:, :] = [50, 50, 50, 255]
        img.threshold(127)
        assert layer.pixels[0, 0, 0] == 255
        assert layer.pixels[9, 0, 0] == 0

    def test_undo_integration(self):
        img = GimpImage(10, 10)
        layer = img.new_layer("L")
        layer.pixels[:] = [100, 100, 100, 255]
        img.invert()
        assert layer.pixels[0, 0, 0] == 155
        img.undo()
        assert layer.pixels[0, 0, 0] == 100


if __name__ == "__main__":
    import traceback
    test_classes = [
        TestGimpImage, TestGimpLayer, TestGimpGroupLayer,
        TestGimpChannel, TestGimpSelection, TestGimpPath,
        TestColorOperations, TestTransformOperations,
        TestDrawableOperations, TestPaintEngine,
        TestResources, TestFilterSystem, TestUndoSystem,
        TestTextLayer, TestImageAdjustments,
    ]
    passed = 0
    failed = 0
    errors = []
    for cls in test_classes:
        obj = cls()
        for name in dir(obj):
            if name.startswith("test_"):
                try:
                    getattr(obj, name)()
                    passed += 1
                except Exception as e:
                    failed += 1
                    errors.append(f"{cls.__name__}.{name}: {e}")
                    traceback.print_exc()
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print(f"\nFailures:")
        for e in errors:
            print(f"  - {e}")
    print(f"{'='*60}")
