"""A 1-hidden-layer multilayer perceptron trained by backpropagation.

This is the payoff module: a network that learns a function a single linear
classifier provably cannot -- XOR -- using nothing but lists of floats and the
chain rule written out by hand.

Architecture
------------
    input (n_in)  ->  hidden (n_hidden, tanh)  ->  output (1, sigmoid)

Forward pass
------------
    z1 = W1 . x + b1          # hidden pre-activations  (n_hidden,)
    a1 = tanh(z1)             # hidden activations
    z2 = W2 . a1 + b2         # output pre-activation   (scalar)
    a2 = sigmoid(z2)          # predicted probability of class 1

Loss
----
Binary cross-entropy, averaged over the batch (same as logistic regression).

Backward pass (chain rule)
--------------------------
With sigmoid output + cross-entropy loss, the output error simplifies to

    dL/dz2 = a2 - y                                  (the familiar residual)

Propagating back through W2 and the tanh hidden layer (tanh'(z) = 1 - tanh(z)^2):

    dL/da1 = dL/dz2 * W2
    dL/dz1 = dL/da1 * (1 - a1^2)

Gradients are accumulated over the batch and averaged, then applied by gradient
descent. Weights are initialized with small random values (symmetry breaking):
if every hidden unit started identical they would stay identical forever.
"""

from __future__ import annotations

import math
import random
from typing import List, Sequence

from . import linalg

Vector = List[float]
Matrix = List[List[float]]


def _sigmoid(z: float) -> float:
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


class MLP:
    """Multilayer perceptron with one tanh hidden layer and a sigmoid output.

    Parameters
    ----------
    n_in:
        Number of input features.
    n_hidden:
        Number of hidden units.
    lr:
        Learning rate.
    n_iters:
        Number of full-batch training epochs.
    seed:
        Seed for the local RNG used to initialize the weights (reproducible).
    """

    def __init__(
        self,
        n_in: int,
        n_hidden: int = 4,
        lr: float = 0.5,
        n_iters: int = 5000,
        seed: int = 0,
    ) -> None:
        self.n_in = n_in
        self.n_hidden = n_hidden
        self.lr = lr
        self.n_iters = n_iters
        rng = random.Random(seed)

        # Small random init in [-0.5, 0.5] breaks symmetry between hidden units.
        # W1[h] are the weights feeding hidden unit h from the inputs.
        self.W1: Matrix = [[rng.uniform(-0.5, 0.5) for _ in range(n_in)] for _ in range(n_hidden)]
        self.b1: Vector = [0.0] * n_hidden
        # W2 are the weights from the hidden layer to the single output unit.
        self.W2: Vector = [rng.uniform(-0.5, 0.5) for _ in range(n_hidden)]
        self.b2: float = 0.0

        self.loss_history: List[float] = []

    def _forward(self, x: Sequence[float]):
        """Forward pass for one sample. Returns (a1, a2) for reuse in backprop."""
        z1 = [linalg.dot(self.W1[h], x) + self.b1[h] for h in range(self.n_hidden)]
        a1 = [math.tanh(z) for z in z1]
        z2 = linalg.dot(self.W2, a1) + self.b2
        a2 = _sigmoid(z2)
        return a1, a2

    def predict_proba(self, X: Matrix) -> Vector:
        """Probability of class 1 for each row of ``X``."""
        return [self._forward(x)[1] for x in X]

    def predict(self, X: Matrix, threshold: float = 0.5) -> List[int]:
        """Hard 0/1 predictions."""
        return [1 if p >= threshold else 0 for p in self.predict_proba(X)]

    def fit(self, X: Matrix, y: Sequence[int]) -> "MLP":
        """Train by full-batch gradient descent with backpropagation."""
        if not X:
            raise ValueError("fit: empty training set")
        n = len(X)
        eps = 1e-12
        self.loss_history = []

        for _ in range(self.n_iters):
            # Accumulators for batch-averaged gradients.
            gW1 = [[0.0] * self.n_in for _ in range(self.n_hidden)]
            gb1 = [0.0] * self.n_hidden
            gW2 = [0.0] * self.n_hidden
            gb2 = 0.0
            loss = 0.0

            for i in range(n):
                x = X[i]
                target = y[i]

                # ---- forward ----
                a1, a2 = self._forward(x)

                # ---- loss (cross-entropy, clamped) ----
                pc = min(max(a2, eps), 1.0 - eps)
                loss += -(target * math.log(pc) + (1 - target) * math.log(1.0 - pc))

                # ---- backward ----
                # Output layer: with sigmoid+BCE, dL/dz2 = a2 - y.
                dz2 = a2 - target
                for h in range(self.n_hidden):
                    gW2[h] += dz2 * a1[h]
                gb2 += dz2

                # Hidden layer: backprop through W2 then through tanh.
                for h in range(self.n_hidden):
                    da1 = dz2 * self.W2[h]
                    dz1 = da1 * (1.0 - a1[h] * a1[h])  # tanh'(z) = 1 - tanh(z)^2
                    for j in range(self.n_in):
                        gW1[h][j] += dz1 * x[j]
                    gb1[h] += dz1

            loss /= n
            self.loss_history.append(loss)

            # ---- batch-averaged gradient-descent update ----
            inv = 1.0 / n
            for h in range(self.n_hidden):
                for j in range(self.n_in):
                    self.W1[h][j] -= self.lr * inv * gW1[h][j]
                self.b1[h] -= self.lr * inv * gb1[h]
                self.W2[h] -= self.lr * inv * gW2[h]
            self.b2 -= self.lr * inv * gb2

        return self
