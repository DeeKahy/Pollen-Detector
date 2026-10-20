"""Minimal collection server for pollen devices.

    pip install -r requirements.txt
    POLLEN_TOKENS="pollen-01:secret1,pollen-02:secret2" python3 app.py

Endpoints
  POST /api/v1/upload      multipart: image file + meta (JSON string)  [Bearer token]
  POST /api/v1/heartbeat   JSON device status                          [Bearer token]
  GET  /api/v1/captures    ?device=&limit=   list of captures (JSON)
  GET  /api/v1/devices     devices with last heartbeat
  GET  /                   overview page with latest images
  GET  /files/<path>       stored images
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

DATA = Path(os.environ.get("POLLEN_DATA", "./server-data")).resolve()
FILES = DATA / "files"
FILES.mkdir(parents=True, exist_ok=True)
TOKENS = dict(p.split(":", 1) for p in os.environ.get("POLLEN_TOKENS", "pollen-01:change-me").split(",") if ":" in p)

db = sqlite3.connect(DATA / "server.db", check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE IF NOT EXISTS captures (
  id INTEGER PRIMARY KEY, device_id TEXT, device_capture_id INTEGER, ts TEXT, kind TEXT,
  sample_id INTEGER, path TEXT, meta TEXT, received_at TEXT,
  UNIQUE(device_id, device_capture_id));
CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, last_seen TEXT, status TEXT);
""")
lock = threading.Lock()
app = Flask(__name__)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def auth_device():
    device = request.headers.get("X-Device-Id", "")
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not device or TOKENS.get(device) != token:
        abort(401, "bad device id or token")
    return device


@app.post("/api/v1/upload")
def upload():
    device = auth_device()
    f = request.files.get("image")
    if f is None:
        abort(400, "missing image")
    meta = json.loads(request.form.get("meta", "{}"))
    cap_id = int(request.form.get("capture_id", 0))
    day = (meta.get("ts") or now())[:10]
    rel = Path(secure_filename(device)) / day / secure_filename(f.filename or f"{cap_id}.png")
    (FILES / rel).parent.mkdir(parents=True, exist_ok=True)
    f.save(FILES / rel)
    (FILES / rel).with_suffix(".json").write_text(json.dumps(meta, indent=2))
    try:  # small preview for the web page
        from PIL import Image
        with Image.open(FILES / rel) as im:
            im.thumbnail((400, 400))
            im.convert("RGB").save((FILES / rel).with_suffix(".thumb.jpg"), "JPEG", quality=80)
    except Exception as e:
        app.logger.warning("thumbnail failed: %s", e)
    with lock:
        db.execute("INSERT OR REPLACE INTO captures(device_id, device_capture_id, ts, kind, sample_id, path, meta, "
                   "received_at) VALUES (?,?,?,?,?,?,?,?)",
                   (device, cap_id, meta.get("ts"), meta.get("kind"), meta.get("sample_id"), str(rel),
                    json.dumps(meta), now()))
        db.execute("INSERT INTO devices(device_id, last_seen) VALUES(?,?) "
                   "ON CONFLICT(device_id) DO UPDATE SET last_seen=excluded.last_seen", (device, now()))
        db.commit()
    return jsonify(ok=True, path=str(rel))


@app.post("/api/v1/heartbeat")
def heartbeat():
    device = auth_device()
    with lock:
        db.execute("INSERT INTO devices(device_id, last_seen, status) VALUES(?,?,?) "
                   "ON CONFLICT(device_id) DO UPDATE SET last_seen=excluded.last_seen, status=excluded.status",
                   (device, now(), json.dumps(request.get_json(silent=True))))
        db.commit()
    return jsonify(ok=True)


def rows(sql, args=()):
    with lock:
        return [dict(r) for r in db.execute(sql, args).fetchall()]


@app.get("/api/v1/captures")
def captures():
    dev = request.args.get("device")
    limit = int(request.args.get("limit", 50))
    if dev:
        return jsonify(rows("SELECT * FROM captures WHERE device_id=? ORDER BY ts DESC LIMIT ?", (dev, limit)))
    return jsonify(rows("SELECT * FROM captures ORDER BY ts DESC LIMIT ?", (limit,)))


@app.get("/api/v1/devices")
def devices():
    return jsonify(rows("SELECT d.device_id, d.last_seen, d.status, COUNT(c.id) AS captures "
                        "FROM devices d LEFT JOIN captures c USING(device_id) GROUP BY d.device_id"))


@app.get("/files/<path:rel>")
def files(rel):
    return send_from_directory(FILES, rel)


@app.get("/")
def index():
    devs = rows("SELECT d.device_id, d.last_seen, COUNT(c.id) AS n FROM devices d "
                "LEFT JOIN captures c USING(device_id) GROUP BY d.device_id")
    caps = rows("SELECT * FROM captures ORDER BY ts DESC LIMIT 60")
    dev_html = "".join(f"<tr><td>{d['device_id']}</td><td>{d['last_seen']}</td><td>{d['n']}</td></tr>" for d in devs)
    cap_html = "".join(
        f"<a href='/files/{c['path']}' target='_blank'><img loading='lazy' src='/files/{c['path'].rsplit('.', 1)[0]}.thumb.jpg'>"
        f"<br>{c['device_id']} · {c['kind']} · {(c['ts'] or '')[5:16].replace('T', ' ')}</a>" for c in caps)
    return Response(f"""<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>
<title>Pollen server</title><style>body{{font:14px system-ui;margin:16px;background:#f6f7f4;color:#1d211b}}
@media (prefers-color-scheme:dark){{body{{background:#141713;color:#e6eae2}}}}
table{{border-collapse:collapse}}td,th{{padding:3px 10px;border-bottom:1px solid #8884;text-align:left}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}}
.g a{{font-size:11px;color:inherit;text-decoration:none}}.g img{{width:100%;border-radius:4px}}</style>
<h1>Pollen server</h1><h2>Devices</h2><table><tr><th>device</th><th>last seen (UTC)</th><th>captures</th></tr>{dev_html}</table>
<h2>Latest captures</h2><div class=g>{cap_html}</div>""", mimetype="text/html")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 8000)))
