-- BigQuery is the reporting store; Firestore remains the transactional diary store.
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.fitness.food_sources` (
 source_id STRING NOT NULL, name STRING, url STRING, release_date DATE
);
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.fitness.food_catalog` (
 food_id STRING NOT NULL, source_id STRING NOT NULL, name STRING NOT NULL,
 canonical_name STRING, diet STRING, category STRING, basis_grams FLOAT64,
 estimated BOOL, record JSON
) CLUSTER BY food_id, source_id;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.food_nutrients` AS
SELECT food_id, nutrient, SAFE_CAST(JSON_VALUE(record.nutrients[nutrient]) AS FLOAT64) AS amount_per_100g,
 IF(nutrient='kcal','kcal','g') AS unit
FROM `YOUR_PROJECT_ID.fitness.food_catalog`,UNNEST(['kcal','protein','fat','carbs','fiber']) nutrient;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.food_portions` AS
SELECT food_id,offset AS portion_index,JSON_VALUE(p,'$.label') AS label,
 SAFE_CAST(JSON_VALUE(p,'$.grams') AS FLOAT64) AS grams
FROM `YOUR_PROJECT_ID.fitness.food_catalog`,UNNEST(JSON_QUERY_ARRAY(record,'$.portions')) p WITH OFFSET;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.food_images` AS
SELECT food_id,JSON_VALUE(record,'$.image') AS image_path,
 JSON_VALUE(record,'$.imageCredit') AS attribution,estimated AS illustrative
FROM `YOUR_PROJECT_ID.fitness.food_catalog` WHERE JSON_VALUE(record,'$.image') IS NOT NULL;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.recipe_ingredients` AS
SELECT food_id AS recipe_id,offset AS ingredient_index,JSON_VALUE(i,'$.food.id') AS ingredient_food_id,
 SAFE_CAST(JSON_VALUE(i,'$.grams') AS FLOAT64) AS grams
FROM `YOUR_PROJECT_ID.fitness.food_catalog`,UNNEST(JSON_QUERY_ARRAY(record,'$.ingredients')) i WITH OFFSET;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.diary_days` AS
SELECT owner_id,revision,received_at,SAFE_CAST(day_key AS DATE) AS diary_date,payload.days[day_key] AS day
FROM `YOUR_PROJECT_ID.fitness.latest_diaries`,UNNEST(JSON_KEYS(JSON_QUERY(payload,'$.days'),1)) day_key;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.meal_entries` AS
SELECT owner_id,diary_date,revision,JSON_VALUE(m,'$.id') AS entry_id,JSON_VALUE(m,'$.foodId') AS food_id,
 JSON_VALUE(m,'$.name') AS food_name,JSON_VALUE(m,'$.meal') AS meal,
 SAFE_CAST(JSON_VALUE(m,'$.grams') AS FLOAT64) AS grams,
 SAFE_CAST(JSON_VALUE(m,'$.nutrients.kcal') AS FLOAT64) AS kcal,
 SAFE_CAST(JSON_VALUE(m,'$.nutrients.protein') AS FLOAT64) AS protein_g,
 SAFE_CAST(JSON_VALUE(m,'$.nutrients.fat') AS FLOAT64) AS fat_g,
 SAFE_CAST(JSON_VALUE(m,'$.nutrients.carbs') AS FLOAT64) AS carbs_g,
 SAFE_CAST(JSON_VALUE(m,'$.nutrients.fiber') AS FLOAT64) AS fiber_g,
 JSON_QUERY(m,'$.food') AS food_snapshot
FROM `YOUR_PROJECT_ID.fitness.diary_days`,UNNEST(JSON_QUERY_ARRAY(day,'$.meals')) m;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.checkins` AS
SELECT owner_id,diary_date,revision,SAFE_CAST(JSON_VALUE(day,'$.weight') AS FLOAT64) AS weight_kg,
 SAFE_CAST(JSON_VALUE(day,'$.sleep') AS FLOAT64) AS sleep_hours FROM `YOUR_PROJECT_ID.fitness.diary_days`;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.activity_entries` AS
SELECT owner_id,diary_date,revision,JSON_VALUE(a,'$.id') AS activity_id,JSON_VALUE(a,'$.name') AS name,
 SAFE_CAST(JSON_VALUE(a,'$.minutes') AS FLOAT64) AS minutes,JSON_VALUE(a,'$.source') AS source
FROM `YOUR_PROJECT_ID.fitness.diary_days`,UNNEST(JSON_QUERY_ARRAY(day,'$.exercise')) a;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.user_profiles` AS
SELECT owner_id,revision,JSON_VALUE(payload,'$.profile.name') AS display_name,
 JSON_VALUE(payload,'$.profile.diet') AS diet,JSON_VALUE(payload,'$.profile.goal') AS goal,
 JSON_QUERY(payload,'$.profile.targets') AS targets FROM `YOUR_PROJECT_ID.fitness.latest_diaries`;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.user_food_preferences` AS
SELECT owner_id,food_id,COUNT(*) AS times_logged,MAX(diary_date) AS last_logged,
 AVG(grams) AS average_grams FROM `YOUR_PROJECT_ID.fitness.meal_entries` GROUP BY owner_id,food_id;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.user_custom_foods` AS
SELECT owner_id,JSON_VALUE(f,'$.id') AS food_id,JSON_VALUE(f,'$.name') AS name,f AS record
FROM `YOUR_PROJECT_ID.fitness.latest_diaries`,UNNEST(ARRAY_CONCAT(IFNULL(JSON_QUERY_ARRAY(payload,'$.customFoods'),[]),IFNULL(JSON_QUERY_ARRAY(payload,'$.recipes'),[]))) f;
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.fitness.login_events` (
 event_id STRING NOT NULL,owner_id STRING NOT NULL,auth_project STRING,
 signed_in_at TIMESTAMP,observed_at TIMESTAMP
) PARTITION BY DATE(observed_at) CLUSTER BY owner_id;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.users` AS
SELECT owner_id,ANY_VALUE(auth_project) AS auth_project,MIN(signed_in_at) AS first_observed_sign_in,
 MAX(signed_in_at) AS last_observed_sign_in,COUNT(DISTINCT event_id) AS observed_sessions
FROM `YOUR_PROJECT_ID.fitness.login_events` GROUP BY owner_id;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.restaurants` AS
SELECT JSON_VALUE(record,'$.restaurant') AS restaurant_name,COUNT(*) AS foods,
 ARRAY_AGG(DISTINCT source_id) AS source_ids
FROM `YOUR_PROJECT_ID.fitness.food_catalog` WHERE JSON_VALUE(record,'$.restaurant') IS NOT NULL GROUP BY restaurant_name;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.brands` AS
SELECT COALESCE(JSON_VALUE(record,'$.brand'),JSON_VALUE(record,'$.source')) AS brand_or_source,COUNT(*) AS foods
FROM `YOUR_PROJECT_ID.fitness.food_catalog` WHERE STARTS_WITH(food_id,'brand-') GROUP BY brand_or_source;
