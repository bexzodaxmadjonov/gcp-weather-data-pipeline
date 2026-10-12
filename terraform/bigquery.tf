resource "google_bigquery_dataset" "weather" {
  dataset_id = var.bq_dataset_id
  location   = var.region
  labels     = local.labels
}

resource "google_bigquery_table" "gold" {
  dataset_id          = google_bigquery_dataset.weather.dataset_id
  table_id            = "weather_realtime_gold"
  deletion_protection = false
  labels              = local.labels

  time_partitioning {
    type  = "DAY"
    field = "event_time"
  }

  schema = jsonencode([
    { name = "source_object", type = "STRING", mode = "REQUIRED" },
    { name = "event_time", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "location_name", type = "STRING", mode = "REQUIRED" },
    { name = "location_lat", type = "FLOAT", mode = "NULLABLE" },
    { name = "location_lon", type = "FLOAT", mode = "NULLABLE" },
    { name = "location_type", type = "STRING", mode = "NULLABLE" },
    { name = "ingested_at_utc", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "weather_temperature", type = "FLOAT", mode = "NULLABLE" },
    { name = "weather_humidity", type = "FLOAT", mode = "NULLABLE" },
    { name = "weather_windSpeed", type = "FLOAT", mode = "NULLABLE" },
    { name = "weather_cloudCover", type = "FLOAT", mode = "NULLABLE" },
    { name = "weather_precipitationProbability", type = "FLOAT", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_dataset_iam_member" "airflow_editor" {
  dataset_id = google_bigquery_dataset.weather.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.airflow.member
}

resource "google_project_iam_member" "airflow_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.airflow.member
} 