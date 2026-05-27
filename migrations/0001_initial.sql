CREATE TABLE IF NOT EXISTS replays (
    id TEXT PRIMARY KEY,
    ts TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    replay_id TEXT,
    type TEXT,
    payload TEXT,
    ts TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_replay_id
    ON events (replay_id, id);