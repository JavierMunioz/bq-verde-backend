import asyncio
from passlib.context import CryptContext
# database.py
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DETAILS = "mongodb://localhost:27017"  # Cambia si usas Atlas u otro host

client = AsyncIOMotorClient(MONGO_DETAILS)

database = client.bqverde  # Nombre de tu base de datos

# Colección de ejemplo
user_collection = database.get_collection("users")
ticket_collection = database.get_collection("ticket")
counters_collection = database.get_collection("counters")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
    username = "admin"
    password = "password123"  # Cambia esto
    email = "admin@example.com"

    hashed_password = pwd_context.hash(password)

    user_data = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password
    }

    # Verificar si ya existe
    existing = await user_collection.find_one({"username": username})
    if existing:
        print("Admin ya existe")
    else:
        result = await user_collection.insert_one(user_data)
        print(f"Admin creado con ID: {result.inserted_id}")

# Ejecutar
if __name__ == "__main__":
    asyncio.run(create_admin())