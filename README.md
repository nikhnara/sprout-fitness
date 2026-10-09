# Sprout

A personal, mobile-first fitness and calorie tracker. Navy and lime dashboard, animated 3D-style companion, weighed food portions, custom foods and recipes, daily nutrition, weight, sleep and exercise, editable goals, and honest progress tracking.

## Current status

The frontend is functional and saves on this device. Cloud API, schema and deployment files are prepared, but **not deployed**. Source is published to `nikhnara/sprout-fitness`. GCP project `sprout-fitness` is verified and APIs enabled; the GitHub connection is complete; deployment remains pending. The avatar is generated from the three photos selected by the user. Raw photos are not included in the frontend. Browser visual QA is unverified because the environment's browser policy check was unavailable.

### Run locally

`python3 -m http.server 5173 --directory dist`

Open http://localhost:5173. No frontend package installation/build is required. Use a modern browser supporting ES modules, structuredClone and crypto.randomUUID (HTTPS or localhost).

### Features

- Daily calories, protein, carbohydrates, fat, fiber, sleep, weight, and exercise minutes.
- Vegetarian-with-dairy default, all-food and plant-food filters, gram and USDA portion conversions.
- 7,793 official USDA SR Legacy records with record links, preserved missing values, and imported gram conversions.
- Custom nutrition labels and recipes calculated from ingredient weights and finished cooked batch weight.
- Meal editing/deletion, date navigation, daily quests and transparent rule-based suggestions.
- Weight differences and date-scaled trend graph; weekly averages report sample counts. Missing days are not zero.
- JSON backup, single-owner Google sign-in, manual initial sync and automatic sync after signed-in edits once configured.
- Firestore stores the latest diary; BigQuery stores timestamped JSON snapshots for analysis. Optimistic revisions protect against overwriting another device. Failed BigQuery exports remain in an outbox and retry on sync.

## Preferred deployment: GitHub first

Push to `main` in `nikhnara/sprout-fitness`; Google Cloud Build fetches the commit, runs checks, deploys the API and publishes the GCS UI. See [the setup guide](docs/github-deployment.md). The pipeline is prepared; its cloud connection and first live deployment are pending. Do not use the local deploy script for normal releases.

## Cloud setup from scratch (infrastructure reference)

1. Create a new Google Cloud project and attach billing. Choose a budget alert. Send the project ID back to continue assisted deployment. Do not reuse another application's production project.
2. Install Terraform if needed; authenticate your local Google Cloud CLI and application default credentials. Use a dedicated new project; the provided IAM roles are scoped to that project/dataset.
3. From `infra`, run `terraform init`, then `terraform plan -var='project_id=YOUR_PROJECT_ID' -var='bucket_name=YOUR_UNIQUE_BUCKET'`. Review the plan before `terraform apply` with the same variables. It creates a private **UI-only** GCS bucket, private BigQuery dataset and JSON events table, Firestore database, API service account, and required APIs. Never upload diary JSON or secrets to the UI bucket. Organization policies may prohibit public buckets; use an approved hosting configuration in that case.
4. Enable Google as a provider in Firebase Authentication, register the web app, and add the frontend hostname to Firebase authorized domains. Use the public Firebase web config as `_FIREBASE_CONFIG` in Cloud Build. The API verifies Firebase ID tokens with Firebase Admin and limits access to the configured owner's verified Google account.
5. Frontend files remain in private GCS storage, served by `sprout-web` on Cloud Run. The selected custom domain is `gamna.app`; adding it to Firebase authorized domains does not establish DNS or HTTPS hosting. Those must be configured separately before using it as the production origin.
6. Releases come from GitHub through `cloudbuild.yaml`. The local deploy script has been retired. Configure `_BUCKET_NAME`, `_OWNER_EMAIL`, `_FIREBASE_CONFIG`, and `_FRONTEND_ORIGIN` on the trigger after confirming the resource project. No downloaded service-account key is required.
7. Replace `YOUR_PROJECT_ID` in `server/schema.sql` and run it with BigQuery to create the deduplicated and latest-state views. Streaming insert IDs are best-effort; use the views for analysis.
8. Verify the API rejects unauthenticated and non-owner requests; sign in as owner, add a disposable test meal, sync, confirm its JSON in BigQuery, restore on a second browser, and exercise a stale-revision conflict. Cloud integration remains unverified until these checks pass.

No resources have been created and no cloud costs have been incurred by this project setup. Cloud Run, Firestore, BigQuery, GCS and optional load balancers can incur charges once deployed. Min instances default to zero; max instances are capped at two.

### JSON shape

The BigQuery event has `event_id`, hashed Google `owner_id`, server `received_at`, increasing `revision`, and `payload` of BigQuery JSON type. Payload contains `version`, `profile`, `days`, `customFoods`, and `recipes`. Each food entry keeps food ID, source record, grams, meal, and nutrient snapshot, so future catalog changes do not silently recalculate the past.

### Data and research

- [USDA downloadable data](https://fdc.nal.usda.gov/download-datasets/): imported SR Legacy April 2018, a stable archival dataset rather than a claim of latest branded nutrition. `dist/data-provenance.json` includes archive URL, SHA-256 and count. Rebuild with `python3 scripts/import_usda.py /path/to/archive.zip`.
- [ICMR–NIN IFCT 2017](https://www.nin.res.in/ebooks/IFCT2017.pdf): authoritative Indian food reference identified, but not imported. No FSSAI/FSAI certification claimed. Indian cooked dishes vary by recipe; use the recipe builder rather than presenting a generic dish as a measured regulatory value.
- [Cronometer food workflow](https://support.cronometer.com/hc/en-us/articles/360018239492-Foods-Overview) informed custom foods, recipes and visible nutrition provenance. This is product-workflow research, not a user-review study.
- [Apple HealthKit](https://developer.apple.com/documentation/healthkit): native iPhone/Watch data access requires an authorized native integration. No direct Apple Fitness web connection is implemented; manual logging is ready.
- [Google static GCS hosting](https://docs.cloud.google.com/storage/docs/hosting-static-website) and [BigQuery JSON](https://docs.cloud.google.com/bigquery/docs/json-data).

Diet tags are conservative category/keyword heuristics, not ingredient-level guarantees. Review labels for strict dietary restrictions. Unknown nutrient values remain null, not zero. Grams describe edible portions with preparation retained in food names. Initial nutrition targets are example values; user age, height, weight, activity and medical circumstances were not provided, so no personalized calorie prescription is calculated.

### Known limitations

- Preview and browser interactions were not visually verified due to browser access restrictions. Node calculation/catalog tests and Python request-validation tests are included.
- The JSON snapshot API has an 800 KB limit; a larger long-term diary needs per-day event storage before this ceiling. The UI does not silently delete history.
- Sync is device-first with explicit conflict handling; it does not automatically merge concurrent device edits. Export local changes before restoring cloud state. Failed BigQuery writes retry when the app next syncs; no unattended retry scheduler is deployed.
- A companion image with animation provides a dimensional look; this is not a rigged 3D avatar editor. The current avatar is a generated likeness, displayed as a layered image.
- WebMCP exposes a feature-detected read-only daily summary, but runtime validation was unavailable.
- Google Fonts loads from its CDN, with system fallbacks. No analytics or advertising scripts.

## Checks

`node --test tests/*.test.mjs`

`python3 -m unittest discover -s tests -p 'test_*.py'`

`node --check dist/app.js`

`python3 -m py_compile server/app.py server/validation.py`

## GitHub

Repository: [nikhnara/sprout-fitness](https://github.com/nikhnara/sprout-fitness). The app and pipeline are on `main`. Future releases use the Cloud Build workflow once its GCP connection is configured. Do not commit credentials or personal diary exports.

## Personal experience revision — October 7, 2026

The earlier companion has been removed from the UI. A temporary monogram reserves the avatar position until the user supplies a face photo for a male likeness. The new dark spatial stage uses pointer-responsive perspective and layered live metrics, with reduced-motion support; it is not a fully rigged 3D character.

Food Studio now opens on familiar foods and combinations, with a meal tray that recalculates every portion before a deliberate log action. Chobani/yogurt/yoghurt/yogrut search resolves the curated Chobani 20g Vanilla 190g cup. Its photographed label reads 140 kcal, 20g protein, 3g fat, 9g carbohydrate and **2g fiber**. Source: https://giantfood.com/groceries/product/chobani-20g-protein-lowfat-vanilla-greek-yogurt-cup-6-7-oz-cup/370506. The photo is product imagery supplied via Giant Food/Syndigo, not generated packaging; rights remain with its owners. Other flavors and sizes are not assumed to match.

Chana curry and latte presets carry explicit estimate labels from the user's supplied prior conversation. The curry image is AI-generated illustrative food photography. Historical meals were not imported because their dates are unknown. New profiles use the prior 2,100 kcal / 95g protein goals. Existing unchanged starter targets (2,000/100) migrate once; customized values remain intact.

Training includes a draft no-door-anchor upper/lower split, a three-day full-body fallback, and 12-week progression guidance. HASfit source: https://hasfit.com/workouts/home/strength-weight-training/full-body-resistance-band-workout/. General activity source: https://www.cdc.gov/physical-activity-basics/guidelines/adults.html. This is not a guaranteed-results or personalized clinical program.

Validation: seven JavaScript nutrition/catalog/preset tests and five Python validation tests pass. Browser access was retried and remains blocked by the unavailable admin-policy check, so visual and interaction QA remain unverified. GCS, BigQuery and remote GitHub deployment remain pending as before.

## Food studio revision — October 8, 2026

Separate food illustrations are wired for chana, rice, dry oats, cooked oatmeal, dal, rajma, roti, idli, dosa, curd, paneer, dry soya, butter, ghee and oil. The generated poha asset is reserved until a suitable nutrient source is added. Images are illustrative and do not determine nutrients. The earlier combined chana/rice image appears only on the combination preset.

Seven recipe templates expose editable ingredient grams, cooking-fat shortcuts, and finished batch yield. All dish templates are estimates, not authoritative measurements of a cooked dish. The meal tray recalculates on each valid keystroke and blocks logging invalid weights. Saved entries retain nutrient snapshots.

Paneer: Amul Malai manufacturer's label (323 kcal, 20 g protein, 25 g fat, 4.5 g carbs per 100 g; unquantified fiber remains null). Soya: Bon Vegan dry chunks, manufacturer catalogue page 33. The EU label's 27 g available carbohydrate and 8.8 g fiber are combined to approximate USDA total-carbohydrate reporting; this is documented in the food note. This is not a verified Nutrela record.

Checks: 10 JavaScript tests and 5 Python validation tests pass. First review covered portion scaling, oil additions, cooked yield, missing values and invalid quantities. Second source review covered separate image paths, touch targets, small-screen rules, sources and reduced motion. Actual rendered desktop/mobile visual and interaction reviews remain blocked by the browser security-policy check. GCS, BigQuery, and remote GitHub remain unconnected.

## Firebase migration

The frontend now uses Firebase Google popup sign-in and requests a current ID token for each API call. Firebase manages login persistence and token refresh; tokens are not included in diary JSON exports. The API verifies Firebase token signatures, issuer, audience and expiry via Firebase Admin, then requires the configured owner's verified email and Google provider. Standard verification does not perform an additional revocation lookup. Sign-out retains the local diary on this device.

The user supplied Firebase project `sprout-fitness-1eb7f`, which differs from the previously verified infrastructure project `sprout-fitness`. The user confirmed this split: Firebase Auth is in `sprout-fitness-1eb7f`; hosting, Firestore and BigQuery stay in `sprout-fitness`. The public Firebase config is in `config/firebase.web.json` and the build defaults. Runtime `FIREBASE_PROJECT_ID` selects the authentication project independently from storage. Firebase UID-based storage identities differ from the former direct-Google identities; any existing cloud diaries would need an explicit migration (none were deployed by this task).

Unit tests cover token retrieval delegation and owner policy with mocked SDK boundaries; they do not constitute a live Firebase/browser integration test.

Verified user-created resources: UI bucket `sprout-fitness-ui` (`US-CENTRAL1`), Firestore `(default)` (`nam5`), and Cloud Build connection `sprout-github` (`COMPLETE`). Terraform is a reference until existing resources are imported.
