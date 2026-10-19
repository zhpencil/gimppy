"""
Text module — extracted from app/text/:
  gimptext.c, gimptextlayer.c, gimptextlayout.c.
Provides text layer creation and manipulation.
"""

import numpy as np
from typing import Tuple, Optional

from .enums import TextJustification, TextDirection
from .exceptions import TextError


class GimpText:
    """
    Text object — from gimptext.c.
    Holds text content, font, size, color, and layout properties.
    """

    def __init__(self, text: str = "", font: str = "Sans-serif",
                 size: float = 12.0, color: Tuple[int, int, int] = (0, 0, 0)):
        self.text = text
        self.markup: Optional[str] = None
        self.font = font
        self.size = size
        self.color = color
        self.antialias = True
        self.hint_style = "slight"
        self.kerning = True
        self.language = "en"
        self.direction = TextDirection.LTR
        self.justification = TextJustification.LEFT
        self.indent = 0.0
        self.line_spacing = 0.0
        self.letter_spacing = 0.0
        self.outline = False
        self.outline_width = 1.0
        self.outline_color = (0, 0, 0)
        self.outline_antialias = True
        self._dynamic = True

    def set_text(self, text: str) -> None:
        self.text = text
        self.markup = None
        self._dynamic = True

    def set_markup(self, markup: str) -> None:
        self.markup = markup
        self._dynamic = True

    def get_display_text(self) -> str:
        if self.markup:
            import re
            return re.sub(r'<[^>]+>', '', self.markup)
        return self.text


