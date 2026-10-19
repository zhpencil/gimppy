"""
Path / Vector module — extracted from app/path/:
  gimppath.c, gimpstroke.c, gimpbezierstroke.c, gimpanchor.c.
Provides vector path and Bezier curve operations.
"""

import math
import numpy as np
from typing import List, Tuple, Optional

from .exceptions import PathError


class Anchor:
    """
    Path anchor point — from gimpanchor.c.
    A control point on a Bezier stroke.
    """

    def __init__(self, x: float, y: float,
                 type_: str = "smooth"):
        self.x = x
        self.y = y
        self.type = type_  # "smooth", "corner", "symmetric"

    def __repr__(self):
        return f"Anchor({self.x:.1f}, {self.y:.1f}, {self.type})"


class Stroke:
    """
    Bezier stroke — from gimpbezierstroke.c.
    A sequence of anchor points forming a Bezier curve.
    Supports moveto, lineto, conicto, cubicto operations.
    """

    def __init__(self, closed: bool = False):
        self.anchors: List[Anchor] = []
        self.closed = closed
        self._coords_cache = None

    def add_anchor(self, x: float, y: float,
                   type_: str = "smooth") -> Anchor:
        anchor = Anchor(x, y, type_)
        self.anchors.append(anchor)
        self._coords_cache = None
        return anchor

    def moveto(self, x: float, y: float) -> Anchor:
        return self.add_anchor(x, y, "corner")

    def lineto(self, x: float, y: float) -> Anchor:
        return self.add_anchor(x, y, "corner")

    def conicto(self, cx: float, cy: float, x: float, y: float) -> None:
        self.add_anchor(cx, cy, "smooth")
        self.add_anchor(x, y, "corner")

    def cubicto(self, c1x: float, c1y: float,
                c2x: float, c2y: float,
                x: float, y: float) -> None:
        self.add_anchor(c1x, c1y, "smooth")
        self.add_anchor(c2x, c2y, "smooth")
        self.add_anchor(x, y, "corner")

    def close(self) -> None:
        self.closed = True

    def reverse(self) -> None:
        self.anchors.reverse()
        self._coords_cache = None

    def translate(self, dx: float, dy: float) -> None:
        for a in self.anchors:
            a.x += dx
            a.y += dy
        self._coords_cache = None

    def scale(self, sx: float, sy: float) -> None:
        for a in self.anchors:
            a.x *= sx
            a.y *= sy
        self._coords_cache = None

    def rotate(self, angle_rad: float) -> None:
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        for a in self.anchors:
            nx = a.x * c - a.y * s
            ny = a.x * s + a.y * c
            a.x, a.y = nx, ny
        self._coords_cache = None

    def flip(self, axis: str = "horizontal", center: float = 0.0) -> None:
        for a in self.anchors:
            if axis == "horizontal":
                a.x = 2 * center - a.x
            else:
                a.y = 2 * center - a.y
        self._coords_cache = None

    def get_length(self, precision: int = 100) -> float:
        points = self.interpolate(precision)
        length = 0.0
        for i in range(1, len(points)):
            dx = points[i][0] - points[i-1][0]
            dy = points[i][1] - points[i-1][1]
            length += math.sqrt(dx*dx + dy*dy)
        return length

    def get_point_at_distance(self, dist: float,
                              precision: int = 100) -> Optional[Tuple[float, float]]:
        points = self.interpolate(precision)
        if not points:
            return None
        accumulated = 0.0
        for i in range(1, len(points)):
            dx = points[i][0] - points[i-1][0]
            dy = points[i][1] - points[i-1][1]
            seg_len = math.sqrt(dx*dx + dy*dy)
            if accumulated + seg_len >= dist:
                t = (dist - accumulated) / max(seg_len, 1e-10)
                return (points[i-1][0] + dx * t,
                        points[i-1][1] + dy * t)
            accumulated += seg_len
        return points[-1]

    def interpolate(self, precision: int = 100) -> List[Tuple[float, float]]:
        if self._coords_cache is not None:
            return self._coords_cache
        if len(self.anchors) < 2:
            if self.anchors:
                self._coords_cache = [(self.anchors[0].x, self.anchors[0].y)]
            else:
                self._coords_cache = []
            return self._coords_cache

        points = []
        n = len(self.anchors)
        i = 0
        while i < n:
            if i + 2 < n and self.anchors[i+1].type == "smooth":
                p0 = (self.anchors[i].x, self.anchors[i].y)
                p1 = (self.anchors[i+1].x, self.anchors[i+1].y)
                p2 = (self.anchors[i+2].x, self.anchors[i+2].y)
                for t_idx in range(precision):
                    t = t_idx / precision
                    x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
                    y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
                    points.append((x, y))
                points.append(p2)
                i += 3
            elif i + 3 < n and self.anchors[i+1].type == "smooth" and self.anchors[i+2].type == "smooth":
                p0 = (self.anchors[i].x, self.anchors[i].y)
                p1 = (self.anchors[i+1].x, self.anchors[i+1].y)
                p2 = (self.anchors[i+2].x, self.anchors[i+2].y)
                p3 = (self.anchors[i+3].x, self.anchors[i+3].y)
                for t_idx in range(precision):
                    t = t_idx / precision
                    x = (1-t)**3*p0[0] + 3*(1-t)**2*t*p1[0] + 3*(1-t)*t**2*p2[0] + t**3*p3[0]
                    y = (1-t)**3*p0[1] + 3*(1-t)**2*t*p1[1] + 3*(1-t)*t**2*p2[1] + t**3*p3[1]
                    points.append((x, y))
                points.append(p3)
                i += 4
            else:
                p0 = (self.anchors[i].x, self.anchors[i].y)
                if i + 1 < n:
                    p1 = (self.anchors[i+1].x, self.anchors[i+1].y)
                    for t_idx in range(precision):
                        t = t_idx / precision
                        points.append((p0[0] + (p1[0]-p0[0])*t,
                                       p0[1] + (p1[1]-p0[1])*t))
                    points.append(p1)
                    i += 2
                else:
                    points.append(p0)
                    i += 1

        if self.closed and points:
            points.append(points[0])
        self._coords_cache = points
        return points

    def get_bounds(self) -> Tuple[float, float, float, float]:
        points = self.interpolate()
        if not points:
            return (0, 0, 0, 0)
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (min(xs), min(ys), max(xs), max(ys))

    @staticmethod
    def from_points(points: List[Tuple[float, float]],
                    closed: bool = False) -> 'Stroke':
        stroke = Stroke(closed=closed)
        for i, (x, y) in enumerate(points):
            stroke.add_anchor(x, y, "corner" if i == 0 else "smooth")
        return stroke

    @staticmethod
    def ellipse(cx: float, cy: float, rx: float, ry: float) -> 'Stroke':
        stroke = Stroke(closed=True)
        kappa = 0.5522847498
        stroke.moveto(cx + rx, cy)
        stroke.cubicto(cx + rx, cy + ry * kappa,
                       cx + rx * kappa, cy + ry,
                       cx, cy + ry)
        stroke.cubicto(cx - rx * kappa, cy + ry,
                       cx - rx, cy + ry * kappa,
                       cx - rx, cy)
        stroke.cubicto(cx - rx, cy - ry * kappa,
                       cx - rx * kappa, cy - ry,
                       cx, cy - ry)
        stroke.cubicto(cx + rx * kappa, cy - ry,
                       cx + rx, cy - ry * kappa,
                       cx + rx, cy)
        return stroke


