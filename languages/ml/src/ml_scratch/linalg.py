"""Minimal linear-algebra helpers over plain Python lists.

A "vector" is a ``list[float]`` and a "matrix" is a ``list[list[float]]`` in
row-major order (each inner list is one row). These are the only data structures
the learners use, so you can ``print`` them and read them directly.

Everything here is intentionally tiny and explicit. In the numpy upgrade these
functions all collapse to a single operator (``@``, ``*``, ``.T``); seeing the
loop version first is the whole point.
"""

from __future__ import annotations

from typing import List, Sequence

Vector = List[float]
Matrix = List[List[float]]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    """Inner product of two equal-length vectors: sum_i a_i * b_i."""
    if len(a) != len(b):
        raise ValueError(f"dot: length mismatch {len(a)} != {len(b)}")
    return sum(ai * bi for ai, bi in zip(a, b))


def vec_add(a: Sequence[float], b: Sequence[float]) -> Vector:
    """Element-wise vector addition."""
    if len(a) != len(b):
        raise ValueError(f"vec_add: length mismatch {len(a)} != {len(b)}")
    return [ai + bi for ai, bi in zip(a, b)]


def vec_sub(a: Sequence[float], b: Sequence[float]) -> Vector:
    """Element-wise vector subtraction (a - b)."""
    if len(a) != len(b):
        raise ValueError(f"vec_sub: length mismatch {len(a)} != {len(b)}")
    return [ai - bi for ai, bi in zip(a, b)]


def scalar_mul(s: float, a: Sequence[float]) -> Vector:
    """Multiply every element of ``a`` by scalar ``s``."""
    return [s * ai for ai in a]


def matvec(m: Matrix, v: Sequence[float]) -> Vector:
    """Matrix-vector product: result_i = dot(row_i, v)."""
    return [dot(row, v) for row in m]


def transpose(m: Matrix) -> Matrix:
    """Transpose a matrix. ``zip(*m)`` does the work; we re-wrap as lists."""
    if not m:
        return []
    return [list(col) for col in zip(*m)]


def squared_norm(a: Sequence[float]) -> float:
    """Sum of squares of the vector's components (||a||^2)."""
    return sum(ai * ai for ai in a)


def euclidean_sq(a: Sequence[float], b: Sequence[float]) -> float:
    """Squared Euclidean distance between two points.

    We deliberately avoid the square root: k-means only ever *compares*
    distances and minimizes a sum of squared distances, so the monotone
    ``sqrt`` is wasted work (and a needless source of float error).
    """
    if len(a) != len(b):
        raise ValueError(f"euclidean_sq: length mismatch {len(a)} != {len(b)}")
    return sum((ai - bi) ** 2 for ai, bi in zip(a, b))


def mean_rows(rows: Matrix) -> Vector:
    """Column-wise mean of a list of equal-length rows (the centroid)."""
    if not rows:
        raise ValueError("mean_rows: empty input has no mean")
    n = len(rows)
    dim = len(rows[0])
    acc = [0.0] * dim
    for r in rows:
        for j in range(dim):
            acc[j] += r[j]
    return [s / n for s in acc]
