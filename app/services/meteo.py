"""Open-Meteo client. Async via httpx, parallelised across cities."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date

import httpx

from app.core.cities import City
from app.core.config import Settings
from app.schemas.weather import WeatherMeans

HOURLY_VARS = ("temperature_2m", "wind_speed_10m", "relative_humidity_2m", "cloud_cover")


class OpenMeteoError(RuntimeError):
    """Raised when Open-Meteo returns a malformed or unusable response."""


@dataclass(frozen=True)
class CityWeather:
    city: City
    weather: WeatherMeans
    hours_sampled: int


async def fetch_city_weather(
    client: httpx.AsyncClient,
    settings: Settings,
    city: City,
    start: date,
    end: date,
) -> CityWeather:
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_VARS),
        "wind_speed_unit": "kmh",
        "timezone": "UTC",
    }
    payload = await _get_with_retry(client, settings.open_meteo_base_url, params)
    return CityWeather(city=city, **_aggregate(payload))


async def _get_with_retry(
    client: httpx.AsyncClient, url: str, params: dict, attempts: int = 3
) -> dict:
    """Open-Meteo's free tier rate-limits at ~10 rps. Retry briefly on 429/5xx."""
    delay = 0.5
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await client.get(url, params=params)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < attempts - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
    raise last_exc or RuntimeError("retry loop exited unexpectedly")


def _aggregate(payload: dict) -> dict:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise OpenMeteoError("Response missing 'hourly' block")

    series = {var: hourly.get(var) or [] for var in HOURLY_VARS}
    times = hourly.get("time") or []

    samples = []
    for idx, _ in enumerate(times):
        row = [series[var][idx] if idx < len(series[var]) else None for var in HOURLY_VARS]
        if all(value is not None for value in row):
            samples.append(row)

    if not samples:
        raise OpenMeteoError("No usable hourly samples in response")

    means = [sum(col) / len(col) for col in zip(*samples)]
    weather = WeatherMeans(
        temperature_c=round(means[0], 2),
        wind_speed_kmh=round(means[1], 2),
        relative_humidity_pct=round(means[2], 2),
        cloud_cover_pct=round(means[3], 2),
    )
    return {"weather": weather, "hours_sampled": len(samples)}


async def fetch_all(
    settings: Settings, cities: tuple[City, ...], start: date, end: date
) -> list[CityWeather]:
    timeout = httpx.Timeout(settings.open_meteo_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [fetch_city_weather(client, settings, c, start, end) for c in cities]
        return await asyncio.gather(*tasks)
