"""Unit tests for the scoring functions. Pure logic, no I/O."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.schemas.weather import WeatherMeans
from app.services.scoring import (
    score_cloud,
    score_components,
    score_humidity,
    score_temperature,
    score_wind,
    weighted_total,
)


def test_temperature_anchor_at_24c_is_full_marks():
    assert score_temperature(24.0) == 10.0


def test_temperature_decreases_one_per_degree_off():
    assert score_temperature(25.0) == 9.0
    assert score_temperature(23.0) == 9.0
    assert score_temperature(20.0) == 6.0
    assert score_temperature(34.0) == 0.0


def test_temperature_clamps_at_zero():
    assert score_temperature(-10.0) == 0.0
    assert score_temperature(50.0) == 0.0


def test_wind_zero_is_full_marks():
    assert score_wind(0.0) == 10.0


def test_wind_decreases_with_speed():
    assert score_wind(25.0) == 5.0
    assert score_wind(50.0) == 0.0
    assert score_wind(75.0) == 0.0


def test_humidity_anchor_at_50pct():
    assert score_humidity(50.0) == 10.0


def test_humidity_extremes_score_zero():
    assert score_humidity(0.0) == 0.0
    assert score_humidity(100.0) == 0.0


def test_humidity_symmetric():
    assert score_humidity(40.0) == score_humidity(60.0)
    assert score_humidity(25.0) == 5.0


def test_cloud_anchor_at_25pct():
    assert score_cloud(25.0) == 10.0


def test_cloud_extremes_score_zero():
    assert score_cloud(0.0) == 0.0
    assert score_cloud(100.0) == 0.0


def test_cloud_asymmetry():
    """Linear up to 25%, then linear down to 100%. Different slopes."""
    assert score_cloud(12.5) == 5.0
    assert score_cloud(62.5) == pytest.approx(5.0, abs=0.01)


def test_weighted_total_ideal_day():
    perfect = WeatherMeans(
        temperature_c=24.0, wind_speed_kmh=0.0, relative_humidity_pct=50.0, cloud_cover_pct=25.0
    )
    components = score_components(perfect)
    assert weighted_total(components, Settings()) == 10.0


def test_weighted_total_worst_day():
    worst = WeatherMeans(
        temperature_c=-30.0, wind_speed_kmh=200.0, relative_humidity_pct=0.0, cloud_cover_pct=0.0
    )
    components = score_components(worst)
    assert weighted_total(components, Settings()) == 0.0


def test_weights_sum_to_one():
    s = Settings()
    total = s.weight_temperature + s.weight_wind + s.weight_humidity + s.weight_cloud
    assert total == pytest.approx(1.0, abs=1e-9)
