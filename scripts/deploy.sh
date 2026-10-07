#!/usr/bin/env bash
set -euo pipefail
# Run only after provisioning infra and configuring OAuth. Uses your local gcloud login.
: "${PROJECT_ID:?Set PROJECT_ID}" "${BUCKET_NAME:?Set BUCKET_NAME}" "${OWNER_EMAIL:?Set OWNER_EMAIL}" "${GOOGLE_CLIENT_ID:?Set GOOGLE_CLIENT_ID}" "${FRONTEND_ORIGIN:?Set FRONTEND_ORIGIN to the authorized HTTPS origin}"
REGION="${REGION:-us-central1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASK_ENV_FILE="$(mktemp)"
trap 'rm -f "$TASK_ENV_FILE"' EXIT
export PROJECT_ID OWNER_EMAIL GOOGLE_CLIENT_ID FRONTEND_ORIGIN TASK_ENV_FILE
python3 - <<'PY'
import os,json
from pathlib import Path
Path(os.environ['TASK_ENV_FILE']).write_text(json.dumps({'GOOGLE_CLOUD_PROJECT':os.environ['PROJECT_ID'],'GOOGLE_CLIENT_ID':os.environ['GOOGLE_CLIENT_ID'],'OWNER_EMAIL':os.environ['OWNER_EMAIL'],'ALLOWED_ORIGINS':os.environ['FRONTEND_ORIGIN'],'BIGQUERY_TABLE':os.environ['PROJECT_ID']+'.fitness.events'}))
PY
gcloud run deploy sprout-api --source "$ROOT/server" --project "$PROJECT_ID" --region "$REGION" --service-account "sprout-api@${PROJECT_ID}.iam.gserviceaccount.com" --env-vars-file "$TASK_ENV_FILE" --allow-unauthenticated --max-instances 2 --memory 512Mi --quiet
# Cloud Run accepts requests publicly; every diary route verifies the owner Google ID token.
API_URL="$(gcloud run services describe sprout-api --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
export API_URL ROOT
python3 - <<'PY'
import json,os
from pathlib import Path
Path(os.environ['ROOT']+'/dist/config.js').write_text('window.SPROUT_CONFIG = '+json.dumps({'apiUrl':os.environ['API_URL'],'googleClientId':os.environ['GOOGLE_CLIENT_ID']})+';\n')
PY
gcloud storage rsync "$ROOT/dist" "gs://${BUCKET_NAME}" --recursive --project "$PROJECT_ID"
# Avoid stale configuration while iterating; no delete-unmatched flag is used.
gcloud storage objects update "gs://${BUCKET_NAME}/config.js" "gs://${BUCKET_NAME}/index.html" --cache-control='no-cache' --project "$PROJECT_ID"
printf 'Frontend: https://storage.googleapis.com/%s/index.html\nAPI: %s\n' "$BUCKET_NAME" "$API_URL"
