"""Hardware self-checks shown in the web UI ("Hardware checks" card).

Each check returns {"name", "status": ok|warn|fail|info, "detail"}. Wiring checks use
`pinctrl` to briefly turn a pin into an input with a pull-up: a pin wired to something
(e.g. a ULN2003 input, which has a resistor to GND) reads low, a loose pin reads high.
"""
import logging
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

log = logging.getLogger("pollen.checks")

# BCM2837 power-on pull defaults, used if a pin's pull can't be read back
DEFAULT_PULL = {p: ("pu" if p <= 8 else "pd") for p in range(28)}
# Pins worth scanning for stray wires (skip 0/1 HAT EEPROM, 2/3 I2C with board pull-ups, 14/15 UART)
SCAN_PINS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
COIL_NAMES = ["IN1", "IN2", "IN3", "IN4"]


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def _check(name, status, detail):
    return {"name": name, "status": status, "detail": detail}


# ---------- pinctrl helpers ----------
def _pin_state(pin):
    """Return (function, pull) from `pinctrl get`, e.g. ('ip', 'pd') or ('op', None)."""
    rc, out = _run(["pinctrl", "get", str(pin)])
    m = re.match(r"\s*\d+:\s+(\w+)\s+(\S+)", out) if rc == 0 else None
    if not m:
        return None, None
    # Pi 3 (BCM2837) can't read pulls back and prints "--"; caller then uses DEFAULT_PULL
    pull = m.group(2) if m.group(2) in ("pu", "pd", "pn") else None
    return m.group(1), pull


def _probe_pullup(pin):
    """Set pin to input+pull-up and read it. True = pulled low (something connected)."""
    _run(["pinctrl", "set", str(pin), "ip", "pu"])
    time.sleep(0.05)
    rc, out = _run(["pinctrl", "lev", str(pin)])
    return out.strip() == "0" if rc == 0 else None


# ---------- individual checks ----------
def check_system():
    out = []
    model = Path("/proc/device-tree/model").read_text(errors="ignore").strip("\x00\n") \
        if Path("/proc/device-tree/model").exists() else socket.gethostname()
    rc, ips = _run(["hostname", "-I"])
    out.append(_check("Device", "info", f"{model} · {socket.gethostname()} · IP {ips if rc == 0 else '?'}"))

    rc, thr = _run(["vcgencmd", "get_throttled"])
    if rc == 0 and "=" in thr:
        bits = int(thr.split("=")[1], 16)
        if bits & 0x1:
            out.append(_check("Power supply", "fail", "Under-voltage NOW - use a proper 5 V / 2.5 A supply"))
        elif bits & 0x10000:
            out.append(_check("Power supply", "warn",
                              "Under-voltage happened since boot (motor/fan inrush?) - check supply"))
        else:
            out.append(_check("Power supply", "ok", "No under-voltage since boot"))
        if bits & 0x4:
            out.append(_check("Throttling", "warn", "CPU is throttled right now (heat or power)"))

    try:
        t = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
        out.append(_check("CPU temperature", "ok" if t < 70 else "warn", f"{t:.1f} °C"))
    except (OSError, ValueError):
        pass
    return out


def check_camera(hw):
    out = []
    rc, txt = _run(["rpicam-hello", "--list-cameras"], timeout=15)
    if rc == -1:
        out.append(_check("Camera detected", "info", "rpicam-hello not available"))
    elif "No cameras available" in txt or not re.search(r"^\s*\d+\s*:", txt, re.M):
        out.append(_check("Camera detected", "fail",
                          "No camera found at boot. Power off, then check the ribbon is in the CAMERA "
                          "socket (between HDMI and audio), blue tab towards Ethernet, fully latched at both ends."))
    else:
        first = next(line.strip() for line in txt.splitlines() if re.match(r"^\s*\d+\s*:", line))
        out.append(_check("Camera detected", "ok", first))

    cam = hw.camera
    if hw.mock:
        out.append(_check("Camera in app", "info", "Mock hardware mode"))
    elif cam.mock:
        out.append(_check("Camera in app", "fail",
                          f"Using fake images. {cam.error or ''} - fix the cable, reboot, or press Retry camera."))
    else:
        model = cam.picam.camera_properties.get("Model") if cam.picam else "?"
        out.append(_check("Camera in app", "ok", f"Real camera running ({model})"))
    return out


def check_wiring(cfg, hw, ctl):
    """Probe stepper inputs and look for wires on pins that should be empty."""
    if hw.mock:
        return [_check("Wiring", "info", "Mock hardware mode - no wiring checks")]
    if shutil.which("pinctrl") is None:
        return [_check("Wiring", "info", "pinctrl not installed - wiring checks skipped")]

    pins = cfg["pins"]
    stepper_pins = list(pins["stepper"])
    used = set(stepper_pins) | {pins["fan"], pins["led"]}
    out = []

    # Stepper inputs: only while the motor is idle; hold the controller lock so nothing moves.
    with ctl._action("wiring check"):
        hw.stepper.release()
        missing = []
        for name, pin in zip(COIL_NAMES, stepper_pins):
            connected = _probe_pullup(pin)
            _run(["pinctrl", "set", str(pin), "op", "dl", "pn"])  # back to output low for gpiozero
            if connected is False:
                missing.append(f"{name} (GPIO{pin})")
        if missing:
            out.append(_check("Stepper inputs", "fail",
                              "Nothing connected on " + ", ".join(missing) + ". Check those jumper wires."))
        else:
            out.append(_check("Stepper inputs", "ok",
                              "IN1-IN4 all connected (GPIO " + "/".join(map(str, stepper_pins)) + ")"))

        # Unused pins: a pin that is pulled low by something is probably a misplaced wire.
        stray = []
        for pin in SCAN_PINS:
            if pin in used:
                continue
            func, pull = _pin_state(pin)
            if func != "ip":  # in use by something else (SPI, overlay...) - leave it alone
                continue
            connected = _probe_pullup(pin)
            _run(["pinctrl", "set", str(pin), "ip", pull or DEFAULT_PULL[pin]])
            if connected:
                stray.append(f"GPIO{pin}")
        if stray:
            out.append(_check("Unexpected wires", "warn",
                              "Something is connected to " + ", ".join(stray) +
                              " which the software doesn't use - a wire one pin off?"))
        else:
            out.append(_check("Unexpected wires", "ok", "No wires on unused GPIO pins"))

    out.append(_check("Fan / LED wiring", "info",
                      f"Can't be detected electrically - switch them on above and look "
                      f"(fan GPIO{pins['fan']}, LED GPIO{pins['led']})"))
    out.append(_check("ULN2003 power", "info",
                      "Run the coil test: LEDs A, B, C, D should light one after another. "
                      "No LEDs at all = board has no 5 V / GND."))
    return out


def run_all(cfg, hw, ctl):
    results = []
    for fn, args in ((check_system, ()), (check_camera, (hw,)), (check_wiring, (cfg, hw, ctl))):
        try:
            results.extend(fn(*args))
        except Exception as e:
            log.exception("Check %s failed", fn.__name__)
            results.append(_check(fn.__name__.replace("check_", "").title(), "warn",
                                  f"Check could not run: {type(e).__name__}: {e}"))
    return {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "checks": results}
