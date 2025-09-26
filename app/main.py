import time
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
from .schemas import OCRRequestGCS, OCRResponse, SimpleOCRResponse
from .ocr import run_ocr_bytes, run_ocr_gcs
from .ocr import average_confidence  
from .utils import validate_file

app = FastAPI(title="GCP Vision OCR API", version="1.1.0")
MAX_UPLOAD_MB = 15

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# --- existing endpoints (unchanged) ---
@app.post("/ocr/image", response_model=OCRResponse)
async def ocr_image(
    file: UploadFile = File(...),
    language_hints: Optional[List[str]] = Query(default=None),
    use_document_ocr: bool = Query(default=True),
):
    try:
        content = await file.read()
        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File too large (> {MAX_UPLOAD_MB} MB)")
        result = run_ocr_bytes(content, language_hints, use_document_ocr)
        return JSONResponse(status_code=200, content=result.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ocr/gcs", response_model=OCRResponse)
def ocr_gcs(payload: OCRRequestGCS):
    try:
        result = run_ocr_gcs(payload.gcs_uri, payload.language_hints, payload.use_document_ocr)
        return JSONResponse(status_code=200, content=result.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ocr/simple/image", response_model=SimpleOCRResponse)
async def ocr_simple_image(
    file: UploadFile = File(...),
    language_hints: Optional[list[str]] = Query(default=None),
    use_document_ocr: bool = Query(default=True),
):
    t0 = time.perf_counter()
    try:
        # Read file
        content = await file.read()

        # ✅ Validate upload (file existence, extension, size)
        validate_file(file, content)

        # Run OCR
        result = run_ocr_bytes(content, language_hints, use_document_ocr)

        # Handle case where no text is found
        if not result.text.strip():
            ms = int((time.perf_counter() - t0) * 1000)
            return SimpleOCRResponse(
                success=True,
                text="",
                confidence=0.0,
                processing_time_ms=ms
            )

        # Compute avg confidence
        conf = average_confidence(result.blocks)
        ms = int((time.perf_counter() - t0) * 1000)

        return SimpleOCRResponse(
            success=True,
            text=result.text,
            confidence=conf,
            processing_time_ms=ms
        )

    except HTTPException:
        raise
    except Exception as e:
        ms = int((time.perf_counter() - t0) * 1000)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ocr/simple/gcs", response_model=SimpleOCRResponse)
def ocr_simple_gcs(payload: OCRRequestGCS):
    t0 = time.perf_counter()
    try:
        result = run_ocr_gcs(payload.gcs_uri, payload.language_hints, payload.use_document_ocr)
        conf = average_confidence(result.blocks)
        ms = int((time.perf_counter() - t0) * 1000)
        return SimpleOCRResponse(success=True, text=result.text, confidence=conf, processing_time_ms=ms)
    except Exception as e:
        ms = int((time.perf_counter() - t0) * 1000)
        raise HTTPException(status_code=500, detail=str(e))
