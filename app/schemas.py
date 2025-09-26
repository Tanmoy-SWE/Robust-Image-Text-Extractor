# app/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any  # 👈 add Dict, Any

class OCRRequestGCS(BaseModel):
    gcs_uri: str = Field(..., example="gs://my-bucket/path/image.jpg")
    language_hints: Optional[List[str]] = Field(default=None, example=["en", "bn"])
    use_document_ocr: bool = Field(default=True)

class OCRBlock(BaseModel):
    text: str
    confidence: float
    bbox: List[List[float]]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

class OCRResponse(BaseModel):
    text: str
    language: Optional[str] = None
    blocks: List[OCRBlock] = []

class SimpleOCRResponse(BaseModel):
    success: bool
    text: str
    confidence: Optional[float] = None
    processing_time_ms: int

# Optional richer response (if you added /ocr/plus/image)
class SimpleOCRPlusResponse(BaseModel):
    success: bool
    text: str
    confidence: Optional[float] = None
    processing_time_ms: int
    cache_hit: bool = False
    metadata: Optional[Dict[str, Any]] = None
