"""
Math utilities extracted from GIMP's libgimpmath.
Provides matrix and vector operations for geometric transforms.
"""

import math
from typing import List, Tuple


class Matrix3:
    """
    3x3 affine transformation matrix, extracted from libgimpmath/gimpmatrix.c.
    Stored as a flat list of 9 floats in row-major order:
        [a00, a01, a02,
         a10, a11, a12,
         a20, a21, a22]
    """

    def __init__(self, values: List[float] = None):
        if values is None:
            self.m = [1, 0, 0, 0, 1, 0, 0, 0, 1]
        else:
            if len(values) != 9:
                raise ValueError("Matrix3 requires exactly 9 values")
            self.m = list(values)

    def __getitem__(self, idx):
        return self.m[idx]

    def __mul__(self, other: 'Matrix3') -> 'Matrix3':
        a = self.m
        b = other.m
        return Matrix3([
            a[0]*b[0] + a[1]*b[3] + a[2]*b[6],
            a[0]*b[1] + a[1]*b[4] + a[2]*b[7],
            a[0]*b[2] + a[1]*b[5] + a[2]*b[8],
            a[3]*b[0] + a[4]*b[3] + a[5]*b[6],
            a[3]*b[1] + a[4]*b[4] + a[5]*b[7],
            a[3]*b[2] + a[4]*b[5] + a[5]*b[8],
            a[6]*b[0] + a[7]*b[3] + a[8]*b[6],
            a[6]*b[1] + a[7]*b[4] + a[8]*b[7],
            a[6]*b[2] + a[7]*b[5] + a[8]*b[8],
        ])

    def determinant(self) -> float:
        m = self.m
        return (m[0] * (m[4]*m[8] - m[5]*m[7]) -
                m[1] * (m[3]*m[8] - m[5]*m[6]) +
                m[2] * (m[3]*m[7] - m[4]*m[6]))

    def inverse(self) -> 'Matrix3':
        det = self.determinant()
        if abs(det) < 1e-12:
            raise ValueError("Matrix is singular, cannot invert")
        m = self.m
        inv_det = 1.0 / det
        return Matrix3([
            (m[4]*m[8] - m[5]*m[7]) * inv_det,
            (m[2]*m[7] - m[1]*m[8]) * inv_det,
            (m[1]*m[5] - m[2]*m[4]) * inv_det,
            (m[5]*m[6] - m[3]*m[8]) * inv_det,
            (m[0]*m[8] - m[2]*m[6]) * inv_det,
            (m[2]*m[3] - m[0]*m[5]) * inv_det,
            (m[3]*m[7] - m[4]*m[6]) * inv_det,
            (m[1]*m[6] - m[0]*m[7]) * inv_det,
            (m[0]*m[4] - m[1]*m[3]) * inv_det,
        ])

    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        m = self.m
        nx = m[0]*x + m[1]*y + m[2]
        ny = m[3]*x + m[4]*y + m[5]
        return (nx, ny)

    @staticmethod
    def identity() -> 'Matrix3':
        return Matrix3()

    @staticmethod
    def translate(tx: float, ty: float) -> 'Matrix3':
        return Matrix3([1, 0, tx, 0, 1, ty, 0, 0, 1])

    @staticmethod
    def scale(sx: float, sy: float) -> 'Matrix3':
        return Matrix3([sx, 0, 0, 0, sy, 0, 0, 0, 1])

    @staticmethod
    def rotate(angle_rad: float) -> 'Matrix3':
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        return Matrix3([c, -s, 0, s, c, 0, 0, 0, 1])

    @staticmethod
    def shear(sx: float, sy: float) -> 'Matrix3':
        return Matrix3([1, sx, 0, sy, 1, 0, 0, 0, 1])

    @staticmethod
    def perspective(x0, y0, x1, y1, x2, y2, x3, y3,
                    dest_x0, dest_y0, dest_x1, dest_y1,
                    dest_x2, dest_y2, dest_x3, dest_y3) -> 'Matrix3':
        denom = ((x0 - x2) * (y1 - y2) - (x1 - x2) * (y0 - y2))
        if abs(denom) < 1e-12:
            raise ValueError("Degenerate perspective transform")

        def _map_quad(x0, y0, x1, y1, x2, y2, x3, y3):
            d = ((x0 - x2) * (y1 - y2) - (x1 - x2) * (y0 - y2))
            if abs(d) < 1e-12:
                return (0, 0, 0, 0, 0, 0, 0, 0)
            a1 = x1 - x0
            a2 = x3 - x0
            a3 = x0 - x1 + x2 - x3
            b1 = y1 - y0
            b2 = y3 - y0
            b3 = y0 - y1 + y2 - y3
            c1 = x2 - x0
            c2 = x3 - x0
            c3 = x0 - x1 + x2 - x3
            d1 = y2 - y0
            d2 = y3 - y0
            d3 = y0 - y1 + y2 - y3

            g = (a3 * d2 - a2 * d3) / (b3 * d2 - b2 * d3) if abs(b3*d2 - b2*d3) > 1e-12 else 0
            h = (b3 * c2 - b2 * c3) / (b3 * d2 - b2 * d3) if abs(b3*d2 - b2*d3) > 1e-12 else 0
            a = x1 - x0 + g * x1
            b = x3 - x0 + h * x3
            c = x0
            d = y1 - y0 + g * y1
            e = y3 - y0 + h * y3
            f = y0
            return (a, b, c, d, e, f, g, h)

        src = _map_quad(x0, y0, x1, y1, x2, y2, x3, y3)
        dst = _map_quad(dest_x0, dest_y0, dest_x1, dest_y1, dest_x2, dest_y2, dest_x3, dest_y3)

        sa, sb, sc, sd, se, sf, sg, sh = src
        da, db, dc, dd, de, df, dg, dh = dst

        if abs(dg) < 1e-12 and abs(dh) < 1e-12:
            return Matrix3([da, db, dc, dd, de, df, 0, 0, 1])

        return Matrix3([da, db, dc, dd, de, df, dg, dh, 1])


class Vector2:
    """2D vector from libgimpmath/gimpvector.h."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self) -> 'Vector2':
        l = self.length()
        if l < 1e-12:
            return Vector2(0, 0)
        return Vector2(self.x / l, self.y / l)

    def dot(self, other: 'Vector2') -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: 'Vector2') -> float:
        return self.x * other.y - self.y * other.x

    def __add__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x * scalar, self.y * scalar)

    def distance(self, other: 'Vector2') -> float:
        return (self - other).length()

    def __repr__(self):
        return f"Vector2({self.x}, {self.y})"


class Vector3:
    """3D vector from libgimpmath/gimpvector.h."""

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z

    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'Vector3':
        l = self.length()
        if l < 1e-12:
            return Vector3(0, 0, 0)
        return Vector3(self.x/l, self.y/l, self.z/l)

    def dot(self, other: 'Vector3') -> float:
        return self.x*other.x + self.y*other.y + self.z*other.z

    def cross(self, other: 'Vector3') -> 'Vector3':
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x+other.x, self.y+other.y, self.z+other.z)

    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x-other.x, self.y-other.y, self.z-other.z)

    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x*scalar, self.y*scalar, self.z*scalar)

    def distance(self, other: 'Vector3') -> float:
        return (self - other).length()

    def __repr__(self):
        return f"Vector3({self.x}, {self.y}, {self.z})"
