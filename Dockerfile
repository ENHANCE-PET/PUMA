# Base image
FROM python:3.10-slim

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
