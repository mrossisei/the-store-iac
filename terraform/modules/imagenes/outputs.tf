output "repositories" {
  description = "URL de cada repositorio ECR."
  value       = { for service, repo in aws_ecr_repository.this : service => repo.repository_url }
}
