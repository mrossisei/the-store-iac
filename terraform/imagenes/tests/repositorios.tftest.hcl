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
run "build_images_requires_version" {
  command = plan
  variables { build_images = true }
  expect_failures = [var.build_images]
}
run "default_does_not_build" {
  command = plan
  assert {
    condition     = length(terraform_data.publicacion) == 0
    error_message = "Por defecto Terraform no construye ni publica."
  }
}
run "explicit_build_runs_publisher" {
  command = plan
  variables {
    build_images     = true
    app_version      = "v1"
    release_manifest = "releases.json"
  }
  assert {
    condition     = length(terraform_data.publicacion) == 1
    error_message = "build_images debe disparar la publicación."
  }
}
