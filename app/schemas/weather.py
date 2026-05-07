"""Pydantic schemas for the public API surface."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class WeatherMeans(BaseModel):
    """Period-averaged weather variables used as scoring inputs."""

    temperature_c: float = Field(..., description="Mean 2 m air temperature in degrees Celsius")
    wind_speed_kmh: float = Field(..., description="Mean 10 m wind speed in km/h")
    relative_humidity_pct: float = Field(..., ge=0, le=100, description="Mean relative humidity (%)")
    cloud_cover_pct: float = Field(..., ge=0, le=100, description="Mean total cloud cover (%)")


class ComponentScores(BaseModel):
    """Per-variable scores on a 0–10 scale before weighting."""

    temperature: float = Field(..., ge=0, le=10)
    wind: float = Field(..., ge=0, le=10)
    humidity: float = Field(..., ge=0, le=10)
    cloud: float = Field(..., ge=0, le=10)


class CityScore(BaseModel):
    city: str
    country: str
    latitude: float
    longitude: float
    weather: WeatherMeans
    components: ComponentScores
    score: float = Field(..., ge=0, le=10, description="Weighted total score (0–10)")
    rank: int = Field(..., ge=1)


class CitiesScoresResponse(BaseModel):
    start_date: date
    end_date: date
    hours_sampled: int = Field(..., ge=0, description="Number of hourly observations used")
    results: list[CityScore]
