# Pollen collection server (minimal)

Receives images + metadata from devices, stores them on disk, shows an overview page.
Can run on any computer/VPS (or even another Pi) reachable by the devices.

```bash
pip install -r requirements.txt
POLLEN_TOKENS="pollen-01:secret1,pollen-02:secret2" POLLEN_DATA=./server-data python3 app.py
# -> http://<host>:8000
```

On each device set in `config.yaml`:
```yaml
upload: {enabled: true, server_url: "http://<host>:8000", token: secret1}
```
(`device_id` in the device config must match the name in `POLLEN_TOKENS`.)

Storage: `server-data/files/<device>/<date>/<image>.png` + `.json` metadata + `.thumb.jpg`,
index in `server-data/server.db` (SQLite).

This is a prototype: Flask's development server, plain HTTP, tokens in an env var.
Before running it on the internet put it behind HTTPS (e.g. Caddy as a reverse proxy) and
run it with gunicorn. Later this is where detection/classification and the public map/API go.
