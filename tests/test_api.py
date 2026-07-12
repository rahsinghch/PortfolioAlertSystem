import io

from fastapi.testclient import TestClient
from api.app import app


def test_root_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "Portfolio Risk Alert API is running"


def test_list_samples_endpoint():
    client = TestClient(app)
    response = client.get("/samples")
    assert response.status_code == 200
    samples = response.json()["samples"]
    assert len(samples) >= 3


def test_analyze_sample_endpoint():
    client = TestClient(app)
    samples = client.get("/samples").json()["samples"]
    response = client.get(f"/samples/{samples[0]}")
    assert response.status_code == 200
    assert "severity" in response.json()


def test_analyze_sample_endpoint_unknown_name():
    client = TestClient(app)
    response = client.get("/samples/does-not-exist")
    assert response.status_code == 404


def test_analyze_upload_json():
    client = TestClient(app)
    payload = b'{"portfolio_id": "P1", "fund": "Fund 1", "holdings": [{"issuer": "A", "asset_type": "Equity", "sector": "Tech", "geography": "US", "market_value": 100, "weight_pct": 100}]}'
    response = client.post(
        "/analyze/upload",
        files={"file": ("portfolio.json", io.BytesIO(payload), "application/json")},
    )
    assert response.status_code == 200
    assert response.json()["portfolio_id"] == "P1"


def test_analyze_upload_csv():
    client = TestClient(app)
    csv_bytes = (
        b"issuer,asset_type,sector,geography,market_value,weight_pct\n"
        b"Asset A,Equity,Tech,US,100,60\n"
        b"Asset B,Bond,Fixed Income,US,100,40\n"
    )
    response = client.post(
        "/analyze/upload",
        files={"file": ("holdings.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"portfolio_id": "CSV-P1", "fund": "CSV Fund"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["portfolio_id"] == "CSV-P1"


def test_analyze_upload_rejects_unsupported_type():
    client = TestClient(app)
    response = client.post(
        "/analyze/upload",
        files={"file": ("holdings.txt", io.BytesIO(b"not supported"), "text/plain")},
    )
    assert response.status_code == 400
