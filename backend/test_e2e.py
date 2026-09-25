import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_all():
    print("=== 1. Testing Metadata ===")
    r = client.get("/api/v1/metadata")
    assert r.status_code == 200, f"Metadata failed: {r.status_code}"
    meta = r.json()
    print("Metadata OK: depths =", len(meta["depths_m"]), "dates =", meta["dates"]["count"])

    print("=== 2. Testing Raster Field PNGs at various depths & dates ===")
    for d, z in [("2025-01-01", 0), ("2025-02-15", 100), ("2025-04-30", 1000)]:
        r = client.get(f"/api/v1/field.png?date={d}&depth={z}")
        assert r.status_code == 200, f"PNG failed: {r.status_code}"
        assert r.headers["content-type"] == "image/png"
        print(f"PNG ({d}, {z}m) OK: {len(r.content)} bytes")

    print("=== 3. Testing Ocean Sounding Profiles ===")
    ocean_points = [
        (15.0, 88.0, "Bay of Bengal"),
        (14.0, 65.0, "Arabian Sea"),
        (6.0, 78.0, "South of Sri Lanka"),
    ]
    for lat, lon, name in ocean_points:
        r = client.get(f"/api/v1/profile?lat={lat}&lon={lon}&date=2025-02-15")
        assert r.status_code == 200, f"Profile failed for {name}: {r.status_code}"
        data = r.json()
        print(f"{name} ({lat}, {lon}) -> Snapped: {data['snapped']}, Surface: {data['temperature_c'][0]}°C, 1000m: {data['temperature_c'][-1]}°C")

    print("=== 4. Testing Land Cell Masking (expecting 422) ===")
    land_points = [
        (20.0, 78.0, "Central India"),
        (24.0, 50.0, "Arabian Desert"),
    ]
    for lat, lon, name in land_points:
        r = client.get(f"/api/v1/profile?lat={lat}&lon={lon}&date=2025-02-15")
        assert r.status_code == 422, f"Expected 422 for {name}, got {r.status_code}"
        print(f"Land check for {name} ({lat}, {lon}) -> Handled gracefully with 422: {r.json()['error']}")

    print("=== 5. Testing Timeseries Queries ===")
    r = client.get("/api/v1/timeseries?lat=15.0&lon=88.0&depth=100")
    assert r.status_code == 200
    ts = r.json()
    print(f"Timeseries OK: {len(ts['dates'])} days, stats = {ts['stats']}")

    print("=== 6. Testing Basin Average ===")
    r = client.get("/api/v1/basin_average?depth=0")
    assert r.status_code == 200
    print(f"Basin Average OK: surface mean = {r.json()['stats']}")

    print("=== 7. Testing Frontend Build Serving ===")
    r = client.get("/")
    assert r.status_code == 200
    assert "OceanEmbed Viewer" in r.text or "root" in r.text
    print("Frontend static mount OK: HTTP 200")

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all()
