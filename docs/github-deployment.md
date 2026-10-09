# GitHub → Cloud Build → Sprout

Repository: https://github.com/nikhnara/sprout-fitness

GCP project supplied by the owner: `sprout-fitness`. Project access is verified and required APIs are enabled. The user completed manual provisioning. Read-only checks confirm the `sprout-fitness-ui` bucket in `US-CENTRAL1`, Firestore `(default)` in `nam5`, and `sprout-github` in COMPLETE state. IAM grants and BigQuery setup are user-reported, not yet independently verified. Planned region: `us-central1`. See `infra/sprout.tfvars.example`; no credentials belong in this file.

The production source of truth is `main`. Google Cloud fetches commits through its GitHub connection and executes `cloudbuild.yaml`. No local deployment or GitHub-stored service-account key is required.

## Release path

1. Push or merge changes into `main`.
2. Cloud Build validates its configuration, runs JavaScript and Python tests, builds the API container, and pushes an image tagged with the full Git commit SHA.
3. It builds the HTTPS frontend container and deploys the API image to Cloud Run using the separate `sprout-api` runtime identity.
4. It generates the public frontend configuration in the build workspace, uploads frontend assets to GCS, then uploads `index.html` last and deploys the HTTPS frontend. It never commits generated cloud configuration back to Git.
5. BigQuery and Firestore are provisioned once, not recreated on every release. Diary JSON stays in private backend storage, outside the frontend bucket and Git repository.

## One-time setup reference

- Resources were created manually. Do not apply Terraform over them without importing them first. The `infra/` files describe the intended resources; they have not been imported or validated against live state. It creates the existing storage/API prerequisites plus an Artifact Registry repository and `sprout-build` service account.
- No purchased domain is required. The pipeline deploys `sprout-web`, a small Cloud Run service reading UI assets from the private GCS bucket. Planned HTTPS origin: `https://sprout-web-5993706635.us-central1.run.app`. Verify this origin after deployment. Its runtime identity can read only the UI bucket; it cannot read diary storage.
- Enable Google login in Firebase Authentication, add the actual frontend hostname to authorized domains, and provide the public Firebase web configuration through `_FIREBASE_CONFIG`. Set the diary owner email in `_OWNER_EMAIL`.
- In Cloud Build, create a GitHub connection in `us-central1`, authorize the Google GitHub app for this repository only, then link the repository. Copy its full resource: `projects/PROJECT/locations/us-central1/connections/CONNECTION/repositories/REPOSITORY`.
- Supply `github_repository_resource`, `owner_email`, `firebase_config`, and `frontend_origin` to Terraform. Its `sprout-main` trigger watches `^main$`, uses `cloudbuild.yaml`, and runs as `sprout-build`. Leave the repository resource empty until the other setup is ready; no trigger is created in that case.
- Run the trigger once against the committed main branch. Then validate owner sign-in, saving, BigQuery JSON ingestion, restore, and conflict protection. A successful build alone does not verify the full diary flow.

The build identity has Cloud Run admin and logging writer at project scope, Artifact Registry writer on the Sprout repository, object admin on the frontend bucket, and permission to act as the API and frontend runtime identities. Cloud Run is publicly reachable but every diary route verifies the owner's Firebase ID token. The Cloud Build connection uses Google's managed authorization; no downloaded account key is needed.

## Trigger substitutions

| Name | Value |
| --- | --- |
| `_REGION` | `us-central1` |
| `_BUCKET_NAME` | Dedicated UI bucket name |
| `_OWNER_EMAIL` | Diary owner's Google email |
| `_FIREBASE_CONFIG` | Public Firebase web configuration as a JSON object |
| `_FRONTEND_ORIGIN` | Dedicated HTTPS origin, without a trailing slash |

These are configuration identifiers; private keys and tokens must never be committed. Protect `main` and limit repository write access: a push to main is production deployment authority.

## Failures and rollback

Tests or configuration failures stop deployment before changes to production. API and GCS deployment are separate operations, not one atomic release; an upload failure can leave the previous UI with the new API. Keep API changes backward compatible. Revert the problematic commit on main to trigger a new build of the previous code. GCS object versioning is also enabled; no destructive bucket synchronization runs.

The local `scripts/deploy.sh` is disabled; releases use Cloud Build. Terraform and live cloud integration have not yet been exercised in a real project.

References: [Cloud Build triggers](https://docs.cloud.google.com/build/docs/automating-builds/create-manage-triggers), [Deploy to Cloud Run](https://docs.cloud.google.com/build/docs/deploying-builds/deploy-cloud-run), [Build service accounts](https://docs.cloud.google.com/build/docs/securing-builds/configure-user-specified-service-accounts).

Google documents the predictable Cloud Run service URL format at https://docs.cloud.google.com/run/docs/triggering/https-request#deterministic_url. The planned URL is not live yet.

Requested production domain: `gamna.app`. DNS and HTTPS connection are not confirmed. The Firebase project supplied (`sprout-fitness-1eb7f`) differs from the original infrastructure project (`sprout-fitness`); this split is confirmed. The API validates Firebase tokens against the auth project and uses the infrastructure project explicitly for data clients.

## Current Firebase release settings

Use the checked-in `_FIREBASE_CONFIG` default (public Firebase web identifiers) and `_REGION=us-central1`. Set `_BUCKET_NAME=sprout-fitness-ui`, `_OWNER_EMAIL` to the owner's Google account, and `_FRONTEND_ORIGIN=https://gamna.app`. Firebase Authentication belongs to `sprout-fitness-1eb7f`; resource operations and Cloud Build belong to `sprout-fitness`. Do not replace the Firebase `authDomain` with `gamna.app` just because the site domain changed; the auth helper hosting would also need configuration.

Adding `gamna.app` to Firebase authorized domains is not a DNS or TLS setup. Domain routing through Cloudflare remains to be configured. The first build may be used to create the Cloud Run services; live login and API calls must be tested from the configured frontend origin after domain setup. No analytics SDK is loaded even though the public config includes a measurement ID.
