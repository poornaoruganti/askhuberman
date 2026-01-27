# ---------- Builder stage ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (build tools only in builder)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install deps into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


# ---------- Runtime stage ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Create non-root user
RUN useradd -m -u 10001 appuser

# Copy venv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY ./rag /app/rag
COPY ./api /app/api

# Permissions
RUN chown -R appuser:appuser /app
USER appuser


ENV PORT=8000

EXPOSE 8000

# Optional: a simple healthcheck (won't break Azure if endpoint missing, but best if you add /health)
# HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
#   CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT','8000') + '/health').read()"

# Gunicorn (prod) + Uvicorn worker
# Tweak workers based on CPU: (2 * cores) + 1 is common; Azure SKUs vary.
# CMD ["gunicorn", "api.server:app", \
#      "-k", "uvicorn.workers.UvicornWorker", \
#      "-b", "0.0.0.0:${PORT}", \
#      "--workers", "2", \
#      "--timeout", "60", \
#      "--graceful-timeout", "30", \
#      "--keep-alive", "5", \
#      "--access-logfile", "-", \
#      "--error-logfile", "-"]

CMD ["sh", "-c", "\
gunicorn api.server:app \
-k uvicorn.workers.UvicornWorker \
-b 0.0.0.0:${PORT} \
--workers 2 \
--timeout 60 \
--graceful-timeout 30 \
--keep-alive 5 \
--access-logfile - \
--error-logfile - \
"]
