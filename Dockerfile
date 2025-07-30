# syntax=docker/dockerfile:1

######################## 1. builder ########################
FROM python:3.12-slim AS builder
WORKDIR /w

# Install deps to a throw‑away location
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy application code last (keeps cache hot)
COPY src/ ./src/

######################## 2. final, ultra‑light ########################
# Distroless image ships only the Python 3 interpreter and SSL certs
FROM gcr.io/distroless/python3-debian12:nonroot

# Bring in site‑packages and application
COPY --from=builder /install /usr/local
COPY --from=builder /w/src/ /app/src/
WORKDIR /app

# The distroless python image defaults to ["python3"] entrypoint
ENTRYPOINT ["python3", "/app/src/bot.py"]

# Harden further
USER nonroot:nonroot       # already the default tag, but explicit is better
ENV PYTHONUNBUFFERED=1