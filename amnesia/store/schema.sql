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
