#!/usr/bin/env python3
"""Narrated demo of every learner in :mod:`ml_scratch`.

Run it directly:

    python3 /mnt/data/workspace/learning-ml/src/demo.py

It prints, for each model, the loss/inertia falling and the final metric, so you
can *see* that gradient descent, k-means, and backpropagation are all working.
Everything is seeded, so the numbers are identical on every run.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the package importable whether or not the repo is installed.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ml_scratch import datasets, metrics  # noqa: E402
from ml_scratch.kmeans import KMeans  # noqa: E402
from ml_scratch.linear_regression import LinearRegression  # noqa: E402
from ml_scratch.logistic_regression import LogisticRegression  # noqa: E402
from ml_scratch.mlp import MLP  # noqa: E402


def _rule(title: str) -> None:
    print("\n" + "=" * 66)
    print(title)
    print("=" * 66)


def _loss_trace(history, n=5):
    """Show the first and last few loss values to illustrate the descent."""
    if len(history) <= 2 * n:
        return ", ".join(f"{v:.5f}" for v in history)
    head = ", ".join(f"{v:.5f}" for v in history[:n])
    tail = ", ".join(f"{v:.5f}" for v in history[-n:])
    return f"{head}  ...  {tail}"


def demo_linear_regression() -> None:
    _rule("1) LINEAR REGRESSION  (batch gradient descent, MSE)")
    true_w, true_b = (2.0, -3.0), 5.0
    X, y = datasets.make_linear_regression(weights=true_w, bias=true_b, noise=0.4, seed=0)
    Xs, _, _ = datasets.standardize(X)
    Xtr, Xte, ytr, yte = metrics.train_test_split(X, y, test_fraction=0.25, seed=7)

    model = LinearRegression(lr=0.02, n_iters=4000).fit(Xtr, ytr)
    preds = model.predict(Xte)

    print(f"true weights = {true_w}, true bias = {true_b}")
    print(f"learned w    = {tuple(round(w, 3) for w in model.weights)}, b = {round(model.bias, 3)}")
    print(f"MSE first->last: {_loss_trace(model.loss_history)}")
    print(f"test  MSE = {metrics.mean_squared_error(yte, preds):.4f}")
    print(f"test  R^2 = {metrics.r2_score(yte, preds):.4f}")
    _ = Xs  # standardization is demonstrated; raw X already trains fine here


def demo_logistic_regression() -> None:
    _rule("2) LOGISTIC REGRESSION  (sigmoid, cross-entropy)")
    X, y = datasets.make_blobs_2class(seed=1)
    Xtr, Xte, ytr, yte = metrics.train_test_split(X, y, test_fraction=0.25, seed=11)

    model = LogisticRegression(lr=0.2, n_iters=3000).fit(Xtr, ytr)
    preds = model.predict(Xte)

    print(f"cross-entropy first->last: {_loss_trace(model.loss_history)}")
    print(f"test accuracy = {metrics.accuracy(yte, preds):.3f}")
    cm = metrics.confusion_matrix(yte, preds, n_classes=2)
    print(f"confusion matrix [[TN, FP], [FN, TP]] = {cm}")


def demo_kmeans() -> None:
    _rule("3) K-MEANS CLUSTERING  (Lloyd's algorithm, inertia)")
    X, true_labels, true_centers = datasets.make_kmeans_blobs(seed=2)
    km = KMeans(n_clusters=3, n_init=10, seed=0).fit(X)

    print(f"true centers   = {[[round(c, 2) for c in ctr] for ctr in true_centers]}")
    found = sorted([round(c, 2) for c in ctr] for ctr in km.centroids)
    print(f"found centers  = {found}")
    print(f"inertia first->last: {_loss_trace(km.inertia_history)}")
    print(f"final inertia  = {km.inertia_:.3f}")


def demo_mlp() -> None:
    _rule("4) MLP + BACKPROP  (solving XOR, not linearly separable)")
    X, y = datasets.make_xor(repeats=1)  # the 4 canonical corners
    net = MLP(n_in=2, n_hidden=4, lr=0.5, n_iters=5000, seed=0).fit(X, y)

    print(f"cross-entropy first->last: {_loss_trace(net.loss_history)}")
    print("truth table:")
    for point in [[0, 0], [0, 1], [1, 0], [1, 1]]:
        p = net.predict_proba([point])[0]
        print(f"  {point} -> p(1)={p:.3f} -> class {1 if p >= 0.5 else 0}")
    print(f"accuracy = {metrics.accuracy(y, net.predict(X)):.3f}")


def main() -> None:
    print("ml_scratch demo -- classical ML from scratch in pure Python (no numpy)")
    demo_linear_regression()
    demo_logistic_regression()
    demo_kmeans()
    demo_mlp()
    print("\nAll demos finished. See test_ml.py for the assertion-backed checks.")


if __name__ == "__main__":
    main()
