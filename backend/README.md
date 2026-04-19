# Kubebot

A RAG-powered Kubernetes documentation assistant. Ask questions about Kubernetes resources and get grounded answers from the official API documentation.

## Prerequisites

- Docker & Docker Compose
- Minikube (for extracting Kubernetes API docs)
- Python 3.13+
- OpenAI API key

## Quick Start

1. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

2. **Run the development script**

   ```bash
   ./dev.sh
   ```

   This will:
   - Start minikube (if not already running)
   - Start the PostgreSQL database with pgvector
   - Run the Dagster ETL pipeline to populate the database
   - Start the FastAPI server

3. **Query the bot**

   ```bash
   # Simple endpoint (direct RAG)
   curl -s -X POST localhost:8000/ask_simple \
     --data '{"question":"what are pods"}' \
     -H "Content-Type: application/json" | jq -r '.answer'

   # Agent endpoint (with tool use)
   curl -s -X POST localhost:8000/ask \
     --data '{"question":"what are pods"}' \
     -H "Content-Type: application/json" | jq -r '.answer'
   ```

## Shell Alias

Add this to your `~/.bashrc` for easy querying with markdown rendering:

```bash
alias kubebot='f(){ curl -s -X POST localhost:8000/ask --data "{\"question\":\"$1\"}" -H "Content-Type: application/json" | jq -r ".answer" | glow; }; f'
```

Then use:

```bash
kubebot "how do I configure a deployment?"
```

Requires [glow](https://github.com/charmbracelet/glow) for markdown rendering:

```bash
sudo snap install glow
```

## Development

### Project Structure

```
├── app.py                 # FastAPI application
├── dev.sh                 # Development startup script
├── docker-compose.yml     # Docker services (db, api)
├── etl/                   # Dagster ETL pipeline
│   ├── definitions.py     # Dagster definitions
│   └── assets/
│       ├── extract.py     # kubectl api-resources & explain
│       ├── transform.py   # Chunking
│       └── load.py        # Embedding & pgvector storage
├── models/                # Pydantic models
├── prompts/               # System prompts
├── services/
│   ├── chat.py            # RAG and agent pipelines
│   └── db.py              # Database connection & search
└── tools/
    └── search.py          # LangChain tools for agent
```

### Running Services Individually

**Database only:**

```bash
docker compose up -d db
```

**Dagster UI (for ETL debugging):**

```bash
source .venv/bin/activate
dagster dev -m etl.definitions
# Open http://localhost:3000
```

**API only (after db is running):**

```bash
docker compose up -d api --build
```

**Re-run ETL pipeline:**

```bash
source .venv/bin/activate
dagster asset materialize -m etl.definitions --select '*'
```

### Environment Variables

| Variable          | Default     | Description                        |
| ----------------- | ----------- | ---------------------------------- |
| `OPENAI_API_KEY`  | -           | OpenAI API key (required)          |
| `DB_HOST`         | `localhost` | PostgreSQL host                    |
| `DB_PORT`         | `5432`      | PostgreSQL port                    |
| `DB_USER`         | `dev`       | Database user                      |
| `DB_PASSWORD`     | `devpass`   | Database password                  |
| `DB_NAME`         | `kubebot`   | Database name                      |
| `DAGSTER_DB_HOST` | `localhost` | DB host for Dagster (runs on host) |
| `DAGSTER_DB_PORT` | `5433`      | DB port for Dagster (mapped port)  |

### Rebuilding

After code changes:

```bash
docker compose up -d api --build
```

After ETL changes, re-run the pipeline:

```bash
dagster asset materialize -m etl.definitions --select '*'
```

## API Endpoints

| Endpoint      | Method | Description                                   |
| ------------- | ------ | --------------------------------------------- |
| `/ask_simple` | POST   | Direct RAG pipeline (faster, simpler)         |
| `/ask`        | POST   | Agent pipeline with tool use (richer answers) |

**Request body:**

```json
{
  "question": "your question here"
}
```

**Response:**

```json
{
  "answer": "markdown formatted answer",
  "sources": [
    {
      "doc_path": "pods",
      "title": "pods",
      "relevant_info": "..."
    }
  ]
}
```
