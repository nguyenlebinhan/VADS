FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/vads

RUN addgroup --system vads \
    && adduser --system --ingroup vads --home /opt/vads/.runtime vads \
    && mkdir -p /opt/vads/.runtime \
    && chown -R vads:vads /opt/vads/.runtime

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

RUN python -m pip install --no-cache-dir .

USER vads

# Railway injects $PORT dynamically; default to 8000 for other platforms
ENV PORT=8000

EXPOSE ${PORT}

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
