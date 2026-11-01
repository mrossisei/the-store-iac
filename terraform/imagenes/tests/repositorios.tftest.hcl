mock_provider "aws" {}
run "five_immutable_repositories" {
  command = plan
  assert {
    condition     = length(module.repositories.repositories) == 5
    error_message = "Se requieren los cinco repositorios."
  }
  assert {
    condition     = length(output.images) == 0
    error_message = "Crear repositorios no selecciona ni publica versiones."
  }
}
run "reject_unknown_version" {
  command = plan
  variables { app_version = "latest" }
  expect_failures = [var.app_version]
}
