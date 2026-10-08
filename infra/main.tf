terraform {
  required_version = ">= 1.5"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
  }
}
variable "project_id" { type = string }
variable "region" { default = "us-central1" }
variable "bucket_name" { type = string }
provider "google" {
  project = var.project_id
  region = var.region
}
resource "google_project_service" "services" {
  for_each = toset(["run.googleapis.com", "cloudbuild.googleapis.com", "artifactregistry.googleapis.com", "bigquery.googleapis.com", "firestore.googleapis.com", "storage.googleapis.com", "secretmanager.googleapis.com", "iam.googleapis.com"])
  service = each.value
  disable_on_destroy = false
}
resource "google_storage_bucket" "frontend" {
  name = var.bucket_name
  location = "US"
  uniform_bucket_level_access = true
  force_destroy = false
  website {
    main_page_suffix = "index.html"
    not_found_page = "index.html"
  }
  versioning { enabled = true }
  depends_on = [google_project_service.services]
}
# UI objects remain private; the frontend service serves their contents.
resource "google_bigquery_dataset" "fitness" {
  dataset_id = "fitness"
  location = "US"
  delete_contents_on_destroy = false
  depends_on = [google_project_service.services]
}
resource "google_bigquery_table" "events" {
  dataset_id = google_bigquery_dataset.fitness.dataset_id
  table_id = "events"
  deletion_protection = true
  time_partitioning {
    type = "DAY"
    field = "received_at"
  }
  clustering = ["owner_id"]
  schema = jsonencode([
    {name="event_id",type="STRING",mode="REQUIRED"},
    {name="owner_id",type="STRING",mode="REQUIRED"},
    {name="received_at",type="TIMESTAMP",mode="REQUIRED"},
    {name="revision",type="INTEGER",mode="REQUIRED"},
    {name="payload",type="JSON",mode="REQUIRED"}
  ])
}
resource "google_firestore_database" "diary" {
  project = var.project_id
  name = "(default)"
  location_id = "nam5"
  type = "FIRESTORE_NATIVE"
  deletion_policy = "ABANDON"
  depends_on = [google_project_service.services]
}
resource "google_service_account" "api" {
  account_id = "sprout-api"
  display_name = "Sprout diary API"
}
resource "google_bigquery_dataset_iam_member" "writer" {
  dataset_id = google_bigquery_dataset.fitness.dataset_id
  role = "roles/bigquery.dataEditor"
  member = "serviceAccount:${google_service_account.api.email}"
}
resource "google_project_iam_member" "firestore" {
  project = var.project_id
  role = "roles/datastore.user"
  member = "serviceAccount:${google_service_account.api.email}"
}
output "asset_url" { value = "https://storage.googleapis.com/${var.bucket_name}/index.html" }
output "service_account" { value = google_service_account.api.email }
