"""API integration tests for the phase acceptance criteria.

Uses a temporary MODEL_OUTPUT_DIR so the real data folder is never touched.
Run from the repo root:  python -m unittest discover -s scripts/tests -v
"""
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BACKEND = os.path.join(REPO, "backend")

_TMP = tempfile.mkdtemp(prefix="oe_model_output_")
os.environ["MODEL_OUTPUT_DIR"] = _TMP
sys.path.insert(0, BACKEND)
sys.path.insert(0, os.path.join(REPO, "scripts"))

import config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from save_model_output import save_model_output  # noqa: E402

# Sample model-output file generated from mock data (never read from the real data folder)
_SAMPLE_DIR = tempfile.mkdtemp(prefix="oe_sample_")
SAMPLE = os.path.join(_SAMPLE_DIR, "thetao_2026-09-25.nc")


def _make_sample():
    if not os.path.exists(SAMPLE):
        from providers.mock_provider import MockProvider
        arr = MockProvider().get_temperature("2026-09-25")["thetao"].values
        save_model_output(arr, "2026-09-25", out_dir=_SAMPLE_DIR, model_version="TEST-FILE-FROM-MOCK")


def setUpModule():
    _make_sample()


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)
    shutil.rmtree(_SAMPLE_DIR, ignore_errors=True)


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        config.DATA_SOURCE = "mock"

    def tearDown(self):
        config.DATA_SOURCE = "mock"


class TestMockMode(ApiTestCase):
    def test_meta(self):
        r = self.client.get("/api/v1/meta")
        self.assertEqual(r.status_code, 200)
        m = r.json()
        self.assertEqual(m["data_source"], "mock")
        self.assertIn("2026-09-25", m["dates"]["all_dates"])
        self.assertEqual(m["per_date"]["2026-09-25"]["valid_upto"], "2026-09-26")
        # the existing endpoint keeps working
        self.assertEqual(self.client.get("/api/v1/metadata").status_code, 200)

    def test_field_and_derived(self):
        r = self.client.get("/api/v1/field?date=2026-09-25&depth=50")
        self.assertEqual(r.status_code, 200)
        f = r.json()
        self.assertEqual(len(f["values"]), 101)
        self.assertEqual(len(f["values"][0]), 241)
        for var in ("d20", "d26", "mld", "front_0m", "front_50m", "front_100m",
                    "subsurface_front_flag", "tchp", "confidence"):
            r = self.client.get(f"/api/v1/derived?date=2026-09-25&var={var}")
            self.assertEqual(r.status_code, 200, var)
        d20 = np.array(self.client.get("/api/v1/derived?date=2026-09-25&var=d20").json()["values"], dtype=float)
        ocean = d20[~np.isnan(d20)]
        self.assertTrue(np.isnan(d20).any())  # land
        self.assertTrue(40 < np.median(ocean) < 250)
        self.assertEqual(self.client.get("/api/v1/derived.png?date=2026-09-25&var=d20").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/derived?date=2026-09-25&var=bogus").status_code, 422)

    def test_profile_has_derived(self):
        r = self.client.get("/api/v1/profile?lat=15&lon=88&date=2025-02-15")
        self.assertEqual(r.status_code, 200)
        self.assertIn("d20", r.json()["derived"])
        self.assertEqual(self.client.get("/api/v1/profile?lat=20&lon=78&date=2025-02-15").status_code, 422)

    def test_timeseries_range(self):
        r = self.client.get("/api/v1/timeseries?lat=15&lon=88&depth=100&start=2025-02-01&end=2025-02-10")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["dates"]), 10)

    def test_pfz_enriched(self):
        r = self.client.get("/api/v1/pfz/enriched?sector=GOA&date=2026-09-25")
        self.assertEqual(r.status_code, 200)
        e = r.json()
        self.assertEqual(len(e["rows"]), 7)
        for row in e["rows"]:
            for k in ("d20_m", "mld_m", "front_50m", "subsurface_front", "confidence", "confidence_level",
                      "profile", "summary_text", "grid_cell_lat", "grid_cell_lon"):
                self.assertIn(k, row)
            self.assertEqual(len(row["profile"]), 15)
            self.assertNotIn("NaN", row["summary_text"])
            self.assertLessEqual(len(row["summary_text"]), config.FISHERMAN_MESSAGE_MAX_CHARS)
        hi = self.client.get("/api/v1/pfz/enriched?sector=GOA&date=2026-09-25&lang=hi").json()
        self.assertIn("मीटर", hi["rows"][0]["summary_text"])
        for row in hi["rows"]:
            self.assertLessEqual(len(row["summary_text"]), config.FISHERMAN_MESSAGE_MAX_CHARS)

    def test_pfz_empty_sector(self):
        r = self.client.get("/api/v1/pfz/enriched?sector=KERALA&date=2026-09-25")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["rows"], [])
        self.assertEqual(r.json()["message"], "No PFZ advisory loaded for this sector and date")

    def test_pfz_csv(self):
        r = self.client.get("/api/v1/export/pfz.csv?sector=GOA&date=2026-09-25")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.content.decode("utf-8-sig").strip().splitlines()), 8)

    def test_validation_placeholder(self):
        v = self.client.get("/api/v1/validation").json()
        self.assertEqual(len(v["metrics"]), 15)
        if v["status"] == "final":          # the team's real results
            self.assertNotIn("message", v)
            self.assertTrue(any(m["rmse_c"] is not None for m in v["metrics"]))
        else:                               # shipped placeholder
            self.assertEqual(v["message"], "Validation results pending")
            self.assertTrue(all(m["rmse_c"] is None for m in v["metrics"]))

    def test_netcdf_exports(self):
        import xarray as xr
        r = self.client.get("/api/v1/export/netcdf?date=2026-09-25")
        self.assertEqual(r.status_code, 200)
        p = os.path.join(_TMP, "t.nc")
        with open(p, "wb") as f:
            f.write(r.content)
        with xr.open_dataset(p) as ds:
            self.assertEqual(dict(ds.sizes), {"time": 1, "depth": 15, "lat": 101, "lon": 241})
            self.assertEqual(ds["thetao"].dims, ("time", "depth", "lat", "lon"))
            self.assertEqual(ds["thetao"].dtype, np.float32)
            self.assertEqual(ds["thetao"].attrs["units"], "degree_Celsius")
            self.assertEqual(ds["thetao"].attrs["standard_name"], "sea_water_potential_temperature")
            self.assertEqual(ds.attrs["Conventions"], "CF-1.8")
            self.assertEqual(ds.attrs["valid_upto"], "2026-09-26")
            self.assertEqual(str(ds.time.values[0])[:10], "2026-09-25")
            self.assertEqual(ds["depth"].attrs["positive"], "down")
        r = self.client.get("/api/v1/export/derived?date=2026-09-25")
        self.assertEqual(r.status_code, 200)
        with open(p, "wb") as f:
            f.write(r.content)
        with xr.open_dataset(p) as ds:
            self.assertIn("d20", ds)
            self.assertEqual(ds["d20"].attrs["units"], "m")


