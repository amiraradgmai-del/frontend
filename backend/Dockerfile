FROM public.ecr.aws/docker/library/python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py && pip install --upgrade pip && pip install .

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

FROM base AS test
RUN pip install ".[dev]"
COPY tests ./tests
CMD ["pytest"]

FROM base AS runtime
RUN addgroup --system taxai && adduser --system --ingroup taxai taxai
USER taxai

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
