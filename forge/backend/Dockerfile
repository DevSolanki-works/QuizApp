# ── Forge Backend Dockerfile ──────────────────────────────────────────────────
#
# Build (ARM64 dev machine, multi-arch for Cloud Run):
#   docker buildx build --platform linux/amd64,linux/arm64 -t forge-backend .
#
# Run locally:
#   docker run -p 8000:8000 -e GEMINI_API_KEY=your_key forge-backend

# Use the slim variant — smaller image, faster Cold Starts on Cloud Run.
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# ── Install dependencies first (cached layer) ─────────────────────────────────
# Copying requirements before source code means Docker reuses this layer
# on rebuilds if only source files changed — much faster iteration.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application source ───────────────────────────────────────────────────
COPY . .

# ── Expose port ───────────────────────────────────────────────────────────────
# Cloud Run injects PORT env var; uvicorn reads it below.
EXPOSE 8080

# ── Start server ──────────────────────────────────────────────────────────────
# Cloud Run sets $PORT (usually 8080). We default to 8080 for consistency.
# --host 0.0.0.0 is required — default 127.0.0.1 is unreachable inside Docker.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
