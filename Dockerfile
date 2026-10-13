# ====================================
# VisionGuard AI - Dockerfile
# ====================================
# Multi-stage build: Python app + Playwright browsers

FROM python:3.10-slim

# System dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    fontconfig \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only to keep image small)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Run the API server (respects cloud-provided $PORT if set)
CMD ["sh", "-c", "uvicorn api_backend.main_api:app --host 0.0.0.0 --port ${PORT:-8000}"]
