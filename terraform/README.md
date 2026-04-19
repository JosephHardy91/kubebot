# Terraform — Cloud Deployment (In Progress)

This directory contains Terraform configuration for deploying Kubebot to AWS (EKS + RDS + ECR + VPC).

> **Status:** Work in progress. The application currently runs locally via Docker Compose.
> See the [backend README](../backend/README.md) for local setup instructions.

## Resources

- `main.tf` — Provider and backend configuration
- `vpc.tf` — VPC and networking
- `eks.tf` — EKS cluster
- `rds.tf` — PostgreSQL (RDS)
- `ecr.tf` — Elastic Container Registry
- `iam.tf` — IAM roles and policies
- `variables.tf` — Input variables
- `outputs.tf` — Stack outputs
