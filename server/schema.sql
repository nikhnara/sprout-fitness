-- Replace YOUR_PROJECT_ID before running. Use a dataset location matching your deployment policy.
CREATE SCHEMA IF NOT EXISTS `YOUR_PROJECT_ID.fitness` OPTIONS(location='US');
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.fitness.events` (
  event_id STRING NOT NULL,
  owner_id STRING NOT NULL,
  received_at TIMESTAMP NOT NULL,
  revision INT64 NOT NULL,
  payload JSON NOT NULL
) PARTITION BY DATE(received_at) CLUSTER BY owner_id;
-- Streaming insert IDs provide best-effort deduplication. Use this view for exact event-level deduplication.
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.events_deduplicated` AS
SELECT * FROM `YOUR_PROJECT_ID.fitness.events`
QUALIFY ROW_NUMBER() OVER (PARTITION BY owner_id,event_id ORDER BY received_at DESC)=1;
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.fitness.latest_diaries` AS
SELECT * FROM `YOUR_PROJECT_ID.fitness.events_deduplicated`
QUALIFY ROW_NUMBER() OVER (PARTITION BY owner_id ORDER BY revision DESC)=1;
