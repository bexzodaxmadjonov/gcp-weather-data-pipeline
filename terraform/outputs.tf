output "function_url" {
  value = google_cloudfunctions2_function.ingest.service_config[0].uri
}

output "bronze_bucket" {
  value = google_storage_bucket.bronze.name
}

output "silver_bucket" {
  value = google_storage_bucket.silver.name
}

output "bq_gold_table" {
  value = "${var.project_id}.${google_bigquery_dataset.weather.dataset_id}.${google_bigquery_table.gold.table_id}"
}