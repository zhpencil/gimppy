"""
Generate one representative output image per test category (15 categories).
Each image visually demonstrates the key features of that category.
"""

import sys, os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gimppy import (
    GimpImage, GimpLayer, GimpGroupLayer, GimpLayerMask,
    GimpChannel, GimpSelection, GimpPath, Stroke,
    GimpText, GimpTextLayer,
    GimpBrush, GimpPattern, GimpGradient, GimpPalette, GimpDynamics,
    GimpFilter, FilterStack,
    Brush, PaintOptions, Matrix3,
)
from gimppy.enums import (
    ImageType, LayerMode, FillType, FlipType, RotationType,
    SelectionOperation, DesaturateMode, BrushShape,
    GradientType, GuideOrientation, GridStyle,
    InterpolationType, HistogramChannel, MaskApplyMode,
)
from gimppy import color, drawable, paint
from gimppy.fileio import load_image

def to_rgba(pixels):
    """Ensure pixels have 4 channels (RGBA)."""
    if pixels.ndim == 2:
        pixels = pixels[:, :, np.newaxis]
    if pixels.shape[2] == 1:
        return np.concatenate([pixels, pixels, pixels,
                               np.full((*pixels.shape[:2], 1), 255, dtype=np.uint8)], axis=2)
    if pixels.shape[2] == 3:
        return np.concatenate([pixels, np.full((*pixels.shape[:2], 1), 255, dtype=np.uint8)], axis=2)
    return pixels

LENA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lena.jpg")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_output")
os.makedirs(OUT, exist_ok=True)

def load_lena():
    data = load_image(LENA)
    img = GimpImage(data["width"], data["height"], data["image_type"], name="Lena")
    for ld in data.get("layers", []):
        pixels = ld["pixels"]
        has_alpha = ld.get("has_alpha", pixels.shape[2] >= 4 if pixels.ndim == 3 else False)
        layer = GimpLayer(pixels.shape[1], pixels.shape[0], ld.get("name","Lena"),
                          img.image_type, has_alpha=has_alpha)
        layer.pixels = pixels
        img.add_layer(layer)
    return img

def save(img, name):
    out = os.path.join(OUT, f"cat_{name}.png")
    img.save(out)
    print(f"  -> {os.path.basename(out)} ({os.path.getsize(out):,} bytes)")

W, H = 256, 256

# ============================================================
print("=== 1. 文件加载 ===")
# ============================================================
img = load_lena()
save(img, "01_file_load")

# ============================================================
print("=== 2. 图层操作 ===")
# ============================================================
img = GimpImage(W, H)
bg = img.new_layer("BG", FillType.WHITE)
# Layer 1: original Lena quadrant
lena = load_lena()
lena_layer = lena.active_layer
src = to_rgba(lena_layer.pixels[:128, :128])
bg.pixels[:128, :128] = src
# Layer 2: red overlay with opacity
red = img.new_layer("Red 50%")
red.pixels[64:192, 64:192, :3] = [255, 0, 0]
red.pixels[64:192, 64:192, 3] = 128
red.set_opacity(0.5)
# Layer 3: blue with multiply mode
blue = img.new_layer("Blue Multiply")
blue.pixels[32:224, 32:224, :3] = [0, 0, 255]
blue.pixels[32:224, 32:224, 3] = 180
blue.set_mode(LayerMode.MULTIPLY)
blue.set_opacity(0.4)
# Layer mask on red
mask = red.create_mask()
mask.pixels[:64, :] = 0
mask.pixels[192:, :] = 0
red.add_mask(mask)
save(img, "02_layers")

# ============================================================
print("=== 3. 选区操作 ===")
# ============================================================
img = GimpImage(W, H)
layer = img.new_layer("BG", FillType.WHITE)
# Draw selection regions as colored areas
# Rectangle selection -> fill red
img.selection.select_rectangle(10, 10, 80, 80, antialias=False)
layer.pixels[10:90, 10:90, :3] = [255, 0, 0]
layer.pixels[10:90, 10:90, 3] = 200
img.selection.select_none()
# Ellipse selection -> fill green
img.selection.select_ellipse(130, 10, 110, 110, antialias=False)
img.selection.feather(3.0)
sel_mask = img.selection.pixels.astype(np.float32) / 255.0
for c in range(3):
    layer.pixels[:, :, c] = (layer.pixels[:, :, c].astype(np.float32) * (1 - sel_mask) +
                              np.array([0, 200, 0])[c] * sel_mask).astype(np.uint8)
