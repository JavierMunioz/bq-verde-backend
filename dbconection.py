# database.py
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DETAILS = "mongodb://localhost:27017"  # Cambia si usas Atlas u otro host

client = AsyncIOMotorClient(MONGO_DETAILS)

db = client.bqverde  # Nombre de tu base de datos

user_collection = db["users"]
category_collection = db["categories"]
news_collection = db["news"]
document_collection = db["documents"]