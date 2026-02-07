# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl libffi-dev libssl-dev python3-dev pkg-config \
    libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev \
    libtiff5-dev libharfbuzz-dev libfribidi-dev \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Heavy AI Libs (Cached Layer)
RUN pip install --no-cache-dir \
    torch==2.4.1 \
    torchvision==0.19.1

# Install Requirements
COPY requirements.txt .
RUN --mount=type=cache,id=pip,target=/root/.cache/pip \
    pip install -r requirements.txt

# Set Python path
ENV PYTHONPATH=/app

# Copy Application Code
COPY . .

# Create directories
RUN mkdir -p /app/uploads /app/cache_slices /app/processed /app/data

# --- FIX START: Zidna el script houni ---
COPY start.sh .

# Rakkaz mli7: Hédhi tsal7 mochkla tsir kèn tsajjalt script b Windows (CRLF)
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# Na77ina 'chmod -R 755 /app' 5aterha RZINA barcha 3al PyTorch
# Just na3tiw permission l script w l dossieret elli nest7a9ouhom
RUN chmod -R 777 /app/uploads /app/processed /app/data

EXPOSE 5030

# Lansi el script elli fih Celery + Web
CMD ["./start.sh"]