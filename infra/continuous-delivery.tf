# The GitHub connection is authorized once in Cloud Build's console.
# Supply its full repository resource to enable the main-branch trigger.
variable "github_repository_resource" {
  type = string
  default = ""
}
variable "owner_email" { default = "" }
variable "google_client_id" { default = "" }
variable "frontend_origin" { default = "" }
resource "google_artifact_registry_repository" "images" {
  location = var.region
  repository_id = "sprout"
  format = "DOCKER"
  depends_on = [google_project_service.services]
}
resource "google_service_account" "build" {
  account_id = "sprout-build"
  display_name = "Sprout GitHub deployment"
}
resource "google_project_iam_member" "build_roles" {
  for_each = toset(["roles/run.admin", "roles/logging.logWriter"])
  project = var.project_id
  role = each.value
  member = "serviceAccount:${google_service_account.build.email}"
}
resource "google_service_account_iam_member" "build_runtime" {
  service_account_id = google_service_account.api.name
  role = "roles/iam.serviceAccountUser"
  member = "serviceAccount:${google_service_account.build.email}"
}
resource "google_artifact_registry_repository_iam_member" "build_images" {
  location = var.region
  repository = google_artifact_registry_repository.images.name
  role = "roles/artifactregistry.writer"
  member = "serviceAccount:${google_service_account.build.email}"
}
resource "google_storage_bucket_iam_member" "build_assets" {
  bucket = google_storage_bucket.frontend.name
  role = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.build.email}"
}
resource "google_cloudbuild_trigger" "main" {
  count = var.github_repository_resource == "" ? 0 : 1
  name = "sprout-main"
  location = var.region
  service_account = google_service_account.build.id
  repository_event_config {
    repository = var.github_repository_resource
    push { branch = "^main$" }
  }
  filename = "cloudbuild.yaml"
  substitutions = {
    _REGION = var.region
    _BUCKET_NAME = var.bucket_name
    _OWNER_EMAIL = var.owner_email
    _GOOGLE_CLIENT_ID = var.google_client_id
    _FRONTEND_ORIGIN = var.frontend_origin
  }
  depends_on = [google_project_iam_member.build_roles, google_service_account_iam_member.build_runtime, google_artifact_registry_repository_iam_member.build_images, google_storage_bucket_iam_member.build_assets]
}
output "build_service_account" { value = google_service_account.build.email }
