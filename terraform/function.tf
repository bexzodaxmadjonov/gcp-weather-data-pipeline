resource "google_storage_bucket" "function_source" {
  name                        = "${var.bucket_name}-fn-source"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels
}

data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../function"
  output_path = "${path.module}/function-source.zip"
  excludes    = ["__pycache__", ".venv"]
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "ingest-${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.function_zip.output_path
}

resource "google_cloudfunctions2_function" "ingest" {
  name     = "weather-ingest-${var.env}"
  location = var.region
  labels   = local.labels

  build_config {
    runtime     = "python311"
    entry_point = "ingest"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.function_zip.name
      }
    }
  }

  service_config {
    service_account_email = google_service_account.ingest.email
    available_memory      = "256M"
    timeout_seconds       = 60
    max_instance_count    = 1
    ingress_settings      = "ALLOW_ALL"

    environment_variables = {
      BUCKET_NAME = google_storage_bucket.bronze.name
      LOCATIONS   = join(",", var.locations)
    }

    secret_environment_variables {
      key        = "WEATHER_API_KEY"
      project_id = var.project_id
      secret     = google_secret_manager_secret.weather_api_key.secret_id
      version    = "latest"
    }
  }

  depends_on = [
    google_secret_manager_secret.weather_api_key,
    google_secret_manager_secret_iam_member.ingest_accessor,
  ]
}

resource "google_cloud_run_service_iam_member" "scheduler_invoker" {
  location = google_cloudfunctions2_function.ingest.location
  service  = google_cloudfunctions2_function.ingest.name
  role     = "roles/run.invoker"
  member   = google_service_account.scheduler.member
}

