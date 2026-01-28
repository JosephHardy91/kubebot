# IAM role for EKS pods to access AWS services
module "irsa_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.project_name}-app-role"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["default:kubebot-app", "default:kubebot-etl"]
    }
  }

  role_policy_arns = {
    secrets = aws_iam_policy.secrets_access.arn
  }
}

# Policy to read secrets from Secrets Manager
resource "aws_iam_policy" "secrets_access" {
  name        = "${var.project_name}-secrets-access"
  description = "Allow access to kubebot secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.app_secrets.arn
        ]
      }
    ]
  })
}

# Store secrets in AWS Secrets Manager
resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "${var.project_name}/app-secrets"
  description = "Kubebot application secrets"
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    DB_HOST        = aws_db_instance.main.address
    DB_PORT        = "5432"
    DB_NAME        = "kubebot"
    DB_USER        = "kubebot"
    DB_PASSWORD    = var.db_password
    OPENAI_API_KEY = var.openai_api_key
  })
}