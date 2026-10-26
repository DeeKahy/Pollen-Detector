"""Configuration loading with defaults."""
import copy
from pathlib import Path

import yaml

DEFAULTS = {
    "device_id": "pollen-01",
    "mock": "auto",
    "data_dir": "./data",
    "pins": {"stepper": [17, 27, 22, 23], "fan": 18, "led": 24},
    "stepper": {
        "half_step": True,
        "step_delay_s": 0.0015,
        "release_after_move": True,
        "invert_direction": False,
    },
    "fan": {"pwm": False, "pwm_frequency": 25, "duty": 1.0},
    "camera": {
        "resolution": [4056, 3040],
        "exposure_us": 2000,
        "analogue_gain": 1.0,
        "save_dng": False,
        "led_settle_s": 0.5,
        "preview_width": 1014,
        "awb": True,
        "colour_gain_red": 2.0,
        "colour_gain_blue": 2.0,
        "brightness": 0.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "sharpness": 1.0,
        "noise_reduction": "high_quality",
    },
    "cycle": {
        "enabled": True,
        "start_paused": True,
        "interval_min": 30,
        "blow_s": 600,
        "pitch_steps": 1500,
        "camera_offset_cycles": 1,
    },
    "upload": {
        "enabled": False,
        "server_url": "http://localhost:8000",
        "token": "change-me",
        "interval_s": 30,
        "timeout_s": 120,
        "delete_after_upload": False,
        "heartbeat": True,
    },
    "web": {"host": "0.0.0.0", "port": 8080, "password": ""},
    "log_file": "pollen.log",
}


def _merge(base, override):
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path):
    path = Path(path)
    user = {}
    if path.exists():
        user = yaml.safe_load(path.read_text()) or {}
    cfg = _merge(DEFAULTS, user)
    # resolve data_dir relative to the config file
    data_dir = Path(cfg["data_dir"]).expanduser()
    if not data_dir.is_absolute():
        data_dir = (path.parent if path.exists() else Path.cwd()) / data_dir
    cfg["data_dir"] = str(data_dir.resolve())
    if int(cfg["cycle"]["camera_offset_cycles"]) < 1:
        raise ValueError("cycle.camera_offset_cycles must be >= 1")
    cfg["_path"] = str(path.resolve())
    return cfg
