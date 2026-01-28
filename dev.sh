#!/bin/bash
# dev.sh

docker compose down -v
docker compose up -d
echo "Waiting for postgres..."
sleep 3
dagster dev -m etl.definitions