terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
  }
}

provider "docker" {}

resource "docker_network" "private_network" {
  name = "todo_network"
  lifecycle {
    create_before_destroy = true
  }
}

resource "docker_volume" "db_volume" {
  name = "postgres_data"
}

resource "docker_image" "postgres_img" {
  name = "postgres:16-alpine"
  keep_locally = true
}

resource "docker_container" "db_container" {
  name  = "todo_db"
  image = docker_image.postgres_img.image_id
  
  networks_advanced {
    name = docker_network.private_network.name
  }
  
  env = [
    "POSTGRES_USER=postgres",
    "POSTGRES_PASSWORD=supersecretpassword",
    "POSTGRES_DB=todo"
  ]
  
  volumes {
    volume_name    = docker_volume.db_volume.name
    container_path = "/var/lib/postgresql/data"
  }

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U postgres -d todo"]
    interval = "5s"
    timeout  = "5s"
    retries  = 5
  }
}

resource "docker_image" "app_img" {
  name = "todo_list_py-web:latest"
  keep_locally = true
}

resource "docker_container" "app_container" {
  name  = "todo_app"
  image = docker_image.app_img.image_id
  
  command = [
    "sh", "-c",
    "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"
  ]
  
  networks_advanced {
    name = docker_network.private_network.name
  }
  
  ports {
    internal = 8000
    external = 8001
  }
  
  env = [
    "POSTGRES_USER=postgres",
    "POSTGRES_PASSWORD=supersecretpassword",
    "POSTGRES_HOST=todo_db",
    "POSTGRES_PORT=5432",
    "POSTGRES_DB=todo"
  ]
  
  depends_on = [docker_container.db_container]
}