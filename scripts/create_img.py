import base64
import uuid
import os
from pathlib import Path

def save_base64_image(base64_str: str, folder: str = "uploads/news") -> str:
    """
    Guarda una imagen en base64 (con prefijo data:image/...) en disco.
    Devuelve la ruta relativa: /uploads/news/xxx.jpg
    """
    if not base64_str or not isinstance(base64_str, str):
        raise ValueError("Invalid base64 string")

    try:
        # Separar header de datos
        if "," not in base64_str:
            raise ValueError("Missing comma in base64 string")

        header, encoded = base64_str.split(",", 1)

        # Validar que sea imagen
        if not header.startswith("data:image/"):
            raise ValueError(f"Invalid header: {header}")

        # Decodificar base64
        file_data = base64.b64decode(encoded, validate=True)  # ← validate=True evita basura

        # Validar tamaño (ej: máximo 5MB)
        if len(file_data) > 50 * 1024 * 1024:
            raise ValueError("Image too large (max 5MB)")

        # Crear carpeta si no existe
        Path(folder).mkdir(parents=True, exist_ok=True)

        # Generar nombre único
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = Path(folder) / filename

        # Guardar archivo
        with open(filepath, "wb") as f:
            f.write(file_data)

        # Verificar que se creó
        if not filepath.exists():
            raise OSError(f"File not created: {filepath}")

        return f"/{folder}/{filename}"

    except Exception as e:
        raise ValueError(f"Failed to save image: {str(e)}")