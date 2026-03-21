# -------------------
# Builder Stage
# -------------------
FROM python:3.11-slim AS builder

WORKDIR /install

RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps \
    --wheel-dir /install/wheels -r requirements.txt


# -------------------
# Runtime Stage
# -------------------
FROM python:3.11-slim

WORKDIR /app

# Python runtime settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install dependencies from wheels
COPY --from=builder /install/wheels /wheels
COPY requirements.txt .

RUN pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Copy application code
COPY ./app ./app

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
