"""ml_scratch: classical machine learning implemented from scratch in pure Python.

No numpy, no scikit-learn. Standard library plus :mod:`math` only.

The point of this package is *pedagogical transparency*: every number that the
optimizer touches is a plain Python ``float`` in a plain Python ``list``, so you
can read the arithmetic of gradient descent, the chain rule, and k-means without
a tensor library hiding it. Once the mechanics are clear, the README's
"Upgrade path" shows how each module maps onto numpy / scikit-learn / PyTorch.

Modules
-------
linalg            : tiny vector/matrix helpers (dot, matvec, transpose, ...)
datasets          : seeded, deterministic synthetic data generators
metrics           : MSE, accuracy, confusion matrix, train/test split
linear_regression : batch gradient descent + MSE for linear regression
logistic_regression : sigmoid + binary cross-entropy classifier
kmeans            : Lloyd's algorithm with inertia and convergence
mlp               : 1-hidden-layer multilayer perceptron + backpropagation
"""

from . import linalg, datasets, metrics  # noqa: F401
from .linear_regression import LinearRegression  # noqa: F401
from .logistic_regression import LogisticRegression  # noqa: F401
from .kmeans import KMeans  # noqa: F401
from .mlp import MLP  # noqa: F401

__all__ = [
    "linalg",
    "datasets",
    "metrics",
    "LinearRegression",
    "LogisticRegression",
    "KMeans",
    "MLP",
]
