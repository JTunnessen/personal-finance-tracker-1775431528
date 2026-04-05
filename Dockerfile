# ── Stage 1: Build (nothing to transpile, just validate structure) ──────────
FROM python:3.11-slim AS builder
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY backend/ ./backend/
COPY frontend/ ./frontend/
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
