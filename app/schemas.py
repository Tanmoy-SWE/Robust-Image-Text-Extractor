from pydantic import BaseModel, Field
from typing import List, Optional

class OCRRequestGCS(BaseModel):
    gcs_uri: str = Field(..., example="gs://my-bucket/path/image.png")
    language_hints: Optional[List[str]] = Field(default=None, example=["en", "bn"])
    use_document_ocr: bool = Field(default=True, description="document_text_detection vs text_detection")

class OCRBlock(BaseModel):
    text: str
    confidence: float
    bbox: List[List[float]]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

class OCRResponse(BaseModel):
    text: str
    language: Optional[str] = None
    blocks: List[OCRBlock] = []
