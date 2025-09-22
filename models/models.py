from pydantic import BaseModel, Field
from pydantic_core import core_schema
from typing import Any, Optional, List
from bson import ObjectId
from datetime import datetime

# ========================
# PyObjectId para Pydantic v2 (igual que tú lo tienes)
# ========================
class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Any) -> dict:
        json_schema = handler(core_schema)
        json_schema.update(type="string", example="507f1f77bcf86cd799439011")
        return json_schema

    @classmethod
    def validate(cls, value: Any) -> str:
        if isinstance(value, ObjectId):
            return str(value)
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return str(ObjectId(value))


# ========================
# Modelo Document
# ========================
class DocumentBase(BaseModel):
    name: str
    document_url: str
    description: str
    autor: str
    date_disponibility: datetime


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    document_url: Optional[str] = None


class DocumentInDB(DocumentBase):
    id: PyObjectId = Field(alias="_id")  # ← Usa PyObjectId, no str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# ========================
# Modelo News (¡CATEGORÍA COMO STR!)
# ========================
class NewsBase(BaseModel):
    title: str
    category: str  # ← ¡Aquí! Solo string, sin ObjectId, sin dolor
    content: str
    img_url: Optional[str] = None


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None  # ← Sigue siendo str
    content: Optional[str] = None
    img_url: Optional[str] = None


class NewsInDB(NewsBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }


# ========================
# Modelo Station
# ========================
class StationBase(BaseModel):
    name: str
    lon: int = Field(..., ge=-180, le=180, description="Longitud entre -180 y 180")
    lat: int = Field(..., ge=-90, le=90, description="Latitud entre -90 y 90")
    charts_permited: List[str]  # ← Lista de strings (nombres o IDs de gráficos permitidos)


class StationCreate(StationBase):
    pass


class StationUpdate(BaseModel):
    name: Optional[str] = None
    lon: Optional[int] = None
    lat: Optional[int] = None
    charts_permited: Optional[List[str]] = None


class StationInDB(StationBase):
    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }