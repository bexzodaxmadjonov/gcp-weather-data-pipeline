resource "google_storage_bucket" "bronze" {
  name                        = "${var.bucket_name}-bronze"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels
}

resource "google_storage_bucket" "silver" {
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels
}

resource "google_storage_bucket_iam_member" "ingest_bronze_writer" {
  bucket = google_storage_bucket.bronze.name
  role   = "roles/storage.objectCreator"
  member = google_service_account.ingest.member
}

resource "google_storage_bucket_iam_member" "airflow_bronze_reader" {
  bucket = google_storage_bucket.bronze.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.airflow.member
}

resource "google_storage_bucket_iam_member" "airflow_silver_writer" {
  bucket = google_storage_bucket.silver.name
  role   = "roles/storage.objectCreator"
  member = google_service_account.airflow.member
}

resource "google_storage_bucket_iam_member" "airflow_silver_reader" {
  bucket = google_storage_bucket.silver.name
  role   = "roles/storage.objectViewer"
  member = google_service_account.airflow.member
}

