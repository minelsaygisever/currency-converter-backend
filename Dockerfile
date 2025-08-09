FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# ---

FROM python:3.11-slim
WORKDIR /app

RUN addgroup --system app && adduser --system --group app
USER app

COPY --from=builder /app/wheels /wheels

COPY . .

RUN pip install --no-cache-dir /wheels/*

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]