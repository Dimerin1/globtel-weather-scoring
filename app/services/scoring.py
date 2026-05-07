"""Pure scoring functions. No I/O, fully deterministic, easy to unit-test."""

from __future__ import annotations

from app.core.config import Settings
from app.schemas.weather import ComponentScores, WeatherMeans

WIND_ZERO_KMH: float = 50.0
"""Wind speed at which the wind score reaches 0.

Open-Meteo returns 10 m wind in km/h by default. The recruitment spec only
fixes the upper anchor (0 km/h → 10 points), so we choose 50 km/h as the
lower anchor: ~Beaufort 7 (near-gale), where outdoor activity stops being
pleasant. Documented in the README."""


def score_temperature(temperature_c: float) -> float:
    return max(0.0, 10.0 - abs(temperature_c - 24.0))


def score_wind(wind_speed_kmh: float) -> float:
    if wind_speed_kmh <= 0:
        return 10.0
    return max(0.0, 10.0 - (wind_speed_kmh / WIND_ZERO_KMH) * 10.0)


def score_humidity(humidity_pct: float) -> float:
    """50 % is best (10 pts). 0 % and 100 % both give 0. Linear on each side."""
    return max(0.0, 10.0 - abs(humidity_pct - 50.0) / 5.0)


def score_cloud(cloud_pct: float) -> float:
    """Asymmetric peak at 25 %. 0 % and 100 % both give 0. Linear on each side."""
    if cloud_pct <= 25.0:
        return (cloud_pct / 25.0) * 10.0
    return max(0.0, 10.0 - (cloud_pct - 25.0) / 7.5)


def score_components(weather: WeatherMeans) -> ComponentScores:
    return ComponentScores(
        temperature=round(score_temperature(weather.temperature_c), 4),
        wind=round(score_wind(weather.wind_speed_kmh), 4),
        humidity=round(score_humidity(weather.relative_humidity_pct), 4),
        cloud=round(score_cloud(weather.cloud_cover_pct), 4),
    )


def weighted_total(components: ComponentScores, settings: Settings) -> float:
    total = (
        components.temperature * settings.weight_temperature
        + components.wind * settings.weight_wind
        + components.humidity * settings.weight_humidity
        + components.cloud * settings.weight_cloud
    )
    return round(total, 4)
