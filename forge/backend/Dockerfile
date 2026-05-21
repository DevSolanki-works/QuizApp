# ─────────────────────────────────────────────────────────
# Forge Backend — Dockerfile
# Target: Google Cloud Run (linux/amd64)
# Dev machine: ARM64 (Apple Silicon / ARM Linux)
#
# WHY python:3.12-slim?
#   - "slim" = no dev tools, no docs, smaller image (~130MB vs ~900MB)
#   - Smaller image = faster Cloud Run cold starts = better UX
#   - 3.12 gives us the latest asyncio improvements
#
# IMPORTANT for ARM64 devs:
#   Build for Cloud Run (which is amd64) with:
#     docker buildx build --platform linux/amd64 -t forge-backend .
#   Or use multi-arch:
#     docker buildx build --platform linux/amd64,linux/arm64 ...
# ─────────────────────────────────────────────────────────

FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# WHY copy requirements first?
# Docker caches each layer. If we copy requirements BEFORE source code,
# the pip install layer is cached as long as requirements.txt doesn't change.
# Code edits don't re-trigger a slow pip install. Huge time saver.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the source code
COPY . .

# Cloud Run injects the PORT env var (usually 8080).
# We expose it here for documentation; Cloud Run ignores EXPOSE.
EXPOSE 8080

# Start uvicorn on the port Cloud Run provides via $PORT env var.
# --host 0.0.0.0 = listen on all interfaces (required in containers)
# --workers 1     = one process. More workers = multiple in-memory states = chaos.
#                  For our in-memory design, ALWAYS use 1 worker.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]