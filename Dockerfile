# === build stage (optional; keeps final image small) ===
FROM python:3.11-slim AS base

# OS deps (pandas needs these)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# === final image ===
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
COPY --from=base /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=base /usr/local/bin /usr/local/bin
COPY --from=base /usr/local/include /usr/local/include

# App files
COPY app.py ./app.py
COPY static ./static

# Health (optional)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  wget -qO- http://127.0.0.1:${PORT}/health || exit 1

EXPOSE ${PORT}
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
