# Skiritai — AI-driven browser test automation framework
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy package source
COPY pyproject.toml ./
COPY skiritai/ ./skiritai/

# Install core + web extras
RUN pip install --no-cache-dir ".[web]"

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy examples
COPY examples/ ./examples/

ENV HEADLESS=true

# Default: run the web server
EXPOSE 8000
CMD ["skiritai", "serve", "--host", "0.0.0.0", "--port", "8000"]
