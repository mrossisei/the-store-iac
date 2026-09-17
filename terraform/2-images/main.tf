# Leemos los outputs de la capa 1 (patrón terraform_remote_state): así la capa
# de artefactos no necesita conocer cómo se creó el registry, sólo su dirección.
data "terraform_remote_state" "platform" {
  backend = "local"
  config = {
    path = var.platform_state_path
  }
}

locals {
  registry    = data.terraform_remote_state.platform.outputs.registry_host
  source_root = abspath(var.source_root)

  # Archivos que forman parte del contexto de build de cada servicio. Se
  # excluyen artefactos locales de compilación que no viajan en la imagen.
  excluded_prefixes = ["node_modules/", "target/", "dist/", ".git/", "build/"]

  source_files = {
    for svc, dir in var.services : svc => sort([
      for f in fileset("${local.source_root}/${dir}", "**") : f
      if !anytrue([for p in local.excluded_prefixes : startswith(f, p)])
    ])
  }

  # Tag = primeros 12 caracteres del SHA-1 de la concatenación de los hashes
  # de todos los archivos fuente del servicio (content-addressed tag).
  image_tags = {
    for svc, dir in var.services : svc => substr(
      sha1(join("\n", [for f in local.source_files[svc] : "${f}:${filesha1("${local.source_root}/${dir}/${f}")}"])),
      0, 12
    )
  }

  image_names = {
    for svc, dir in var.services : svc => "${local.registry}/${var.image_prefix}-${svc}:${local.image_tags[svc]}"
  }
}

# Build local con BuildKit (docker build). El bloque `build` sólo se ejecuta
# cuando cambia el nombre (= cambia el tag = cambió el código fuente).
resource "docker_image" "service" {
  for_each = var.services

  name         = local.image_names[each.key]
  keep_locally = var.keep_images_locally

  build {
    context    = "${local.source_root}/${each.value}"
    dockerfile = "Dockerfile"
    tag        = [local.image_names[each.key]]
    labels = {
      "org.opencontainers.image.source"   = "the-store/src/${each.value}"
      "org.opencontainers.image.revision" = local.image_tags[each.key]
    }
  }

  triggers = {
    source_hash = local.image_tags[each.key]
  }
}

# Push al registry local (docker push). keep_remotely evita que un destroy de
# esta capa borre las imágenes que los entornos todavía referencian.
resource "docker_registry_image" "service" {
  for_each = var.services

  name          = docker_image.service[each.key].name
  keep_remotely = true

  triggers = {
    image_id = docker_image.service[each.key].image_id
  }
}