layer.pixels[:, :, 3] = np.maximum(layer.pixels[:, :, 3], (sel_mask * 200).astype(np.uint8))
img.selection.select_none()
# Polygon selection -> fill blue
img.selection.select_polygon([(128,130),(240,170),(180,250),(70,230)], antialias=False)
layer.pixels[130:251, 70:241, :3] = np.where(
    img.selection.pixels[130:251, 70:241, np.newaxis] > 127,
    [0, 0, 255], layer.pixels[130:251, 70:241, :3]
)
img.selection.select_none()
# Inverted selection border -> yellow border
img.selection.select_rectangle(5, 5, 246, 246, antialias=False)
img.selection.select_rectangle(15, 15, 226, 226, SelectionOperation.SUBTRACT, antialias=False)
border = img.selection.pixels.astype(np.float32) / 255.0
for c in range(3):
    layer.pixels[:, :, c] = (layer.pixels[:, :, c].astype(np.float32) * (1 - border) +
                              np.array([255, 255, 0])[c] * border).astype(np.uint8)
save(img, "03_selection")

# ============================================================
print("=== 4. 色彩调整 ===")
# ============================================================
lena = load_lena()
lp = to_rgba(lena.active_layer.pixels.copy())
if lp.shape[2] == 3:
    lp = np.concatenate([lp, np.full((*lp.shape[:2], 1), 255, dtype=np.uint8)], axis=2)
img = GimpImage(W, H)
layer = img.new_layer("Color Adjustments")
# 4 quadrants: original, brightness+contrast, hue shift, desaturate
layer.pixels[:128, :128] = lp[:128, :128]  # original
layer.pixels[:128, 128:] = color.brightness_contrast(lp[:128, 128:], brightness=0.3, contrast=0.3)
layer.pixels[128:, :128] = color.hue_saturation(lp[128:, :128], hue_offset=90, saturation=0.4)
layer.pixels[128:, 128:] = color.desaturate(lp[128:, 128:], DesaturateMode.LUMINANCE)
save(img, "04_color_adjust")

# ============================================================
print("=== 5. 图像级色彩+撤销 ===")
# ============================================================
img = load_lena()
# Apply then undo to show reversibility
img.brightness_contrast(brightness=0.4)
img.invert()
# Undo invert
img.undo()
# Result: only brightness applied
save(img, "05_color_undo")

# ============================================================
print("=== 6. 几何变换 ===")
# ============================================================
lena = load_lena()
lp = to_rgba(lena.active_layer.pixels.copy())
img = GimpImage(W, H)
layer = img.new_layer("Transforms")
# 4 quadrants: original, h-flip, v-flip, 90-rotate
layer.pixels[:128, :128] = lp[:128, :128]
layer.pixels[:128, 128:] = np.fliplr(lp[:128, 128:])
layer.pixels[128:, :128] = np.flipud(lp[128:, :128])
layer.pixels[128:, 128:] = np.rot90(lp[128:, 128:], k=1)
save(img, "06_transforms")

# ============================================================
print("=== 7. 绘画引擎 ===")
# ============================================================
img = GimpImage(W, H)
canvas = img.new_layer("Canvas", FillType.WHITE)
# Brush stroke (red)
opts = PaintOptions()
opts.brush = Brush(size=12, hardness=0.8)
paint.paintbrush_stroke(canvas, [(20,40),(60,20),(100,60),(140,20),(180,50),(230,30)],
                        (220, 50, 50, 255), opts)
# Pencil stroke (black)
opts2 = PaintOptions()
opts2.brush = Brush(size=4, hardness=1.0)
paint.pencil_stroke(canvas, [(20,80),(230,80)], (0, 0, 0, 255), opts2)
# Airbrush (blue)
opts3 = PaintOptions()
opts3.brush = Brush(size=30, hardness=0.2)
opts3.rate = 60
paint.airbrush_stroke(canvas, [(40,120),(100,160),(180,130),(230,170)],
                      (50, 80, 220, 200), opts3)
# Eraser on white bg -> transparent
canvas.pixels[:, :, 3] = 255
opts4 = PaintOptions()
opts4.brush = Brush(size=20, hardness=1.0)
paint.eraser_stroke(canvas, [(20,210),(230,210)], opts4)
# Smudge
opts5 = PaintOptions()
opts5.brush = Brush(size=15, hardness=0.5)
paint.smudge_stroke(canvas, [(20,240),(230,240)], rate=0.6, options=opts5)
save(img, "07_paint")

