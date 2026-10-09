# Gamna review — October 9, 2026

## Product decisions and research

- Login precedes diary access. Firebase's verified UID determines the server-side diary path; clients cannot select an owner. Existing owner hash identities remain stable. Anonymous local data is offered for explicit migration only to the original owner account.
- Food discovery now exposes the full 7,793-record library through diet and category filters, pagination, preparation-specific names, common Indian ingredient synonyms, recipe templates, recent-meal repeat and exact barcode lookup.
- USDA distinguishes analytical, survey, branded and historic sources. SR Legacy's final release was April 2018; these records must not be represented as current branded products. https://fdc.nal.usda.gov/data-documentation/
- Open Food Facts is community-maintained and cannot be treated as regulatory certification. Exact barcode requests are cached and globally limited to 12/minute, below the documented 15/minute product limit. Missing nutrients remain null. No search-as-you-type calls. ODbL data and CC BY-SA image attribution appear in the UI. https://openfoodfacts.github.io/openfoodfacts-server/api/
- Recipe templates are modeled ingredient totals, not measured FSSAI/IFCT values. Added paneer bhurji, palak paneer, soya masala, khichdi, aloo gobi, bhindi masala, vegetable pulao and curd rice. Shared staple illustrations are illustrative, not exact dish photographs.
- Activity providers: HASfit resistance-band library, Fitness Blender workout filters, Yoga With Adriene free library. Gamna does not prescribe sets, reps or programs. https://hasfit.com/workouts/home/strength-weight-training/full-body-resistance-band-workout/ ; https://www.fitnessblender.com/videos ; https://yogawithadriene.com/free-yoga-videos/
- Shortcut HTTP support is documented by Apple. Device measurements arrive in a private review inbox through an expiring upload-only key. No claim of direct HealthKit access. https://support.apple.com/guide/shortcuts/request-your-first-api-apd58d46713f/ios

## Data and security checks

Live read-only pre-release audit: gamna.app certificate and mapping Ready; no public principals on UI bucket; infrastructure Firestore rules explicitly deny all direct client reads/writes; Firestore diaries empty; BigQuery events count zero. Therefore no existing end-to-end signed-in write could be confirmed.

Automated API tests use Flask with isolated cloud adapters: two-user isolation, forged/missing credentials, origin rejection, revision conflicts, event idempotency, durable analytics retry, photo validation/isolation, upload-only token revocation, import deduplication and distributed rate-limit behavior. They are not a third-party penetration test or a substitute for live Firebase sign-in verification.

DOM interaction tests run in a DOM library without a browser, real account or network. They cover welcome gating, onboarding, labeled cards, live portion totals, save, all sections, poses, account changes and logout. Browser visual review was blocked by an unavailable admin-enforced security check; no browser workaround was used.

Photo companions use a browser crop and SVG color quantization over a shaded illustrated body, with 12 pose configurations. They are not rigged 3D models or AI-generated likenesses.

## Development

- `npm ci --ignore-scripts && npm test`
- Install `server/requirements.txt`, then `python -m unittest discover -s tests -p 'test_*.py'`.
- `python tests/preview_server.py` serves a localhost-only fake-account UI fixture at port 5174. This fixture is outside `dist` and never deployed.
- Infrastructure resources retain their existing Sprout identifiers to avoid recreating data stores. Public product copy uses Gamna.

## Required live acceptance

Sign in on gamna.app, explicitly import the earlier local diary if desired, log one entry, reload and verify the same diary. Confirm its UID-hashed Firestore document and matching BigQuery event. Repeat with a second account and verify an empty independent diary. Review desktop/mobile rendering and a real iPhone Shortcut with explicit health permissions.

## Dependency checks

The initial macOS Python 3.9 environment selected older vulnerable dependency versions. Release checks were moved to Python 3.12 (matching the containers), and patched floors added for Pillow, requests, urllib3, anyio, h2, hpack and msgpack. Container pip is upgraded to a patched version. JavaScript lockfile audit returned zero known vulnerabilities.

Final Python 3.12 dependency scan: no known vulnerabilities reported. JavaScript tests: 17; Python tests: 27; DOM interaction flow: passed. Dependency findings do not establish that an application has no vulnerabilities.
