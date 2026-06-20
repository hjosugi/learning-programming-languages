"""Linear regression trained by batch gradient descent.

Model
-----
    y_hat = w . x + b

Loss (mean squared error over the whole batch)
----------------------------------------------
    L(w, b) = (1/n) * sum_i (y_hat_i - y_i)^2

Gradients (the calculus we are implementing by hand)
----------------------------------------------------
Let r_i = y_hat_i - y_i be the residual. Then

    dL/dw_j = (2/n) * sum_i r_i * x_ij
    dL/db   = (2/n) * sum_i r_i

"Batch" means we average the gradient over *all* samples before each update
(as opposed to stochastic / mini-batch GD). The update rule is

    w <- w - lr * dL/dw
    b <- b - lr * dL/db
"""

from __future__ import annotations

from typing import List, Sequence

from . import linalg

Vector = List[float]
Matrix = List[List[float]]


class LinearRegression:
    """Ordinary least squares fit via full-batch gradient descent.

    Parameters
    ----------
    lr:
        Learning rate (step size). Too large diverges; too small crawls.
    n_iters:
        Maximum number of gradient-descent steps.
    tol:
        Convergence tolerance. Training stops early once the absolute decrease
        in loss between consecutive steps drops below ``tol``.
    """

    def __init__(self, lr: float = 0.01, n_iters: int = 5000, tol: float = 1e-9) -> None:
        self.lr = lr
        self.n_iters = n_iters
        self.tol = tol
        self.weights: Vector = []
        self.bias: float = 0.0
        # loss_history[t] is the MSE measured *before* the t-th update, so it is
        # a clean record of the descent that tests/demos can assert on.
        self.loss_history: List[float] = []

    def _predict_raw(self, X: Matrix) -> Vector:
        return [linalg.dot(self.weights, row) + self.bias for row in X]

    def fit(self, X: Matrix, y: Sequence[float]) -> "LinearRegression":
        """Run batch gradient descent on (X, y). Returns ``self`` (fluent API)."""
        if not X:
            raise ValueError("fit: empty training set")
        n = len(X)
        dim = len(X[0])
        self.weights = [0.0] * dim
        self.bias = 0.0
        self.loss_history = []

        prev_loss = float("inf")
        for _ in range(self.n_iters):
            preds = self._predict_raw(X)
            residuals = [p - t for p, t in zip(preds, y)]  # r_i = y_hat - y

            # Mean squared error for this step (record before updating).
            loss = sum(r * r for r in residuals) / n
            self.loss_history.append(loss)

            # Gradient of MSE w.r.t. each weight and the bias.
            grad_w = [0.0] * dim
            for i in range(n):
                ri = residuals[i]
                xi = X[i]
                for j in range(dim):
                    grad_w[j] += ri * xi[j]
            grad_w = [(2.0 / n) * g for g in grad_w]
            grad_b = (2.0 / n) * sum(residuals)

            # Parameter update.
            self.weights = [w - self.lr * g for w, g in zip(self.weights, grad_w)]
            self.bias -= self.lr * grad_b

            # Early stop once the loss stops meaningfully improving.
            if abs(prev_loss - loss) < self.tol:
                break
            prev_loss = loss

        return self

    def predict(self, X: Matrix) -> Vector:
        """Predict continuous targets for each row of ``X``."""
        if not self.weights:
            raise RuntimeError("predict: call fit() first")
        return self._predict_raw(X)
