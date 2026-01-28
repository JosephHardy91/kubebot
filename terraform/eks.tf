module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.project_name
  cluster_version = "1.29"

  cluster_endpoint_public_access = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # EKS Managed Node Group
  eks_managed_node_groups = {
    default = {
      name           = "${var.project_name}-nodes"
      instance_types = [var.eks_node_instance_type]

      min_size     = 1
      max_size     = 3
      desired_size = var.eks_node_count

      # Needed for pgvector and general workloads
      disk_size = 50
    }
  }

  # Allow nodes to pull from ECR
  enable_cluster_creator_admin_permissions = true

  tags = {
    Name = var.project_name
  }
}