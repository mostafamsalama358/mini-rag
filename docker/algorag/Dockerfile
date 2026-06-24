FROM ghcr.io/astral-sh/uv:python3.11-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    libavif-dev \
    pkg-config \
    libjpeg-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt .

RUN uv pip install \
    --system \
    --no-cache \
    -r requirements.txt

COPY src/ .

RUN mkdir -p /app/models/db_schemes/algorag/

COPY docker/algorag/alembic.ini \
     /app/models/db_schemes/algorag/alembic.ini

COPY docker/algorag/entrypoint.sh /entrypoint.sh

RUN sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]