"""In-backend GNN-OAM engine (DATA_SOURCE=model) on small fake Kaggle artifacts.

Skipped automatically when torch is not installed.
"""
import os
import shutil
import sys
import tempfile
import time
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
sys.path.insert(0, HERE)

try:
    import torch  # noqa: F401
    HAVE_TORCH = True
except ImportError:
    HAVE_TORCH = False

import config  # noqa: E402


@unittest.skipUnless(HAVE_TORCH, "torch not installed")
class TestGnnModelMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fake_gnn_artifacts import make_fake_run
        cls.tmp = tempfile.mkdtemp(prefix="oe_gnn_")
        cls.art = os.path.join(cls.tmp, "artifacts")
        cls.out = os.path.join(cls.tmp, "gnn_output")
        make_fake_run(cls.art, n_days=35)
        cls._saved = (config.GNN_ARTIFACTS_DIR, config.GNN_OUTPUT_CACHE_DIR, config.DATA_SOURCE,
                      config.OUTPUT_DIR, config.DERIVED_DIR)
        config.GNN_ARTIFACTS_DIR, config.GNN_OUTPUT_CACHE_DIR = cls.art, cls.out
        config.OUTPUT_DIR = config.DERIVED_DIR = cls.tmp   # keep fake-model exports out of backend/data
        from fastapi.testclient import TestClient
        from main import app
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        (config.GNN_ARTIFACTS_DIR, config.GNN_OUTPUT_CACHE_DIR, config.DATA_SOURCE,
         config.OUTPUT_DIR, config.DERIVED_DIR) = cls._saved
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        config.DATA_SOURCE = "model"

    def test_meta_and_field(self):
        m = self.client.get("/api/v1/meta").json()
        self.assertEqual(m["data_source"], "model")
        self.assertIn("epoch 20", m["model_version"])
        dates = m["dates"]["all_dates"]
        self.assertEqual(dates[0], "2023-06-30")           # first day with a full 30-day window
        self.assertEqual(len(dates), 6)

        t0 = time.time()
        r = self.client.get(f"/api/v1/field?date={dates[-1]}&depth=100")
        self.assertEqual(r.status_code, 200, r.text)
        first = time.time() - t0
        vals = np.array(r.json()["values"], dtype=float)
        self.assertTrue(np.isnan(vals).any() and np.isfinite(vals).any())
        self.assertTrue(os.path.exists(os.path.join(self.out, f"thetao_{dates[-1]}.nc")))

        t0 = time.time()
        self.client.get(f"/api/v1/derived?date={dates[-1]}&var=d20")
        self.assertLess(time.time() - t0, max(first, 1.0))   # served from cache, not recomputed
        m = self.client.get("/api/v1/meta").json()
        self.assertIn(dates[-1], m["ready_dates"])

    def test_timeseries_does_not_trigger_runs(self):
        def n_files():
            return len([f for f in os.listdir(self.out) if f.endswith(".nc")]) if os.path.isdir(self.out) else 0
        before = n_files()
        r = self.client.get("/api/v1/timeseries?lat=15&lon=65&depth=0")
        self.assertIn(r.status_code, (200, 404, 422))
        self.assertEqual(n_files(), before)

    def test_netcdf_export(self):
        date = self.client.get("/api/v1/meta").json()["dates"]["all_dates"][0]
        r = self.client.get(f"/api/v1/export/netcdf?date={date}")
        self.assertEqual(r.status_code, 200)

    def test_validation_against_target_cache(self):
        from gnn_engine.engine import get_engine
        eng = get_engine()
        d = eng.available_dates()[0]
        truth = eng.truth(d)
        self.assertEqual(truth.shape, (15, 101, 241))
        self.assertEqual(eng.split_of("2023-07-01"), "test")


if __name__ == "__main__":
    unittest.main()
