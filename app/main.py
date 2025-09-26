# app/main.py (only the relevant additions/changes shown)
import time
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from .schemas import OCRRequestGCS, OCRResponse, SimpleOCRResponse, SimpleOCRPlusResponse
from .ocr import run_ocr_bytes, run_ocr_gcs, average_confidence
from .utils import validate_file, preprocess_text, extract_image_metadata, SimpleLRUCache, RateLimiter, cache_key_for

app = FastAPI(title="GCP Vision OCR API", version="1.3.0")

# Per-instance cache & rate limiter (Cloud Run note: not shared across instances)
CACHE = SimpleLRUCache(maxsize=256)
LIMITER = RateLimiter(limit=60, window_secs=60)   # 60 req/min per client key

def _client_key(req: Request) -> str:
    # Prefer X-Forwarded-For if present (Cloud Run)
    return req.headers.get("x-forwarded-for") or req.client.host or "unknown"

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# ------- Existing simple endpoint (now supports PNG/GIF, preprocessing, caching, rate limiting) -------
@app.post("/ocr/simple/image", response_model=SimpleOCRResponse)
async def ocr_simple_image(
    request: Request,
    file: UploadFile = File(...),
    language_hints: Optional[List[str]] = Query(default=None),
    use_document_ocr: bool = Query(default=True),
):
    t0 = time.perf_counter()
    # Rate limit
    LIMITER.check(_client_key(request))

    try:
        content = await file.read()
        # Validate (now accepts JPG/JPEG/PNG/GIF, size <= 10MB, and real image bytes)
        validate_file(file, content)

        # Cache lookup
        key = cache_key_for(content, language_hints, use_document_ocr)
        cached = CACHE.get(key)
        if cached:
            text = preprocess_text(cached["text"])
            conf = cached.get("confidence")
            ms = int((time.perf_counter() - t0) * 1000)
            return SimpleOCRResponse(success=True, text=text, confidence=conf, processing_time_ms=ms)

        # Run OCR
        result = run_ocr_bytes(content, language_hints, use_document_ocr)

        # Post-process text
        cleaned = preprocess_text(result.text)

        # Handle no-text-found (200, empty string as per spec)
        if not cleaned:
            ms = int((time.perf_counter() - t0) * 1000)
            # cache empty too, so repeated uploads don't hit Vision again
            CACHE.set(key, {"text": "", "confidence": 0.0})
            return SimpleOCRResponse(success=True, text="", confidence=0.0, processing_time_ms=ms)

        # Average confidence
        conf = average_confidence(result.blocks)

        # Cache and return
        CACHE.set(key, {"text": cleaned, "confidence": conf})
        ms = int((time.perf_counter() - t0) * 1000)
        return SimpleOCRResponse(success=True, text=cleaned, confidence=conf, processing_time_ms=ms)

    except HTTPException:
        raise
    except Exception as e:
        ms = int((time.perf_counter() - t0) * 1000)
        raise HTTPException(status_code=500, detail=str(e))


# ------- New: rich response with metadata + cache flag -------
@app.post("/ocr/plus/image", response_model=SimpleOCRPlusResponse)
async def ocr_plus_image(
    request: Request,
    file: UploadFile = File(...),
    language_hints: Optional[List[str]] = Query(default=None),
    use_document_ocr: bool = Query(default=True),
):
    t0 = time.perf_counter()
    LIMITER.check(_client_key(request))

    content = await file.read()
    validate_file(file, content)
    metadata = extract_image_metadata(content)

    key = cache_key_for(content, language_hints, use_document_ocr)
    cached = CACHE.get(key)
    cache_hit = cached is not None
    if cached:
        text = preprocess_text(cached["text"])
        conf = cached.get("confidence")
        ms = int((time.perf_counter() - t0) * 1000)
        return SimpleOCRPlusResponse(
            success=True, text=text, confidence=conf, processing_time_ms=ms, cache_hit=True, metadata=metadata
        )

    result = run_ocr_bytes(content, language_hints, use_document_ocr)
    cleaned = preprocess_text(result.text)
    conf = average_confidence(result.blocks) if cleaned else 0.0

    CACHE.set(key, {"text": cleaned, "confidence": conf})
    ms = int((time.perf_counter() - t0) * 1000)
    return SimpleOCRPlusResponse(
        success=True, text=cleaned, confidence=conf, processing_time_ms=ms, cache_hit=False, metadata=metadata
    )


# ------- New: batch endpoint -------
@app.post("/ocr/simple/batch")
async def ocr_simple_batch(
    request: Request,
    files: List[UploadFile] = File(..., description="One or more image files (JPG/JPEG/PNG/GIF)"),
    language_hints: Optional[List[str]] = Query(default=None),
    use_document_ocr: bool = Query(default=True),
):
    """Process multiple files in a single request and return a list of simple responses."""
    LIMITER.check(_client_key(request))
    results = []
    for f in files:
        t0 = time.perf_counter()
        try:
            content = await f.read()
            validate_file(f, content)
            key = cache_key_for(content, language_hints, use_document_ocr)
            cached = CACHE.get(key)
            if cached:
                cleaned = preprocess_text(cached["text"])
                conf = cached.get("confidence")
                ms = int((time.perf_counter() - t0) * 1000)
                results.append({"filename": f.filename, "success": True, "text": cleaned, "confidence": conf, "processing_time_ms": ms, "cache_hit": True})
                continue

            r = run_ocr_bytes(content, language_hints, use_document_ocr)
            cleaned = preprocess_text(r.text)
            conf = average_confidence(r.blocks) if cleaned else 0.0
            CACHE.set(key, {"text": cleaned, "confidence": conf})
            ms = int((time.perf_counter() - t0) * 1000)
            results.append({"filename": f.filename, "success": True, "text": cleaned, "confidence": conf, "processing_time_ms": ms, "cache_hit": False})
        except HTTPException as he:
            results.append({"filename": f.filename, "success": False, "error": he.detail})
        except Exception as e:
            results.append({"filename": f.filename, "success": False, "error": str(e)})
    return {"results": results}
