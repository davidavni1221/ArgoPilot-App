from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import date

# --- Catalogues ---
class Crop(BaseModel):
    id: str
    name: str

class Soil(BaseModel):
    id: str
    name: str
    available_water_mm_per_m: int

class Emitter(BaseModel):
    id: str
    name: str
    flow_lph: float

# --- Farms ---
class Farm(BaseModel):
    id: UUID
    name: str

class FarmCreate(BaseModel):
    name: str = Field(..., min_length=1)

class FarmUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)

# --- Plots ---
class Plot(BaseModel):
    id: UUID
    farm_id: str
    name: str
    area_m2: float
    crop_id: str
    planting_date: date
    soil_id: str
    row_spacing_m: float
    emitter_spacing_m: float
    emitter_id: str
    lat: float
    lon: float
        
class PlotCreate(BaseModel):
    farm_id: str
    name: str = Field(..., min_length=1)
    area_m2: float = Field(..., gt=0)
    crop_id: str
    planting_date: date
    soil_id: str
    row_spacing_m: float = Field(..., gt=0)
    emitter_spacing_m: float = Field(..., gt=0)
    emitter_id: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
        
class PlotUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    area_m2: Optional[float] = Field(None, gt=0)
    crop_id: Optional[str] = None
    planting_date: Optional[date] = None
    soil_id: Optional[str] = None
    row_spacing_m: Optional[float] = Field(None, gt=0)
    emitter_spacing_m: Optional[float] = Field(None, gt=0)
    emitter_id: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)