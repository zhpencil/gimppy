"""
Color adjustment operations — extracted from app/operations/:
  gimpoperationbrightnesscontrast.c, gimpoperationlevels.c,
  gimpoperationcurves.c, gimpoperationhuesaturation.c,
  gimpoperationcolorbalance.c, gimpoperationdesaturate.c,
  gimpoperationcolorize.c, gimpoperationposterize.c,
  gimpoperationthreshold.c, gimpoperationequalize.c,
  gimpoperationshadowsHighlights.c.
"""

import math
import numpy as np
from typing import Tuple, Optional, List

from .enums import DesaturateMode, HistogramChannel
from .exceptions import ColorError


def brightness_contrast(pixels: np.ndarray, brightness: float = 0.0,
                        contrast: float = 0.0) -> np.ndarray:
    """
    Brightness/Contrast — from gimpoperationbrightnesscontrast.c.
    brightness: -1.0 to 1.0
    contrast: -1.0 to 1.0
    """
    result = pixels.astype(np.float32)
    channels = min(3, result.shape[2])

    if contrast != 0:
        factor = (1.0 + contrast) / (1.0 - min(contrast, 0.99))
        for c in range(channels):
            result[:, :, c] = ((result[:, :, c] / 255.0 - 0.5) * factor + 0.5) * 255.0

    if brightness != 0:
        for c in range(channels):
            result[:, :, c] += brightness * 255.0

    return np.clip(result, 0, 255).astype(np.uint8)


def levels(pixels: np.ndarray,
           input_black: float = 0.0, input_white: float = 1.0,
           gamma: float = 1.0,
           output_black: float = 0.0, output_white: float = 1.0,
           channel: int = -1) -> np.ndarray:
    """
    Levels adjustment — from gimpoperationlevels.c.
    input_black/white: 0.0-1.0 input range
    gamma: 0.1-10.0
    output_black/white: 0.0-1.0 output range
    channel: -1 for all, 0=R, 1=G, 2=B
    """
    result = pixels.astype(np.float32) / 255.0
    channels = min(3, result.shape[2])

    ch_start = max(0, channel) if channel >= 0 else 0
    ch_end = min(ch_start + 1, channels) if channel >= 0 else channels

    in_range = max(input_white - input_black, 0.001)
    out_range = output_white - output_black

    for c in range(ch_start, ch_end):
        val = result[:, :, c]
        val = (val - input_black) / in_range
        val = np.clip(val, 0, 1)
        if gamma != 1.0:
            val = np.power(val, 1.0 / gamma)
        val = val * out_range + output_black
        result[:, :, c] = val

    return np.clip(result * 255, 0, 255).astype(np.uint8)


