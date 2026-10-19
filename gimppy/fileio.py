"""
File I/O module — extracted from app/file/ and app/xcf/:
  file-open.c, file-save.c, xcf-load.c, xcf-save.c,
  and plug-ins/file-jpeg/, file-png/, file-psd/, etc.
Provides load/save for multiple image formats.
"""

import struct
import numpy as np
from typing import Optional, Tuple
from pathlib import Path

from .enums import ImageType, Precision
from .exceptions import FileIOError


def load_image(filepath: str) -> dict:
    """
    Load an image file — from file-open.c.
    Returns a dict with image data suitable for constructing a GimpImage.
    Supports XCF, PNG, JPEG, BMP, TIFF, PSD (via Pillow fallback).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileIOError(f"File not found: {filepath}")

    ext = path.suffix.lower()
    if ext == '.xcf':
        return _load_xcf(filepath)
    else:
        return _load_via_pillow(filepath)


def save_image(filepath: str, image_data: dict, **kwargs) -> None:
    """
    Save an image file — from file-save.c.
    image_data: dict with 'layers', 'width', 'height', 'image_type'
    """
    path = Path(filepath)
    ext = path.suffix.lower()
    if ext == '.xcf':
        _save_xcf(filepath, image_data)
    else:
        _save_via_pillow(filepath, image_data, **kwargs)


def _load_xcf(filepath: str) -> dict:
    """
    Load XCF (GIMP native format) — from xcf-load.c.
    Simplified XCF reader for basic image data.
    """
    with open(filepath, 'rb') as f:
        magic = f.read(9)
        if magic[:8] != b'gimp xcf':
            raise FileIOError("Not a valid XCF file")

        version_byte = magic[8:9]
        if version_byte in (b'v', b'0'):
            version = 0
        elif version_byte == b'b' or magic[8:10] == b'fi':
            version = 1
        else:
            version = 0

        width = struct.unpack('>I', f.read(4))[0]
        height = struct.unpack('>I', f.read(4))[0]
        color_mode = struct.unpack('>I', f.read(4))[0]

        type_map = {0: ImageType.RGB, 1: ImageType.GRAY, 2: ImageType.INDEXED}
        image_type = type_map.get(color_mode, ImageType.RGB)

        precision = Precision.U8

        props = _read_xcf_properties(f)

        layer_offsets = []
        while True:
            offset = struct.unpack('>I', f.read(4))[0]
            if offset == 0:
                break
            layer_offsets.append(offset)

        channel_offsets = []
        while True:
            offset = struct.unpack('>I', f.read(4))[0]
            if offset == 0:
                break
            channel_offsets.append(offset)

        return {
            "width": width,
            "height": height,
            "image_type": image_type,
            "precision": precision,
            "layers": [],
            "channels": [],
            "source_format": "xcf",
        }


def _read_xcf_properties(f) -> dict:
    props = {}
    while True:
        data = f.read(8)
        if len(data) < 8:
            break
        prop_type, prop_size = struct.unpack('>II', data)
        if prop_type == 0:
            break
        if prop_size > 0:
            f.read(prop_size)
    return props


def _save_xcf(filepath: str, image_data: dict) -> None:
    """
    Save XCF — from xcf-save.c.
    Simplified XCF writer.
    """
    with open(filepath, 'wb') as f:
        f.write(b'gimp xcf v0.0')
        f.write(struct.pack('>I', image_data.get("width", 1)))
        f.write(struct.pack('>I', image_data.get("height", 1)))
        type_map = {ImageType.RGB: 0, ImageType.GRAY: 1, ImageType.INDEXED: 2}
        f.write(struct.pack('>I', type_map.get(image_data.get("image_type", ImageType.RGB), 0)))
        f.write(struct.pack('>I', 0))
        f.write(struct.pack('>I', 0))
        f.write(struct.pack('>I', 0))


def _load_via_pillow(filepath: str) -> dict:
    """Load image via Pillow as fallback."""
    try:
        from PIL import Image
    except ImportError:
        raise FileIOError(
            f"Cannot load {filepath}: Pillow not installed. "
            "Install with: pip install Pillow"
        )

    img = Image.open(filepath)
    width, height = img.size

    if img.mode == 'RGBA':
        image_type = ImageType.RGB
        pixels = np.array(img, dtype=np.uint8)
        has_alpha = True
    elif img.mode == 'RGB':
        image_type = ImageType.RGB
        pixels = np.array(img, dtype=np.uint8)
        has_alpha = False
    elif img.mode == 'L':
        image_type = ImageType.GRAY
        pixels = np.array(img, dtype=np.uint8)[:, :, np.newaxis]
        has_alpha = False
    elif img.mode == 'LA':
        image_type = ImageType.GRAY
        pixels = np.array(img, dtype=np.uint8)
        has_alpha = True
    elif img.mode == 'P':
        img = img.convert('RGBA')
        image_type = ImageType.RGB
        pixels = np.array(img, dtype=np.uint8)
        has_alpha = True
    else:
        img = img.convert('RGBA')
        image_type = ImageType.RGB
        pixels = np.array(img, dtype=np.uint8)
        has_alpha = True

    return {
        "width": width,
        "height": height,
        "image_type": image_type,
        "precision": Precision.U8,
        "layers": [{"pixels": pixels, "name": "Background", "has_alpha": has_alpha}],
        "channels": [],
        "source_format": "pillow",
    }


def _save_via_pillow(filepath: str, image_data: dict, **kwargs) -> None:
    """Save image via Pillow as fallback."""
    try:
        from PIL import Image
    except ImportError:
        raise FileIOError(
            f"Cannot save {filepath}: Pillow not installed. "
            "Install with: pip install Pillow"
        )

    layers = image_data.get("layers", [])
    if not layers:
        raise FileIOError("No layers to save")

    pixels = layers[0].get("pixels")
    if pixels is None:
        raise FileIOError("Layer has no pixel data")

    if pixels.ndim == 3:
        channels = pixels.shape[2]
        if channels == 4:
            mode = 'RGBA'
        elif channels == 3:
            mode = 'RGB'
        elif channels == 1:
            mode = 'L'
            pixels = pixels[:, :, 0]
        else:
            mode = 'RGB'
            pixels = pixels[:, :, :3]
    elif pixels.ndim == 2:
        mode = 'L'
    else:
        raise FileIOError(f"Unexpected pixel dimensions: {pixels.ndim}")

    img = Image.fromarray(pixels, mode=mode)

    ext = Path(filepath).suffix.lower()
    save_kwargs = {}
    if ext in ('.jpg', '.jpeg'):
        if mode == 'RGBA':
            img = img.convert('RGB')
        save_kwargs['quality'] = kwargs.get('quality', 95)
    elif ext == '.png':
        save_kwargs['compress_level'] = kwargs.get('compress_level', 6)
    elif ext == '.bmp':
        if mode == 'RGBA':
            img = img.convert('RGB')
    elif ext == '.webp':
        save_kwargs['quality'] = kwargs.get('quality', 95)

    img.save(filepath, **save_kwargs)


def get_supported_formats() -> list:
    """Return list of supported file extensions."""
    formats = ['.xcf', '.bmp', '.ico']
    try:
        from PIL import Image
        formats.extend([
            '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.webp',
            '.gif', '.psd', '.ppm', '.pgm', '.pbm',
        ])
    except ImportError:
        pass
    return formats
