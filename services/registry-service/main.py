from fastapi import FastAPI, Depends, Request, Response
from fastapi.responses import JSONResponse
from datetime import date
from typing import Optional
import sqlite3
import uuid

from database import get_db
from models import Crop, Soil, Emitter, Farm, FarmCreate, FarmUpdate, Plot, PlotCreate, PlotUpdate

app = FastAPI()

# --- מנגנון שגיאות RFC 9457 ---
class APIError(Exception):
    def __init__(self, status_code: int, code: str, title: str, detail: str):
        self.status_code = status_code
        self.code = code
        self.title = title
        self.detail = detail

@app.exception_handler(APIError)
def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": exc.title,
            "status": exc.status_code,
            "detail": exc.detail,
            "code": exc.code
        },
        media_type="application/problem+json"
    )

# --- API Endpoints ---
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/v1/crops", response_model=list[Crop])
def get_crops(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT id, name FROM crops").fetchall()
    return [dict(row) for row in rows]
    
@app.get("/v1/crops/{id}", response_model=Crop)
def get_crop(id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id, name FROM crops WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Crop not found")
    return dict(row)
# --- Soils ---
@app.get("/v1/soils", response_model=list[Soil])
def get_soils(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT id, name, available_water_mm_per_m FROM soils").fetchall()
    return [dict(row) for row in rows]

@app.get("/v1/soils/{id}", response_model=Soil)
def get_soil(id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id, name, available_water_mm_per_m FROM soils WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Soil not found")
    return dict(row)

# --- Emitters ---
@app.get("/v1/emitters", response_model=list[Emitter])
def get_emitters(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT id, name, flow_lph FROM emitters").fetchall()
    return [dict(row) for row in rows]

@app.get("/v1/emitters/{id}", response_model=Emitter)
def get_emitter(id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id, name, flow_lph FROM emitters WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Emitter not found")
    return dict(row)
# --- Farms ---
@app.post("/v1/farms", response_model=Farm, status_code=201)
def create_farm(farm_in: FarmCreate, db: sqlite3.Connection = Depends(get_db)):
    farm_id = str(uuid.uuid4())
    db.execute("INSERT INTO farms (id, name) VALUES (?, ?)", (farm_id, farm_in.name))
    db.commit()
    return {"id": farm_id, "name": farm_in.name}

@app.get("/v1/farms", response_model=list[Farm])
def get_farms(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT id, name FROM farms").fetchall()
    return [dict(row) for row in rows]
    
@app.get("/v1/farms/{id}", response_model=Farm)
def get_farm(id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id, name FROM farms WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Farm not found")
    return dict(row)
@app.patch("/v1/farms/{id}", response_model=Farm)
def update_farm(id: str, farm_in: FarmUpdate, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id, name FROM farms WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Farm not found")
    
    if farm_in.name is not None:
        db.execute("UPDATE farms SET name = ? WHERE id = ?", (farm_in.name, id))
        db.commit()
        return {"id": id, "name": farm_in.name}
        
    return dict(row)

@app.delete("/v1/farms/{id}", status_code=204, response_class=Response)
def delete_farm(id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id FROM farms WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Farm not found")
        
    plots_count = db.execute("SELECT COUNT(*) FROM plots WHERE farm_id = ?", (id,)).fetchone()[0]
    if plots_count > 0:
        raise APIError(409, "CONFLICT", "Conflict", "Delete a farm that still has plots")
        
    db.execute("DELETE FROM farms WHERE id = ?", (id,))
    db.commit()
@app.get("/v1/plots", response_model=list[Plot])
def get_plots(farm_id: Optional[str] = None, db: sqlite3.Connection = Depends(get_db)):
    if farm_id:
        rows = db.execute("SELECT * FROM plots WHERE farm_id = ?", (farm_id,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM plots").fetchall()
    return [dict(row) for row in rows]
        
@app.get("/v1/plots/{id}", response_model=Plot)
def get_plot(id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM plots WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Plot not found")
    return dict(row)    
@app.post("/v1/plots", response_model=Plot, status_code=201)
def create_plot(plot_in: PlotCreate, db: sqlite3.Connection = Depends(get_db)):
    # 1. בדיקה שהתאריך אינו בעתיד
    if plot_in.planting_date > date.today():
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Planting date cannot be in the future")
        
    # 2. בדיקה שהפריטים קיימים בקטלוגים
    if not db.execute("SELECT id FROM crops WHERE id = ?", (plot_in.crop_id,)).fetchone():
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Unknown crop")
    if not db.execute("SELECT id FROM soils WHERE id = ?", (plot_in.soil_id,)).fetchone():
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Unknown soil")
    if not db.execute("SELECT id FROM emitters WHERE id = ?", (plot_in.emitter_id,)).fetchone():
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Unknown emitter")
        
    # 3. בדיקה שאין חלקה באותו שם באותה חווה
    existing = db.execute("SELECT id FROM plots WHERE farm_id = ? AND name = ?", (plot_in.farm_id, plot_in.name)).fetchone()
    if existing:
        raise APIError(409, "CONFLICT", "Conflict", "Duplicate plot name on the same farm")
        
    # 4. שמירה במסד הנתונים
    plot_id = str(uuid.uuid4())
    try:
        db.execute("""
            INSERT INTO plots (
                id, farm_id, name, area_m2, crop_id, planting_date, soil_id, 
                row_spacing_m, emitter_spacing_m, emitter_id, lat, lon
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plot_id, plot_in.farm_id, plot_in.name, plot_in.area_m2, plot_in.crop_id, 
            plot_in.planting_date.isoformat(), plot_in.soil_id, plot_in.row_spacing_m, 
            plot_in.emitter_spacing_m, plot_in.emitter_id, plot_in.lat, plot_in.lon
        ))
        db.commit()
    except sqlite3.IntegrityError:
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Invalid farm_id or constraints")
        
    row = db.execute("SELECT * FROM plots WHERE id = ?", (plot_id,)).fetchone()
    return dict(row)
@app.patch("/v1/plots/{id}", response_model=Plot)
def update_plot(id: str, plot_in: PlotUpdate, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM plots WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Plot not found")
        
    update_data = plot_in.model_dump(exclude_unset=True)
    if not update_data:
        return dict(row)
        
    if "planting_date" in update_data and update_data["planting_date"] > date.today():
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Planting date cannot be in the future")
    if "crop_id" in update_data and not db.execute("SELECT id FROM crops WHERE id = ?", (update_data["crop_id"],)).fetchone():
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Unknown crop")
    if "soil_id" in update_data and not db.execute("SELECT id FROM soils WHERE id = ?", (update_data["soil_id"],)).fetchone():
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Unknown soil")
    if "emitter_id" in update_data and not db.execute("SELECT id FROM emitters WHERE id = ?", (update_data["emitter_id"],)).fetchone():
        raise APIError(422, "VALIDATION", "Unprocessable Entity", "Unknown emitter")
        
    if "name" in update_data:
        existing = db.execute("SELECT id FROM plots WHERE farm_id = ? AND name = ? AND id != ?", (row["farm_id"], update_data["name"], id)).fetchone()
        if existing:
            raise APIError(409, "CONFLICT", "Conflict", "Duplicate plot name on the same farm")
            
    set_clauses = []
    values = []
    for key, value in update_data.items():
        set_clauses.append(f"{key} = ?")
        values.append(value.isoformat() if isinstance(value, date) else value)
            
    values.append(id)
    db.execute(f"UPDATE plots SET {', '.join(set_clauses)} WHERE id = ?", values)
    db.commit()
    
    updated_row = db.execute("SELECT * FROM plots WHERE id = ?", (id,)).fetchone()
    return dict(updated_row)

@app.delete("/v1/plots/{id}", status_code=204, response_class=Response)
def delete_plot(id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT id FROM plots WHERE id = ?", (id,)).fetchone()
    if not row:
        raise APIError(404, "NOT_FOUND", "Not Found", "Plot not found")
        
    db.execute("DELETE FROM plots WHERE id = ?", (id,))
    db.commit()