import base64
import uuid
import os
from pathlib import Path

def save_base64_document(base64_str: str, folder: str = "uploads/documents") -> str:
    """
    Guarda un documento en base64 (con prefijo data:application/...) en disco.
    Devuelve la ruta relativa: /uploads/documents/xxx.ext

    Soporta: PDF, DOCX, XLSX, TXT, ODT, PPTX, etc.
    """
    if not base64_str or not isinstance(base64_str, str):
        raise ValueError("Invalid base64 string")

    try:
        # Separar header de datos
        if "," not in base64_str:
            raise ValueError("Missing comma in base64 string")

        header, encoded = base64_str.split(",", 1)

        # Validar que sea un tipo de documento
        if not header.startswith("data:application/"):
            raise ValueError(f"Invalid document header: {header}. Expected 'data:application/...'")

        # Extraer extensión a partir del MIME type
        mime_type = header.split(";")[0].replace("data:", "")
        extension = get_extension_from_mime(mime_type)
        if not extension:
            raise ValueError(f"Unsupported document MIME type: {mime_type}")

        # Decodificar base64
        file_data = base64.b64decode(encoded, validate=True)

        # Validar tamaño (ej: máximo 50MB)
        if len(file_data) > 50 * 1024 * 1024:
            raise ValueError("Document too large (max 50MB)")

        # Crear carpeta si no existe
        Path(folder).mkdir(parents=True, exist_ok=True)

        # Generar nombre único con extensión correcta
        filename = f"{uuid.uuid4().hex}.{extension}"
        filepath = Path(folder) / filename

        # Guardar archivo
        with open(filepath, "wb") as f:
            f.write(file_data)

        # Verificar que se creó
        if not filepath.exists():
            raise OSError(f"File not created: {filepath}")

        return f"/{folder}/{filename}"

    except Exception as e:
        raise ValueError(f"Failed to save document: {str(e)}")


def get_extension_from_mime(mime_type: str) -> str:
    """
    Mapea MIME types comunes a extensiones de archivo.
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