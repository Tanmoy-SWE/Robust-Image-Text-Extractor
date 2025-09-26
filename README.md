# OCR Image Text Extractor (FastAPI + Google Cloud Vision + Cloud Run)

## 📌 Overview
This project is a serverless API that extracts text from uploaded images using **Google Cloud Vision OCR** and runs on **Google Cloud Run**.

It accepts JPG/JPEG image files, validates input (file size and type), performs OCR, and returns the extracted text in a structured JSON response.

---

## ⚙️ Features
- Accepts JPG/JPEG uploads via `multipart/form-data`
- Extracts text using Google Cloud Vision API
- Validation: only `.jpg`/`.jpeg`, max 10 MB
- Proper error handling (missing file, wrong format, oversized file)
- JSON responses with success flag, confidence score, and processing time
- Deployed to Cloud Run (serverless, auto-scalable)

---

## 📡 API Documentation

### Health Check
**Endpoint**
```
GET /healthz
```
**Response**
```json
{"status": "ok"}
```

---

### Extract Text (Simple)
**Endpoint**
```
POST /ocr/simple/image
```

**Input**
- `file` (form-data, JPG/JPEG only, max 10 MB)
- Optional query params:
  - `language_hints`: e.g. `en`, `bn`
  - `use_document_ocr`: boolean, default `true`

**Output**
```json
{
  "success": true,
  "text": "extracted text content here",
  "confidence": 0.95,
  "processing_time_ms": 1234
}
```

**Error Codes**
- `400 Bad Request` → No file uploaded
- `415 Unsupported Media Type` → File not JPG/JPEG
- `413 Payload Too Large` → File exceeds 10 MB
- `200 OK` with `"text": ""` → Valid image but no text detected

---

### Example `curl` Request
```bash
curl -X POST "https://fastapi-ocr-735947868321.asia-south1.run.app/ocr/simple/image"   -F "file=@test_image.jpg"
```

---

## 🛠 Implementation Details
- **Framework**: FastAPI (Python)
- **OCR Service**: Google Cloud Vision API
- **Validation**: `validate_file()` enforces format and size rules
- **Error Handling**: Proper HTTP status codes
- **Deployment**: Dockerized and deployed to Cloud Run via Artifact Registry

---

## 🚀 Deployment Steps

1. **Enable APIs**
```bash
gcloud services enable run.googleapis.com vision.googleapis.com storage.googleapis.com
```

2. **Create Artifact Registry repo**
```bash
gcloud artifacts repositories create ocr-repo \
  --repository-format=docker \
  --location=asia-south1 \
  --description="OCR app images"
```

3. **Build & Push**
```bash
gcloud builds submit --tag asia-south1-docker.pkg.dev/PROJECT_ID/ocr-repo/fastapi-ocr
```
*(Or build locally with Docker and push if Cloud Build IAM is restricted.)*

4. **Deploy to Cloud Run**
```bash
gcloud run deploy fastapi-ocr \
  --image asia-south1-docker.pkg.dev/PROJECT_ID/ocr-repo/fastapi-ocr \
  --region asia-south1 \
  --allow-unauthenticated \
  --service-account vision-ocr-sa@PROJECT_ID.iam.gserviceaccount.com \
  --port 8080
```

5. **Test** with curl or Postman.

---

## 📝 Example Response
```json
{
  "success": true,
  "text": "Invoice #12345 Date: 2025-09-24 Total: $540",
  "confidence": 0.97,
  "processing_time_ms": 842
}
```

---

## 🧪 Testing
- Use Postman or curl with `multipart/form-data` upload
- Try with sample JPG images in `/samples`
- Verify proper error responses with `.png` or oversized files

---

## 📂 Repo Contents
- `app/` → FastAPI code (`main.py`, `ocr.py`, `schemas.py`, `utils.py`)
- `requirements.txt` → dependencies
- `Dockerfile` → container definition
- `.gitignore` → ignores `.env`, service account JSONs, venvs
- `README.md` → this file


✨ Enjoy the serverless OCR API running in Google Cloud!
