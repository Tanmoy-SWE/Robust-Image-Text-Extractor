from pydantic import BaseModel, Field
from typing import List, Optional

class OCRRequestGCS(BaseModel):
    gcs_uri: str = Field(..., example="gs://my-bucket/path/image.png")
    language_hints: Optional[List[str]] = Field(default=None, example=["en", "bn"])
    use_document_ocr: bool = Field(default=True)

class OCRBlock(BaseModel):
    text: str
    confidence: float
    bbox: List[List[float]]

class OCRResponse(BaseModel):
    text: str
    language: Optional[str] = None
    blocks: List[OCRBlock] = []

# NEW: simple envelope
class SimpleOCRResponse(BaseModel):
    success: bool
    text: str
    confidence: Optional[float] = None
    processing_time_ms: int
