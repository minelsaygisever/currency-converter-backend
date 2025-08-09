FROM python:3.11-slim as builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# ---

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*

COPY . .

RUN addgroup --system app && adduser --system --group app

RUN chown -R app:app /app

USER app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]