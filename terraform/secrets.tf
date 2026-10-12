resource "google_secret_manager_secret" "weather_api_key" {
  secret_id = "weather_api_key-${var.env}"
  labels    = local.labels

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "weather_api_key" {
  secret      = google_secret_manager_secret.weather_api_key.id
  secret_data = var.weather_api_key
}

resource "google_secret_manager_secret_iam_member" "ingest_accessor" {
  secret_id = google_secret_manager_secret.weather_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.ingest.member
}