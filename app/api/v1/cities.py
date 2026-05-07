"""GET /api/v1/cities-scores."""

from __future__ import annotations

from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.cities import CITIES
from app.core.config import Settings, get_settings
from app.schemas.weather import CitiesScoresResponse, CityScore
from app.services import meteo, scoring

router = APIRouter()


def _yesterday() -> date:
    return date.today() - timedelta(days=1)


def _validate_range(start: date, end: date) -> None:
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )
    if end >= date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be in the past (Open-Meteo archive only covers historical data)",
        )


@router.get(
    "/cities-scores",
    response_model=CitiesScoresResponse,
    summary="Ranked weather scores for the configured cities",
)
async def cities_scores(
    start_date: date | None = Query(default=None, description="Defaults to yesterday (UTC)"),
    end_date: date | None = Query(default=None, description="Defaults to yesterday (UTC)"),
    settings: Settings = Depends(get_settings),
) -> CitiesScoresResponse:
    start = start_date or _yesterday()
    end = end_date or _yesterday()
    _validate_range(start, end)

    try:
        rows = await meteo.fetch_all(settings, CITIES, start, end)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Open-Meteo upstream error: {exc.__class__.__name__}",
        ) from exc
    except meteo.OpenMeteoError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    scored = []
    for row in rows:
        components = scoring.score_components(row.weather)
        total = scoring.weighted_total(components, settings)
        scored.append((row, components, total))

    scored.sort(key=lambda item: item[2], reverse=True)

    results = [
        CityScore(
            city=row.city.name,
            country=row.city.country,
            latitude=row.city.latitude,
            longitude=row.city.longitude,
            weather=row.weather,
            components=components,
            score=total,
            rank=idx + 1,
        )
        for idx, (row, components, total) in enumerate(scored)
    ]

    hours = rows[0].hours_sampled if rows else 0
    return CitiesScoresResponse(start_date=start, end_date=end, hours_sampled=hours, results=results)