class GimpPath:
    """
    Path object — from gimppath.c.
    A collection of strokes forming a complete vector path.
    """

    def __init__(self, name: str = "Path"):
        self.name = name
        self.strokes: List[Stroke] = []
        self.visible = True
        self.locked = False
        self._tags: list = []
        self._parasites = {}

    def add_stroke(self, stroke: Stroke) -> None:
        self.strokes.append(stroke)

    def remove_stroke(self, index: int) -> None:
        if 0 <= index < len(self.strokes):
            self.strokes.pop(index)

    def get_stroke(self, index: int) -> Optional[Stroke]:
        if 0 <= index < len(self.strokes):
            return self.strokes[index]
        return None

    @property
    def stroke_count(self) -> int:
        return len(self.strokes)

    def get_bounds(self) -> Tuple[float, float, float, float]:
        if not self.strokes:
            return (0, 0, 0, 0)
        all_bounds = [s.get_bounds() for s in self.strokes]
        return (
            min(b[0] for b in all_bounds),
            min(b[1] for b in all_bounds),
            max(b[2] for b in all_bounds),
            max(b[3] for b in all_bounds),
        )

    def translate(self, dx: float, dy: float) -> None:
        for s in self.strokes:
            s.translate(dx, dy)

    def scale(self, sx: float, sy: float) -> None:
        for s in self.strokes:
            s.scale(sx, sy)

    def rotate(self, angle_rad: float) -> None:
        for s in self.strokes:
            s.rotate(angle_rad)

    def copy(self) -> 'GimpPath':
        new_path = GimpPath(self.name)
        new_path.visible = self.visible
        new_path.locked = self.locked
        for s in self.strokes:
            new_stroke = Stroke(s.closed)
            for a in s.anchors:
                new_stroke.add_anchor(a.x, a.y, a.type)
            new_path.strokes.append(new_stroke)
        return new_path

    def to_selection_mask(self, width: int, height: int) -> np.ndarray:
        mask = np.zeros((height, width), dtype=np.uint8)
        for stroke in self.strokes:
            points = stroke.interpolate()
            for i in range(len(points) - 1):
                x0, y0 = int(points[i][0]), int(points[i][1])
                x1, y1 = int(points[i+1][0]), int(points[i+1][1])
                _draw_line(mask, x0, y0, x1, y1, 255)
        return mask

    def to_svg(self) -> str:
        parts = [f'<path d="']
        for stroke in self.strokes:
            if not stroke.anchors:
                continue
            parts.append(f'M {stroke.anchors[0].x:.2f} {stroke.anchors[0].y:.2f} ')
            i = 1
            while i < len(stroke.anchors):
                if i + 2 < len(stroke.anchors) and stroke.anchors[i].type == "smooth":
                    parts.append(f'Q {stroke.anchors[i].x:.2f} {stroke.anchors[i].y:.2f} '
                                 f'{stroke.anchors[i+1].x:.2f} {stroke.anchors[i+1].y:.2f} ')
                    i += 3
                elif i + 3 < len(stroke.anchors):
                    parts.append(f'C {stroke.anchors[i].x:.2f} {stroke.anchors[i].y:.2f} '
                                 f'{stroke.anchors[i+1].x:.2f} {stroke.anchors[i+1].y:.2f} '
                                 f'{stroke.anchors[i+2].x:.2f} {stroke.anchors[i+2].y:.2f} ')
                    i += 4
                else:
                    parts.append(f'L {stroke.anchors[i].x:.2f} {stroke.anchors[i].y:.2f} ')
                    i += 1
            if stroke.closed:
                parts.append('Z ')
        parts.append('"/>')
        return ''.join(parts)


def _draw_line(img: np.ndarray, x0: int, y0: int, x1: int, y1: int,
               value: int) -> None:
    h, w = img.shape[:2]
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            img[y0, x0] = value
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
