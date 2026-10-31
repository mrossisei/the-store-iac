variable "private_subnet_ids" {
  type = map(string)
  validation {
    condition     = toset(keys(var.private_subnet_ids)) == toset(["a", "b"])
    error_message = "Se requieren las subredes privadas a y b."
  }
}
variable "application_security_group_id" { type = string }
variable "instance_profile_name" { type = string }
variable "ami_id" { type = string }
variable "instance_type" { type = string }
variable "environment" { type = any }
variable "tools" { type = any }
