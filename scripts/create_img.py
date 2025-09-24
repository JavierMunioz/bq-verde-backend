import base64
import uuid
from pathlib import Path

def save_base64_image(base64_str: str, folder: str = "uploads/news") -> str:
    """
    Guarda una imagen codificada en base64 en el sistema de archivos.
    Espera un string con formato data:image/... y devuelve la ruta relativa del archivo guardado.
    """
    if not base64_str or not isinstance(base64_str, str):
        raise ValueError("Invalid base64 string")

    if "," not in base64_str:
        raise ValueError("Missing comma in base64 string")

    header, encoded = base64_str.split(",", 1)

    if not header.startswith("data:image/"):
        raise ValueError("Expected image data URI (data:image/...)")

    file_data = base64.b64decode(encoded, validate=True)

    if len(file_data) > 5 * 1024 * 1024:  # 5 MB límite
        raise ValueError("Image too large (max 5MB)")

    Path(folder).mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = Path(folder) / filename

    with open(filepath, "wb") as f:
        f.write(file_data)

    if not filepath.exists():
        raise OSError(f"File not created: {filepath}")

    return f"/{folder}/{filename}"