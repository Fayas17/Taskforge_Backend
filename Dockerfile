# -------------------
# Builder Stage
# -------------------
FROM python:3.11-slim AS builder

WORKDIR /install

RUN apt-get update && apt-get install -y build-essential

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /install/wheels -r requirements.txt


# -------------------
# Runtime Stage
# -------------------
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=builder /install/wheels /wheels
COPY requirements.txt .

RUN pip install --no-cache /wheels/*

COPY ./app ./app
COPY .env .env

CMD ["uvicorn", "app.auth_service.main:app", "--host", "0.0.0.0", "--port", "8000"]