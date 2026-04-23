# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir build && python -m build -w

FROM python:3.12-slim-bookworm

# Install git for GitSource
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

WORKDIR /app
COPY --from=builder /build/dist/*.whl ./
RUN pip install --no-cache-dir ./*.whl && rm ./*.whl

RUN mkdir -p /data/skills /data/locks && \
    chown -R appuser:appuser /data

# Read-only rootfs compatibility: Python may need to write to /tmp
ENV TMPDIR=/tmp

USER appuser

EXPOSE 8080

ENTRYPOINT ["skills-mcp-server"]
CMD ["run", "--config", "/config/config.yaml"]
