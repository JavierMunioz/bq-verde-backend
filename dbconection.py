# database.py
from motor.motor_asyncio import AsyncIOMotorClient

# URI de conexión a la base de datos MongoDB (local por defecto)
MONGO_DETAILS = "mongodb://localhost:27017"

# Cliente asíncrono para interactuar con MongoDB
client = AsyncIOMotorClient(MONGO_DETAILS)

# Base de datos utilizada por la aplicación
db = client.bqverde

# Colecciones de la base de datos, utilizadas para operaciones CRUD
user_collection = db["users"]          # Almacena información de los usuarios
news_collection = db["news"]           # Almacena noticias
document_collection = db["documents"]  # Almacena documentos generales