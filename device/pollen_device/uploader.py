"""Background uploader: pushes queued captures to the server and sends heartbeats.

Captures stay in the local queue until the server answers 2xx, so network outages
just delay uploads.
"""
import json
import logging
import threading

import requests

from .storage import iso, utcnow

log = logging.getLogger("pollen.upload")


class Uploader(threading.Thread):
    def __init__(self, cfg, store, status_fn):
        super().__init__(daemon=True, name="uploader")
        self.cfg = cfg
        self.store = store
        self.status_fn = status_fn
        self._stop = threading.Event()
        self._kick = threading.Event()
        self.last_result = None
        self.lock = threading.Lock()

    @property
    def ucfg(self):
        return self.cfg["upload"]

    def _url(self, endpoint):
        return self.ucfg["server_url"].rstrip("/") + endpoint

    def _headers(self):
        return {"Authorization": f"Bearer {self.ucfg['token']}", "X-Device-Id": self.cfg["device_id"]}

    def run(self):
        while not self._stop.is_set():
            self._kick.wait(float(self.ucfg["interval_s"]))
            self._kick.clear()
            if self._stop.is_set():
                break
            if not self.ucfg["enabled"]:
                continue
            try:
                self.upload_pending()
                if self.ucfg.get("heartbeat", True):
                    self.heartbeat()
            except Exception:
                log.exception("Uploader error")

    def kick(self):
        self._kick.set()

    def stop(self):
        self._stop.set()
        self._kick.set()

    def upload_pending(self, limit=20):
        with self.lock:
            ok = failed = 0
            for row in self.store.pending_uploads(limit):
                path = self.store.abs_path(row["path"])
                if not path.exists():
                    self.store.mark_failed(row["id"], "file missing")
                    failed += 1
                    continue
                try:
                    with open(path, "rb") as f:
                        r = requests.post(
                            self._url("/api/v1/upload"),
                            headers=self._headers(),
                            files={"image": (path.name, f, "image/png")},
                            data={"meta": row["meta"], "capture_id": row["id"],
                                  "device_id": self.cfg["device_id"]},
                            timeout=float(self.ucfg["timeout_s"]),
                        )
                except requests.RequestException as e:
                    self.store.mark_failed(row["id"], e)
                    self.last_result = {"ts": iso(utcnow()), "ok": ok, "failed": failed + 1, "error": str(e)}
                    log.warning("Upload failed (network): %s", e)
                    return self.last_result  # server unreachable - try again next round
                if r.ok:
                    self.store.mark_uploaded(row["id"])
                    ok += 1
                    if self.ucfg["delete_after_upload"]:
                        path.unlink(missing_ok=True)
                else:
                    self.store.mark_failed(row["id"], f"HTTP {r.status_code}: {r.text[:200]}")
                    failed += 1
                    log.warning("Upload of #%d rejected: HTTP %d %s", row["id"], r.status_code, r.text[:200])
                    if r.status_code in (401, 403):
                        break  # wrong token - no point continuing
            self.last_result = {"ts": iso(utcnow()), "ok": ok, "failed": failed, "error": None}
            if ok or failed:
                log.info("Upload round: %d ok, %d failed", ok, failed)
            return self.last_result

    def heartbeat(self):
        try:
            requests.post(self._url("/api/v1/heartbeat"), headers=self._headers(),
                          json=json.loads(json.dumps(self.status_fn(), default=str)), timeout=15)
        except requests.RequestException as e:
            log.debug("Heartbeat failed: %s", e)
