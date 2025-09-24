import base64
import uuid
import os
from pathlib import Path

def save_base64_document(base64_str: str, folder: str = "uploads/documents") -> str:
    """
    Guarda un archivo codificado en base64 en el sistema de archivos.
    Devuelve la ruta relativa del archivo guardado.
    """
    if not base64_str or not isinstance(base64_str, str):
        raise ValueError("Invalid base64 string")

    if "," not in base64_str:
        raise ValueError("Missing comma in base64 string")

    header, encoded = base64_str.split(",", 1)

    if not header.startswith("data:application/"):
        raise ValueError("Invalid document header. Expected 'data:application/...'")

    mime_type = header.split(";")[0].replace("data:", "")
    extension = get_extension_from_mime(mime_type)
    if not extension:
        raise ValueError(f"Unsupported MIME type: {mime_type}")

    file_data = base64.b64decode(encoded, validate=True)

    if len(file_data) > 50 * 1024 * 1024:
        raise ValueError("Document too large (max 50MB)")

    Path(folder).mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{extension}"
    filepath = Path(folder) / filename

    with open(filepath, "wb") as f:
        f.write(file_data)

    if not filepath.exists():
        raise OSError(f"File not created: {filepath}")

    return f"/{folder}/{filename}"


def get_extension_from_mime(mime_type: str) -> str:
    """
    Devuelve la extensión de archivo correspondiente al tipo MIME dado.
    """
    mime_to_ext = {
        "application/pdf": "pdf",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.ms-powerpoint": "ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "application/rtf": "rtf",
        "text/plain": "txt",
        "application/vnd.oasis.opendocument.text": "odt",
        "application/vnd.oasis.opendocument.spreadsheet": "ods",
        "application/vnd.oasis.opendocument.presentation": "odp",
        "application/json": "json",
        "application/xml": "xml",
        "text/csv": "csv",
    }
    return mime_to_ext.get(mime_type, "")
