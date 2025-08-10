# syntax=docker/dockerfile:1

######################## 1. builder ########################
FROM python:3.12-slim AS builder
WORKDIR /w

# Install deps to a throw‑away location
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code last (keeps cache hot)
COPY src/ ./src/

######################## 2. final, ultra‑light ########################
# Distroless image ships only the Python 3 interpreter and SSL certs
FROM gcr.io/distroless/python3-debian12:nonroot

# Bring in site‑packages and application
COPY --from=builder /usr/local /usr/local
COPY --from=builder /w/src/ /app/src/
WORKDIR /app

# Set default environment variables
ENV DISCORD_TOKEN=""
ENV DISCORD_CHANNEL_ID="0"
ENV DISCORD_MESSAGE_ID="0"
ENV VALHEIM_HOST="localhost"
ENV VALHEIM_QUERY_PORT="2457"
ENV UPDATE_PERIOD="60"
ENV HEALTH_PORT="8080"
ENV PYTHONUNBUFFERED="1"

# The distroless python image defaults to ["python3"] entrypoint
ENTRYPOINT ["python3", "/app/src/bot.py"]

# Harden further
USER nonroot:nonroot

# Expose health port for clarity
EXPOSE 8080

# Container healthcheck using Python (no curl/wget in distroless)
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD ["python3", "-c", "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8080/healthz'); sys.exit(0)"]
