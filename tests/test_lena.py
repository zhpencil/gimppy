"""
Comprehensive test using lena.jpg (256x256 JPEG).
Tests every major feature of gimppy against a real image.
"""

import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gimppy import (
    GimpImage, GimpLayer, GimpGroupLayer, GimpLayerMask,
    GimpChannel, GimpSelection, GimpPath, Stroke,
    GimpText, GimpTextLayer,
    GimpBrush, GimpPattern, GimpGradient, GimpPalette, GimpDynamics,
    GimpFilter, FilterStack,
    Brush, PaintOptions, Matrix3, Vector2, Vector3,
)
from gimppy.enums import (
    ImageType, LayerMode, FillType, FlipType, RotationType,
    SelectionOperation, DesaturateMode, BrushShape,
    GradientType, RepeatMode, GuideOrientation, GridStyle,
    InterpolationType, HistogramChannel, MaskApplyMode,
    ConvertPaletteType,
)
from gimppy import color, drawable, paint, transform
from gimppy.fileio import load_image, save_image

LENA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lena.jpg")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

passed = 0
failed = 0
errors = []


def report(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {name} {detail}")
    else:
        failed += 1
        errors.append(name)
        print(f"  [FAIL] {name} {detail}")


def load_lena():
    data = load_image(LENA_PATH)
    img = GimpImage(data["width"], data["height"], data["image_type"], name="Lena")
    for ld in data.get("layers", []):
        pixels = ld["pixels"]
        has_alpha = ld.get("has_alpha", pixels.shape[2] >= 4 if pixels.ndim == 3 else False)
        layer = GimpLayer(pixels.shape[1], pixels.shape[0],
                          ld.get("name", "Lena"), img.image_type, has_alpha=has_alpha)
        layer.pixels = pixels
        img.add_layer(layer)
    return img


# ============================================================
print("=" * 60)
print("  gimppy 全面功能测试 — 使用 lena.jpg (256x256)")
print("=" * 60)

# ============================================================
print("\n--- 1. 文件加载 ---")
# ============================================================
try:
    data = load_image(LENA_PATH)
    report("加载 lena.jpg", data["width"] == 256 and data["height"] == 256,
           f"({data['width']}x{data['height']}, {data['image_type'].value})")
except Exception as e:
    report("加载 lena.jpg", False, str(e))

try:
    img = load_lena()
    report("创建 GimpImage", img.width == 256 and len(img.layers) == 1,
           f"({img})")
except Exception as e:
    report("创建 GimpImage", False, str(e))
    img = GimpImage(256, 256)
    img.new_layer("Lena", FillType.WHITE)

lena_layer = img.active_layer
original_pixels = lena_layer.pixels.copy()

# ============================================================
print("\n--- 2. 图层操作 ---")
# ============================================================
try:
    bg = img.new_layer("White BG", FillType.WHITE)
    report("新建图层(白色填充)", np.all(bg.pixels[:, :, :3] == 255))
except Exception as e:
    report("新建图层", False, str(e))

try:
    fg = img.new_layer("Foreground")
    fg.pixels[50:150, 50:150, :3] = [255, 0, 0]
    fg.pixels[50:150, 50:150, 3] = 200
    report("新建图层(红色矩形)", fg.pixels[100, 100, 0] == 255)
except Exception as e:
    report("新建图层(红色矩形)", False, str(e))

try:
    report("图层数量", len(img.layers) == 3, f"({len(img.layers)} layers)")
except Exception as e:
    report("图层数量", False, str(e))

try:
    img.remove_layer(fg)
    report("删除图层", len(img.layers) == 2)
except Exception as e:
    report("删除图层", False, str(e))

try:
    dup_layer = lena_layer.copy()
    dup_layer.name = "Lena Copy"
    img.add_layer(dup_layer)
    report("复制图层", tuple(dup_layer.pixels[128, 128]) == tuple(lena_layer.pixels[128, 128]))
    img.remove_layer(dup_layer)
except Exception as e:
    report("复制图层", False, str(e))

try:
    group = img.new_group_layer("Test Group")
    child = GimpLayer(256, 256, "Child", FillType.WHITE)
    group.add_layer(child)
    report("图层组", len(group.children) == 1)
    img.remove_layer(group)
except Exception as e:
    report("图层组", False, str(e))

try:
    lena_layer.set_opacity(0.8)
    report("设置透明度", abs(lena_layer.opacity - 0.8) < 1e-6)
    lena_layer.set_opacity(1.0)
except Exception as e:
    report("设置透明度", False, str(e))

try:
    lena_layer.set_mode(LayerMode.MULTIPLY)
    report("设置混合模式", lena_layer.mode == LayerMode.MULTIPLY)
    lena_layer.set_mode(LayerMode.NORMAL)
except Exception as e:
    report("设置混合模式", False, str(e))

try:
    mask = lena_layer.create_mask()
    mask.pixels[:, :128] = 0
    lena_layer.add_mask(mask)
    report("添加蒙版(左半黑)", lena_layer.mask is not None)
    lena_layer.remove_mask(MaskApplyMode.DISCARD)
    report("移除蒙版", lena_layer.mask is None)
except Exception as e:
    report("蒙版操作", False, str(e))

try:
    lena_layer.add_alpha() if not lena_layer.has_alpha else None
    report("添加Alpha通道", lena_layer.has_alpha)
except Exception as e:
    report("添加Alpha通道", False, str(e))

# ============================================================
print("\n--- 3. 选区操作 ---")
# ============================================================
try:
    img.selection.select_all()
    report("全选", np.all(img.selection.pixels == 255))
except Exception as e:
    report("全选", False, str(e))

try:
    img.selection.select_none()
    report("取消全选", np.all(img.selection.pixels == 0))
except Exception as e:
    report("取消全选", False, str(e))

try:
    img.selection.select_rectangle(50, 50, 100, 100, antialias=False)
    report("矩形选区", img.selection.pixels[100, 100] == 255 and
           img.selection.pixels[0, 0] == 0)
except Exception as e:
    report("矩形选区", False, str(e))

try:
    img.selection.select_ellipse(28, 28, 200, 200, antialias=False)
    report("椭圆选区", img.selection.pixels[128, 128] == 255)
except Exception as e:
    report("椭圆选区", False, str(e))

try:
    img.selection.select_polygon(
        [(128, 20), (230, 128), (128, 236), (26, 128)],
        antialias=False
    )
    report("多边形选区(菱形)", img.selection.pixels[128, 128] == 255 and
           img.selection.pixels[0, 0] == 0)
except Exception as e:
    report("多边形选区", False, str(e))

try:
    img.selection.select_round_rectangle(30, 30, 196, 196, 20, antialias=False)
    report("圆角矩形选区", img.selection.pixels[128, 128] == 255)
except Exception as e:
    report("圆角矩形选区", False, str(e))

try:
    img.selection.select_rectangle(50, 50, 100, 100, antialias=False)
    img.selection.select_invert()
    report("选区反选", img.selection.pixels[0, 0] == 255 and
           img.selection.pixels[100, 100] == 0)
except Exception as e:
    report("选区反选", False, str(e))

try:
    img.selection.select_rectangle(80, 80, 50, 50, antialias=False)
    img.selection.feather(5.0)
    report("选区羽化", 0 < img.selection.pixels[80, 105] < 255,
           f"(edge pixel={img.selection.pixels[80, 105]})")
except Exception as e:
    report("选区羽化", False, str(e))

try:
    img.selection.select_rectangle(100, 100, 50, 50, antialias=False)
    before_sum = img.selection.pixels.sum()
    img.selection.grow(5)
    after_sum = img.selection.pixels.sum()
    report("选区扩展", after_sum > before_sum,
           f"(sum: {before_sum} -> {after_sum})")
except Exception as e:
    report("选区扩展", False, str(e))

try:
    img.selection.select_rectangle(80, 80, 80, 80, antialias=False)
    before_sum = img.selection.pixels.sum()
    img.selection.shrink(5)
    after_sum = img.selection.pixels.sum()
    report("选区收缩", after_sum < before_sum,
           f"(sum: {before_sum} -> {after_sum})")
except Exception as e:
    report("选区收缩", False, str(e))

try:
    img.selection.select_rectangle(100, 100, 50, 50, antialias=False)
    contours = img.selection.get_boundary()
    report("获取选区边界", len(contours) > 0,
           f"({len(contours)} contours)")
except Exception as e:
    report("获取选区边界", False, str(e))

try:
    img.selection.select_rectangle(50, 50, 30, 30, antialias=False)
    img.selection.select_rectangle(70, 70, 30, 30,
                                   SelectionOperation.ADD, antialias=False)
    report("选区相加", img.selection.pixels[60, 60] == 255 and
           img.selection.pixels[90, 90] == 255)
except Exception as e:
    report("选区相加", False, str(e))

try:
    img.selection.select_all()
    ch = GimpChannel(256, 256, "Saved Selection")
    img.selection.save_to_channel(ch)
    report("选区保存到通道", np.array_equal(ch.pixels, img.selection.pixels))
except Exception as e:
    report("选区保存到通道", False, str(e))

img.selection.select_none()

# ============================================================
print("\n--- 4. 色彩调整 ---")
# ============================================================
lena_layer.pixels = original_pixels.copy()

try:
    result = color.brightness_contrast(lena_layer.pixels, brightness=0.3, contrast=0.1)
    report("亮度/对比度", result[128, 128, 0] > lena_layer.pixels[128, 128, 0],
           f"(pixel {lena_layer.pixels[128,128,0]} -> {result[128,128,0]})")
except Exception as e:
    report("亮度/对比度", False, str(e))

try:
    result = color.levels(lena_layer.pixels, input_black=0.1, input_white=0.9, gamma=1.2)
    report("色阶调整", result.shape == lena_layer.pixels.shape)
except Exception as e:
    report("色阶调整", False, str(e))

try:
    result = color.levels_stretch(lena_layer.pixels)
    report("自动色阶", result.shape == lena_layer.pixels.shape)
except Exception as e:
    report("自动色阶", False, str(e))

try:
    result = color.curves(lena_layer.pixels,
                          [(0.0, 0.0), (0.5, 0.8), (1.0, 1.0)], channel=0)
    report("曲线调整", result.shape == lena_layer.pixels.shape)
except Exception as e:
    report("曲线调整", False, str(e))

try:
    result = color.hue_saturation(lena_layer.pixels, hue_offset=90, saturation=0.5)
    report("色相/饱和度", not np.array_equal(result[:,:,:3], lena_layer.pixels[:,:,:3]))
except Exception as e:
    report("色相/饱和度", False, str(e))

try:
    result = color.color_balance(lena_layer.pixels, cyan_red=0.5, magenta_green=-0.3)
    report("色彩平衡", result[128, 128, 0] > lena_layer.pixels[128, 128, 0])
except Exception as e:
    report("色彩平衡", False, str(e))

try:
    result = color.desaturate(lena_layer.pixels, DesaturateMode.LUMINANCE)
    report("去色", result[128, 128, 0] == result[128, 128, 1] == result[128, 128, 2])
except Exception as e:
    report("去色", False, str(e))

try:
    result = color.colorize(lena_layer.pixels, (0.2, 0.4, 0.8))
    report("色调化", result.shape == lena_layer.pixels.shape)
except Exception as e:
    report("色调化", False, str(e))

try:
    result = color.posterize(lena_layer.pixels, levels=4)
    unique_r = len(np.unique(result[:, :, 0]))
    report("色调分离", unique_r <= 5, f"(R通道 {unique_r} 个色阶)")
except Exception as e:
    report("色调分离", False, str(e))

try:
    result = color.threshold(lena_layer.pixels, value=127)
    vals = set(np.unique(result[:, :, :3]))
    report("阈值化", vals.issubset({0, 255}), f"(唯一值: {vals})")
except Exception as e:
    report("阈值化", False, str(e))

try:
    result = color.invert(lena_layer.pixels)
    report("反色", result[128, 128, 0] == 255 - lena_layer.pixels[128, 128, 0])
except Exception as e:
    report("反色", False, str(e))

try:
    result = color.equalize(lena_layer.pixels)
    report("直方图均衡化", result.shape == lena_layer.pixels.shape)
except Exception as e:
    report("直方图均衡化", False, str(e))

try:
    result = color.shadows_highlights(lena_layer.pixels, shadows=30, highlights=-20)
    report("阴影/高光", result.shape == lena_layer.pixels.shape)
except Exception as e:
    report("阴影/高光", False, str(e))

try:
    hist = color.compute_histogram(lena_layer.pixels, HistogramChannel.VALUE)
    report("计算直方图", len(hist) == 256 and hist.sum() == 256 * 256,
           f"(sum={hist.sum()})")
except Exception as e:
    report("计算直方图", False, str(e))

try:
    hist_r = color.compute_histogram(lena_layer.pixels, HistogramChannel.RED)
    report("R通道直方图", hist_r.sum() == 256 * 256)
except Exception as e:
    report("R通道直方图", False, str(e))

# ============================================================
print("\n--- 5. 图像级色彩调整(带撤销) ---")
# ============================================================
lena_layer.pixels = original_pixels.copy()
img.undo_stack.clear()

try:
    img.brightness_contrast(brightness=0.2)
    bc_pixel = lena_layer.pixels[128, 128, 0]
    img.undo()
    report("图像亮度调整+撤销",
           lena_layer.pixels[128, 128, 0] == original_pixels[128, 128, 0],
           f"(before={original_pixels[128,128,0]}, adjusted={bc_pixel}, undone={lena_layer.pixels[128,128,0]})")
except Exception as e:
    report("图像亮度调整+撤销", False, str(e))

try:
    img.invert()
    inv_pixel = lena_layer.pixels[128, 128, 0]
    img.undo()
    report("图像反色+撤销",
           lena_layer.pixels[128, 128, 0] == original_pixels[128, 128, 0])
except Exception as e:
    report("图像反色+撤销", False, str(e))

try:
    img.desaturate()
    gray_pixel = lena_layer.pixels[128, 128]
    report("图像去色", gray_pixel[0] == gray_pixel[1] == gray_pixel[2])
    img.undo()
except Exception as e:
    report("图像去色", False, str(e))

try:
    img.equalize()
    report("图像直方图均衡化", True)
    img.undo()
except Exception as e:
    report("图像直方图均衡化", False, str(e))

# ============================================================
print("\n--- 6. 几何变换 ---")
# ============================================================
lena_layer.pixels = original_pixels.copy()

try:
    test_layer = lena_layer.copy()
    test_layer.name = "Flip Test"
    img.add_layer(test_layer)
    img.flip(FlipType.HORIZONTAL)
    img.remove_layer(test_layer)
    report("水平翻转", True)
except Exception as e:
    report("水平翻转", False, str(e))

lena_layer.pixels = original_pixels.copy()

try:
    test_layer = lena_layer.copy()
    test_layer.name = "VFlip Test"
    img.add_layer(test_layer)
    img.flip(FlipType.VERTICAL)
    img.remove_layer(test_layer)
    report("垂直翻转", True)
except Exception as e:
    report("垂直翻转", False, str(e))

lena_layer.pixels = original_pixels.copy()

try:
    m = Matrix3.translate(10, 20)
    x, y = m.transform_point(5, 5)
    report("矩阵平移", abs(x - 15) < 1e-6 and abs(y - 25) < 1e-6)
except Exception as e:
    report("矩阵平移", False, str(e))

try:
    m = Matrix3.scale(2.0, 3.0)
    x, y = m.transform_point(10, 10)
    report("矩阵缩放", abs(x - 20) < 1e-6 and abs(y - 30) < 1e-6)
except Exception as e:
    report("矩阵缩放", False, str(e))

try:
    import math
    m = Matrix3.rotate(math.pi / 2)
    x, y = m.transform_point(1, 0)
    report("矩阵旋转90°", abs(x) < 1e-6 and abs(y - 1) < 1e-6)
except Exception as e:
    report("矩阵旋转90°", False, str(e))

try:
    m = Matrix3.translate(5, 10)
    inv = m.inverse()
    x, y = inv.transform_point(5, 10)
    report("矩阵求逆", abs(x) < 1e-6 and abs(y) < 1e-6)
except Exception as e:
    report("矩阵求逆", False, str(e))

try:
    v = Vector2(3, 4)
    report("Vector2长度", abs(v.length() - 5.0) < 1e-6)
except Exception as e:
    report("Vector2长度", False, str(e))

try:
    v1 = Vector3(1, 0, 0)
    v2 = Vector3(0, 1, 0)
    cross = v1.cross(v2)
    report("Vector3叉积", cross.z == 1.0)
except Exception as e:
    report("Vector3叉积", False, str(e))

try:
    drawable.drawable_offset(lena_layer, 10, 10, wrap=True)
    report("像素偏移(环绕)", True)
    lena_layer.pixels = original_pixels.copy()
except Exception as e:
    report("像素偏移", False, str(e))

# ============================================================
print("\n--- 7. 绘画引擎 ---")
# ============================================================
canvas = GimpLayer(256, 256, "Canvas", FillType.WHITE, has_alpha=True)

try:
    opts = PaintOptions()
    opts.brush = Brush(size=15, hardness=0.8)
    pts = [(20, 128), (80, 80), (140, 180), (200, 100), (240, 128)]
    paint.paintbrush_stroke(canvas, pts, (255, 0, 0, 255), opts)
    report("画笔描边", canvas.pixels[128, 100, 0] > 0)
except Exception as e:
    report("画笔描边", False, str(e))

try:
    canvas2 = GimpLayer(256, 256, "Pencil Canvas", FillType.WHITE, has_alpha=True)
    opts = PaintOptions()
    opts.brush = Brush(size=5, hardness=1.0)
    pts = [(10, 200), (240, 200)]
    paint.pencil_stroke(canvas2, pts, (0, 0, 255, 255), opts)
    report("铅笔描边", True)
except Exception as e:
    report("铅笔描边", False, str(e))

try:
    canvas3 = GimpLayer(256, 256, "Eraser Canvas", FillType.WHITE, has_alpha=True)
    canvas3.pixels[:, :, 3] = 255
    opts = PaintOptions()
    opts.brush = Brush(size=20, hardness=1.0)
    pts = [(10, 128), (240, 128)]
    paint.eraser_stroke(canvas3, pts, opts)
    report("橡皮擦", canvas3.pixels[128, 128, 3] < 255)
except Exception as e:
    report("橡皮擦", False, str(e))

try:
    canvas4 = GimpLayer(256, 256, "Airbrush Canvas", FillType.WHITE, has_alpha=True)
    opts = PaintOptions()
    opts.brush = Brush(size=25, hardness=0.3)
    opts.rate = 80
    pts = [(50, 50), (100, 100), (150, 150), (200, 200)]
    paint.airbrush_stroke(canvas4, pts, (0, 128, 255, 200), opts)
    report("喷枪", True)
except Exception as e:
    report("喷枪", False, str(e))

try:
    canvas5 = GimpLayer(256, 256, "Clone Canvas", FillType.WHITE, has_alpha=True)
    paint.clone_stroke(canvas5, original_pixels,
                       [(50, 50), (100, 100)], source_offset=(0, 0))
    report("克隆工具", True)
except Exception as e:
    report("克隆工具", False, str(e))

try:
    from gimppy.enums import ConvolveType, DodgeBurnType
    canvas6 = GimpLayer(256, 256, "Dodge Canvas", has_alpha=True)
    canvas6.pixels = original_pixels.copy()
    paint.dodge_burn_stroke(canvas6, [(50, 128), (200, 128)],
                            DodgeBurnType.DODGE, intensity=0.3)
    report("减淡工具", True)
except Exception as e:
    report("减淡工具", False, str(e))

try:
    brush = Brush(size=20, hardness=0.5, shape=BrushShape.CIRCLE)
    mask = brush.get_mask()
    report("笔刷蒙版生成", mask.shape[0] > 0 and mask.max() == 1.0,
           f"(shape={mask.shape})")
except Exception as e:
    report("笔刷蒙版生成", False, str(e))

# ============================================================
print("\n--- 8. 矢量路径 ---")
# ============================================================
try:
    path = GimpPath("Lena Outline")
    stroke = Stroke()
    stroke.moveto(20, 20)
    stroke.lineto(236, 20)
    stroke.lineto(236, 236)
    stroke.lineto(20, 236)
    stroke.close()
    path.add_stroke(stroke)
    report("创建矩形路径", path.stroke_count == 1)
except Exception as e:
    report("创建矩形路径", False, str(e))

try:
    ellipse = Stroke.ellipse(128, 128, 100, 80)
    path.add_stroke(ellipse)
    report("创建椭圆路径", path.stroke_count == 2)
except Exception as e:
    report("创建椭圆路径", False, str(e))

try:
    length = ellipse.get_length()
    report("椭圆周长", length > 0, f"({length:.1f}px)")
except Exception as e:
    report("椭圆周长", False, str(e))

try:
    bounds = path.get_bounds()
    report("路径边界", bounds[2] > bounds[0] and bounds[3] > bounds[1],
           f"({bounds})")
except Exception as e:
    report("路径边界", False, str(e))

try:
    path.translate(10, 10)
    report("路径平移", path.strokes[0].anchors[0].x == 30)
    path.translate(-10, -10)
except Exception as e:
    report("路径平移", False, str(e))

try:
    svg = path.to_svg()
    report("导出SVG", '<path' in svg, f"(len={len(svg)})")
except Exception as e:
    report("导出SVG", False, str(e))

try:
    mask = path.to_selection_mask(256, 256)
    report("路径转选区蒙版", mask.sum() > 0)
except Exception as e:
    report("路径转选区蒙版", False, str(e))

try:
    img.add_path(path)
    report("添加路径到图像", len(img.paths) == 1)
    img.remove_path(path)
    report("从图像移除路径", len(img.paths) == 0)
except Exception as e:
    report("路径管理", False, str(e))

# ============================================================
print("\n--- 9. 文本图层 ---")
# ============================================================
try:
    text = GimpText("Hello Lena!", font="Sans-serif", size=24, color=(255, 255, 0))
    tl = GimpTextLayer(text, "Title")
    report("创建文本图层", tl.width > 0 and tl.height > 0,
           f"({tl.width}x{tl.height})")
except Exception as e:
    report("创建文本图层", False, str(e))

try:
    tl.set_text("Updated Text!")
    report("更新文本", tl.is_dynamic)
except Exception as e:
    report("更新文本", False, str(e))

try:
    tl.rasterize()
    report("文本栅格化", not tl.is_dynamic)
except Exception as e:
    report("文本栅格化", False, str(e))

# ============================================================
print("\n--- 10. 资源系统 ---")
# ============================================================
try:
    brush = GimpBrush("Soft Round", BrushShape.CIRCLE, radius=15, hardness=0.5)
    mask = brush.get_mask()
    info = brush.get_info()
    report("笔刷资源", mask.shape[0] > 0 and info["name"] == "Soft Round")
except Exception as e:
    report("笔刷资源", False, str(e))

try:
    pat_data = np.tile(
        np.array([[255, 0, 0], [0, 255, 0]], dtype=np.uint8), (5, 5, 1)
    )
    pattern = GimpPattern("Checker", pat_data)
    report("图案资源", pattern.width > 0 and pattern.height > 0,
           f"({pattern.width}x{pattern.height})")
except Exception as e:
    report("图案资源", False, str(e))

try:
    grad = GimpGradient("Rainbow")
    grad.segments.clear()
    colors = [(255,0,0,255), (255,255,0,255), (0,255,0,255), (0,0,255,255), (128,0,255,255)]
    for i in range(len(colors)-1):
        grad.add_segment(i/(len(colors)-1), (i+1)/(len(colors)-1),
                         colors[i], colors[i+1])
    c0 = grad.get_color_at(0.0)
    c_mid = grad.get_color_at(0.5)
    c1 = grad.get_color_at(1.0)
    report("渐变资源", c0[0] == 255 and c1[2] == 255,
           f"(start={c0}, mid={c_mid}, end={c1})")
except Exception as e:
    report("渐变资源", False, str(e))

try:
    pal = GimpPalette("Lena Palette")
    for y in range(0, 256, 32):
        for x in range(0, 256, 32):
            r, g, b = lena_layer.pixels[y, x, :3]
            pal.add_color(int(r), int(g), int(b), f"({r},{g},{b})")
    report("从图像提取调色板", pal.color_count > 0,
           f"({pal.color_count} colors)")
    closest = pal.find_closest(200, 100, 80)
    report("最近颜色查找", 0 <= closest < pal.color_count)
except Exception as e:
    report("调色板资源", False, str(e))

try:
    dyn = GimpDynamics("Pressure")
    result = dyn.apply(pressure=0.7, velocity=0.3)
    report("笔刷动力学", 0 < result["opacity"] < 1,
           f"(opacity={result['opacity']:.2f}, size={result['size']:.2f})")
except Exception as e:
    report("笔刷动力学", False, str(e))

# ============================================================
print("\n--- 11. 滤镜系统 ---")
# ============================================================
try:
    stack = FilterStack()
    f1 = GimpFilter("Bright+10%",
                    lambda p: color.brightness_contrast(p, brightness=0.1))
    f2 = GimpFilter("Saturate+20%",
                    lambda p: color.hue_saturation(p, saturation=0.2))
    stack.add(f1)
    stack.add(f2)
    result = stack.apply_all(lena_layer.pixels)
    report("滤镜栈应用", result.shape == lena_layer.pixels.shape and
           not np.array_equal(result, lena_layer.pixels))
except Exception as e:
    report("滤镜栈应用", False, str(e))

try:
    f2.visible = False
    result2 = stack.apply_all(lena_layer.pixels)
    report("滤镜可见性切换", not np.array_equal(result, result2))
    f2.visible = True
except Exception as e:
    report("滤镜可见性切换", False, str(e))

try:
    f1.opacity = 0.5
    result3 = stack.apply_all(lena_layer.pixels)
    report("滤镜透明度", not np.array_equal(result3, result))
    f1.opacity = 1.0
except Exception as e:
    report("滤镜透明度", False, str(e))

# ============================================================
print("\n--- 12. 撤销系统 ---")
# ============================================================
try:
    img2 = GimpImage(256, 256)
    l = img2.new_layer("Test")
    l.pixels[:] = [100, 100, 100, 255]
    original = l.pixels[128, 128, 0]

    img2.invert()
    after_invert = l.pixels[128, 128, 0]

    img2.brightness_contrast(brightness=0.5)
    after_bc = l.pixels[128, 128, 0]

    img2.undo()
    after_undo1 = l.pixels[128, 128, 0]

    img2.undo()
    after_undo2 = l.pixels[128, 128, 0]

    img2.redo()
    after_redo = l.pixels[128, 128, 0]

    report("多步撤销/重做",
           after_undo2 == original and after_undo1 == after_invert and after_redo == after_invert,
           f"(orig={original}, inv={after_invert}, bc={after_bc}, "
           f"undo1={after_undo1}, undo2={after_undo2}, redo={after_redo})")
except Exception as e:
    report("多步撤销/重做", False, str(e))

try:
    img3 = GimpImage(10, 10)
    l = img3.new_layer("G")
    l.pixels[:] = [50, 50, 50, 255]
    img3.begin_undo_group("batch")
    img3.invert()
    img3.desaturate()
    img3.end_undo_group()
    img3.undo()
    report("撤销组", l.pixels[0, 0, 0] == 50)
except Exception as e:
    report("撤销组", False, str(e))

# ============================================================
print("\n--- 13. 图像操作 ---")
# ============================================================
try:
    dup = img.duplicate()
    report("复制图像", dup.width == img.width and len(dup.layers) == len(img.layers)
           and dup is not img)
except Exception as e:
    report("复制图像", False, str(e))

try:
    img2 = GimpImage(256, 256)
    l1 = img2.new_layer("BG", FillType.WHITE)
    l2 = img2.new_layer("FG")
    l2.pixels[50:150, 50:150] = [255, 0, 0, 200]
    flat = img2.flatten()
    report("合并所有图层", len(img2.layers) == 1 and not flat.has_alpha)
except Exception as e:
    report("合并所有图层", False, str(e))

try:
    img2 = GimpImage(256, 256)
    l1 = img2.new_layer("BG", FillType.WHITE)
    l2 = img2.new_layer("FG")
    l2.visible = False
    merged = img2.merge_visible_layers()
    report("合并可见图层", len(img2.layers) == 2 and merged in img2.layers,
           f"({len(img2.layers)} layers: {[l.name for l in img2.layers]})")
except Exception as e:
    report("合并可见图层", False, str(e))

try:
    proj = img.get_projection()
    report("获取合成投影", proj.shape[:2] == (256, 256))
except Exception as e:
    report("获取合成投影", False, str(e))

try:
    c = img.pick_color(128, 128, sample_merged=True)
    report("拾色器", len(c) >= 3, f"(color={c[:3]})")
except Exception as e:
    report("拾色器", False, str(e))

try:
    img.convert_grayscale()
    report("转灰度", img.image_type == ImageType.GRAY)
    img.convert_rgb()
    report("转RGB", img.image_type == ImageType.RGB)
except Exception as e:
    report("色彩模式转换", False, str(e))

# ============================================================
print("\n--- 14. 文件保存 ---")
# ============================================================
lena_layer.pixels = original_pixels.copy()

try:
    out_png = os.path.join(OUTPUT_DIR, "lena_original.png")
    img.save(out_png)
    report("保存PNG", os.path.exists(out_png),
           f"({os.path.getsize(out_png)} bytes)")
except Exception as e:
    report("保存PNG", False, str(e))

try:
    out_jpg = os.path.join(OUTPUT_DIR, "lena_save.jpg")
    img.save(out_jpg, quality=95)
    report("保存JPEG", os.path.exists(out_jpg),
           f"({os.path.getsize(out_jpg)} bytes)")
except Exception as e:
    report("保存JPEG", False, str(e))

try:
    out_bmp = os.path.join(OUTPUT_DIR, "lena_save.bmp")
    img.save(out_bmp)
    report("保存BMP", os.path.exists(out_bmp))
except Exception as e:
    report("保存BMP", False, str(e))

# ============================================================
print("\n--- 15. 综合效果输出 ---")
# ============================================================
effects = [
    ("brightness_up", lambda p: color.brightness_contrast(p, brightness=0.3)),
    ("contrast_up", lambda p: color.brightness_contrast(p, contrast=0.4)),
    ("invert", color.invert),
    ("desaturate", lambda p: color.desaturate(p, DesaturateMode.LUMINANCE)),
    ("posterize_4", lambda p: color.posterize(p, 4)),
    ("threshold_128", lambda p: color.threshold(p, 128)),
    ("equalize", color.equalize),
    ("hue_shift_90", lambda p: color.hue_saturation(p, hue_offset=90)),
    ("saturate_50", lambda p: color.hue_saturation(p, saturation=0.5)),
    ("colorize_blue", lambda p: color.colorize(p, (0.1, 0.2, 0.8))),
    ("levels_stretch", color.levels_stretch),
    ("shadows_boost", lambda p: color.shadows_highlights(p, shadows=50)),
]

saved_count = 0
for name, fn in effects:
    try:
        result = fn(original_pixels.copy())
        test_layer = GimpLayer(256, 256, name, has_alpha=True)
        test_layer.pixels = result
        test_img = GimpImage(256, 256)
        test_img.add_layer(test_layer)
        out_path = os.path.join(OUTPUT_DIR, f"lena_{name}.png")
        test_img.save(out_path)
        saved_count += 1
    except Exception as e:
        print(f"  [WARN] 效果 '{name}' 保存失败: {e}")

report("批量效果输出", saved_count == len(effects),
       f"({saved_count}/{len(effects)} files in test_output/)")

# ============================================================
print("\n" + "=" * 60)
print(f"  测试结果: {passed} 通过, {failed} 失败")
if errors:
    print(f"\n  失败项:")
    for e in errors:
        print(f"    - {e}")
print("=" * 60)
print(f"\n  输出文件保存在: {OUTPUT_DIR}/")
if os.path.exists(OUTPUT_DIR):
    files = os.listdir(OUTPUT_DIR)
    print(f"  共 {len(files)} 个文件:")
    for f in sorted(files):
        size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
        print(f"    {f} ({size:,} bytes)")
