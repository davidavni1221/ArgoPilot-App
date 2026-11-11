# Judgment log

Each entry records a suggestion from the coding agent, what was decided, and why.

---

## 1. Error code for a wrong HTTP method (405)

- **Suggested:** the coding agent proposed `VALIDATION` for 405 responses on the read-only catalogue routes.
- **Decided:** `VALIDATION`, with title `Method Not Allowed`.
- **Why:** the spec defines only four error codes (`VALIDATION`, `NOT_FOUND`, `CONFLICT`, `UNAVAILABLE`) and says nothing about 405. A wrong method is a bad request, so `VALIDATION` is the closest fit. The alternative, `NOT_FOUND`, would wrongly suggest that the resource does not exist.

## 2. Unknown `farm_id` when creating a plot

- **Suggested:** the coding agent first noticed that a plot with a non-existent `farm_id` was created successfully, because SQLite does not enforce foreign keys by default.
- **Decided:** check that the farm exists in the handler and return `422 VALIDATION` with `Unknown farm`. Also turn on `PRAGMA foreign_keys = ON` for every connection, so the database rejects the bad row even if the handler check is missing.
- **Why:** the spec lists an unknown farm among the bad fields, and bad fields return 422, not 404. A 404 would mean that the URL itself is missing, which is not the case here. Two layers (handler check and database constraint) protect the data.

## 3. Database unavailable

- **Suggested:** the coding agent wanted to return 503 with `Retry-After` when the database cannot be used.
- **Decided:** open the database with `mode=rw`, so a missing file fails instead of being created as an empty database. Map every `sqlite3.OperationalError` to `503 UNAVAILABLE` with `Retry-After: 5`.
- **Why:** without `mode=rw`, SQLite silently creates an empty file, and every later query fails with a confusing "no such table" error. The trade-off: mapping all `OperationalError`s also hides real SQL bugs as 503. The test suite must therefore keep catching SQL bugs through normal tests.

## 4. `null` in PATCH requests

- **Suggested:** the coding agent first treated `null` the same as "field not sent", which made the request return 200 without changing anything (farms) or fail with a 500 (plots).
- **Decided:** a `null` value for a field that is required returns `422 VALIDATION`. A request with no fields (`{}`) still returns 200 and changes nothing.
- **Why:** `null` is an invalid value, and hiding it hides the caller's mistake. The code uses `model_fields_set` to tell "field was sent as null" apart from "field was not sent".

## 5. Keep `registry.db` out of git

- **Suggested:** the coding agent proposed adding `registry.db` to `.gitignore` and removing it from git tracking.
- **Decided:** ignore the file, and make `seed_registry.sh` the single source of truth. Anyone who clones the repo runs the seed script to create the database.
- **Why:** the database is a binary file that changes on every seed run, so git history would fill with unreadable changes. The spec says the seed creates the database, so the script is the real definition of the data.

## 6. Remove the `rich` dependency

- **Suggested:** the coding agent noticed that `rich` was installed but never imported.
- **Decided:** remove it with `uv remove rich`.
- **Why:** the spec says to delete every feature the task does not list. Colour output is not part of the API, and the service works the same without it.