# ============================================================
print("=== 8. 矢量路径 ===")
# ============================================================
img = GimpImage(W, H)
layer = img.new_layer("BG", FillType.WHITE)
# Draw path strokes as colored lines
path = GimpPath("Demo")
# Rectangle path
s1 = Stroke()
s1.moveto(20, 20); s1.lineto(120, 20); s1.lineto(120, 120); s1.lineto(20, 120); s1.close()
path.add_stroke(s1)
# Ellipse path
s2 = Stroke.ellipse(180, 70, 50, 40)
path.add_stroke(s2)
# Bezier curve
s3 = Stroke()
s3.moveto(20, 200)
s3.cubicto(60, 140, 140, 260, 230, 200)
path.add_stroke(s3)
# Render paths onto layer
mask = path.to_selection_mask(W, H)
layer.pixels[mask > 0, :3] = [30, 30, 200]
layer.pixels[mask > 0, 3] = 255
# Also render ellipse perimeter
ellipse_mask = GimpSelection(W, H)
ellipse_mask.select_ellipse(130, 30, 100, 80, antialias=False)
ellipse_mask.select_ellipse(134, 34, 92, 72, SelectionOperation.SUBTRACT, antialias=False)
em = ellipse_mask.pixels
layer.pixels[em > 127, :3] = [200, 30, 30]
layer.pixels[em > 127, 3] = 255
save(img, "08_paths")

# ============================================================
print("=== 9. 文本图层 ===")
# ============================================================
img = GimpImage(W, H)
layer = img.new_layer("BG", FillType.WHITE)
# Simulate text rendering at different sizes
for i, (txt, size, clr) in enumerate([
    ("Title 24px", 24, (0, 0, 0)),
    ("Body 16px", 16, (80, 80, 80)),
    ("Small 10px", 10, (160, 0, 0)),
]):
    t = GimpText(txt, size=size, color=clr)
    tl = GimpTextLayer(t)
    y_off = 20 + i * 70
    x_off = 20
    h, w = tl.height, tl.width
    if y_off + h <= H and x_off + w <= W:
        layer.pixels[y_off:y_off+h, x_off:x_off+w] = tl.pixels
save(img, "09_text")

# ============================================================
print("=== 10. 资源系统 ===")
# ============================================================
img = GimpImage(W, H)
layer = img.new_layer("Resources")
# Brush shapes
for i, (shape, label_x) in enumerate([(BrushShape.CIRCLE, 20),
                                       (BrushShape.SQUARE, 100),
                                       (BrushShape.DIAMOND, 180)]):
    b = Brush(size=30, hardness=0.7, shape=shape)
    mask = b.get_mask()
    mh, mw = mask.shape
    y0, x0 = 20, label_x
    for by in range(mh):
        for bx in range(mw):
            if mask[by, bx] > 0:
                py, px = y0 + by, x0 + bx
                if py < H and px < W:
                    layer.pixels[py, px, :3] = [50, 50, 200]
                    layer.pixels[py, px, 3] = int(mask[by, bx] * 255)
# Gradient bar
grad = GimpGradient("Test")
grad.segments.clear()
colors = [(255,0,0,255),(255,255,0,255),(0,255,0,255),(0,255,255,255),(0,0,255,255),(128,0,255,255)]
for i in range(len(colors)-1):
    grad.add_segment(i/(len(colors)-1), (i+1)/(len(colors)-1), colors[i], colors[i+1])
for x in range(W):
    c = grad.get_color_at(x / W)
    layer.pixels[130:155, x, :4] = c
# Palette swatches
pal = GimpPalette("Demo")
for y in range(0, 256, 32):
    for x in range(0, 256, 32):
        pal.add_color(*lena.active_layer.pixels[y, x, :3].tolist(), "")
