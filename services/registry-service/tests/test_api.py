from datetime import date, timedelta

import pytest

import database

DEMO_FARM = "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001"  # Demo cooperative: North block, East block
EAST_FARM = "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004"  # East farm: West block, Greenhouse
NORTH_BLOCK = "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002"

ALLOWED_CODES = {"VALIDATION", "NOT_FOUND", "CONFLICT", "UNAVAILABLE"}


def valid_plot(**overrides):
    payload = {
        "farm_id": DEMO_FARM,
        "name": "South block",
        "area_m2": 1000,
        "crop_id": "tomato",
        "planting_date": "2026-03-01",
        "soil_id": "loam",
        "row_spacing_m": 1.5,
        "emitter_spacing_m": 0.4,
        "emitter_id": "dripnet-pc-1.0",
        "lat": 31.25,
        "lon": 34.79,
    }
    payload.update(overrides)
    return payload


def assert_problem(response, status, code):
    """כל שגיאה חייבת להיות problem+json עם status ו-code תקינים (FR-1.4)."""
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == status
    assert body["code"] == code
    assert body["code"] in ALLOWED_CODES
    assert body["type"] == "about:blank"
    assert body["title"] and body["detail"]


# --- Health ---

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Catalogues (read only) ---

def test_list_crops(client):
    response = client.get("/v1/crops")
    assert response.status_code == 200
    assert response.json() == [
        {"id": "tomato", "name": "Tomato"},
        {"id": "bell-pepper", "name": "Bell pepper"},
    ]


def test_get_soil(client):
    response = client.get("/v1/soils/sand")
    assert response.status_code == 200
    assert response.json() == {"id": "sand", "name": "Sand", "available_water_mm_per_m": 83}


def test_get_emitter(client):
    response = client.get("/v1/emitters/dripnet-pc-1.0")
    assert response.status_code == 200
    assert response.json() == {"id": "dripnet-pc-1.0", "name": "DripNet PC", "flow_lph": 1.0}


def test_list_emitters_has_four(client):
    assert len(client.get("/v1/emitters").json()) == 4


def test_unknown_catalogue_item_is_404(client):
    assert_problem(client.get("/v1/crops/potato"), 404, "NOT_FOUND")


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_catalogue_other_methods_are_405(client, method):
    response = getattr(client, method)("/v1/crops/tomato")
    assert_problem(response, 405, "VALIDATION")


def test_unknown_route_is_404_problem(client):
    assert_problem(client.get("/v1/does-not-exist"), 404, "NOT_FOUND")


# --- Farms ---

