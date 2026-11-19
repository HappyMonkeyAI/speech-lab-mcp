# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SPEECH_LAB_OUTPUT_DIR=/data/out \
    SPEECH_LAB_TRANSPORT=streamable-http \
    SPEECH_LAB_HOST=0.0.0.0 \
    SPEECH_LAB_PORT=8765

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install .

RUN mkdir -p /data/out && chown -R app:app /data /app
USER app

VOLUME ["/data/out"]
EXPOSE 8765

ENTRYPOINT ["speech-lab-mcp"]
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8765"]