swatch_y = 170
for i in range(min(32, pal.color_count)):
    r, g, b, _ = pal.colors[i]
    sx = (i % 16) * 16
    sy = swatch_y + (i // 16) * 16
    if sy + 14 <= H and sx + 14 <= W:
        layer.pixels[sy:sy+14, sx:sx+14, :3] = [r, g, b]
        layer.pixels[sy:sy+14, sx:sx+14, 3] = 255
save(img, "10_resources")

# ============================================================
print("=== 11. 滤镜系统 ===")
# ============================================================
lena = load_lena()
lp = to_rgba(lena.active_layer.pixels.copy())
img = GimpImage(W, H)
layer = img.new_layer("Filters")
stack = FilterStack()
# Apply different filter combos to 4 quadrants
f_bc = GimpFilter("B+C", lambda p: color.brightness_contrast(p, brightness=0.15, contrast=0.2))
f_hs = GimpFilter("H+S", lambda p: color.hue_saturation(p, saturation=0.3))
f_inv = GimpFilter("Inv", color.invert)
f_eq = GimpFilter("Eq", color.equalize)

layer.pixels[:128, :128] = f_bc.apply(lp[:128, :128])
layer.pixels[:128, 128:] = f_hs.apply(lp[:128, 128:])
layer.pixels[128:, :128] = f_inv.apply(lp[128:, :128])
layer.pixels[128:, 128:] = f_eq.apply(lp[128:, 128:])
save(img, "11_filters")

# ============================================================
print("=== 12. 撤销系统 ===")
# ============================================================
img = GimpImage(W, H)
layer = img.new_layer("Undo Demo")
lena = load_lena()
lp = to_rgba(lena.active_layer.pixels.copy())
# Show 4 states: original, after invert, after brightness, after undo
layer.pixels[:128, :128] = lp[:128, :128]  # original
layer.pixels[:128, 128:] = color.invert(lp[:128, 128:])  # after invert
layer.pixels[128:, :128] = color.brightness_contrast(
    color.invert(lp[128:, :128]), brightness=0.3)  # after brightness
# Simulate undo of brightness -> back to invert
layer.pixels[128:, 128:] = color.invert(lp[128:, 128:])  # after undo
save(img, "12_undo")

# ============================================================
print("=== 13. 图像操作 ===")
# ============================================================
img = GimpImage(W, H)
layer = img.new_layer("Image Ops")
lena = load_lena()
lp = to_rgba(lena.active_layer.pixels.copy())
# 4 quadrants: duplicate, flatten, merge visible, projection
layer.pixels[:128, :128] = lp[:128, :128]  # original
# Simulate flatten: composite with white bg
bg = np.full((128, 128, 4), [255, 255, 255, 255], dtype=np.uint8)
alpha = lp[128:256, :128, 3:4].astype(np.float32) / 255.0
layer.pixels[128:256, :128, :3] = (lp[128:256, :128, :3].astype(np.float32) * alpha +
                                    255 * (1 - alpha)).astype(np.uint8)
layer.pixels[128:256, :128, 3] = 255
# Merge visible: same as flatten for single visible layer
layer.pixels[:128, 128:] = lp[:128, 128:]
# Color mode conversion: grayscale
gray = color.desaturate(lp[128:, 128:], DesaturateMode.LUMINANCE)
layer.pixels[128:, 128:] = gray
save(img, "13_image_ops")

# ============================================================
print("=== 14. 文件保存 ===")
# ============================================================
img = load_lena()
# Save in all formats
img.save(os.path.join(OUT, "cat_14_save.png"))
img.save(os.path.join(OUT, "cat_14_save.jpg"), quality=95)
img.save(os.path.join(OUT, "cat_14_save.bmp"))
print(f"  -> cat_14_save.png ({os.path.getsize(os.path.join(OUT, 'cat_14_save.png')):,} bytes)")
print(f"  -> cat_14_save.jpg ({os.path.getsize(os.path.join(OUT, 'cat_14_save.jpg')):,} bytes)")
print(f"  -> cat_14_save.bmp ({os.path.getsize(os.path.join(OUT, 'cat_14_save.bmp')):,} bytes)")

# ============================================================
print("=== 15. 综合效果 ===")
# ============================================================
lena = load_lena()
lp = to_rgba(lena.active_layer.pixels.copy())
img = GimpImage(W, H)
layer = img.new_layer("Effects Grid")
# 4x3 grid of effects
effects = [
    ("Original", lp),
    ("Bright+30%", color.brightness_contrast(lp, brightness=0.3)),
    ("Contrast+40%", color.brightness_contrast(lp, contrast=0.4)),
    ("Invert", color.invert(lp)),
    ("Desaturate", color.desaturate(lp, DesaturateMode.LUMINANCE)),
    ("Posterize 4", color.posterize(lp, 4)),
    ("Threshold 128", color.threshold(lp, 128)),
    ("Equalize", color.equalize(lp)),
    ("Hue+90", color.hue_saturation(lp, hue_offset=90)),
    ("Saturate+50%", color.hue_saturation(lp, saturation=0.5)),
    ("Colorize Blue", color.colorize(lp, (0.1, 0.2, 0.8))),
    ("Levels Stretch", color.levels_stretch(lp)),
]
cell_w, cell_h = W // 4, H // 3
for i, (name, pixels) in enumerate(effects):
    row, col = i // 4, i % 4
    y0, y1 = row * cell_h, (row + 1) * cell_h
    x0, x1 = col * cell_w, (col + 1) * cell_w
    # Resize effect to fit cell
    from gimppy.transform import _scale_array
    cell_pixels = _scale_array(pixels[:, :, :3], cell_w, cell_h, "linear")
    layer.pixels[y0:y1, x0:x1, :3] = cell_pixels
    layer.pixels[y0:y1, x0:x1, 3] = 255
save(img, "15_all_effects")

print("\nDone! All 15 category images saved to:", OUT)
