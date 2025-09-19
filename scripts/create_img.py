import base64
import uuid
from pathlib import Path

def save_base64_image(base64_str: str, folder: str = "uploads/news") -> str:
    """
    Guarda una imagen en base64 en el servidor y devuelve la ruta relativa.
    """
    if not base64_str:
        return None

    try:
        # Separar header de datos (si existe)
        if "," in base64_str:
            header, encoded = base64_str.split(",", 1)
            # Validar que sea imagen
            if not header.startswith("data:image/"):
                raise ValueError("Invalid image format")
        else:
            encoded = base64_str

        file_data = base64.b64decode(encoded)

        # Validar tamaño (ej: máximo 5MB)
        if len(file_data) > 50 * 1024 * 1024:
            raise ValueError("Image too large (max 5MB)")

        # Generar nombre único
        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = Path(folder) / filename

        # Crear carpeta si no existe
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "wb") as f:
            f.write(file_data)

        return f"/uploads/news/{filename}"

    except Exception as e:
        raise ValueError(f"Invalid image data: {str(e)}")