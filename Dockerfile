# syntax=docker/dockerfile:1
# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    libffi-dev \
    libssl-dev \
    python3-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    # OpenCV/OpenGL dependencies for ultralytics
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip, setuptools, and wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Pre-install heavy dependencies to leverage Docker layer caching
RUN pip install --no-cache-dir \
    tensorflow==2.14.0 \
    torch==2.4.1 \
    torchvision==0.19.1

# Copy requirements file first (for better caching)
COPY requirements.txt .

# Install Python dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,id=pip,target=/root/.cache/pip \
    pip install -r requirements.txt

# Set Python path to include the app directory
ENV PYTHONPATH=/app

# Copy the taskes package
# Copy taskes package REMOVED (Moved to app/engine)

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/cache_slices /app/processed /app/data

# Set permissions
RUN chmod -R 755 /app

# Expose port (for web service)
EXPOSE 5030

# Default command (overridden by docker-compose). Run the factory entrypoint.
CMD ["python", "run.py"]