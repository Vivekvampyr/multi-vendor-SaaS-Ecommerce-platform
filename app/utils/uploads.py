import logging
import os
from pathlib import Path
import uuid
from fastapi import UploadFile

from app.core.exceptions import BadRequestException

logger = logging.getLogger(__name__)

# Base Upload Directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "products"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed image MIME types and extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def save_product_image_file(upload_file: UploadFile) -> str:
    """
    Validates and stores a product image to local storage.
    Returns the public relative URL path (e.g., /uploads/products/xyz.webp).
    """
    filename = upload_file.filename or ""
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequestException(
            message=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            details={"filename": filename, "extension": ext},
        )

    if upload_file.content_type and upload_file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise BadRequestException(
            message=f"Unsupported MIME type '{upload_file.content_type}'.",
            details={"content_type": upload_file.content_type},
        )

    content = await upload_file.read()
    if len(content) > MAX_FILE_SIZE:
        raise BadRequestException(
            message="File size exceeds maximum permitted limit of 5MB",
            details={"file_size_bytes": len(content), "max_allowed_bytes": MAX_FILE_SIZE},
        )

    unique_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = UPLOAD_DIR / unique_filename

    with open(target_path, "wb") as f:
        f.write(content)

    logger.info("Saved product image file to: %s", str(target_path))
    return f"/uploads/products/{unique_filename}"


def delete_product_image_file(image_url: str) -> bool:
    """
    Deletes the underlying image file from disk if it exists.
    """
    if not image_url.startswith("/uploads/products/"):
        return False

    filename = image_url.split("/uploads/products/")[-1]
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        try:
            os.remove(file_path)
            logger.info("Deleted physical image file: %s", str(file_path))
            return True
        except Exception as exc:
            logger.warning("Failed to delete physical file %s: %s", str(file_path), str(exc))
    return False
