"""
Selection module — extracted from app/core/gimpselection.c,
app/core/gimpchannel-combine.c, and app/tools/gimp*selecttool.c.
Provides selection mask operations and selection tools.
"""

import math
import numpy as np
from typing import Optional, Tuple, List

from .channel import GimpChannel
from .enums import SelectionOperation
from .exceptions import SelectionError


class GimpSelection(GimpChannel):
    """
    Selection mask — extracted from app/core/gimpselection.c.
    Extends GimpChannel with selection-specific operations like
    feather, border, grow, shrink, flood fill, and marching ants boundary.
    """

    def __init__(self, width: int, height: int):
        super().__init__(width, height, "Selection", opacity=1.0)
        self._suspended = 0

    def select_all(self) -> None:
        self.pixels.fill(255)

    def select_none(self) -> None:
        self.pixels.fill(0)

    def select_invert(self) -> None:
        self.pixels = 255 - self.pixels

    def select_rectangle(self, x: int, y: int, width: int, height: int,
                         operation: SelectionOperation = SelectionOperation.REPLACE,
                         antialias: bool = True) -> None:
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.width, x + width), min(self.height, y + height)
        if x0 < x1 and y0 < y1:
            mask[y0:y1, x0:x1] = 255
        if antialias:
            mask = self._antialias_rect(mask, x, y, width, height)
        self._apply_mask(mask, operation)

    def _antialias_rect(self, mask: np.ndarray, x: int, y: int,
                        width: int, height: int) -> np.ndarray:
        result = mask.copy()
        for py in range(max(0, y), min(self.height, y + height)):
            for px in range(max(0, x), min(self.width, x + width)):
                edge = False
                if px == x or px == x + width - 1 or py == y or py == y + height - 1:
                    edge = True
                if edge:
                    result[py, px] = 192
        return result

    def select_ellipse(self, x: int, y: int, width: int, height: int,
                       operation: SelectionOperation = SelectionOperation.REPLACE,
                       antialias: bool = True) -> None:
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        cx = x + width / 2.0
        cy = y + height / 2.0
        rx = width / 2.0
        ry = height / 2.0
        if rx <= 0 or ry <= 0:
            return

        y0 = max(0, int(math.floor(cy - ry - 1)))
        y1 = min(self.height, int(math.ceil(cy + ry + 1)))
        x0 = max(0, int(math.floor(cx - rx - 1)))
        x1 = min(self.width, int(math.ceil(cx + rx + 1)))

        for py in range(y0, y1):
            for px in range(x0, x1):
                dx = (px - cx + 0.5) / rx
                dy = (py - cy + 0.5) / ry
                dist = dx * dx + dy * dy
                if dist <= 1.0:
                    if antialias and dist > 0.9:
                        val = max(0, min(255, int((1.0 - dist) * 255 / 0.1)))
                        mask[py, px] = val
                    else:
                        mask[py, px] = 255
        self._apply_mask(mask, operation)

    def select_polygon(self, points: List[Tuple[int, int]],
                       operation: SelectionOperation = SelectionOperation.REPLACE,
                       antialias: bool = True) -> None:
        if len(points) < 3:
            raise SelectionError("Polygon requires at least 3 points")
        mask = np.zeros((self.height, self.width), dtype=np.uint8)

        min_x = max(0, int(min(p[0] for p in points)) - 1)
        max_x = min(self.width, int(max(p[0] for p in points)) + 2)
        min_y = max(0, int(min(p[1] for p in points)) - 1)
        max_y = min(self.height, int(max(p[1] for p in points)) + 2)

        for py in range(min_y, max_y):
            for px in range(min_x, max_x):
                if self._point_in_polygon(px + 0.5, py + 0.5, points):
                    mask[py, px] = 255
        self._apply_mask(mask, operation)

    @staticmethod
    def _point_in_polygon(x: float, y: float,
                          polygon: List[Tuple[int, int]]) -> bool:
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def select_round_rectangle(self, x: int, y: int, width: int, height: int,
                               corner_radius: float,
                               operation: SelectionOperation = SelectionOperation.REPLACE,
                               antialias: bool = True) -> None:
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        r = min(corner_radius, width / 2, height / 2)

        for py in range(max(0, y), min(self.height, y + height)):
            for px in range(max(0, x), min(self.width, x + width)):
                dx = 0.0
                dy = 0.0
                if px < x + r and py < y + r:
                    dx = (x + r - px - 0.5)
                    dy = (y + r - py - 0.5)
                elif px >= x + width - r and py < y + r:
                    dx = (px + 0.5 - (x + width - r))
                    dy = (y + r - py - 0.5)
                elif px < x + r and py >= y + height - r:
                    dx = (x + r - px - 0.5)
                    dy = (py + 0.5 - (y + height - r))
                elif px >= x + width - r and py >= y + height - r:
                    dx = (px + 0.5 - (x + width - r))
                    dy = (py + 0.5 - (y + height - r))
                else:
                    mask[py, px] = 255
                    continue

                dist = math.sqrt(dx*dx + dy*dy)
                if dist <= r:
                    if antialias and dist > r - 1:
                        mask[py, px] = max(0, int((r - dist) * 255))
                    else:
                        mask[py, px] = 255
        self._apply_mask(mask, operation)

    def select_by_color(self, image_pixels: np.ndarray, x: int, y: int,
                        threshold: int = 15,
                        antialias: bool = True,
                        select_transparent: bool = False,
                        sample_merged: bool = False) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise SelectionError(f"Position ({x}, {y}) out of bounds")
        target = image_pixels[y, x].astype(np.float32)
        diff = np.abs(image_pixels.astype(np.float32) - target)
        channels = min(3, image_pixels.shape[2])
        max_diff = diff[:, :, :channels].max(axis=2)
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        mask[max_diff <= threshold] = 255
        if antialias:
            edge = (max_diff > threshold) & (max_diff <= threshold * 1.5)
            mask[edge] = ((threshold * 1.5 - max_diff[edge]) / (threshold * 0.5) * 255).astype(np.uint8)
        self.pixels = mask

    def select_contiguous_color(self, image_pixels: np.ndarray, x: int, y: int,
                                threshold: int = 15,
                                antialias: bool = True) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise SelectionError(f"Position ({x}, {y}) out of bounds")
        target = image_pixels[y, x].astype(np.float32)
        channels = min(3, image_pixels.shape[2])
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        visited = np.zeros((self.height, self.width), dtype=bool)
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if visited[cy, cx]:
                continue
            visited[cy, cx] = True
            diff = np.abs(image_pixels[cy, cx].astype(np.float32)[:channels] - target[:channels])
            if diff.max() <= threshold:
                mask[cy, cx] = 255
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nx, ny = cx+dx, cy+dy
                    if 0 <= nx < self.width and 0 <= ny < self.height and not visited[ny, nx]:
                        stack.append((nx, ny))
        self.pixels = mask

    def feather(self, radius: float) -> None:
        from .transform import _gaussian_blur_gray
        self.pixels = _gaussian_blur_gray(self.pixels, radius)

    def sharpen(self) -> None:
        self.pixels = np.where(self.pixels > 127, 255, 0).astype(np.uint8)

    def border(self, radius: int) -> None:
        from .transform import _dilate_gray, _erode_gray
        outer = _dilate_gray(self.pixels, radius)
        inner = _erode_gray(self.pixels, radius)
        self.pixels = np.clip(outer.astype(np.int16) - inner.astype(np.int16), 0, 255).astype(np.uint8)

    def grow(self, radius: int) -> None:
        from .transform import _dilate_gray
        self.pixels = _dilate_gray(self.pixels, radius)

    def shrink(self, radius: int) -> None:
        from .transform import _erode_gray
        self.pixels = _erode_gray(self.pixels, radius)

    def flood(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise SelectionError(f"Position ({x}, {y}) out of bounds")
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        visited = np.zeros((self.height, self.width), dtype=bool)
        if self.pixels[y, x] > 0:
            return
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if visited[cy, cx]:
                continue
            visited[cy, cx] = True
            if self.pixels[cy, cx] == 0:
                mask[cy, cx] = 255
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nx, ny = cx+dx, cy+dy
                    if 0 <= nx < self.width and 0 <= ny < self.height and not visited[ny, nx]:
                        stack.append((nx, ny))
        self.pixels = mask

    def save_to_channel(self, channel: GimpChannel) -> None:
        channel.pixels = self.pixels.copy()

    def get_bounds(self) -> Tuple[int, int, int, int]:
        return self.bounds

    def translate(self, dx: int, dy: int) -> None:
        new_pixels = np.zeros_like(self.pixels)
        src_x = max(0, -dx)
        src_y = max(0, -dy)
        dst_x = max(0, dx)
        dst_y = max(0, dy)
        copy_w = min(self.width - src_x, self.width - dst_x)
        copy_h = min(self.height - src_y, self.height - dst_y)
        if copy_w > 0 and copy_h > 0:
            new_pixels[dst_y:dst_y+copy_h, dst_x:dst_x+copy_w] = \
                self.pixels[src_y:src_y+copy_h, src_x:src_x+copy_w]
        self.pixels = new_pixels

    def _apply_mask(self, mask: np.ndarray, operation: SelectionOperation) -> None:
        if operation == SelectionOperation.REPLACE:
            self.pixels = mask
        elif operation == SelectionOperation.ADD:
            self.pixels = np.maximum(self.pixels, mask)
        elif operation == SelectionOperation.SUBTRACT:
            self.pixels = np.clip(self.pixels.astype(np.int16) - mask.astype(np.int16),
                                  0, 255).astype(np.uint8)
        elif operation == SelectionOperation.INTERSECT:
            self.pixels = np.minimum(self.pixels, mask)

    def get_boundary(self) -> List[List[Tuple[int, int]]]:
        segments = []
        h, w = self.pixels.shape
        for y in range(h):
            for x in range(w):
                if self.pixels[y, x] > 127:
                    if x == 0 or self.pixels[y, x-1] <= 127:
                        segments.append(((x, y), (x, y+1)))
                    if x == w-1 or self.pixels[y, x+1] <= 127:
                        segments.append(((x+1, y), (x+1, y+1)))
                    if y == 0 or self.pixels[y-1, x] <= 127:
                        segments.append(((x, y), (x+1, y)))
                    if y == h-1 or self.pixels[y+1, x] <= 127:
                        segments.append(((x, y+1), (x+1, y+1)))
        return self._segments_to_contours(segments)

    @staticmethod
    def _segments_to_contours(segments) -> List[List[Tuple[int, int]]]:
        if not segments:
            return []
        from collections import defaultdict
        adj = defaultdict(list)
        for (a, b) in segments:
            adj[a].append(b)
            adj[b].append(a)

        visited_edges = set()
        contours = []
        for start in adj:
            if start in visited_edges:
                continue
            contour = [start]
            current = start
            while True:
                neighbors = adj[current]
                next_pt = None
                for n in neighbors:
                    edge = (min(current, n), max(current, n))
                    if edge not in visited_edges:
                        next_pt = n
                        break
                if next_pt is None or next_pt == start:
                    break
                edge = (min(current, next_pt), max(current, next_pt))
                visited_edges.add(edge)
                contour.append(next_pt)
                current = next_pt
            if len(contour) > 2:
                contours.append(contour)
        return contours

    def suspend(self) -> None:
        self._suspended += 1

    def resume(self) -> None:
        self._suspended = max(0, self._suspended - 1)

    @property
    def is_suspended(self) -> bool:
        return self._suspended > 0
