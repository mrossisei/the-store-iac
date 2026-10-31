output "clusters" {
  description = "Identidades comprobadas por SSM, TLS y API; no contiene credenciales."
  value = {
    a = { context = data.external.access.result.context_a, uid = data.external.access.result.uid_a }
    b = { context = data.external.access.result.context_b, uid = data.external.access.result.uid_b }
  }
}
