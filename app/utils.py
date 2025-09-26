import os
import io
import time
import hashlib
from typing import Optional, Tuple, Dict, Any, List
from fastapi import UploadFile, HTTPException
from PIL import Image, ExifTags

# Validation config 
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}  # now supports PNG, GIF
MAX_FILE_MB = 10

def validate_file(file: UploadFile, content: bytes):
    """Validate presence, extension whitelist, size, and that the bytes are a real image."""
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded. Please upload a JPG/JPEG/PNG/GIF file.")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type. Allowed: JPG/JPEG/PNG/GIF.")

    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_FILE_MB}MB.")

    # Verify the bytes decode to an image (defends against renamed non-images)
    try:
        with Image.open(io.BytesIO(content)) as im:
            im.verify()  # quick structural check
    except Exception:
        raise HTTPException(status_code=415, detail="Uploaded file is not a valid image.")

    return True

# Text preprocessing 
def preprocess_text(text: str) -> str:
    """Light cleanup: normalize whitespace, strip zero-width chars."""
    if not text:
        return ""
    # Remove zero-width spaces
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    # Normalize whitespace/newlines
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join([ln for ln in lines if ln])           # drop empty lines
    text = " ".join(text.split())                          # collapse spaces
    return text.strip()

# Image metadata extraction 
def extract_image_metadata(content: bytes) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    with Image.open(io.BytesIO(content)) as im:
        meta["format"] = im.format
        meta["mode"] = im.mode
        meta["width"], meta["height"] = im.size
        # Try EXIF if present
        exif_dict = {}
        try:
            raw_exif = im._getexif()  # type: ignore[attr-defined]
            if raw_exif:
                for k, v in raw_exif.items():
                    tag = ExifTags.TAGS.get(k, str(k))
                    # avoid dumping huge binary fields
                    if isinstance(v, (bytes, bytearray)):
                        continue
                    exif_dict[tag] = v
        except Exception:
            pass
        if exif_dict:
            # include a small subset commonly useful
            for k in ("DateTime", "Make", "Model", "Orientation"):
                if k in exif_dict:
                    meta[k] = exif_dict[k]
    return meta

# Cache for identical images 
def _hash_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

class SimpleLRUCache:
    """Very small in-memory cache (per instance) to skip repeated OCR on identical images."""
    def __init__(self, maxsize: int = 256):
        self.maxsize = maxsize
        self._data: Dict[str, Tuple[float, Dict[str, Any]]] = {}  # key -> (ts, payload)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        item = self._data.get(key)
        if item:
            # refresh LRU
            ts, payload = item
            self._data[key] = (time.time(), payload)
            return payload
        return None

    def set(self, key: str, payload: Dict[str, Any]):
        if len(self._data) >= self.maxsize:
            # evict oldest
            oldest_key = min(self._data.items(), key=lambda kv: kv[1][0])[0]
            self._data.pop(oldest_key, None)
        self._data[key] = (time.time(), payload)

# Basic rate limiter (per instance) 
class RateLimiter:
    """Token-bucket-ish limiter: N requests per window_secs per key (e.g., client IP)."""
    def __init__(self, limit: int = 60, window_secs: int = 60):
        self.limit = limit
        self.window = window_secs
        self._hits: Dict[str, List[float]] = {}

    def check(self, key: str):
        now = time.time()
        arr = self._hits.get(key, [])
        # drop old
        arr = [t for t in arr if now - t < self.window]
        if len(arr) >= self.limit:
            # remaining = 0
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        arr.append(now)
        self._hits[key] = arr

def cache_key_for(content: bytes, language_hints: Optional[List[str]], use_document_ocr: bool) -> str:
    return f"{_hash_bytes(content)}|{sorted(language_hints or [])}|{bool(use_document_ocr)}"
