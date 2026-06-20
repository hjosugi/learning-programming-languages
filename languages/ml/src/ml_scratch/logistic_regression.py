"""Binary logistic regression trained by batch gradient descent.

Model
-----
    z       = w . x + b
    p(y=1)  = sigmoid(z) = 1 / (1 + e^{-z})

Loss (binary cross-entropy / log loss, averaged over the batch)
---------------------------------------------------------------
    L = -(1/n) * sum_i [ y_i log(p_i) + (1 - y_i) log(1 - p_i) ]

The pleasant surprise: with the sigmoid + cross-entropy pairing the gradient
collapses to the *same shape* as linear regression's,

    dL/dw_j = (1/n) * sum_i (p_i - y_i) * x_ij
    dL/db   = (1/n) * sum_i (p_i - y_i)

i.e. residual (predicted probability minus label) times input, averaged. That
non-coincidence is why this pairing is the textbook default.
"""

from __future__ import annotations

import math
from typing import List, Sequence

from . import linalg

Vector = List[float]
Matrix = List[List[float]]


def sigmoid(z: float) -> float:
    """Numerically stable logistic sigmoid in [0, 1].

    For large negative ``z`` the naive ``1/(1+e^{-z})`` would compute ``e^{+big}``
    and overflow, so we branch on the sign of ``z`` and use the algebraically
    equal form ``e^{z}/(1+e^{z})`` for the negative branch.
    """
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


class LogisticRegression:
    """Logistic regression classifier for two classes (labels 0 and 1).

    Parameters
    ----------
    lr:
        Learning rate.
    n_iters:
        Maximum gradient-descent steps.
    tol:
        Early-stop tolerance on the change in cross-entropy loss.
    """

    def __init__(self, lr: float = 0.1, n_iters: int = 5000, tol: float = 1e-9) -> None:
        self.lr = lr
        self.n_iters = n_iters
        self.tol = tol
        self.weights: Vector = []
        self.bias: float = 0.0
        self.loss_history: List[float] = []

    def predict_proba(self, X: Matrix) -> Vector:
        """Probability of class 1 for each row of ``X``."""
        if not self.weights:
            raise RuntimeError("predict_proba: call fit() first")
        return [sigmoid(linalg.dot(self.weights, row) + self.bias) for row in X]

    def predict(self, X: Matrix, threshold: float = 0.5) -> List[int]:
        """Hard 0/1 labels by thresholding the predicted probability."""
        return [1 if p >= threshold else 0 for p in self.predict_proba(X)]

    def fit(self, X: Matrix, y: Sequence[int]) -> "LogisticRegression":
        """Run batch gradient descent to minimize cross-entropy. Returns self."""
        if not X:
            raise ValueError("fit: empty training set")
        n = len(X)
        dim = len(X[0])
        self.weights = [0.0] * dim
        self.bias = 0.0
        self.loss_history = []

        prev_loss = float("inf")
        eps = 1e-12
        for _ in range(self.n_iters):
            probs = [sigmoid(linalg.dot(self.weights, row) + self.bias) for row in X]

            # Cross-entropy loss for this step (clamped to avoid log(0)).
            loss = 0.0
            for t, p in zip(y, probs):
                pc = min(max(p, eps), 1.0 - eps)
                loss += -(t * math.log(pc) + (1 - t) * math.log(1.0 - pc))
            loss /= n
            self.loss_history.append(loss)

            # Gradient: (p - y) * x averaged over the batch.
            grad_w = [0.0] * dim
            grad_b = 0.0
            for i in range(n):
                err = probs[i] - y[i]
                grad_b += err
                xi = X[i]
                for j in range(dim):
                    grad_w[j] += err * xi[j]
            grad_w = [g / n for g in grad_w]
            grad_b /= n

            self.weights = [w - self.lr * g for w, g in zip(self.weights, grad_w)]
            self.bias -= self.lr * grad_b

            if abs(prev_loss - loss) < self.tol:
                break
            prev_loss = loss

        return self
