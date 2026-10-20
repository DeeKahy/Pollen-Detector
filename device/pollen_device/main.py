"""Entry point: python3 -m pollen_device --config config.yaml"""
import argparse
import collections
import logging
import logging.handlers
import signal
import sys
import threading
from pathlib import Path

from .config import load_config
from .cycle import Controller
from .hardware import Hardware, resolve_mock
from .storage import Store
from .uploader import Uploader
from .web import create_app


class RingBuffer(logging.Handler):
    def __init__(self, n=400):
        super().__init__()
        self.buf = collections.deque(maxlen=n)

    def emit(self, record):
        self.buf.append(self.format(record))


def setup_logging(cfg):
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout), RingBuffer()]
    if cfg.get("log_file"):
        Path(cfg["data_dir"]).mkdir(parents=True, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            Path(cfg["data_dir"]) / cfg["log_file"], maxBytes=2_000_000, backupCount=3))
    for h in handlers:
        h.setFormatter(fmt)
        root.addHandler(h)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    return handlers[1].buf


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pollen sampler device controller")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--mock", action="store_true", help="force mock hardware")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    logbuf = setup_logging(cfg)
    log = logging.getLogger("pollen")
    if not Path(args.config).exists():
        log.warning("Config %s not found - using defaults", args.config)

    mock = True if args.mock else resolve_mock(cfg["mock"])
    hw = Hardware(cfg, mock)
    store = Store(cfg["data_dir"], cfg["device_id"])
    ctl = Controller(cfg, hw, store)
    app = None
    uploader = Uploader(cfg, store, lambda: app.config["status_fn"]())
    app = create_app(cfg, ctl, hw, store, uploader, logbuf)

    def on_signal(signum, _frame):
        log.info("Signal %d - shutting down", signum)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, on_signal)

    threading.Thread(target=ctl.loop, daemon=True, name="scheduler").start()
    uploader.start()
    log.info("Pollen device %s up - web UI on http://%s:%d  (data in %s)",
             cfg["device_id"], cfg["web"]["host"], cfg["web"]["port"], cfg["data_dir"])
    try:
        app.run(host=cfg["web"]["host"], port=int(cfg["web"]["port"]), threaded=True, use_reloader=False)
    finally:
        ctl.shutdown()
        uploader.stop()
        hw.close()
        log.info("Stopped, all outputs off")


if __name__ == "__main__":
    main()
