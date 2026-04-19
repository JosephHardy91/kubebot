# Kubebot User Stories

A K8s docs RAG assistant.

## Stack

| Layer | Tool |
|-------|------|
| API | FastAPI |
| RAG | LangChain |
| Vector DB | Postgres + pgvector |
| ETL | Dagster or Airflow (TBD) |
| Container | Docker |
| Orchestration | Kubernetes (EKS) |
| Infra | Terraform |
| CI/CD | GitHub Actions |

---

## Epic: Chat Interface

| Story | Description |
|-------|-------------|
| Ask question | User sends a K8s question, gets an answer |
| See sources | Response includes links to K8s docs used |
| Follow-up | User can ask clarifying questions (conversation context) |

---

## Epic: RAG Pipeline

| Story | Description |
|-------|-------------|
| Retrieve relevant docs | Query finds top-k relevant chunks |
| Generate answer | LLM synthesizes answer from chunks |
| Handle "I don't know" | Graceful response when docs don't cover question |

---

## Epic: ETL / Ingestion

| Story | Description |
|-------|-------------|
| Ingest K8s docs | Scrape/pull kubernetes.io/docs |
| Chunk documents | Split into embeddable chunks |
| Generate embeddings | Vectorize chunks |
| Store in vector DB | Load into pgvector |
| Scheduled refresh | Re-run weekly/on-demand |

---

## Epic: Infrastructure

| Story | Description |
|-------|-------------|
| Provision EKS | Terraform creates cluster |
| Provision database | Postgres + pgvector on RDS or in-cluster |
| Networking | VPC, subnets, security groups |
| DNS/Ingress | Reachable at kubebot.whatever.com |

---

## Epic: CI/CD

| Story | Description |
|-------|-------------|
| Build on push | GitHub Actions builds Docker images |
| Run tests | Unit + integration tests pass |
| Push to ECR | Images stored in AWS |
| Deploy to EKS | kubectl apply or ArgoCD sync |

---

## Epic: Observability

| Story | Description |
|-------|-------------|
| Health endpoint | /health returns status |
| Logs | Queryable logs (CloudWatch or Loki) |
| Metrics | Request latency, error rate |

---

## MVP Scope

### In

- Single question/answer
- Manual ETL trigger
- Basic deploy
- Health endpoint

### Out (for now)

- Conversation context
- Scheduled refresh
- ArgoCD GitOps
- Full observability

---

## Build Order

| Phase | What |
|-------|------|
| 1 | Terraform basics (S3, IAM) |
| 2 | FastAPI + LangChain RAG locally (Docker Compose) |
| 3 | ETL pipeline locally |
| 4 | Terraform EKS cluster |
| 5 | Deploy to EKS |
| 6 | GitHub Actions CI/CD |
