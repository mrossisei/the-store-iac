variable "namespace" {
  type    = string
  default = "the-store"
}

variable "quarantine" {
  description = "Servicios aislados retirando todos sus allows; no modifica pods."
  type        = set(string)
  default     = []
  validation {
    condition     = alltrue([for app in var.quarantine : contains(["ui", "catalog", "carts", "orders", "checkout"], app)])
    error_message = "quarantine admite ui, catalog, carts, orders y checkout."
  }
}

variable "pod_cidr" {
  type    = string
  default = "10.244.0.0/16"
  validation {
    condition     = can(cidrnetmask(var.pod_cidr)) && var.pod_cidr != "0.0.0.0/0"
    error_message = "Se requiere el CIDR IPv4 real de pods."
  }
}

variable "service_cidr" {
  type    = string
  default = "172.20.0.0/16"
  validation {
    condition     = can(cidrnetmask(var.service_cidr)) && var.service_cidr != "0.0.0.0/0"
    error_message = "Se requiere el CIDR IPv4 real de Services."
  }
}
