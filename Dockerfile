# ==============================================================================
# Autonomous AI Open-World Ecosystem: Production Multi-Stage Hardened Dockerfile
# ==============================================================================

# Build Stage
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Minimal Runtime Stage
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    VAULT_PATH=/app/vault \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000

# Install curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root unprivileged service user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy installed Python packages from builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appgroup . /app

# Ensure vault directory exists and is writable by appuser
RUN mkdir -p /app/vault && chown -R appuser:appgroup /app/vault

USER appuser

EXPOSE 8000

# Container Healthcheck verifying FastAPI Gateway status
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/status || exit 1

# Launch Gateway Server with Uvicorn
CMD ["python", "-m", "uvicorn", "gateway_server:app", "--host", "0.0.0.0", "--port", "8000"]