def levels_stretch(pixels: np.ndarray) -> np.ndarray:
    """Auto levels — stretch each channel to full range."""
    result = pixels.copy()
    channels = min(3, result.shape[2])
    for c in range(channels):
        ch = result[:, :, c]
        lo = np.percentile(ch, 1)
        hi = np.percentile(ch, 99)
        if hi - lo < 1:
            continue
        result[:, :, c] = np.clip((ch.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
    return result


def curves(pixels: np.ndarray, curve_points: List[Tuple[float, float]],
           channel: int = -1) -> np.ndarray:
    """
    Curves adjustment — from gimpoperationcurves.c.
    curve_points: list of (input, output) pairs, each 0.0-1.0
    """
    lut = _build_curve_lut(curve_points)
    result = pixels.copy()
    channels = min(3, result.shape[2])
    ch_start = max(0, channel) if channel >= 0 else 0
    ch_end = min(ch_start + 1, channels) if channel >= 0 else channels
    for c in range(ch_start, ch_end):
        result[:, :, c] = lut[result[:, :, c]]
    return result


def _build_curve_lut(points: List[Tuple[float, float]]) -> np.ndarray:
    lut = np.zeros(256, dtype=np.uint8)
    if not points:
        return np.arange(256, dtype=np.uint8)
    points = sorted(points, key=lambda p: p[0])
    for i in range(256):
        x = i / 255.0
        if x <= points[0][0]:
            lut[i] = int(points[0][1] * 255)
        elif x >= points[-1][0]:
            lut[i] = int(points[-1][1] * 255)
        else:
            for j in range(len(points) - 1):
                if points[j][0] <= x <= points[j+1][0]:
                    t = (x - points[j][0]) / max(points[j+1][0] - points[j][0], 1e-10)
                    t = t * t * (3 - 2 * t)
                    val = points[j][1] * (1 - t) + points[j+1][1] * t
                    lut[i] = int(val * 255)
                    break
    return lut


def hue_saturation(pixels: np.ndarray,
                   hue_offset: float = 0.0,
                   saturation: float = 0.0,
                   lightness: float = 0.0) -> np.ndarray:
    """
    Hue/Saturation — from gimpoperationhuesaturation.c.
    hue_offset: -180 to 180 degrees
    saturation: -1.0 to 1.0
    lightness: -1.0 to 1.0
    """
    result = pixels.astype(np.float32)
    channels = min(3, result.shape[2])
    if channels < 3:
        return np.clip(result, 0, 255).astype(np.uint8)

    r, g, b = result[:,:,0]/255, result[:,:,1]/255, result[:,:,2]/255
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    diff = mx - mn
    l = (mx + mn) / 2

    s = np.where(diff < 1e-10, 0,
                 np.where(l <= 0.5, diff / (mx + mn + 1e-10),
                          diff / (2.0 - mx - mn + 1e-10)))
    h = np.zeros_like(l)
    mask_r = (mx == r) & (diff > 1e-10)
    mask_g = (mx == g) & (diff > 1e-10)
    mask_b = (mx == b) & (diff > 1e-10)
    h[mask_r] = ((g[mask_r] - b[mask_r]) / (diff[mask_r] + 1e-10)) % 6
    h[mask_g] = ((b[mask_g] - r[mask_g]) / (diff[mask_g] + 1e-10)) + 2
    h[mask_b] = ((r[mask_b] - g[mask_b]) / (diff[mask_b] + 1e-10)) + 4
    h = h / 6.0

    h = (h + hue_offset / 360.0) % 1.0
    s = np.clip(s * (1 + saturation), 0, 1)
    l = np.clip(l + lightness, 0, 1)

    def _hsl_to_rgb(h, s, l):
        c = (1 - np.abs(2*l - 1)) * s
        x = c * (1 - np.abs((h * 6) % 2 - 1))
        m = l - c / 2
        r = np.zeros_like(h)
        g = np.zeros_like(h)
        b = np.zeros_like(h)
        for lo, hi, rv, gv, bv in [
            (0, 1/6, c, x, np.zeros_like(h)),
            (1/6, 2/6, x, c, np.zeros_like(h)),
            (2/6, 3/6, np.zeros_like(h), c, x),
            (3/6, 4/6, np.zeros_like(h), x, c),
            (4/6, 5/6, x, np.zeros_like(h), c),
            (5/6, 1.0, c, np.zeros_like(h), x),
        ]:
            mask = (h >= lo) & (h < hi)
            r[mask] = rv[mask]
            g[mask] = gv[mask]
            b[mask] = bv[mask]
        return r + m, g + m, b + m

    nr, ng, nb = _hsl_to_rgb(h, s, l)
    result[:,:,0] = np.clip(nr * 255, 0, 255)
    result[:,:,1] = np.clip(ng * 255, 0, 255)
    result[:,:,2] = np.clip(nb * 255, 0, 255)
    return result.astype(np.uint8)


def colorize(pixels: np.ndarray, color: Tuple[float, float, float],
             lightness: float = 0.5) -> np.ndarray:
    """
    Colorize — from gimpoperationcolorize.c.
    Applies a single hue to the image preserving luminosity.
    """
    result = pixels.astype(np.float32)
    channels = min(3, result.shape[2])
    if channels < 3:
        return pixels.copy()
    lum = 0.299 * result[:,:,0] + 0.587 * result[:,:,1] + 0.114 * result[:,:,2]
    lum = lum / 255.0
    for c in range(3):
        result[:,:,c] = (color[c] * lum * 2.0 * (1 - lum) + color[c] * lum * lum) * 255
    return np.clip(result, 0, 255).astype(np.uint8)


def desaturate(pixels: np.ndarray, mode: DesaturateMode = DesaturateMode.LUMINANCE) -> np.ndarray:
    """
    Desaturate — from gimpoperationdesaturate.c.
    """
    result = pixels.copy()
    channels = min(3, result.shape[2])
    if channels < 3:
        return result
    r, g, b = result[:,:,0].astype(np.float32), result[:,:,1].astype(np.float32), result[:,:,2].astype(np.float32)
    if mode == DesaturateMode.LIGHTNESS:
        gray = (np.maximum(np.maximum(r, g), b) + np.minimum(np.minimum(r, g), b)) / 2
    elif mode == DesaturateMode.VALUE:
        gray = np.maximum(np.maximum(r, g), b)
    else:
        gray = 0.299 * r + 0.587 * g + 0.114 * b
    result[:,:,0] = gray.astype(np.uint8)
    result[:,:,1] = gray.astype(np.uint8)
    result[:,:,2] = gray.astype(np.uint8)
    return result


def posterize(pixels: np.ndarray, levels: int = 4) -> np.ndarray:
    """
    Posterize — from gimpoperationposterize.c.
    Reduces each channel to the specified number of levels.
    """
    if levels < 2:
        levels = 2
    result = pixels.astype(np.float32)
    channels = min(3, result.shape[2])
    for c in range(channels):
        result[:,:,c] = np.floor(result[:,:,c] / 256.0 * levels) / (levels - 1) * 255
    return np.clip(result, 0, 255).astype(np.uint8)


def threshold(pixels: np.ndarray, value: int = 127) -> np.ndarray:
    """
    Threshold — from gimpoperationthreshold.c.
    Converts to black and white at the given threshold.
    """
    result = pixels.copy()
    channels = min(3, result.shape[2])
    if channels >= 3:
        gray = 0.299 * result[:,:,0].astype(np.float32) + \
               0.587 * result[:,:,1].astype(np.float32) + \
               0.114 * result[:,:,2].astype(np.float32)
    else:
        gray = result[:,:,0].astype(np.float32)
    mask = gray >= value
    for c in range(channels):
        result[:,:,c] = np.where(mask, 255, 0)
    return result


def invert(pixels: np.ndarray) -> np.ndarray:
    """Invert — from gimpdrawable-color.c."""
    result = pixels.copy()
    channels = min(3, result.shape[2])
    for c in range(channels):
        result[:,:,c] = 255 - result[:,:,c]
    return result


def equalize(pixels: np.ndarray) -> np.ndarray:
    """
    Equalize — from gimpoperationequalize.c / gimpdrawable-equalize.c.
    Histogram equalization.
    """
    result = pixels.copy()
    channels = min(3, result.shape[2])
    for c in range(channels):
        hist = np.histogram(result[:,:,c].flatten(), bins=256, range=(0,256))[0]
        cdf = hist.cumsum()
        cdf_min = cdf[cdf > 0].min() if np.any(cdf > 0) else 0
        total = result.shape[0] * result.shape[1]
        denom = max(total - cdf_min, 1)
        lut = ((cdf - cdf_min) * 255 / denom).clip(0, 255).astype(np.uint8)
        result[:,:,c] = lut[result[:,:,c]]
    return result


def color_balance(pixels: np.ndarray,
                  cyan_red: float = 0.0,
                  magenta_green: float = 0.0,
                  yellow_blue: float = 0.0,
                  shadows: bool = True,
                  midtones: bool = True,
                  highlights: bool = True) -> np.ndarray:
    """
    Color Balance — from gimpoperationcolorbalance.c.
    cyan_red, magenta_green, yellow_blue: -1.0 to 1.0
    """
    result = pixels.astype(np.float32)
    channels = min(3, result.shape[2])
    if channels < 3:
        return pixels.copy()

    lum = 0.299 * result[:,:,0] + 0.587 * result[:,:,1] + 0.114 * result[:,:,2]
    shadow_mask = np.clip(1.0 - lum / 127.5, 0, 1) if shadows else np.zeros_like(lum)
    highlight_mask = np.clip((lum - 127.5) / 127.5, 0, 1) if highlights else np.zeros_like(lum)
    midtone_mask = np.ones_like(lum) if midtones else np.zeros_like(lum)
    midtone_mask = midtone_mask * (1 - shadow_mask) * (1 - highlight_mask)
    weight = shadow_mask + midtone_mask + highlight_mask

    cr = cyan_red * 100 * weight
    mg = magenta_green * 100 * weight
    yb = yellow_blue * 100 * weight

    result[:,:,0] = np.clip(result[:,:,0] + cr - mg, 0, 255)
    result[:,:,1] = np.clip(result[:,:,1] + mg - yb, 0, 255)
    result[:,:,2] = np.clip(result[:,:,2] + yb - cr, 0, 255)
    return result.astype(np.uint8)


def shadows_highlights(pixels: np.ndarray,
                       shadows: float = 0.0,
                       highlights: float = 0.0,
                       white_point: float = 0.0,
                       radius: float = 100.0,
                       compress: float = 0.5,
                       shadows_cc: float = 0.0,
                       highlights_cc: float = 0.0) -> np.ndarray:
    """
    Shadows/Highlights — from gimpoperationshadowshighlights.c (simplified).
    shadows, highlights: -100 to 100
    """
    result = pixels.astype(np.float32)
    channels = min(3, result.shape[2])
    if channels < 3:
        return pixels.copy()

    lum = 0.299 * result[:,:,0] + 0.587 * result[:,:,1] + 0.114 * result[:,:,2]
    shadow_mask = np.clip(1.0 - lum / 128.0, 0, 1)
    highlight_mask = np.clip((lum - 128.0) / 128.0, 0, 1)

    for c in range(channels):
        result[:,:,c] += shadows * shadow_mask * 2.55
        result[:,:,c] += highlights * highlight_mask * 2.55

    return np.clip(result, 0, 255).astype(np.uint8)


def compute_histogram(pixels: np.ndarray,
                      channel: HistogramChannel = HistogramChannel.VALUE) -> np.ndarray:
    """
    Histogram — from gimpdrawable-histogram.c / gimphistogram.c.
    Returns a 256-element array of counts.
    """
    if channel == HistogramChannel.VALUE:
        gray = 0.299 * pixels[:,:,0].astype(np.float32) + \
               0.587 * pixels[:,:,1].astype(np.float32) + \
               0.114 * pixels[:,:,2].astype(np.float32)
        return np.histogram(gray.flatten(), bins=256, range=(0,256))[0]
    elif channel == HistogramChannel.RED:
        c = 0
    elif channel == HistogramChannel.GREEN:
        c = 1
    elif channel == HistogramChannel.BLUE:
        c = 2
    elif channel == HistogramChannel.ALPHA:
        c = pixels.shape[2] - 1
    else:
        c = 0
    return np.histogram(pixels[:,:,c].flatten(), bins=256, range=(0,256))[0]
