# Outputs de las capas anteriores (patrón terraform_remote_state).
data "terraform_remote_state" "platform" {
  backend = "local"
  config = {
    path = var.platform_state_path
  }
}

data "terraform_remote_state" "images" {
  backend = "local"
  config = {
    path = var.images_state_path
  }
}

provider "kubernetes" {
  config_path    = data.terraform_remote_state.platform.outputs.kubeconfig_path
  config_context = data.terraform_remote_state.platform.outputs.kube_context
}
