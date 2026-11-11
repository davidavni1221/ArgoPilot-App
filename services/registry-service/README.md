# registry-service

FastAPI service that stores farms, plots, and the read-only catalogues (crops, soils, emitters) for AgroPilot.

Data is kept in one SQLite file, `registry.db`, which is created by a seed script and is not tracked by git.

## Setup

Requirements: `uv`, and the `sqlite3` command-line tool (`sudo apt install sqlite3`).

```bash
uv sync
bash seed_registry.sh          # creates registry.db with 15 seed rows
```

Run the service:

```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

Check it: http://127.0.0.1:8000/health returns `{"status": "ok"}`. Interactive docs are at http://127.0.0.1:8000/docs.

Run the tests:

```bash
uv run pytest
```

The tests build a fresh database from the seed script for each test, so they never change `registry.db`.

## Endpoints

| Method | Path | Success |
|---|---|---|
| POST | `/v1/farms` | 201 |
| GET | `/v1/farms` | 200 |
| GET | `/v1/farms/{id}` | 200 |
| PATCH | `/v1/farms/{id}` | 200 |
| DELETE | `/v1/farms/{id}` | 204 |
| POST | `/v1/plots` | 201 |
| GET | `/v1/plots` (optional `?farm_id=`) | 200 |
| GET | `/v1/plots/{id}` | 200 |
| PATCH | `/v1/plots/{id}` | 200 |
| DELETE | `/v1/plots/{id}` | 204 |
| GET | `/v1/crops`, `/v1/crops/{id}` | 200 |
| GET | `/v1/soils`, `/v1/soils/{id}` | 200 |
| GET | `/v1/emitters`, `/v1/emitters/{id}` | 200 |

Catalogue routes are read-only. Any other method on them returns 405.

## Errors

Every error is `application/problem+json` (RFC 9457) with a `code` field, one of:

- `VALIDATION`: bad field, unknown crop/soil/emitter/farm, wrong method (422 or 405).
- `NOT_FOUND`: unknown id or route (404).
- `CONFLICT`: duplicate plot name in one farm, or deleting a farm that still has plots (409).
- `UNAVAILABLE`: database file missing or unusable (503, with `Retry-After: 5`).

Example:

```json
{
  "type": "about:blank",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": "Unknown emitter",
  "code": "VALIDATION"
}
```

## Performance

Measured at 10 requests per second for 30 seconds per endpoint (about 300 requests each), against a copy of the seed database, from a single local client, with 0 errors:

| Endpoint | p95 |
|---|---|
| GET /v1/farms | 11.1 ms |
| GET /v1/farms/{id} | 12.2 ms |
| GET /v1/plots | 12.8 ms |
| GET /v1/plots/{id} | 11.9 ms |
| GET /v1/crops | 10.9 ms |
| GET /v1/crops/{id} | 11.4 ms |
| GET /v1/soils | 12.1 ms |
| GET /v1/soils/{id} | 11.7 ms |
| GET /v1/emitters | 12.2 ms |
| GET /v1/emitters/{id} | 11.9 ms |

The target is p95 at or below 100 ms.

## Layout

- `main.py`: routes, validation rules, and error handling.
- `models.py`: request and response shapes.
- `database.py`: opens a database connection per request.
- `seed_registry.sh`: builds `registry.db` with the catalogues, two farms, and four plots.
- `tests/`: automated tests.
- `docs/judgment-log.md`: decisions taken during the build, and why.
