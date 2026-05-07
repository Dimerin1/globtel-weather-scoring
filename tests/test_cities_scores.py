"""Endpoint tests for /api/v1/cities-scores. Open-Meteo is mocked via respx."""

from __future__ import annotations

from datetime import date, timedelta

import httpx
import pytest
import respx

from app.core.cities import CITIES

ENDPOINT = "/api/v1/cities-scores"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def _stub_response(latitude: float, longitude: float) -> dict:
    """Return a fixed 24-hour stub. Same payload for every city so that the
    ranking depends only on coordinates if we vary the stub by lat/lon.
    Here we tweak temperature by latitude to produce a deterministic order."""
    base_temp = 24.0 - abs(latitude - 50.0) * 0.5
    return {
        "latitude": latitude,
        "longitude": longitude,
        "elevation": 100,
        "hourly": {
            "time": [f"2026-05-06T{h:02d}:00" for h in range(24)],
            "temperature_2m": [base_temp] * 24,
            "wind_speed_10m": [10.0] * 24,
            "relative_humidity_2m": [55.0] * 24,
            "cloud_cover": [30.0] * 24,
        },
        "hourly_units": {
            "temperature_2m": "°C",
            "wind_speed_10m": "km/h",
            "relative_humidity_2m": "%",
            "cloud_cover": "%",
        },
    }


@pytest.fixture
def mock_meteo():
    with respx.mock(assert_all_called=False) as router:
        def responder(request: httpx.Request) -> httpx.Response:
            params = dict(request.url.params)
            lat = float(params["latitude"])
            lon = float(params["longitude"])
            return httpx.Response(200, json=_stub_response(lat, lon))

        router.get(ARCHIVE_URL).mock(side_effect=responder)
        yield router


def test_defaults_to_yesterday(client, mock_meteo):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    response = client.get(ENDPOINT)

    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == yesterday
    assert data["end_date"] == yesterday
    assert data["hours_sampled"] == 24


def test_returns_all_six_cities_ranked(client, mock_meteo):
    response = client.get(ENDPOINT)
    assert response.status_code == 200
    results = response.json()["results"]

    assert len(results) == len(CITIES)
    assert {r["city"] for r in results} == {c.name for c in CITIES}

    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert [r["rank"] for r in results] == list(range(1, len(CITIES) + 1))


def test_response_shape(client, mock_meteo):
    response = client.get(ENDPOINT)
    body = response.json()["results"][0]

    assert {"city", "country", "latitude", "longitude", "weather", "components", "score", "rank"} <= body.keys()
    assert {"temperature_c", "wind_speed_kmh", "relative_humidity_pct", "cloud_cover_pct"} <= body["weather"].keys()
    assert {"temperature", "wind", "humidity", "cloud"} <= body["components"].keys()
    assert 0 <= body["score"] <= 10


def test_custom_date_range(client, mock_meteo):
    response = client.get(ENDPOINT, params={"start_date": "2026-01-01", "end_date": "2026-01-07"})
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2026-01-01"
    assert data["end_date"] == "2026-01-07"


def test_rejects_inverted_range(client, mock_meteo):
    response = client.get(ENDPOINT, params={"start_date": "2026-02-01", "end_date": "2026-01-01"})
    assert response.status_code == 400
    assert "start_date" in response.json()["detail"]


def test_rejects_future_end_date(client, mock_meteo):
    future = (date.today() + timedelta(days=2)).isoformat()
    response = client.get(ENDPOINT, params={"end_date": future})
    assert response.status_code == 400


def test_handles_upstream_error(client):
    with respx.mock() as router:
        router.get(ARCHIVE_URL).mock(return_value=httpx.Response(500))
        response = client.get(ENDPOINT)
    assert response.status_code == 502


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
