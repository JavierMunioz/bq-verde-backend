import asyncio
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient

# Configuración de conexión a MongoDB
MONGO_DETAILS = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.bqverde

# Colecciones de la base de datos
user_collection = database.get_collection("users")
ticket_collection = database.get_collection("ticket")
counters_collection = database.get_collection("counters")

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
    """
    Crea un usuario administrador predeterminado si no existe.
    """
    username = "admin"
    password = "password123"  # Cambiar en producción
    email = "admin@example.com"

    hashed_password = pwd_context.hash(password)
    user_data = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password
    }

    existing = await user_collection.find_one({"username": username})
    if existing:
        print("Admin ya existe")
    else:
        result = await user_collection.insert_one(user_data)
        print(f"Admin creado con ID: {result.inserted_id}")

if __name__ == "__main__":
    asyncio.run(create_admin())