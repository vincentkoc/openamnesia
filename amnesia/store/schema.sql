CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  source TEXT NOT NULL,
  session_id TEXT NOT NULL,
  turn_index INTEGER NOT NULL,
  actor TEXT NOT NULL,
  content TEXT NOT NULL,
  tool_name TEXT,
  tool_status TEXT,
  tool_args_json TEXT,
  tool_result_json TEXT,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  session_key TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  source TEXT NOT NULL,
  start_ts TEXT NOT NULL,
  end_ts TEXT NOT NULL,
  summary TEXT,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS moments (
  moment_id TEXT PRIMARY KEY,
  session_key TEXT NOT NULL,
  start_turn INTEGER NOT NULL,
  end_turn INTEGER NOT NULL,
  intent TEXT,
  outcome TEXT,
  friction_score REAL,
  summary TEXT,
  evidence_json TEXT,
  artifacts_json TEXT
);

CREATE TABLE IF NOT EXISTS skills (
  skill_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  trigger_json TEXT,
  steps_json TEXT,
  checks_json TEXT,
  version TEXT NOT NULL,
  status TEXT NOT NULL,
  metrics_json TEXT,
  created_ts TEXT NOT NULL,
  updated_ts TEXT NOT NULL,
  UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS skill_evals (
  eval_id TEXT PRIMARY KEY,
  skill_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  dataset_ref TEXT,
  metrics_json TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS skill_patches (
  patch_id TEXT PRIMARY KEY,
  skill_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  diff_json TEXT,
  rationale_json TEXT,
  eval_before_id TEXT,
  eval_after_id TEXT,
  promoted_bool INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS exports (
  export_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  type TEXT NOT NULL,
  path TEXT NOT NULL,
  payload_json TEXT
);

CREATE TABLE IF NOT EXISTS source_status (
  source TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  last_poll_ts TEXT NOT NULL,
  records_seen INTEGER NOT NULL,
  records_ingested INTEGER NOT NULL,
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS ingest_audit (
  audit_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  source TEXT NOT NULL,
  event_count INTEGER NOT NULL,
  session_count INTEGER NOT NULL,
  moment_count INTEGER NOT NULL,
  skill_count INTEGER NOT NULL,
  details_json TEXT
);

CREATE TABLE IF NOT EXISTS entity_mentions (
  mention_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  source TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_value TEXT NOT NULL,
  confidence REAL NOT NULL,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS entity_rollups (
  rollup_id TEXT PRIMARY KEY,
  bucket_start_ts TEXT NOT NULL,
  bucket_granularity TEXT NOT NULL,
  source TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_value TEXT NOT NULL,
  mention_count INTEGER NOT NULL,
  meta_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_source_ts ON events(source, ts);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_actor_ts ON events(actor, ts);
CREATE INDEX IF NOT EXISTS idx_moments_session ON moments(session_key);
CREATE INDEX IF NOT EXISTS idx_mentions_source_ts ON entity_mentions(source, ts);
CREATE INDEX IF NOT EXISTS idx_mentions_type_value ON entity_mentions(entity_type, entity_value);
CREATE INDEX IF NOT EXISTS idx_rollups_bucket ON entity_rollups(bucket_granularity, bucket_start_ts);
