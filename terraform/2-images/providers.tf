provider "docker" {
  host = var.docker_host

  # El registry local no tiene autenticación ni TLS. El provider necesita
  # saberlo explícitamente: el prefijo "http://" le indica que consulte el
  # digest por HTTP plano (sin él asume HTTPS) y auth_disabled evita que
  # busque credenciales en ~/.docker/config.json.
  registry_auth {
    address       = "http://${data.terraform_remote_state.platform.outputs.registry_host}"
    auth_disabled = true
  }
}
