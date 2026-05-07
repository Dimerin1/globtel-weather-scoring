# Globtel Weather Scoring

Ranks six European cities by yesterday's weather, using hourly readings from the [Open-Meteo](https://open-meteo.com) historical archive and a weighted comfort score.

Built for the Globtel recruitment task. FastAPI on the back, a single editorial HTML page on the front, Docker for shipping.

## What's inside

- **API**: `GET /api/v1/cities-scores` returns a sorted list with weather data, component scores, and a weighted total.
- **UI**: `GET /` serves a single page with two date inputs, a button, and a ranked list. No build step, no framework.
- **Cities**: Warsaw, Gdansk, Berlin, Krakow, Nurnberg, Munich.
- **Default range**: yesterday (UTC). Custom ranges accepted as ISO dates.

## Quick start

### Docker (recommended)

```bash
docker compose up --build
```

Then open <http://localhost:8000>.

### Local

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. Interactive docs at `/docs`.

## API

### `GET /api/v1/cities-scores`

| Param        | Type    | Default     | Notes                                  |
| ------------ | ------- | ----------- | -------------------------------------- |
| `start_date` | `date`  | yesterday   | ISO 8601 (`YYYY-MM-DD`)                |
| `end_date`   | `date`  | yesterday   | ISO 8601, must be in the past          |

#### Example

```bash
curl 'http://localhost:8000/api/v1/cities-scores?start_date=2026-04-15&end_date=2026-04-15' | jq
```

#### Response shape

```json
{
  "start_date": "2026-04-15",
  "end_date": "2026-04-15",
  "hours_sampled": 24,
  "results": [
    {
      "rank": 1,
      "city": "Krakow",
      "country": "Poland",
      "latitude": 50.0647,
      "longitude": 19.945,
      "weather": {
        "temperature_c": 20.4,
        "wind_speed_kmh": 11.7,
        "relative_humidity_pct": 44.0,
        "cloud_cover_pct": 51.0
      },
      "components": {
        "temperature": 6.4,
        "wind": 7.66,
        "humidity": 8.8,
        "cloud": 6.53
      },
      "score": 7.14
    }
  ]
}
```

Errors: `400` for an inverted or future range, `502` if Open-Meteo is unhappy.

## Scoring

Hourly readings for the date range are averaged per city, then each variable is mapped onto a 0–10 scale and combined into a weighted total.

| Variable          | Best at | Score formula                          | Weight |
| ----------------- | ------- | -------------------------------------- | ------ |
| Temperature (°C)  | 24      | `max(0, 10 - abs(t - 24))`             | 35%    |
| Wind (km/h)       | 0       | `max(0, 10 - wind / 5)` (0 at 50 km/h) | 20%    |
| Humidity (%)      | 50      | `max(0, 10 - abs(h - 50) / 5)`         | 20%    |
| Cloud cover (%)   | 25      | linear up to 25, linear down to 100    | 25%    |

The wind anchor is the only piece of judgement: the spec only fixes the upper end (0 km/h = 10 points), so 50 km/h was picked as the lower anchor. That's Beaufort 7, the point where outdoor activity stops being pleasant. See [`app/services/scoring.py`](app/services/scoring.py).

## Project layout

```
app/
  api/v1/cities.py        GET /api/v1/cities-scores
  core/cities.py          City registry (name + coords)
  core/config.py          Settings, weights, env overrides
  schemas/weather.py      Pydantic response models
  services/meteo.py       Open-Meteo async client (httpx, parallel + retry)
  services/scoring.py     Pure scoring functions
  templates/index.html    Single-page UI (Jinja2)
  main.py                 App factory
tests/
  test_scoring.py         Unit tests for scoring math
  test_cities_scores.py   Endpoint tests with mocked upstream
Dockerfile, docker-compose.yml
requirements.txt          Runtime deps
requirements-dev.txt      + pytest, respx
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

22 tests covering the scoring math, response shape, validation, defaults, custom ranges, and upstream-error handling. Open-Meteo is mocked with `respx` so tests are offline and deterministic.

## Configuration

Override via env vars (or a `.env` file):

| Variable             | Default                                          |
| -------------------- | ------------------------------------------------ |
| `WEIGHT_TEMPERATURE` | `0.35`                                           |
| `WEIGHT_WIND`        | `0.20`                                           |
| `WEIGHT_HUMIDITY`    | `0.20`                                           |
| `WEIGHT_CLOUD`       | `0.25`                                           |
| `OPEN_METEO_BASE_URL`| `https://archive-api.open-meteo.com/v1/archive` |

## Notes

- Open-Meteo's archive lags about a day behind real time, so "yesterday" usually works, but "today" won't.
- The free tier rate-limits at roughly 10 req/sec. The client retries on 429 with exponential backoff.
- Hourly data is averaged before scoring, not scored per hour and averaged after. Both readings of the spec are valid; this one is simpler.

## Stack

FastAPI · Pydantic v2 · httpx · Jinja2 · pytest · respx · Docker · Fraunces + DM Sans.

Data from [Open-Meteo](https://open-meteo.com).
