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

## 7. Automated test suite: 64 tests

- **Suggested:** the coding agent proposed one test for each rule in the spec, plus the failure cases for each rule.
- **Decided:** 64 tests, run with `uv run pytest`. Each test builds a fresh database from `seed_registry.sh`, so the real `registry.db` is never changed.
- **Why 64:** 64 is not a target. It is the number pytest reports when every rule is covered with its success case and its failure cases. Parametrized tests count once per value: for example, the four wrong HTTP methods on a catalogue route, and the six out-of-range latitude and longitude values, each count as separate tests.
- **Check:** the same tests were run against the original commit, and 23 failed. A test suite that passes on both the broken and the fixed code proves nothing, so this check matters.

Test list, grouped by area:

```text
Health
  test_health

Catalogues (read only)
  test_list_crops
  test_get_soil
  test_get_emitter
  test_list_emitters_has_four
  test_unknown_catalogue_item_is_404
  test_catalogue_other_methods_are_405[post, put, patch, delete]
  test_unknown_route_is_404_problem

Farms
  test_list_farms
  test_create_farm
  test_create_farm_empty_name_is_422
  test_get_farm
  test_get_unknown_farm_is_404
  test_patch_farm_name
  test_patch_farm_empty_body_changes_nothing
  test_patch_farm_null_name_is_422
  test_patch_unknown_farm_is_404
  test_delete_farm_without_plots
  test_delete_farm_with_plots_is_409
  test_delete_unknown_farm_is_404

Plots: read
  test_list_all_plots
  test_list_plots_filtered_by_farm
  test_list_plots_unknown_farm_is_empty_list
  test_get_plot_has_only_listed_fields
  test_get_unknown_plot_is_404

Plots: create
  test_create_plot
  test_create_plot_today_is_allowed
  test_create_plot_unknown_farm_is_422
  test_create_plot_unknown_crop_is_422
  test_create_plot_unknown_soil_is_422
  test_create_plot_unknown_emitter_is_422
  test_create_plot_non_positive_values_are_422[area, row spacing, emitter spacing, each with 0 and -1]
  test_create_plot_future_planting_date_is_422
  test_create_plot_latitude_out_of_range_is_422[-90.1, 90.1]
  test_create_plot_longitude_out_of_range_is_422[-180.1, 180.1]
  test_create_plot_latitude_bounds_are_allowed
  test_create_plot_duplicate_name_same_farm_is_409
  test_create_plot_same_name_other_farm_is_allowed

Plots: update
  test_patch_plot_changes_only_given_fields
  test_patch_plot_empty_body_changes_nothing
  test_patch_plot_null_field_is_422[area_m2, planting_date, name, lat, crop_id]
  test_patch_plot_unknown_crop_is_422
  test_patch_plot_future_date_is_422
  test_patch_plot_duplicate_name_is_409
  test_patch_plot_same_name_keeps_itself_allowed
  test_patch_unknown_plot_is_404

Plots: delete
  test_delete_plot
  test_delete_unknown_plot_is_404

Database
  test_connection_from_get_db_enforces_foreign_keys
  test_missing_database_returns_503_with_retry_after
```

## 8. Latency measurement scope

- **Suggested:** the coding agent first measured only the farm and plot GET routes (list and by id), because the spec's NFR-1.1 names "GET list and GET by id" without naming resources.
- **Decided:** measure every GET route, including the catalogues (crops, soils, emitters), in one run with the same conditions.
- **Why:** the NFR says "GET list and GET by id" without limiting it to farms and plots, and the catalogues are GET routes too. Measuring all ten routes in one run keeps the conditions identical, so the results can be compared directly.
- **Method:** 10 requests per second for 30 seconds per route (about 300 requests each), against a copy of the seed database, on a local machine, with a single sequential client. p95 is the value at position ceil(0.95 × n) in the sorted latencies.
- **Result:** every route has p95 between 11 ms and 13 ms, with 0 errors. The target is 100 ms.
- **Limits:** this is a local single-client test with 4 plots. It does not show behaviour under heavier load or a larger dataset.
