# main.py
from scripts.create_img import save_base64_image
from scripts.create_doc import save_base64_document
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from models.models import *
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import os
import asyncio
from uvicorn.config import Config
from uvicorn.server import Server

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="Sistema de News & Documents")

# Middleware para limitar tamaño de subidas (50 MB)
class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int = 50 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_upload_size:
            return JSONResponse(
                status_code=413,
                content={"detail": "File too large (max 50 MB)"},
            )
        return await call_next(request)

app.add_middleware(LimitUploadSizeMiddleware)

# Servir archivos estáticos (imágenes y documentos)
os.makedirs("uploads/news", exist_ok=True)
os.makedirs("uploads/documents", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de autenticación
SECRET_KEY = os.getenv("SECRET_KEY", "una-clave-secreta-muy-larga-y-segura-1234567890")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Conexión a MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client["bqverde"]

# Colecciones
user_collection = db["users"]
news_collection = db["news"]
document_collection = db["documents"]
station_collection = db["stations"]

# === UTILIDADES DE AUTENTICACIÓN ===

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await user_collection.find_one({"username": username})
    if user is None:
        raise credentials_exception
    return user

# === ENDPOINTS DE AUTENTICACIÓN ===

@app.post("/login", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await user_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# === ENDPOINTS DE NOTICIAS ===

@app.post("/news", response_model=NewsInDB, status_code=status.HTTP_201_CREATED)
async def create_news(news: NewsCreate, current_user: dict = Depends(get_current_user)):
    news_dict = news.dict()

    # Procesar imagen si se envía en base64
    if news_dict.get("img_url"):
        try:
            image_url = save_base64_image(news_dict["img_url"])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error saving image: {str(e)}")
        news_dict["img_url"] = image_url
    else:
        news_dict["img_url"] = None

    now = datetime.utcnow()
    news_dict["created_at"] = now
    news_dict["updated_at"] = now

    result = await news_collection.insert_one(news_dict)
    news_dict["_id"] = str(result.inserted_id)

    # Renombrar imagen con el ID del documento (mejor gestión de archivos)
    if news_dict["img_url"]:
        old_path = f".{news_dict['img_url']}"
        extension = Path(old_path).suffix
        new_filename = f"{news_dict['_id']}{extension}"
        new_path = Path("uploads/news") / new_filename

        try:
            os.rename(old_path, new_path)
            final_url = f"/uploads/news/{new_filename}"
            await news_collection.update_one(
                {"_id": result.inserted_id},
                {"$set": {"img_url": final_url}}
            )
            news_dict["img_url"] = final_url
        except Exception as e:
            print(f"Advertencia: no se pudo renombrar la imagen: {e}")

    return NewsInDB(**news_dict)

@app.get("/news", response_model=List[NewsInDB])
async def list_news(category: Optional[str] = None):
    query = {"category": category} if category else {}
    news_list = []
    async for n in news_collection.find(query).sort("created_at", -1):
        n["_id"] = str(n["_id"])
        news_list.append(NewsInDB(**n))
    return news_list

@app.get("/news/{news_id}", response_model=NewsInDB)
async def get_news(news_id: str):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=400, detail="Invalid news ID")
    news = await news_collection.find_one({"_id": ObjectId(news_id)})
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    news["_id"] = str(news["_id"])
    return NewsInDB(**news)

@app.put("/news/{news_id}", response_model=NewsInDB)
async def update_news(
    news_id: str,
    news_update: NewsUpdate,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=400, detail="Invalid news ID")

    existing = await news_collection.find_one({"_id": ObjectId(news_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="News not found")

    update_data = {k: v for k, v in news_update.dict(exclude_unset=True).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Manejo de nueva imagen
    if "img_url" in update_data and update_data["img_url"]:
        base64_str = update_data["img_url"]
        try:
            new_image_url = save_base64_image(base64_str)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error saving image: {str(e)}")

        # Eliminar imagen anterior
        old_url = existing.get("img_url")
        if old_url and os.path.exists(f".{old_url}"):
            os.remove(f".{old_url}")

        # Renombrar nueva imagen con ID del documento
        old_path = f".{new_image_url}"
        ext = Path(old_path).suffix
        new_filename = f"{news_id}{ext}"
        new_path = Path("uploads/news") / new_filename
        try:
            os.rename(old_path, new_path)
            update_data["img_url"] = f"/uploads/news/{new_filename}"
        except Exception as e:
            update_data["img_url"] = new_image_url  # fallback

    update_data["updated_at"] = datetime.utcnow()

    await news_collection.update_one({"_id": ObjectId(news_id)}, {"$set": update_data})
    updated = await news_collection.find_one({"_id": ObjectId(news_id)})
    updated["_id"] = str(updated["_id"])
    return NewsInDB(**updated)

@app.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(news_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=400, detail="Invalid news ID")
    news = await news_collection.find_one({"_id": ObjectId(news_id)})
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    if news.get("img_url") and os.path.exists(f".{news['img_url']}"):
        os.remove(f".{news['img_url']}")

    await news_collection.delete_one({"_id": ObjectId(news_id)})

# === ENDPOINTS DE DOCUMENTOS ===

@app.post("/documents", response_model=DocumentInDB, status_code=status.HTTP_201_CREATED)
async def create_document(doc: DocumentCreate, current_user: dict = Depends(get_current_user)):
    doc_dict = doc.dict()

    if not doc_dict.get("document_url", "").startswith(("data:application/", "data:text/")):
        raise HTTPException(
            status_code=400,
            detail="document_url must be a base64 string with 'data:application/...' or 'data:text/...' prefix"
        )

    try:
        doc_dict["document_url"] = save_base64_document(doc_dict["document_url"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid document: {str(e)}")

    doc_dict["created_at"] = datetime.utcnow()
    result = await document_collection.insert_one(doc_dict)
    doc_dict["_id"] = str(result.inserted_id)
    return DocumentInDB(**doc_dict)

@app.get("/documents", response_model=List[DocumentInDB])
async def list_documents():
    docs = []
    async for d in document_collection.find().sort("name", 1):
        d["_id"] = str(d["_id"])
        docs.append(DocumentInDB(**d))
    return docs

@app.get("/documents/{doc_id}", response_model=DocumentInDB)
async def get_document(doc_id: str):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await document_collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc["_id"] = str(doc["_id"])
    return DocumentInDB(**doc)

@app.put("/documents/{doc_id}", response_model=DocumentInDB)
async def update_document(
    doc_id: str,
    doc_update: DocumentUpdate,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    update_data = {k: v for k, v in doc_update.dict(exclude_unset=True).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await document_collection.update_one({"_id": ObjectId(doc_id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    updated = await document_collection.find_one({"_id": ObjectId(doc_id)})
    updated["_id"] = str(updated["_id"])
    return DocumentInDB(**updated)

@app.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    await document_collection.delete_one({"_id": ObjectId(doc_id)})

# === ENDPOINTS DE ESTACIONES ===

@app.post("/stations", response_model=StationInDB, status_code=status.HTTP_201_CREATED)
async def create_station(station: StationCreate, current_user: dict = Depends(get_current_user)):
    station_dict = station.dict()
    station_dict["created_at"] = datetime.utcnow()
    result = await station_collection.insert_one(station_dict)
    station_dict["_id"] = str(result.inserted_id)
    return StationInDB(**station_dict)

@app.get("/stations", response_model=List[StationInDB])
async def list_stations():
    stations = []
    async for s in station_collection.find().sort("name", 1):
        s["_id"] = str(s["_id"])
        stations.append(StationInDB(**s))
    return stations

@app.get("/stations/{station_id}", response_model=StationInDB)
async def get_station(station_id: str):
    if not ObjectId.is_valid(station_id):
        raise HTTPException(status_code=400, detail="Invalid station ID")
    station = await station_collection.find_one({"_id": ObjectId(station_id)})
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    station["_id"] = str(station["_id"])
    return StationInDB(**station)

@app.put("/stations/{station_id}", response_model=StationInDB)
async def update_station(
    station_id: str,
    station_update: StationUpdate,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(station_id):
        raise HTTPException(status_code=400, detail="Invalid station ID")

    update_data = {k: v for k, v in station_update.dict(exclude_unset=True).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await station_collection.update_one({"_id": ObjectId(station_id)}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Station not found")

    updated = await station_collection.find_one({"_id": ObjectId(station_id)})
    updated["_id"] = str(updated["_id"])
    return StationInDB(**updated)

@app.delete("/stations/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_station(station_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(station_id):
        raise HTTPException(status_code=400, detail="Invalid station ID")
    await station_collection.delete_one({"_id": ObjectId(station_id)})

# === ENDPOINTS AUXILIARES ===

@app.post("/init-admin", include_in_schema=False)
async def init_admin():
    """Crea un usuario administrador para desarrollo."""
    if await user_collection.find_one({"username": "admin"}):
        return {"message": "Admin user already exists"}
    hashed_pw = get_password_hash("admin123")
    await user_collection.insert_one({
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": hashed_pw,
        "is_admin": True
    })
    return {"message": "Admin created (email: admin@example.com, password: admin123)"}

@app.post("/verify", response_model=dict)
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verifica la validez del token JWT (útil para integración con frontend SSR)."""
    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "is_admin": current_user.get("is_admin", False),
        "message": "Token válido"
    }

# === EJECUCIÓN ===

async def main():
    config = Config(app=app, host="0.0.0.0", port=8000, reload=True)
    server = Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())