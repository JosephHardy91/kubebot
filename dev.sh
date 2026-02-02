#!/bin/bash
# dev.sh
set -e

# Start minikube if not running
echo "Checking minikube..."
if ! minikube status | grep -q "apiserver: Running"; then
    echo "Starting minikube..."
    minikube start
else
    echo "Minikube already running"
fi

# Start database container first
echo "Starting database..."
docker compose down -v
docker compose up -d db
echo "Waiting for postgres..."
sleep 5

# Run ETL to populate database
echo "Running ETL pipeline..."
source .venv/bin/activate
dagster asset materialize -m etl.definitions --select '*'

# Now start the API
echo "Starting API..."
docker compose up -d api --build

echo "✅ Ready! API available at http://localhost:8000"
echo "Run 'dagster dev -m etl.definitions' in a separate terminal for the Dagster UI"