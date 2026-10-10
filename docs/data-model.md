# Gamna data model

## Systems and ownership

Firebase Authentication in `sprout-fitness-1eb7f` owns Google login identities and tokens. View registered accounts under Firebase → Authentication → Users in **that project**. Passwords and tokens are never copied into analytics.

The application and all diary/catalog reporting live in `sprout-fitness`. Every private record is keyed by `owner_id = SHA256(Firebase UID)`. Clients cannot select an owner ID; the API derives it from the verified token. Direct Firestore client access is denied by rules. BigQuery is administrator-only; the browser has no BigQuery credentials or query endpoint.

Firestore is the transactional source of truth. BigQuery is the reporting mirror. The catalog is authored in version-controlled source records, exported reproducibly and loaded by Cloud Build into BigQuery; the same records are used by the website. BigQuery is not queried on every keystroke.

## Operational collections

| Path | Purpose |
|---|---|
| `users/{owner}` | Auth project and last observed sign-in; export marker |
| `diaries/{owner}` | Current diary snapshot, revision, updated time |
| `diaries/{owner}/outbox/{event}` | Durable history awaiting BigQuery export |
| `profiles/{owner}` | Private sanitized photo and connection metadata |
| `diaries/{owner}/imports/{sourceHash}` | Activity awaiting explicit user review |
| `connections/{keyHash}` | Revocable limited-purpose activity credential |
| `foodCache/{barcode}` | Public nutrition product lookup cache |
| `requestLimits/{owner}` | Per-account abuse protection |

## BigQuery: `sprout-fitness.fitness`

| Table/view | Grain and relationships |
|---|---|
| `events` | One accepted diary revision; event_id, owner_id, received_at, revision, payload JSON |
| `events_deduplicated` | Exact owner/event deduplication over streaming retries |
| `latest_diaries` | Highest accepted revision per owner |
| `food_catalog` | One food_id, linked to source_id; canonical record JSON, per-100g basis |
| `food_sources` | One source_id, provenance URL and available source release date |
| `food_nutrients` | food_id + nutrient; nullable amount and explicit unit |
| `food_portions` | food_id + portion_index; label and measured grams |
| `food_images` | food_id → image asset and attribution |
| `recipe_ingredients` | recipe_id + ingredient_index → ingredient_food_id + grams |
| `restaurants`, `brands` | Browse dimensions derived from catalog metadata |
| `diary_days` | owner_id + diary_date at latest revision |
| `meal_entries` | owner_id + entry_id; food_id joins catalog, food_snapshot preserves historical/custom values |
| `checkins` | owner_id + diary_date; weight and sleep |
| `activity_entries` | owner_id + activity_id; date, name and minutes |
| `user_profiles` | owner_id; preferences and goals from latest diary |
| `user_custom_foods` | owner_id + food_id; private user recipes and labels |
| `user_food_preferences` | owner_id + food_id; frequency, last logged date, average grams |
| `login_events` | Observed verified Firebase session; no credentials/email/photo |
| `users` | owner_id; first/last observed sign-in and distinct observed sessions |

Views are intentional: edits and deletions in the latest diary immediately change reporting without stale duplicate child rows. These are logical joins, not enforced foreign keys. Custom food IDs resolve through the owner-scoped custom-food view or the entry snapshot, not through the shared catalog. Login history starts with this release; it is not a historical dump of Firebase accounts.

## Search

Exact-name matches outrank prefix, phrase and alias matches. Within a relevance tier, frequency contributes a bounded logarithmic boost and recency decays over 14 days. Preferences are computed solely from the current user's diary, so deletions and account switches cannot leak another account's ranking. Stable catalog order breaks ties. NDCG is provided for offline judgments; no live NDCG quality claim is made.

## Nutrition provenance

USDA SR Legacy is the April 2018 release. Its restaurant entries are **historical**, not current menu guarantees. Chipotle's additional US records use the linked March 2025 menu with ounces converted using 28.349523125 g/oz. Unknown nutrients remain null. Recipe estimates remain labeled, and cooking yield determines nutrient density. Images of generic paneer do not identify a branded package.

## Repair on 2026-10-09

The live API account lacked `bigquery.tables.updateData`. Firestore had revision 15 while BigQuery had zero events. Granted dataset-level writer access to `gamna-396` and replayed 15 unexported events using their existing event IDs. No meals or measurements were recreated or replaced. Build account `gamna-666` received dataset writer access and project BigQuery Job User for repeatable schema/catalog releases. Enabled Cloud Resource Manager API to manage that grant.

## Remaining acceptance checks

Browser visual verification was unavailable due to the computer-use approval service. DOM checks validate names and interaction but cannot prove pixel layout. Personalized avatar generation requires a chosen runtime provider and explicit photo-processing consent; the default sprite sheet is not personalized. Chain coverage is a dated starter library, not 11 complete current menus.
