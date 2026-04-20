FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY polyroute ./polyroute

RUN pip install --no-cache-dir --upgrade pip build \
 && pip wheel --no-cache-dir --wheel-dir /wheels ".[api,llm]"


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN useradd --create-home --uid 1000 polyroute

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels polyroute[api,llm] \
 && rm -rf /wheels

COPY --chown=polyroute:polyroute web ./web

USER polyroute

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{__import__(\"os\").environ.get(\"PORT\",\"8000\")}/health', timeout=3).status == 200 else 1)"

CMD ["sh", "-c", "uvicorn polyroute.api.server:app --host 0.0.0.0 --port ${PORT}"]
