#!/bin/bash

# Build and run via Docker Compose
docker-compose build
docker-compose up -d

# Placeholder: Run AI agents or slices
echo "Running Tangerine processes..."
docker-compose exec tangerine python common/db_utils.py  # Example; update with actual scripts

# Stop services
docker-compose down
