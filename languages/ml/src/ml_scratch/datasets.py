"""Seeded, deterministic synthetic datasets.

Reproducibility is a first-class requirement here: every generator takes a
``seed`` and uses its *own* :class:`random.Random` instance rather than the
global RNG. That means generating a dataset never perturbs an optimizer that
also uses randomness, and two calls with the same seed return identical data on
any machine / Python build.
"""

from __future__ import annotations

import math
import random
from typing import List, Tuple

Vector = List[float]
Matrix = List[List[float]]


def make_linear_regression(
    n_samples: int = 120,
    weights: Tuple[float, ...] = (2.0, -3.0),
    bias: float = 5.0,
    noise: float = 0.5,
    x_range: Tuple[float, float] = (-5.0, 5.0),
    seed: int = 0,
) -> Tuple[Matrix, Vector]:
    """Generate ``y = X . weights + bias + gaussian_noise``.

    Returns ``(X, y)`` where ``X`` has ``len(weights)`` features per row. The
    true coefficients are returned implicitly via the arguments, so a test can
    assert that gradient descent recovers ``weights``/``bias`` within tolerance.
    """
    rng = random.Random(seed)
    n_features = len(weights)
    lo, hi = x_range
    X: Matrix = []
    y: Vector = []
    for _ in range(n_samples):
        row = [rng.uniform(lo, hi) for _ in range(n_features)]
        target = bias + sum(w * x for w, x in zip(weights, row))
        target += rng.gauss(0.0, noise)
        X.append(row)
        y.append(target)
    return X, y


def make_blobs_2class(
    n_per_class: int = 80,
    centers: Tuple[Tuple[float, float], ...] = ((-2.0, -2.0), (2.0, 2.0)),
    spread: float = 1.0,
    seed: int = 1,
) -> Tuple[Matrix, List[int]]:
    """Two Gaussian blobs labelled 0 and 1 for binary classification.

    Returns ``(X, y)`` with ``y in {0, 1}``. With the default well-separated
    centers a good classifier should reach near-perfect accuracy, which makes a
    crisp test threshold possible.
    """
    rng = random.Random(seed)
    X: Matrix = []
    y: List[int] = []
    for label, (cx, cy) in enumerate(centers):
        for _ in range(n_per_class):
            X.append([rng.gauss(cx, spread), rng.gauss(cy, spread)])
            y.append(label)
    return X, y


def make_kmeans_blobs(
    n_per_cluster: int = 50,
    centers: Tuple[Tuple[float, float], ...] = (
        (0.0, 0.0),
        (8.0, 8.0),
        (0.0, 8.0),
    ),
    spread: float = 0.6,
    seed: int = 2,
) -> Tuple[Matrix, List[int], List[List[float]]]:
    """Well-separated clusters for k-means.

    Returns ``(X, true_labels, true_centers)``. The spread is small relative to
    the inter-center distance, so Lloyd's algorithm should recover the centers
    (up to a label permutation), which a test can check directly.
    """
    rng = random.Random(seed)
    X: Matrix = []
    true_labels: List[int] = []
    for label, (cx, cy) in enumerate(centers):
        for _ in range(n_per_cluster):
            X.append([rng.gauss(cx, spread), rng.gauss(cy, spread)])
            true_labels.append(label)
    return X, true_labels, [list(c) for c in centers]


def make_xor(repeats: int = 25, noise: float = 0.0, seed: int = 3) -> Tuple[Matrix, List[int]]:
    """The classic XOR dataset: not linearly separable, the canonical MLP test.

    The four corners (0,0)->0, (0,1)->1, (1,0)->1, (1,1)->0 are repeated
    ``repeats`` times. A small Gaussian ``noise`` can be added to the inputs to
    discourage memorization; with ``noise=0`` the data is exact.
    """
    rng = random.Random(seed)
    base = [
        ([0.0, 0.0], 0),
        ([0.0, 1.0], 1),
        ([1.0, 0.0], 1),
        ([1.0, 1.0], 0),
    ]
    X: Matrix = []
    y: List[int] = []
    for _ in range(repeats):
        for point, label in base:
            if noise > 0.0:
                X.append([point[0] + rng.gauss(0.0, noise), point[1] + rng.gauss(0.0, noise)])
            else:
                X.append(list(point))
            y.append(label)
    return X, y


def standardize(X: Matrix) -> Tuple[Matrix, Vector, Vector]:
    """Z-score each feature column: (x - mean) / std.

    Returns ``(X_scaled, means, stds)`` so the same transform can be re-applied
    to held-out data. Standardizing puts every feature on a comparable scale,
    which keeps a single global learning rate sane across features. ``std`` is
    floored away from zero to avoid division by zero on constant columns.
    """
    if not X:
        return [], [], []
    n = len(X)
    dim = len(X[0])
    means = [sum(row[j] for row in X) / n for j in range(dim)]
    stds: Vector = []
    for j in range(dim):
        var = sum((row[j] - means[j]) ** 2 for row in X) / n
        stds.append(math.sqrt(var) if var > 1e-12 else 1.0)
    scaled = [[(row[j] - means[j]) / stds[j] for j in range(dim)] for row in X]
    return scaled, means, stds
