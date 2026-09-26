"""Unit tests for backend/derived.py (spec Section 6.7).

Run from the repo root:
    python -m unittest discover -s scripts/tests -v
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import config  # noqa: E402
from derived import (  # noqa: E402
    isotherm_depth, isotherm_depth_field, mixed_layer_depth, tchp, front_strength,
    subsurface_front_flag, gear_depth_range, confidence_field, confidence_level,
    ISO_ABSENT, ISO_NOT_REACHED,
)

DEPTHS = config.DEPTHS_M
LINEAR = np.array([30 - 0.1 * z for z in DEPTHS])


class TestIsotherms(unittest.TestCase):
    def test_d20_linear(self):
        self.assertAlmostEqual(isotherm_depth(LINEAR, DEPTHS, 20.0), 100.0, places=6)

    def test_d26_linear(self):
        self.assertAlmostEqual(isotherm_depth(LINEAR, DEPTHS, 26.0), 40.0, places=6)

    def test_surface_below_20_gives_nan(self):
        cold = LINEAR - 15  # surface 15 degC
        self.assertTrue(np.isnan(isotherm_depth(cold, DEPTHS, 20.0)))
        _, flag = isotherm_depth_field(cold, DEPTHS, 20.0)
        self.assertEqual(int(flag), ISO_ABSENT)

    def test_never_reached_gives_nan_and_flag(self):
        warm = np.full(len(DEPTHS), 25.0)
        d, flag = isotherm_depth_field(warm, DEPTHS, 20.0)
        self.assertTrue(np.isnan(d))
        self.assertEqual(int(flag), ISO_NOT_REACHED)

    def test_land_column_nan(self):
        self.assertTrue(np.isnan(isotherm_depth(np.full(len(DEPTHS), np.nan), DEPTHS, 20.0)))

    def test_grid_matches_scalar(self):
        T = np.repeat(LINEAR[:, None, None], 3, axis=1).repeat(4, axis=2)
        d, _ = isotherm_depth_field(T, DEPTHS, 20.0)
        np.testing.assert_allclose(d, 100.0)


class TestMLD(unittest.TestCase):
    def test_mld_linear(self):
        # T(10) = 29, target 28.8 -> 12 m
        self.assertAlmostEqual(mixed_layer_depth(LINEAR, DEPTHS), 12.0, places=6)

    def test_mld_never_reached(self):
        self.assertTrue(np.isnan(mixed_layer_depth(np.full(len(DEPTHS), 28.0), DEPTHS)))


class TestTCHP(unittest.TestCase):
    def test_tchp_linear(self):
        self.assertAlmostEqual(tchp(LINEAR, DEPTHS), 32.8, delta=0.5)

    def test_tchp_cold_surface_is_zero(self):
        self.assertEqual(tchp(LINEAR - 10, DEPTHS), 0.0)


class TestFronts(unittest.TestCase):
    def test_front_meridional_gradient(self):
        lats = np.array(config.LATS)
        # +1 degC per 0.25 deg latitude, uniform in longitude
        field = np.repeat(((lats - lats[0]) / 0.25)[:, None], len(config.LONS), axis=1)
        g = front_strength(field, lats)
        np.testing.assert_allclose(g[1:-1, 1:-1], 1 / (0.25 * 110.57), rtol=1e-6)
        self.assertAlmostEqual(float(g[50, 100]), 0.0362, places=4)

    def test_front_nan_next_to_land(self):
        lats = np.array(config.LATS)
        field = np.ones((len(config.LATS), len(config.LONS)))
        field[50, 100] = np.nan
        g = front_strength(field, lats)
        self.assertTrue(np.isnan(g[50, 101]))
        self.assertTrue(np.isnan(g[51, 100]))
        self.assertFalse(np.isnan(g[10, 10]))

    def test_subsurface_flag(self):
        thr = config.FRONT_THRESHOLD_C_PER_KM
        f50 = np.array([2 * thr, 2 * thr, 0.0, np.nan])
        f0 = np.array([0.0, 2 * thr, 0.0, 0.0])
        flag = subsurface_front_flag(f50, f0)
        self.assertEqual(flag[0], 1)
        self.assertEqual(flag[1], 0)
        self.assertEqual(flag[2], 0)
        self.assertTrue(np.isnan(flag[3]))


class TestGearAndConfidence(unittest.TestCase):
    def test_gear_depth_range(self):
        g0, g1 = gear_depth_range(LINEAR, DEPTHS, 20.0, 25.0)
        self.assertAlmostEqual(g0, 50.0)
        self.assertAlmostEqual(g1, 100.0)

    def test_gear_not_configured(self):
        self.assertEqual(gear_depth_range(LINEAR, DEPTHS, None, None), (None, None))

    def test_confidence(self):
        c = confidence_field([10.0], [70.0], [{"lat": 10.0, "lon": 70.0}])
        self.assertAlmostEqual(float(c[0, 0]), 1.0)
        self.assertIsNone(confidence_field([10.0], [70.0], []))
        self.assertEqual(confidence_level(0.7), "high")
        self.assertEqual(confidence_level(0.4), "medium")
        self.assertEqual(confidence_level(0.1), "low")
        self.assertEqual(confidence_level(None), "not_available")


if __name__ == "__main__":
    unittest.main()
