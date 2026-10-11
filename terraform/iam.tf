locals {
  labels = {
    env   = var.env
    owner = var.owner
    app   = "weather-pipeline"
  }
}

resource "google_service_account" "ingest" {
  account_id   = "sa-weather-ingest-${var.env}"
  display_name = "Weather ingest function (${var.env})"
}

resource "google_service_account" "airflow" {
  account_id   = "sa-weather-airflow-${var.env}"
  display_name = "Weather Airflow (${var.env})"
}

resource "google_service_account" "scheduler" {
  account_id   = "sa-weather-scheduler-${var.env}"
  display_name = "Weather scheduler invoker (${var.env})"
}
