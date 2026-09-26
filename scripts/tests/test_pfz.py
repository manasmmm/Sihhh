"""Unit tests for backend/pfz.py and backend/summary.py."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import config  # noqa: E402
from pfz import dms_to_decimal, load_pfz, nearest_ocean_cell, sector_info  # noqa: E402
from summary import build_summary  # noqa: E402


class TestDMS(unittest.TestCase):
    def test_spec_example(self):
        self.assertEqual(round(dms_to_decimal("15 31 59 N"), 4), 15.5331)

    def test_east_and_south_west(self):
        self.assertEqual(round(dms_to_decimal("73 19 44 E"), 4), 73.3289)
        self.assertLess(dms_to_decimal("10 0 0 S"), 0)
        self.assertLess(dms_to_decimal("10 0 0 W"), 0)

    def test_bad_value(self):
        with self.assertRaises(ValueError):
            dms_to_decimal("fifteen N")
        with self.assertRaises(ValueError):
            dms_to_decimal("15 75 0 N")


class TestLoader(unittest.TestCase):
    def test_goa_seed(self):
        rows, problems = load_pfz("GOA", "2026-09-25")
        self.assertEqual(len(rows), 7)
        self.assertEqual(problems, [])
        self.assertEqual(rows[0]["landmark"], "Chapora")
        self.assertAlmostEqual(rows[0]["lat"], 15.5331, places=4)
        self.assertEqual(rows[0]["sea_depth_from_m"], 59)

    def test_missing_sector_date(self):
        self.assertEqual(load_pfz("KERALA", "2026-09-25"), ([], []))

    def test_sector_lookup(self):
        self.assertEqual(sector_info("goa")["code"], "GOA")
        self.assertEqual(sector_info("South Tamil Nadu")["code"], "SOUTH_TAMIL_NADU")
        self.assertIsNone(sector_info("Atlantis"))
        self.assertEqual(len(config.PFZ_SECTORS), 14)


class TestNearestOcean(unittest.TestCase):
    def test_land_falls_back_to_neighbour(self):
        ocean = np.zeros((len(config.LATS), len(config.LONS)), dtype=bool)
        ocean[40, 113] = True  # 15.0N, 73.25E
        self.assertEqual(nearest_ocean_cell(15.0, 73.5, ocean), (40, 113))
        ocean[:] = False
        self.assertIsNone(nearest_ocean_cell(15.0, 73.5, ocean))


class TestSummary(unittest.TestCase):
    ROW = {"landmark": "Chapora", "direction": "SW", "bearing_deg": 261, "dist_from_km": 42,
           "dist_to_km": 47, "sea_depth_from_m": 59, "sea_depth_to_m": 64, "d20_m": 98.4,
           "mld_m": None, "subsurface_front": False, "confidence_level": "not_available",
           "valid_upto": "2026-09-26"}

    def test_english(self):
        t = build_summary(self.ROW, "en")
        self.assertIn("42–47 km SW of Chapora", t)
        self.assertIn("near 98 m", t)
        self.assertIn("mixed layer about not available.", t)
        self.assertNotIn("NaN", t)
        self.assertNotIn("None", t)
        self.assertLessEqual(len(t), config.FISHERMAN_MESSAGE_MAX_CHARS)

    def test_hindi(self):
        t = build_summary(self.ROW, "hi")
        self.assertIn("दक्षिण-पश्चिम", t)
        self.assertLessEqual(len(t), config.FISHERMAN_MESSAGE_MAX_CHARS)

    def test_species_sentence(self):
        sp = {"name": "Test fish", "t_min_c": 20, "t_max_c": 25, "configured": True}
        t = build_summary({**self.ROW, "gear_depth_from_m": 50, "gear_depth_to_m": 100}, "en", species=sp)
        self.assertIn("Suggested gear depth for Test fish: 50–100 m.", t)


if __name__ == "__main__":
    unittest.main()
