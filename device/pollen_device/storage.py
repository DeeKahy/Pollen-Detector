"""Local storage: images on disk + a small SQLite database (samples, captures, upload queue, state)."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    id          INTEGER PRIMARY KEY,
    blow_start  TEXT NOT NULL,
    blow_end    TEXT,
    blow_s      REAL,
    fan_duty    REAL,
    tape_steps  INTEGER,
    aborted     INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS captures (
    id          INTEGER PRIMARY KEY,
    ts          TEXT NOT NULL,
    kind        TEXT NOT NULL,           -- sample | untracked | manual
    sample_id   INTEGER REFERENCES samples(id),
    path        TEXT NOT NULL,           -- relative to images dir
    meta        TEXT NOT NULL,           -- JSON
    uploaded_at TEXT,
    attempts    INTEGER DEFAULT 0,
    last_error  TEXT
);
CREATE INDEX IF NOT EXISTS captures_pending ON captures(uploaded_at);
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);
"""


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat(timespec="seconds")


class Store:
    def __init__(self, data_dir, device_id):
        self.dir = Path(data_dir)
        self.images = self.dir / "images"
        self.images.mkdir(parents=True, exist_ok=True)
        self.device_id = device_id
        self.lock = threading.Lock()
        self.db = sqlite3.connect(self.dir / "pollen.db", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def _exec(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur

    def _all(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    # --- key/value state (survives reboots) ---
    def get_state(self, key, default=None):
        rows = self._all("SELECT value FROM state WHERE key=?", (key,))
        return json.loads(rows[0]["value"]) if rows else default

    def set_state(self, key, value):
        self._exec("INSERT INTO state(key, value) VALUES(?, ?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))

    # --- samples (one fan-blowing period on one tape section) ---
    def new_sample(self, blow_start, fan_duty, tape_steps):
        cur = self._exec("INSERT INTO samples(blow_start, fan_duty, tape_steps) VALUES (?, ?, ?)",
                         (iso(blow_start), fan_duty, tape_steps))
        return cur.lastrowid

    def finish_sample(self, sample_id, blow_end, blow_s, aborted):
        self._exec("UPDATE samples SET blow_end=?, blow_s=?, aborted=? WHERE id=?",
                   (iso(blow_end), blow_s, int(aborted), sample_id))

    def get_sample(self, sample_id):
        rows = self._all("SELECT * FROM samples WHERE id=?", (sample_id,))
        return rows[0] if rows else None

    # --- captures (images) ---
    def new_image_path(self, ts):
        rel = Path(ts.strftime("%Y-%m-%d")) / f"{self.device_id}_{ts.strftime('%Y%m%dT%H%M%SZ')}.png"
        n = 1
        while (self.images / rel).exists():  # two captures in the same second
            rel = rel.with_name(f"{self.device_id}_{ts.strftime('%Y%m%dT%H%M%SZ')}_{n}.png")
            n += 1
        return rel

    def abs_path(self, rel):
        return self.images / rel

    def thumb_path(self, rel):
        return self.images / Path(rel).with_suffix(".thumb.jpg")

    def add_capture(self, ts, rel_path, kind, sample_id, meta):
        cur = self._exec(
            "INSERT INTO captures(ts, kind, sample_id, path, meta) VALUES (?, ?, ?, ?, ?)",
            (iso(ts), kind, sample_id, str(rel_path), json.dumps(meta)))
        return cur.lastrowid

    def recent_captures(self, limit=24):
        return self._all("SELECT * FROM captures ORDER BY id DESC LIMIT ?", (limit,))

    def pending_uploads(self, limit=20):
        return self._all("SELECT * FROM captures WHERE uploaded_at IS NULL ORDER BY id LIMIT ?", (limit,))

    def mark_uploaded(self, capture_id):
        self._exec("UPDATE captures SET uploaded_at=?, last_error=NULL WHERE id=?", (iso(utcnow()), capture_id))

    def mark_failed(self, capture_id, error):
        self._exec("UPDATE captures SET attempts=attempts+1, last_error=? WHERE id=?", (str(error)[:500], capture_id))

    def stats(self):
        with self.lock:
            total = self.db.execute("SELECT COUNT(*) FROM captures").fetchone()[0]
            pending = self.db.execute("SELECT COUNT(*) FROM captures WHERE uploaded_at IS NULL").fetchone()[0]
            samples = self.db.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        return {"captures": total, "pending_upload": pending, "samples": samples}
