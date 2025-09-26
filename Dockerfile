FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -U pip && pip install -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo zlib1g && rm -rf /var/lib/apt/lists/*

COPY app ./app

EXPOSE 8080
# ✅ Bind to Cloud Run's PORT, default to 8080 locally
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
