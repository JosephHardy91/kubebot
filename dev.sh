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

# Add aliases if not already present
if ! grep -q "alias kubebot=" ~/.bashrc; then
    echo 'alias kubebot='\''f(){ curl -s -X POST localhost:8000/ask --data "{\"question\":\"$1\"}" -H "Content-Type: application/json" -b ~/.kubebot_cookies -c ~/.kubebot_cookies | jq -r ".answer" | glow; }; f'\''' >> ~/.bashrc
    echo 'alias kubebot_clear='\''rm -f ~/.kubebot_cookies && echo "Session cleared"'\''' >> ~/.bashrc
    echo "Added kubebot aliases to ~/.bashrc - run 'source ~/.bashrc' to activate"
fi