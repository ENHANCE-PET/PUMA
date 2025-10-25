# Base image
FROM python:3.10-slim

# Install build dependencies for packages that need compilation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Install pumaz using uv (much faster than pip)
RUN uv pip install --system pumaz

# Entry point for pumaz CLI
ENTRYPOINT ["pumaz"]

# Default command
CMD ["-h"]