def test_list_farms(client):
    response = client.get("/v1/farms")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_farm(client):
    response = client.post("/v1/farms", json={"name": "New farm"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "New farm"
    assert set(body) == {"id", "name"}


def test_create_farm_empty_name_is_422(client):
    assert_problem(client.post("/v1/farms", json={"name": ""}), 422, "VALIDATION")


def test_get_farm(client):
    response = client.get(f"/v1/farms/{DEMO_FARM}")
    assert response.status_code == 200
    assert response.json() == {"id": DEMO_FARM, "name": "Demo cooperative"}


def test_get_unknown_farm_is_404(client):
    assert_problem(client.get("/v1/farms/00000000-0000-0000-0000-000000000000"), 404, "NOT_FOUND")


def test_patch_farm_name(client):
    response = client.patch(f"/v1/farms/{EAST_FARM}", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json() == {"id": EAST_FARM, "name": "Renamed"}
    assert client.get(f"/v1/farms/{EAST_FARM}").json()["name"] == "Renamed"


def test_patch_farm_empty_body_changes_nothing(client):
    response = client.patch(f"/v1/farms/{EAST_FARM}", json={})
    assert response.status_code == 200
    assert response.json()["name"] == "East farm"


def test_patch_farm_null_name_is_422(client):
    assert_problem(client.patch(f"/v1/farms/{EAST_FARM}", json={"name": None}), 422, "VALIDATION")


def test_patch_unknown_farm_is_404(client):
    assert_problem(client.patch("/v1/farms/nope", json={"name": "x"}), 404, "NOT_FOUND")


def test_delete_farm_without_plots(client):
    created = client.post("/v1/farms", json={"name": "Empty farm"}).json()
    response = client.delete(f"/v1/farms/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/v1/farms/{created['id']}").status_code == 404


def test_delete_farm_with_plots_is_409(client):
    assert_problem(client.delete(f"/v1/farms/{DEMO_FARM}"), 409, "CONFLICT")
    assert client.get(f"/v1/farms/{DEMO_FARM}").status_code == 200


def test_delete_unknown_farm_is_404(client):
    assert_problem(client.delete("/v1/farms/nope"), 404, "NOT_FOUND")


# --- Plots: read ---

def test_list_all_plots(client):
    assert len(client.get("/v1/plots").json()) == 4


def test_list_plots_filtered_by_farm(client):
    plots = client.get(f"/v1/plots?farm_id={EAST_FARM}").json()
    assert len(plots) == 2
    assert {p["name"] for p in plots} == {"West block", "Greenhouse"}


def test_list_plots_unknown_farm_is_empty_list(client):
    response = client.get("/v1/plots?farm_id=nope")
    assert response.status_code == 200
    assert response.json() == []


def test_get_plot_has_only_listed_fields(client):
    response = client.get(f"/v1/plots/{NORTH_BLOCK}")
    assert response.status_code == 200
    assert set(response.json()) == {
        "id", "farm_id", "name", "area_m2", "crop_id", "planting_date", "soil_id",
        "row_spacing_m", "emitter_spacing_m", "emitter_id", "lat", "lon",
    }


def test_get_unknown_plot_is_404(client):
    assert_problem(client.get("/v1/plots/nope"), 404, "NOT_FOUND")


# --- Plots: create ---

def test_create_plot(client):
    response = client.post("/v1/plots", json=valid_plot())
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "South block"
    assert body["planting_date"] == "2026-03-01"
    assert "id" in body


def test_create_plot_today_is_allowed(client):
    response = client.post("/v1/plots", json=valid_plot(planting_date=date.today().isoformat()))
    assert response.status_code == 201


def test_create_plot_unknown_farm_is_422(client):
    assert_problem(client.post("/v1/plots", json=valid_plot(farm_id="nope")), 422, "VALIDATION")


def test_create_plot_unknown_crop_is_422(client):
    assert_problem(client.post("/v1/plots", json=valid_plot(crop_id="potato")), 422, "VALIDATION")


def test_create_plot_unknown_soil_is_422(client):
    assert_problem(client.post("/v1/plots", json=valid_plot(soil_id="mud")), 422, "VALIDATION")


def test_create_plot_unknown_emitter_is_422(client):
    assert_problem(client.post("/v1/plots", json=valid_plot(emitter_id="dripnet-pc-9.9")), 422, "VALIDATION")


@pytest.mark.parametrize("field", ["area_m2", "row_spacing_m", "emitter_spacing_m"])
@pytest.mark.parametrize("value", [0, -1])
def test_create_plot_non_positive_values_are_422(client, field, value):
    assert_problem(client.post("/v1/plots", json=valid_plot(**{field: value})), 422, "VALIDATION")


def test_create_plot_future_planting_date_is_422(client):
    future = (date.today() + timedelta(days=1)).isoformat()
    assert_problem(client.post("/v1/plots", json=valid_plot(planting_date=future)), 422, "VALIDATION")


@pytest.mark.parametrize("lat", [-90.1, 90.1])
def test_create_plot_latitude_out_of_range_is_422(client, lat):
    assert_problem(client.post("/v1/plots", json=valid_plot(lat=lat)), 422, "VALIDATION")


@pytest.mark.parametrize("lon", [-180.1, 180.1])
def test_create_plot_longitude_out_of_range_is_422(client, lon):
    assert_problem(client.post("/v1/plots", json=valid_plot(lon=lon)), 422, "VALIDATION")


def test_create_plot_latitude_bounds_are_allowed(client):
    assert client.post("/v1/plots", json=valid_plot(name="A", lat=90, lon=-180)).status_code == 201


def test_create_plot_duplicate_name_same_farm_is_409(client):
    assert_problem(client.post("/v1/plots", json=valid_plot(name="North block")), 409, "CONFLICT")


def test_create_plot_same_name_other_farm_is_allowed(client):
    response = client.post("/v1/plots", json=valid_plot(farm_id=EAST_FARM, name="North block"))
    assert response.status_code == 201


# --- Plots: update ---

def test_patch_plot_changes_only_given_fields(client):
    response = client.patch(f"/v1/plots/{NORTH_BLOCK}", json={"area_m2": 250})
    assert response.status_code == 200
    body = response.json()
    assert body["area_m2"] == 250
    assert body["name"] == "North block"
    assert body["crop_id"] == "tomato"


def test_patch_plot_empty_body_changes_nothing(client):
    response = client.patch(f"/v1/plots/{NORTH_BLOCK}", json={})
    assert response.status_code == 200
    assert response.json()["area_m2"] == 1000


@pytest.mark.parametrize("field", ["area_m2", "planting_date", "name", "lat", "crop_id"])
def test_patch_plot_null_field_is_422(client, field):
    assert_problem(client.patch(f"/v1/plots/{NORTH_BLOCK}", json={field: None}), 422, "VALIDATION")


def test_patch_plot_unknown_crop_is_422(client):
    assert_problem(client.patch(f"/v1/plots/{NORTH_BLOCK}", json={"crop_id": "potato"}), 422, "VALIDATION")


def test_patch_plot_future_date_is_422(client):
    future = (date.today() + timedelta(days=1)).isoformat()
    assert_problem(client.patch(f"/v1/plots/{NORTH_BLOCK}", json={"planting_date": future}), 422, "VALIDATION")


def test_patch_plot_duplicate_name_is_409(client):
    assert_problem(client.patch(f"/v1/plots/{NORTH_BLOCK}", json={"name": "East block"}), 409, "CONFLICT")


def test_patch_plot_same_name_keeps_itself_allowed(client):
    response = client.patch(f"/v1/plots/{NORTH_BLOCK}", json={"name": "North block"})
    assert response.status_code == 200


def test_patch_unknown_plot_is_404(client):
    assert_problem(client.patch("/v1/plots/nope", json={"area_m2": 5}), 404, "NOT_FOUND")


# --- Plots: delete ---

def test_delete_plot(client):
    assert client.delete(f"/v1/plots/{NORTH_BLOCK}").status_code == 204
    assert_problem(client.get(f"/v1/plots/{NORTH_BLOCK}"), 404, "NOT_FOUND")


def test_delete_unknown_plot_is_404(client):
    assert_problem(client.delete("/v1/plots/nope"), 404, "NOT_FOUND")


# --- Database foreign keys ---

def test_connection_from_get_db_enforces_foreign_keys(db_path):
    """בודק את החיבור שהשירות באמת משתמש בו (get_db), לא חיבור שהבדיקה פתחה בעצמה."""
    import sqlite3

    dependency = database.get_db()  # שומרים את המחולל, אחרת הוא נסגר והחיבור איתו
    conn = next(dependency)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO plots (id, farm_id, name, area_m2, crop_id, planting_date, soil_id, "
                "row_spacing_m, emitter_spacing_m, emitter_id, lat, lon) "
                "VALUES ('x', 'nope', 'n', 1, 'tomato', '2026-01-01', 'loam', 1, 1, 'dripnet-pc-1.0', 1, 1)"
            )
    finally:
        dependency.close()


# --- Database unavailable ---

def test_missing_database_returns_503_with_retry_after(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from main import app

    missing = tmp_path / "does-not-exist.db"
    monkeypatch.setattr(database, "DB_PATH", missing)
    with TestClient(app) as client:
        response = client.get("/v1/farms")
    assert_problem(response, 503, "UNAVAILABLE")
    assert response.headers["retry-after"] == "5"
    assert not missing.exists(), "a missing database must not be created silently"
