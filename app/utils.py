# app/utils.py
from fastapi import File, UploadFile, HTTPException
import os

ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}
MAX_FILE_MB = 10

def validate_file(file: UploadFile, content: bytes):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded. Please upload a JPG/JPEG file.")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type. Only JPG/JPEG allowed.")

    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_FILE_MB}MB.")

    return True
