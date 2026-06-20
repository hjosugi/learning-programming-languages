"""Evaluation metrics and a deterministic train/test split.

All metrics work on plain Python sequences and return plain ``float``/``int``.
They are deliberately separate from the learners so the same metric can score
any model's predictions.
"""

from __future__ import annotations

import random
from typing import List, Sequence, Tuple

Vector = List[float]
Matrix = List[List[float]]


def mean_squared_error(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """MSE = mean over samples of (y_true - y_pred)^2."""
    if len(y_true) != len(y_pred):
        raise ValueError("mean_squared_error: length mismatch")
    if not y_true:
        raise ValueError("mean_squared_error: empty input")
    return sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / len(y_true)


def r2_score(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Coefficient of determination R^2 = 1 - SS_res / SS_tot.

    1.0 is a perfect fit; 0.0 means "no better than predicting the mean".
    """
    if len(y_true) != len(y_pred):
        raise ValueError("r2_score: length mismatch")
    mean = sum(y_true) / len(y_true)
    ss_tot = sum((t - mean) ** 2 for t in y_true)
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    if ss_tot == 0.0:
        # All targets identical: define R^2 as 1.0 iff residuals are also zero.
        return 1.0 if ss_res == 0.0 else 0.0
    return 1.0 - ss_res / ss_tot


def accuracy(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    """Fraction of exactly-correct labels."""
    if len(y_true) != len(y_pred):
        raise ValueError("accuracy: length mismatch")
    if not y_true:
        raise ValueError("accuracy: empty input")
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return correct / len(y_true)


def confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int], n_classes: int = 2) -> Matrix:
    """``cm[i][j]`` = number of samples with true label i predicted as j."""
    cm = [[0.0] * n_classes for _ in range(n_classes)]
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    return cm


def binary_cross_entropy(y_true: Sequence[int], p_pred: Sequence[float], eps: float = 1e-12) -> float:
    """Mean binary cross-entropy (a.k.a. log loss).

    ``p_pred`` are predicted probabilities of class 1. Probabilities are clamped
    to ``[eps, 1-eps]`` so ``log(0)`` can never blow up the loss.
    """
    if len(y_true) != len(p_pred):
        raise ValueError("binary_cross_entropy: length mismatch")
    import math

    total = 0.0
    for t, p in zip(y_true, p_pred):
        p = min(max(p, eps), 1.0 - eps)
        total += -(t * math.log(p) + (1 - t) * math.log(1.0 - p))
    return total / len(y_true)


def train_test_split(
    X: Matrix,
    y: Sequence,
    test_fraction: float = 0.25,
    seed: int = 42,
) -> Tuple[Matrix, Matrix, list, list]:
    """Deterministically shuffle and split into train/test partitions.

    Uses a local :class:`random.Random` seeded with ``seed`` so the split is
    reproducible and independent of any other RNG in the program. Returns
    ``(X_train, X_test, y_train, y_test)``.
    """
    if len(X) != len(y):
        raise ValueError("train_test_split: X and y length mismatch")
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("train_test_split: test_fraction must be in (0, 1)")
    n = len(X)
    indices = list(range(n))
    random.Random(seed).shuffle(indices)
    n_test = max(1, int(round(n * test_fraction)))
    test_idx = set(indices[:n_test])
    X_train, X_test, y_train, y_test = [], [], [], []
    for i in range(n):
        if i in test_idx:
            X_test.append(X[i])
            y_test.append(y[i])
        else:
            X_train.append(X[i])
            y_train.append(y[i])
    return X_train, X_test, y_train, y_test
