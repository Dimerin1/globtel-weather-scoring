"""City registry. Coordinates pinned to city centers for reproducible scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    name: str
    country: str
    latitude: float
    longitude: float


CITIES: tuple[City, ...] = (
    City("Warsaw", "Poland", 52.2297, 21.0122),
    City("Gdansk", "Poland", 54.3520, 18.6466),
    City("Berlin", "Germany", 52.5200, 13.4050),
    City("Krakow", "Poland", 50.0647, 19.9450),
    City("Nurnberg", "Germany", 49.4521, 11.0767),
    City("Munich", "Germany", 48.1351, 11.5820),
)
