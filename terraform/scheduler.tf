resource "google_cloud_scheduler_job" "ingest" {
  name      = "weather-ingest-${var.env}"
  region    = var.region
  schedule  = "*/10 * * * *"
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.ingest.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = google_cloudfunctions2_function.ingest.service_config[0].uri
    }
  }
}