# TESTS.md — OCR API Manual Test Scenarios

Use these commands to validate the deployed OCR API.

**Base endpoint (simple upload):**
`POST https://fastapi-ocr-735947868321.asia-south1.run.app/ocr/simple/image`

You can export the URL to an env var for convenience:
```bash
export API="https://fastapi-ocr-735947868321.asia-south1.run.app"
```

---

## 0) Health Check
```bash
curl -s "$API/healthz"
# Expect: {"status":"ok"} and HTTP 200
```

## 1) Happy Path — JPG upload
```bash
curl -s -X POST "$API/ocr/simple/image" \
  -F "file=@samples/test.jpg"
# Expect: success:true, text (if present), confidence, processing_time_ms
```

## 2) Multiple Formats (PNG / GIF)
```bash
# PNG
curl -s -X POST "$API/ocr/simple/image" -F "file=@samples/test.png"

# GIF
curl -s -X POST "$API/ocr/simple/image" -F "file=@samples/test.gif"
# Expect: same JSON shape as JPG. If restricted to JPG-only, expect 415.
```

## 3) Validation — No file uploaded
```bash
curl -s -X POST "$API/ocr/simple/image" \
  -H "Content-Type: multipart/form-data" \
  -o /dev/stderr -w "HTTP_STATUS:%{http_code}\n"
# Expect: HTTP 400
```

## 4) Validation — Wrong file type
```bash
echo "not an image" > tmp.txt
curl -s -X POST "$API/ocr/simple/image" \
  -F "file=@tmp.txt;type=text/plain" \
  -o /dev/stderr -w "HTTP_STATUS:%{http_code}\n"
# Expect: HTTP 415
```

## 5) Validation — Oversize (>10MB)
```bash
dd if=/dev/zero of=big.bin bs=1M count=11 2>/dev/null
mv big.bin big.jpg
curl -s -X POST "$API/ocr/simple/image" \
  -F "file=@big.jpg;type=image/jpeg" \
  -o /dev/stderr -w "HTTP_STATUS:%{http_code}\n"
# Expect: HTTP 413
```

## 6) No Text Found
```bash
curl -s -X POST "$API/ocr/simple/image" \
  -F "file=@samples/blank.jpg"
# Expect: success:true, text:"", confidence:0.0 (or null), HTTP 200
```

## 7) Language Hints & Document OCR (optional)
```bash
curl -s -X POST "$API/ocr/simple/image?use_document_ocr=true&language_hints=en&language_hints=bn" \
  -F "file=@samples/multilang.jpg"
# Expect: normal simple response, potentially improved recognition
```

## 8) Caching & Metadata (PLUS endpoint, if available)
```bash
# First call (cold)
curl -s -X POST "$API/ocr/plus/image" -F "file=@samples/test.jpg"

# Second call (warm, identical)
curl -s -X POST "$API/ocr/plus/image" -F "file=@samples/test.jpg"
# Expect: second response has "cache_hit": true and usually lower processing_time_ms
```

## 9) Batch Processing (if available)
```bash
curl -s -X POST "$API/ocr/simple/batch" \
  -F "files=@samples/test.jpg" \
  -F "files=@samples/test.png" \
  -F "files=@samples/test.gif"
# Expect: JSON object with a "results" array (one entry per file)
```

## 10) Rate Limiting
```bash
for i in $(seq 1 70); do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/ocr/simple/image" -F "file=@samples/test.jpg")
  printf "req %02d -> %s\n" "$i" "$code"
done
# Expect: initial 200s, later 429 within same minute (depending on configured limit)
```

