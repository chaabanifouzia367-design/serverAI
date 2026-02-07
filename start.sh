#!/bin/bash

# 1. Lansi el Celery Worker (fi 'background' --> &)
# Hédha howa elli bech ya3mel el traitement mta3 el AI
echo "Starting Celery Worker..."
celery -A app.celery_app.celery worker --loglevel=info &

# 2. Lansi el Web Server (fi 'foreground')
# Hédha elli yched el connexion mta3 el site
echo "Starting Web Server..."
python run.py