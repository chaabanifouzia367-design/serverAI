#!/bin/bash

# 1. Start Celery (Mode Solo = A9all RAM momken)
# Zidna: --pool=solo --concurrency=1
echo "Starting Celery Worker (Solo Mode)..."
celery -A app.celery_app.celery worker --loglevel=info --pool=solo --concurrency=1 &

# 2. Start Web Server
echo "Starting Web Server..."
python run.py