class TestFilesMode(ApiTestCase):
    def setUp(self):
        config.DATA_SOURCE = "files"
        for f in os.listdir(_TMP):
            os.remove(os.path.join(_TMP, f))
        shutil.copy(SAMPLE, _TMP)
        shutil.copy(SAMPLE.replace(".nc", ".json"), _TMP)

    def test_sample_file_and_badge(self):
        m = self.client.get("/api/v1/meta").json()
        self.assertEqual(m["data_source"], "model_output_files")
        self.assertEqual(m["model_version"], "TEST-FILE-FROM-MOCK")
        self.assertEqual(m["dates"]["all_dates"], ["2026-09-25"])

    def test_drop_in_new_file_without_restart(self):
        arr = np.load(os.path.join(BACKEND, "data", "land_mask.npy"))
        pred = np.where(arr[None], np.nan, 25.0).astype(np.float32) * np.ones((15, 1, 1), np.float32)
        save_model_output(pred, "2026-09-26", out_dir=_TMP, model_version="drop-test")
        dates = self.client.get("/api/v1/meta").json()["dates"]["all_dates"]
        self.assertEqual(dates, ["2026-09-25", "2026-09-26"])

    def test_bad_file_rejected(self):
        np.save(os.path.join(_TMP, "thetao_2026-09-27.npy"), np.zeros((14, 101, 241), np.float32))
        m = self.client.get("/api/v1/meta").json()
        self.assertNotIn("2026-09-27", m["dates"]["all_dates"])
        self.assertTrue(any("(14, 101, 241)" in e for f in m["invalid_model_files"] for e in f["errors"]))
        st = self.client.get("/api/v1/model-output/status").json()
        bad = [f for f in st["files"] if f["date"] == "2026-09-27"][0]
        self.assertFalse(bad["valid"])
        r = self.client.get("/api/v1/field?date=2026-09-27&depth=0")
        self.assertEqual(r.status_code, 404)
        self.assertIn("failed validation", r.json()["detail"])

    def test_missing_date_message(self):
        r = self.client.get("/api/v1/export/netcdf?date=2026-10-01")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["detail"], "No model output for 2026-10-01 in data/model_output/")

    def test_upload(self):
        with open(SAMPLE, "rb") as f:
            body = f.read()
        r = self.client.post("/api/v1/model-output/upload?filename=thetao_2026-09-28.nc&model_version=up",
                             content=body)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["saved"])
        bad = np.zeros((14, 101, 241), np.float32)
        p = os.path.join(tempfile.gettempdir(), "thetao_2026-09-29.npy")
        np.save(p, bad)
        with open(p, "rb") as f:
            r = self.client.post("/api/v1/model-output/upload?filename=thetao_2026-09-29.npy", content=f.read())
        self.assertEqual(r.status_code, 422)
        self.assertFalse(os.path.exists(os.path.join(_TMP, "thetao_2026-09-29.npy")))


class TestModelModeWithoutArtifacts(ApiTestCase):
    def test_clear_message(self):
        empty = tempfile.mkdtemp(prefix="oe_no_art_")
        old = config.GNN_ARTIFACTS_DIR
        config.GNN_ARTIFACTS_DIR = empty
        try:
            config.DATA_SOURCE = "model"
            r = self.client.get("/api/v1/meta")
            self.assertEqual(r.status_code, 404)
            self.assertIn("gnn_C_full_epoch_20.pt not found", r.json()["detail"])
            self.assertEqual(self.client.get("/api/v1/metadata").status_code, 404)
        finally:
            config.GNN_ARTIFACTS_DIR = old
            shutil.rmtree(empty, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
