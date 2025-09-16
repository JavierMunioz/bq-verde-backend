# main.py — TUS MODELOS ESTÁN BIEN. SOLO CORRIGIENDO ENDPOINTS.

from fastapi import FastAPI, HTTPException, status, Depends
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional
import os
from models.models import *  # Tus modelos están bien
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# === NUEVO: IMPORT MOTOR (¡ESTO ES LO ÚNICO QUE AÑADES!) ===
from motor.motor_asyncio import AsyncIOMotorClient

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="Sistema de News & Documents")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY", "una-clave-secreta-muy-larga-y-segura-1234567890")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# === CONEXIÓN A MONGODB (CAMBIADO A MOTOR ASÍNCRONO) ===
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client["bqverde"]

# Colecciones (¡SOLO LAS QUE USAMOS!)
user_collection = db["users"]
news_collection = db["news"]
document_collection = db["documents"]

# === FUNCIONES DE AUTENTICACIÓN ===

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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

# === ENDPOINTS ===

@app.post("/login", response_model=dict)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await user_collection.find_one({"email": form_data.username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# === NEWS ===

@app.post("/news", response_model=NewsInDB, status_code=status.HTTP_201_CREATED)
async def create_news(
    news: NewsCreate,
    current_user: dict = Depends(get_current_user)
):
    news_dict = news.dict()
    news_dict["created_at"] = news_dict["updated_at"] = datetime.utcnow()
    result = await news_collection.insert_one(news_dict)
    news_dict["_id"] = str(result.inserted_id)
    return NewsInDB(**news_dict)  # ← ¡YA ESTÁ CORREGIDO! (porque convertimos _id a str antes)

@app.get("/news", response_model=List[NewsInDB])
async def list_news(
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if category:
        query["category"] = category

    news_list = []
    async for n in news_collection.find(query).sort("created_at", -1):
        news_list.append(NewsInDB(**{**n, "_id": str(n["_id"])}))  # ← CORREGIDO
    return news_list

@app.get("/news/{news_id}", response_model=NewsInDB)
async def get_news(news_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=400, detail="Invalid news ID")
    news = await news_collection.find_one({"_id": ObjectId(news_id)})
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return NewsInDB(**{**news, "_id": str(news["_id"])})  # ← CORREGIDO

@app.put("/news/{news_id}", response_model=NewsInDB)
async def update_news(
    news_id: str,
    news_update: NewsUpdate,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=400, detail="Invalid news ID")

    update_data = {k: v for k, v in news_update.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = datetime.utcnow()

    result = await news_collection.update_one(
        {"_id": ObjectId(news_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="News not found")

    updated = await news_collection.find_one({"_id": ObjectId(news_id)})
    return NewsInDB(**{**updated, "_id": str(updated["_id"])})  # ← CORREGIDO

@app.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(news_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=400, detail="Invalid news ID")
    result = await news_collection.delete_one({"_id": ObjectId(news_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="News not found")

# === DOCUMENTS ===

@app.post("/documents", response_model=DocumentInDB, status_code=status.HTTP_201_CREATED)
async def create_document(
    doc: DocumentCreate,
    current_user: dict = Depends(get_current_user)
):
    doc_dict = doc.dict()
    result = await document_collection.insert_one(doc_dict)
    doc_dict["_id"] = str(result.inserted_id)
    return DocumentInDB(**doc_dict)  # ← ¡YA ESTÁ CORREGIDO! (porque convertimos _id a str antes)

@app.get("/documents", response_model=List[DocumentInDB])
async def list_documents(current_user: dict = Depends(get_current_user)):
    docs = []
    async for d in document_collection.find().sort("name", 1):
        docs.append(DocumentInDB(**{**d, "_id": str(d["_id"])}))  # ← CORREGIDO
    return docs

@app.get("/documents/{doc_id}", response_model=DocumentInDB)
async def get_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    doc = await document_collection.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentInDB(**{**doc, "_id": str(doc["_id"])})  # ← CORREGIDO

@app.put("/documents/{doc_id}", response_model=DocumentInDB)
async def update_document(
    doc_id: str,
    doc_update: DocumentUpdate,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")

    update_data = {k: v for k, v in doc_update.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = await document_collection.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    updated = await document_collection.find_one({"_id": ObjectId(doc_id)})
    return DocumentInDB(**{**updated, "_id": str(updated["_id"])})  # ← CORREGIDO

@app.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    result = await document_collection.delete_one({"_id": ObjectId(doc_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")

# === EJEMPLO DE USUARIO INICIAL (opcional, para pruebas) ===

@app.post("/init-admin", include_in_schema=False)
async def init_admin():
    user = await user_collection.find_one({"username": "admin"})
    if not user:
        hashed_pw = get_password_hash("admin123")
        await user_collection.insert_one({
            "username": "admin",
            "email": "admin@example.com",
            "hashed_password": hashed_pw,
            "is_admin": True
        })
        return {"message": "Admin user created with email=admin@example.com, password=admin123"}
    return {"message": "Admin user already exists"}

@app.post("/verify", response_model=dict)
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verifica que el JWT sea válido y devuelve los datos básicos del usuario.
    Se usa desde el middleware de Astro para proteger rutas SSR.
    """
    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "is_admin": current_user.get("is_admin", False),
        "message": "Token válido"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)