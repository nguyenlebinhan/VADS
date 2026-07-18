# syntax=docker/dockerfile:1.7
FROM node:20-alpine AS frontend-build

WORKDIR /opt/vads-frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM python:3.12-slim AS runtime

ARG INSTALL_OCR=false

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=20

WORKDIR /opt/vads

RUN addgroup --system vads \
    && adduser --system --ingroup vads --home /opt/vads/.runtime vads \
    && mkdir -p /opt/vads/.runtime \
    && chown -R vads:vads /opt/vads/.runtime

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY --from=frontend-build /opt/vads-frontend/dist ./frontend-dist

RUN python -m pip install --retries 20 --timeout 600 .

RUN if [ "$INSTALL_OCR" = "true" ]; then \
        apt-get update \
        && apt-get install --no-install-recommends --yes libgl1 libglib2.0-0 libgomp1 \
        && rm -rf /var/lib/apt/lists/*; \
    fi

RUN if [ "$INSTALL_OCR" = "true" ]; then \
        python -m pip install --retries 20 --timeout 600 paddlepaddle==3.2.0 \
            --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
            --extra-index-url https://pypi.org/simple \
        && python -m pip install --retries 20 --timeout 600 ".[ocr]"; \
    fi

USER vads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
