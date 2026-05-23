# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies into a prefix dir (keeps final image lean)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Cloud Run injects $PORT at runtime (default 8080)
# Never hard-code the port — Cloud Run won't route to you if you do
ENV PORT=8080
EXPOSE 8080

# Use uvicorn directly (no gunicorn — single process is fine for Cloud Run)
# --workers 1 is intentional: in-memory state must not be split across workers
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
