#!/usr/bin/env python3
"""Assertion-backed test suite for :mod:`ml_scratch`.

Run non-interactively (exits non-zero on any failure):

    python3 /mnt/data/workspace/learning-ml/src/test_ml.py
    # or:  python3 -m unittest discover -s /mnt/data/workspace/learning-ml/src

The tests check the things that actually prove the learners *learn*:
  * loss strictly decreases over training,
  * regression recovers the true coefficients and fits closely,
  * logistic regression and the MLP cross accuracy thresholds,
  * k-means recovers known centers and inertia is monotone non-increasing.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ml_scratch import datasets, linalg, metrics  # noqa: E402
from ml_scratch.kmeans import KMeans  # noqa: E402
from ml_scratch.linear_regression import LinearRegression  # noqa: E402
from ml_scratch.logistic_regression import LogisticRegression, sigmoid  # noqa: E402
from ml_scratch.mlp import MLP  # noqa: E402


def is_non_increasing(seq, slack=1e-9):
    """True if seq[t+1] <= seq[t] + slack for all t (monotone non-increasing)."""
    return all(seq[i + 1] <= seq[i] + slack for i in range(len(seq) - 1))


class TestLinalg(unittest.TestCase):
    def test_dot_and_matvec(self):
        self.assertAlmostEqual(linalg.dot([1, 2, 3], [4, 5, 6]), 32.0)
        self.assertEqual(linalg.matvec([[1, 0], [0, 1]], [7, 9]), [7, 9])

    def test_transpose(self):
        self.assertEqual(linalg.transpose([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]])

    def test_euclidean_sq_and_mean(self):
        self.assertAlmostEqual(linalg.euclidean_sq([0, 0], [3, 4]), 25.0)
        self.assertEqual(linalg.mean_rows([[0, 0], [2, 4]]), [1.0, 2.0])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            linalg.dot([1, 2], [1])


class TestMetrics(unittest.TestCase):
    def test_mse_and_r2_perfect(self):
        self.assertAlmostEqual(metrics.mean_squared_error([1, 2, 3], [1, 2, 3]), 0.0)
        self.assertAlmostEqual(metrics.r2_score([1, 2, 3], [1, 2, 3]), 1.0)

    def test_accuracy_and_confusion(self):
        self.assertAlmostEqual(metrics.accuracy([0, 1, 1, 0], [0, 1, 0, 0]), 0.75)
        cm = metrics.confusion_matrix([0, 1, 1, 0], [0, 1, 0, 0])
        self.assertEqual(cm, [[2, 0], [1, 1]])

    def test_train_test_split_partitions_and_is_deterministic(self):
        X = [[i] for i in range(100)]
        y = list(range(100))
        a = metrics.train_test_split(X, y, test_fraction=0.3, seed=5)
        b = metrics.train_test_split(X, y, test_fraction=0.3, seed=5)
        Xtr, Xte, ytr, yte = a
        # exact partition: no overlap, full coverage, right sizes
        self.assertEqual(len(Xtr) + len(Xte), 100)
        self.assertEqual(len(Xte), 30)
        seen = sorted(yt for yt in ytr) + sorted(yt for yt in yte)
        self.assertEqual(sorted(seen), list(range(100)))
        # determinism across calls with the same seed
        self.assertEqual(a, b)
        # different seed -> (very likely) different split
        c = metrics.train_test_split(X, y, test_fraction=0.3, seed=6)
        self.assertNotEqual(a[3], c[3])


class TestLinearRegression(unittest.TestCase):
    def setUp(self):
        self.true_w = (2.0, -3.0)
        self.true_b = 5.0
        self.X, self.y = datasets.make_linear_regression(
            weights=self.true_w, bias=self.true_b, noise=0.3, seed=0
        )

    def test_loss_decreases(self):
        model = LinearRegression(lr=0.02, n_iters=2000).fit(self.X, self.y)
        self.assertGreater(len(model.loss_history), 1)
        self.assertLess(model.loss_history[-1], model.loss_history[0])
        # batch GD on a convex quadratic with a sane lr is monotone non-increasing
        self.assertTrue(is_non_increasing(model.loss_history, slack=1e-6))

    def test_recovers_coefficients(self):
        model = LinearRegression(lr=0.02, n_iters=8000).fit(self.X, self.y)
        for learned, true in zip(model.weights, self.true_w):
            self.assertAlmostEqual(learned, true, delta=0.2)
        self.assertAlmostEqual(model.bias, self.true_b, delta=0.2)

    def test_fit_is_close_on_holdout(self):
        Xtr, Xte, ytr, yte = metrics.train_test_split(self.X, self.y, seed=7)
        model = LinearRegression(lr=0.02, n_iters=8000).fit(Xtr, ytr)
        preds = model.predict(Xte)
        self.assertGreater(metrics.r2_score(yte, preds), 0.97)

    def test_predict_before_fit_raises(self):
        with self.assertRaises(RuntimeError):
            LinearRegression().predict([[1.0, 2.0]])


class TestLogisticRegression(unittest.TestCase):
    def setUp(self):
        self.X, self.y = datasets.make_blobs_2class(seed=1)

    def test_sigmoid_properties(self):
        self.assertAlmostEqual(sigmoid(0.0), 0.5)
        self.assertGreater(sigmoid(20.0), 0.999)
        self.assertLess(sigmoid(-20.0), 0.001)
        # numerically stable: no OverflowError on large magnitude input
        self.assertAlmostEqual(sigmoid(-1000.0), 0.0, places=6)

    def test_loss_decreases(self):
        model = LogisticRegression(lr=0.2, n_iters=1500).fit(self.X, self.y)
        self.assertLess(model.loss_history[-1], model.loss_history[0])
        self.assertTrue(is_non_increasing(model.loss_history, slack=1e-6))

    def test_high_accuracy(self):
        Xtr, Xte, ytr, yte = metrics.train_test_split(self.X, self.y, seed=11)
        model = LogisticRegression(lr=0.2, n_iters=3000).fit(Xtr, ytr)
        acc = metrics.accuracy(yte, model.predict(Xte))
        self.assertGreater(acc, 0.9)

    def test_probabilities_in_unit_interval(self):
        model = LogisticRegression(lr=0.2, n_iters=500).fit(self.X, self.y)
        for p in model.predict_proba(self.X):
            self.assertGreaterEqual(p, 0.0)
            self.assertLessEqual(p, 1.0)


class TestKMeans(unittest.TestCase):
    def setUp(self):
        self.X, self.true_labels, self.true_centers = datasets.make_kmeans_blobs(seed=2)

    def test_inertia_non_increasing(self):
        km = KMeans(n_clusters=3, n_init=1, seed=0).fit(self.X)
        self.assertTrue(is_non_increasing(km.inertia_history, slack=1e-6))

    def test_recovers_known_centers(self):
        km = KMeans(n_clusters=3, n_init=10, seed=0).fit(self.X)
        # Match each true center to the nearest found center; all must be close.
        for tc in self.true_centers:
            best = min(linalg.euclidean_sq(tc, fc) for fc in km.centroids)
            self.assertLess(best, 1.0)  # within distance 1 of a found center

    def test_recovers_clustering_up_to_permutation(self):
        km = KMeans(n_clusters=3, n_init=10, seed=0).fit(self.X)
        # Points with the same true label should mostly share a predicted label.
        from collections import Counter

        pred = km.labels_
        purity_total = 0
        for k in range(3):
            members = [pred[i] for i in range(len(pred)) if self.true_labels[i] == k]
            purity_total += Counter(members).most_common(1)[0][1]
        purity = purity_total / len(pred)
        self.assertGreater(purity, 0.95)

    def test_predict_assigns_to_nearest_centroid(self):
        km = KMeans(n_clusters=3, n_init=5, seed=0).fit(self.X)
        labels = km.predict(self.true_centers)
        self.assertEqual(len(set(labels)), 3)  # the 3 true centers map to 3 clusters

    def test_too_few_points_raises(self):
        with self.assertRaises(ValueError):
            KMeans(n_clusters=3).fit([[0.0, 0.0]])


class TestMLP(unittest.TestCase):
    def test_loss_decreases_on_xor(self):
        X, y = datasets.make_xor(repeats=1)
        net = MLP(n_in=2, n_hidden=4, lr=0.5, n_iters=2000, seed=0).fit(X, y)
        self.assertLess(net.loss_history[-1], net.loss_history[0])

    def test_solves_xor_above_threshold(self):
        X, y = datasets.make_xor(repeats=1)
        net = MLP(n_in=2, n_hidden=4, lr=0.5, n_iters=5000, seed=0).fit(X, y)
        acc = metrics.accuracy(y, net.predict(X))
        self.assertGreaterEqual(acc, 0.99)  # XOR fully solved

    def test_xor_with_noise_generalizes(self):
        Xtr, ytr = datasets.make_xor(repeats=40, noise=0.1, seed=3)
        Xte, yte = datasets.make_xor(repeats=10, noise=0.1, seed=99)
        net = MLP(n_in=2, n_hidden=6, lr=0.3, n_iters=4000, seed=1).fit(Xtr, ytr)
        acc = metrics.accuracy(yte, net.predict(Xte))
        self.assertGreater(acc, 0.9)

    def test_single_linear_unit_cannot_solve_xor(self):
        # Contrast: logistic regression (no hidden layer) should *fail* on XOR,
        # which is exactly why the MLP exists.
        X, y = datasets.make_xor(repeats=1)
        lr = LogisticRegression(lr=0.5, n_iters=5000).fit(X, y)
        acc = metrics.accuracy(y, lr.predict(X))
        self.assertLessEqual(acc, 0.75)  # cannot exceed 75% on XOR


if __name__ == "__main__":
    unittest.main(verbosity=2)
