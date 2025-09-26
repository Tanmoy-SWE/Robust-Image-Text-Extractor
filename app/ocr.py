from google.cloud import vision
from typing import List, Optional
from .schemas import OCRResponse, OCRBlock
from typing import Optional, List
from .schemas import OCRBlock


def _vertices_to_bbox(vertices) -> List[List[float]]:
    # returns list of 4 points (x,y), normalizing to pixel ints if present
    box = []
    for v in vertices:
        box.append([float(v.x or 0), float(v.y or 0)])
    # pad to 4 if needed
    while len(box) < 4:
        box.append([0.0, 0.0])
    return box

def run_ocr_bytes(
    content: bytes,
    language_hints: Optional[List[str]] = None,
    use_document_ocr: bool = True
) -> OCRResponse:
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=content)

    image_context = vision.ImageContext(language_hints=language_hints or [])

    if use_document_ocr:
        response = client.document_text_detection(image=image, image_context=image_context)
        anno = response.full_text_annotation
        text = anno.text or ""
        blocks: List[OCRBlock] = []
        for page in anno.pages:
            for block in page.blocks:
                block_text = []
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        symbols = "".join([s.text for s in word.symbols])
                        block_text.append(symbols)
                blocks.append(
                    OCRBlock(
                        text=" ".join(block_text).strip(),
                        confidence=float(block.confidence or 0.0),
                        bbox=_vertices_to_bbox(block.bounding_box.vertices),
                    )
                )
        lang = None
        if anno.pages and anno.pages[0].property and anno.pages[0].property.detected_languages:
            lang = anno.pages[0].property.detected_languages[0].language_code
        if response.error.message:
            raise RuntimeError(response.error.message)
        return OCRResponse(text=text, language=lang, blocks=blocks)

    # Simple text_detection (lighter)
    response = client.text_detection(image=image, image_context=image_context)
    if response.error.message:
        raise RuntimeError(response.error.message)
    annotations = response.text_annotations
    text = annotations[0].description if annotations else ""
    blocks: List[OCRBlock] = []
    for a in annotations[1:]:
        blocks.append(
            OCRBlock(
                text=a.description,
                confidence=0.0,  # not provided here
                bbox=_vertices_to_bbox(a.bounding_poly.vertices),
            )
        )
    return OCRResponse(text=text, language=None, blocks=blocks)

def run_ocr_gcs(
    gcs_uri: str,
    language_hints: Optional[List[str]] = None,
    use_document_ocr: bool = True
) -> OCRResponse:
    client = vision.ImageAnnotatorClient()
    image = vision.Image(source=vision.ImageSource(image_uri=gcs_uri))
    image_context = vision.ImageContext(language_hints=language_hints or [])

    if use_document_ocr:
        response = client.document_text_detection(image=image, image_context=image_context)
        anno = response.full_text_annotation
        text = anno.text or ""
        blocks: List[OCRBlock] = []
        for page in anno.pages:
            for block in page.blocks:
                block_text = []
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        symbols = "".join([s.text for s in word.symbols])
                        block_text.append(symbols)
                blocks.append(
                    OCRBlock(
                        text=" ".join(block_text).strip(),
                        confidence=float(block.confidence or 0.0),
                        bbox=_vertices_to_bbox(block.bounding_box.vertices),
                    )
                )
        lang = None
        if anno.pages and anno.pages[0].property and anno.pages[0].property.detected_languages:
            lang = anno.pages[0].property.detected_languages[0].language_code
        if response.error.message:
            raise RuntimeError(response.error.message)
        return OCRResponse(text=text, language=lang, blocks=blocks)

    response = client.text_detection(image=image, image_context=image_context)
    if response.error.message:
        raise RuntimeError(response.error.message)
    annotations = response.text_annotations
    text = annotations[0].description if annotations else ""
    blocks: List[OCRBlock] = []
    for a in annotations[1:]:
        blocks.append(
            OCRBlock(
                text=a.description,
                confidence=0.0,
                bbox=_vertices_to_bbox(a.bounding_poly.vertices),
            )
        )
    return OCRResponse(text=text, language=None, blocks=blocks)


def average_confidence(blocks: List[OCRBlock]) -> Optional[float]:
    vals = [b.confidence for b in blocks if b.confidence is not None]
    return float(sum(vals)/len(vals)) if vals else None
