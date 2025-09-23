import io
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Optional
from .schemas import OCRRequestGCS, OCRResponse
from .ocr import run_ocr_bytes, run_ocr_gcs

app = FastAPI(title="GCP Vision OCR API", version="1.0.0")

MAX_UPLOAD_MB = 15  # Cloud Run default request size is 32MB; keep buffer

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/ocr/image", response_model=OCRResponse)
async def ocr_image(
    file: UploadFile = File(..., description="Image file (jpg,png,webp,pdf page-as-image)"),
    language_hints: Optional[List[str]] = Query(default=None),
    use_document_ocr: bool = Query(default=True, description="Use document_text_detection (better for docs)"),
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
        result = run_ocr_gcs(
            payload.gcs_uri,
            payload.language_hints,
            payload.use_document_ocr
        )
        return JSONResponse(status_code=200, content=result.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
