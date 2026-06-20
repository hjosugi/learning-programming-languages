"""K-means clustering via Lloyd's algorithm.

K-means is *unsupervised*: there are no labels, only points. It alternates two
steps until the assignment stops changing:

1. **Assign** each point to its nearest centroid (by squared distance).
2. **Update** each centroid to the mean of the points assigned to it.

The objective it (locally) minimizes is the **inertia**, the within-cluster sum
of squared distances:

    inertia = sum over points of  euclidean_sq(point, its_centroid)

Each Lloyd iteration provably never increases the inertia, so the inertia is a
monotone non-increasing convergence signal. Because the result depends on the
initial centroids, we support ``n_init`` random restarts and keep the run with
the lowest inertia -- exactly what scikit-learn's KMeans does by default.
"""

from __future__ import annotations

import random
from typing import List, Optional

from . import linalg

Vector = List[float]
Matrix = List[List[float]]


class KMeans:
    """K-means clustering.

    Parameters
    ----------
    n_clusters:
        Number of clusters k.
    n_iters:
        Maximum Lloyd iterations per initialization.
    n_init:
        Number of random restarts; the lowest-inertia run wins.
    tol:
        Convergence tolerance on the decrease in inertia between iterations.
    seed:
        Seed for the local RNG used to pick initial centroids (reproducible).
    """

    def __init__(
        self,
        n_clusters: int = 3,
        n_iters: int = 300,
        n_init: int = 10,
        tol: float = 1e-9,
        seed: int = 0,
    ) -> None:
        self.n_clusters = n_clusters
        self.n_iters = n_iters
        self.n_init = n_init
        self.tol = tol
        self.seed = seed
        self.centroids: Matrix = []
        self.labels_: List[int] = []
        self.inertia_: float = float("inf")
        # Inertia trajectory of the *best* run, for demos/tests of convergence.
        self.inertia_history: List[float] = []

    def _assign(self, X: Matrix, centroids: Matrix) -> List[int]:
        """Assign each point to the index of its nearest centroid."""
        labels = []
        for point in X:
            best_idx = 0
            best_dist = linalg.euclidean_sq(point, centroids[0])
            for idx in range(1, len(centroids)):
                d = linalg.euclidean_sq(point, centroids[idx])
                if d < best_dist:
                    best_dist = d
                    best_idx = idx
            labels.append(best_idx)
        return labels

    def _update(self, X: Matrix, labels: List[int], old: Matrix) -> Matrix:
        """Recompute centroids as the mean of their assigned points.

        An empty cluster keeps its previous centroid (a standard, simple fix
        that avoids dividing by zero and silently dropping a cluster).
        """
        new: Matrix = []
        for k in range(self.n_clusters):
            members = [X[i] for i in range(len(X)) if labels[i] == k]
            new.append(linalg.mean_rows(members) if members else list(old[k]))
        return new

    @staticmethod
    def _inertia(X: Matrix, labels: List[int], centroids: Matrix) -> float:
        return sum(linalg.euclidean_sq(X[i], centroids[labels[i]]) for i in range(len(X)))

    def _run_once(self, X: Matrix, rng: random.Random):
        """One full Lloyd run from random initial centroids (distinct points)."""
        # Initialize centroids at k distinct data points (Forgy initialization).
        init_idx = rng.sample(range(len(X)), self.n_clusters)
        centroids = [list(X[i]) for i in init_idx]

        history: List[float] = []
        labels = self._assign(X, centroids)
        prev_inertia = float("inf")
        for _ in range(self.n_iters):
            centroids = self._update(X, labels, centroids)
            labels = self._assign(X, centroids)
            inertia = self._inertia(X, labels, centroids)
            history.append(inertia)
            if abs(prev_inertia - inertia) < self.tol:
                break
            prev_inertia = inertia
        final_inertia = self._inertia(X, labels, centroids)
        return centroids, labels, final_inertia, history

    def fit(self, X: Matrix) -> "KMeans":
        """Fit k-means with ``n_init`` restarts; keep the lowest-inertia run."""
        if len(X) < self.n_clusters:
            raise ValueError("fit: need at least n_clusters points")
        rng = random.Random(self.seed)
        best: Optional[tuple] = None
        for _ in range(self.n_init):
            centroids, labels, inertia, history = self._run_once(X, rng)
            if best is None or inertia < best[2]:
                best = (centroids, labels, inertia, history)
        assert best is not None
        self.centroids, self.labels_, self.inertia_, self.inertia_history = best
        return self

    def predict(self, X: Matrix) -> List[int]:
        """Assign new points to the nearest fitted centroid."""
        if not self.centroids:
            raise RuntimeError("predict: call fit() first")
        return self._assign(X, self.centroids)
