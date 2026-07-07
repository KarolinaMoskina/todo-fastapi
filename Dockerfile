#Builder
FROM python:3.13-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

#wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


#Runner
FROM python:3.13-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=builder /root/.local /root/.local
COPY --from=builder /build /app

ENV PATH=/root/.local/bin:$PATH

COPY ./app /app/app
COPY ./migrations /app/migrations
COPY ./main.py /app/main.py
COPY ./alembic.ini /app/alembic.ini

# port FastAPI
EXPOSE 8000

# uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]