def _load_font(font_name: str, font_size: int):
    """Try to load a TrueType font, fall back to Pillow default."""
    try:
        from PIL import ImageFont
    except ImportError:
        return None

    import os, sys

    candidates = []

    font_map = {
        "Sans-serif": ["arial.ttf", "calibri.ttf", "segoeui.ttf", "helvetica.ttf"],
        "Serif": ["times.ttf", "timesnewroman.ttf", "georgia.ttf"],
        "Monospace": ["consola.ttf", "cour.ttf", "courier.ttf", "liberationmono-regular.ttf"],
    }

    lower = font_name.lower()
    for key, files in font_map.items():
        if key.lower() in lower or lower in key.lower():
            candidates.extend(files)
            break

    if not candidates:
        candidates.append(font_name)
        if not font_name.endswith((".ttf", ".otf")):
            candidates.extend(["arial.ttf", "calibri.ttf", "segoeui.ttf"])

    search_dirs = []
    if sys.platform == "win32":
        search_dirs.append(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    elif sys.platform == "darwin":
        search_dirs.extend(["/Library/Fonts", "/System/Library/Fonts",
                            os.path.expanduser("~/Library/Fonts")])
    else:
        search_dirs.extend(["/usr/share/fonts", "/usr/local/share/fonts",
                            os.path.expanduser("~/.fonts"),
                            os.path.expanduser("~/.local/share/fonts")])

    for d in search_dirs:
        for name in candidates:
            path = os.path.join(d, name)
            if os.path.isfile(path):
                try:
                    return ImageFont.truetype(path, font_size)
                except (IOError, OSError):
                    continue

    for name in candidates:
        if os.path.isfile(name):
            try:
                return ImageFont.truetype(name, font_size)
            except (IOError, OSError):
                continue

    try:
        return ImageFont.load_default(size=font_size)
    except TypeError:
        return ImageFont.load_default()


class GimpTextLayer:
    """
    Text layer — from gimptextlayer.c.
    A layer that renders text content. Can be dynamic (editable)
    or rasterized (converted to pixels).
    """

    def __init__(self, text_obj: GimpText, name: str = "Text"):
        self.text_obj = text_obj
        self.name = name
        self.visible = True
        self.opacity = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self._rasterized = False
        self._dynamic = True
        self._pixels: Optional[np.ndarray] = None
        self._width = 0
        self._height = 0
        self._layout()

    def _layout(self) -> None:
        text = self.text_obj.get_display_text()
        if not text:
            self._width = 1
            self._height = 1
            self._pixels = np.zeros((1, 1, 4), dtype=np.uint8)
            return

        font_size = max(1, int(self.text_obj.size))

        try:
            self._layout_pillow(text, font_size)
        except ImportError:
            self._layout_fallback(text, font_size)

    def _layout_pillow(self, text: str, font_size: int) -> None:
        from PIL import Image, ImageDraw

        font = _load_font(self.text_obj.font, font_size)

        lines = text.split('\n')

        tmp_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp_img)

        line_metrics = []
        max_width = 0
        for line in lines:
            if not line:
                bbox = (0, 0, 0, font_size)
            else:
                bbox = tmp_draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            line_metrics.append((bbox, w, h))
            max_width = max(max_width, w)

        line_height = int(font_size * 1.3)
        total_height = line_height * len(lines)
        padding = max(2, font_size // 4)

        self._width = max(1, max_width + padding * 2)
        self._height = max(1, total_height + padding * 2)

        img = Image.new("RGBA", (self._width, self._height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        r, g, b = self.text_obj.color
        fill_color = (r, g, b, 255)

        for line_idx, line in enumerate(lines):
            if not line:
                continue
            y = padding + line_idx * line_height
            bbox, w, h = line_metrics[line_idx]

            if self.text_obj.justification == TextJustification.CENTER:
                x = padding + (max_width - w) // 2
            elif self.text_obj.justification == TextJustification.RIGHT:
                x = padding + (max_width - w)
            else:
                x = padding

            y_offset = -bbox[1]
            draw.text((x, y + y_offset), line, font=font, fill=fill_color)

        self._pixels = np.array(img, dtype=np.uint8)

    def _layout_fallback(self, text: str, font_size: int) -> None:
        char_width = max(1, int(font_size * 0.6))
        line_height = max(1, int(font_size * 1.2))

        lines = text.split('\n')
        max_line_len = max(len(line) for line in lines) if lines else 0
        self._width = max(1, max_line_len * char_width)
        self._height = max(1, len(lines) * line_height)

        self._pixels = np.zeros((self._height, self._width, 4), dtype=np.uint8)

        r, g, b = self.text_obj.color
        for line_idx, line in enumerate(lines):
            y_start = line_idx * line_height
            y_end = min(y_start + font_size, self._height)
            for char_idx, ch in enumerate(line):
                if ch == ' ':
                    continue
                x_start = char_idx * char_width
                x_end = min(x_start + char_width - 1, self._width)
                if x_end <= x_start:
                    continue
                self._pixels[y_start:y_end, x_start:x_end, 0] = r
                self._pixels[y_start:y_end, x_start:x_end, 1] = g
                self._pixels[y_start:y_end, x_start:x_end, 2] = b
                self._pixels[y_start:y_end, x_start:x_end, 3] = 255

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def pixels(self) -> np.ndarray:
        return self._pixels

    @property
    def is_dynamic(self) -> bool:
        return self._dynamic and not self._rasterized

    def resize(self, new_width: int, new_height: int) -> None:
        if self._rasterized:
            from .transform import _scale_array
            self._pixels = _scale_array(self._pixels, new_width, new_height, "linear")
        else:
            new_pixels = np.zeros((new_height, new_width, 4), dtype=np.uint8)
            copy_h = min(self._height, new_height)
            copy_w = min(self._width, new_width)
            new_pixels[:copy_h, :copy_w] = self._pixels[:copy_h, :copy_w]
            self._pixels = new_pixels
        self._width = new_width
        self._height = new_height

    def rasterize(self) -> None:
        self._rasterized = True
        self._dynamic = False

    def get_layout_offsets(self) -> Tuple[int, int]:
        return (self.offset_x, self.offset_y)

    def set_text(self, text: str) -> None:
        self.text_obj.set_text(text)
        if not self._rasterized:
            self._layout()

    def set_markup(self, markup: str) -> None:
        self.text_obj.set_markup(markup)
        if not self._rasterized:
            self._layout()

    def copy(self) -> 'GimpTextLayer':
        new_text = GimpText(
            text=self.text_obj.text,
            font=self.text_obj.font,
            size=self.text_obj.size,
            color=self.text_obj.color,
        )
        new_text.markup = self.text_obj.markup
        new_text.antialias = self.text_obj.antialias
        new_text.direction = self.text_obj.direction
        new_text.justification = self.text_obj.justification
        new_layer = GimpTextLayer(new_text, self.name)
        new_layer.visible = self.visible
        new_layer.opacity = self.opacity
        new_layer.offset_x = self.offset_x
        new_layer.offset_y = self.offset_y
        return new_layer
