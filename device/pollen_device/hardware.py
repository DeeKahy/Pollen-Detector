"""Hardware abstraction: stepper motor, switched outputs (fan, LED) and camera.

Every part falls back to a mock implementation so the whole program can be
developed and tested on a laptop without a Raspberry Pi attached.
"""
import colorsys
import io
import logging
import math
import random
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

log = logging.getLogger("pollen.hw")

# 28BYJ-48 + ULN2003 coil sequences (IN1..IN4)
HALF_STEP = [
    (1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
    (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1),
]
FULL_STEP = [(1, 1, 0, 0), (0, 1, 1, 0), (0, 0, 1, 1), (1, 0, 0, 1)]


def running_on_pi():
    try:
        model = Path("/proc/device-tree/model").read_text(errors="ignore")
        return "raspberry pi" in model.lower()
    except OSError:
        return False


def resolve_mock(setting):
    if isinstance(setting, bool):
        return setting
    if str(setting).lower() in ("true", "yes", "1"):
        return True
    if str(setting).lower() in ("false", "no", "0"):
        return False
    return not running_on_pi()


class Stepper:
    """28BYJ-48 driven through a ULN2003 board (4 GPIO pins)."""

    def __init__(self, pins, cfg, mock):
        self.seq = HALF_STEP if cfg["half_step"] else FULL_STEP
        self.delay = float(cfg["step_delay_s"])
        self.release_after = bool(cfg["release_after_move"])
        self.invert = bool(cfg["invert_direction"])
        self.mock = mock
        self.idx = 0
        self.position = 0  # signed count of steps moved (tape odometer)
        self.moving = False
        self.lock = threading.Lock()
        self.coils = None
        if not mock:
            from gpiozero import OutputDevice
            self.coils = [OutputDevice(p, initial_value=False) for p in pins]

    def _apply(self, pattern):
        if self.coils:
            for coil, v in zip(self.coils, pattern):
                coil.value = v

    def release(self):
        self._apply((0, 0, 0, 0))

    def move(self, steps, abort_event=None):
        """Move `steps` (negative = backwards). Returns steps actually moved."""
        steps = int(steps)
        if steps == 0:
            return 0
        sign = 1 if steps > 0 else -1
        direction = -sign if self.invert else sign
        moved = 0
        with self.lock:
            self.moving = True
            try:
                for _ in range(abs(steps)):
                    if abort_event is not None and abort_event.is_set():
                        log.warning("Stepper move aborted after %d steps", moved)
                        break
                    self.idx = (self.idx + direction) % len(self.seq)
                    self._apply(self.seq[self.idx])
                    time.sleep(self.delay)
                    moved += sign
                    self.position += sign
            finally:
                if self.release_after:
                    self.release()
                self.moving = False
        log.info("Stepper moved %d steps (odometer %d)", moved, self.position)
        return moved

    def test_coils(self, seconds_each=2.0):
        """Switch on IN1..IN4 one at a time so the ULN2003 LEDs A-D light in order."""
        with self.lock:
            try:
                for i in range(4):
                    pattern = [0, 0, 0, 0]
                    pattern[i] = 1
                    self._apply(tuple(pattern))
                    log.info("Coil test: IN%d on", i + 1)
                    time.sleep(seconds_each)
            finally:
                self.release()

    def close(self):
        self.release()
        if self.coils:
            for c in self.coils:
                c.close()


class Output:
    """A GPIO output: the fan (through a MOSFET) or one LED colour (directly). Value 0..1.
    active_high=False: the pin goes LOW to switch on (common-anode LED)."""

    def __init__(self, name, pin, mock, pwm=False, pwm_frequency=100, active_high=True):
        self.name = name
        self.pwm = pwm
        self._value = 0.0
        self.dev = None
        if not mock:
            from gpiozero import DigitalOutputDevice, PWMOutputDevice
            if pwm:
                self.dev = PWMOutputDevice(pin, active_high=active_high, frequency=pwm_frequency,
                                           initial_value=0)
            else:
                self.dev = DigitalOutputDevice(pin, active_high=active_high, initial_value=False)

    @property
    def value(self):
        return self._value

    def set(self, value, quiet=False):
        value = max(0.0, min(1.0, float(value)))
        if not self.pwm:
            value = 1.0 if value > 0 else 0.0
        if self.dev is not None:
            self.dev.value = value
        if value != self._value and not quiet:
            log.info("%s -> %s", self.name, f"{value:.2f}" if self.pwm else ("ON" if value else "OFF"))
        self._value = value

    def on(self, duty=1.0):
        self.set(duty)

    def off(self):
        self.set(0)

    def close(self):
        self.off()
        if self.dev is not None:
            self.dev.close()


LED_COLOURS = ("red", "green", "blue")
# Named colours for the RGB LED as [red, green, blue], 0..1.
LED_PRESETS = {
    "white": (1, 1, 1),
    "red": (1, 0, 0),
    "green": (0, 1, 0),
    "blue": (0, 0, 1),
    "yellow": (1, 1, 0),
    "cyan": (0, 1, 1),
    "magenta": (1, 0, 1),
}


def _inverse3(m):
    """Inverse of a 3x3 matrix (list of rows). Raises ValueError if it has none."""
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-12:
        raise ValueError("matrix cannot be inverted")
    return [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
            [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
            [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]


def calibrated_duties(target, matrix):
    """PWM duties (red, green, blue) that make the camera see `target`.

    matrix[i][j] = how much camera channel i (R, G, B) sees when LED colour j is fully on.
    target is [r, g, b] where [1, 1, 1] = the brightest white (to the camera) the LED can make.
    Colours the LED can't make are clipped; too bright ones are scaled down (same hue)."""
    inv = _inverse3(matrix)

    def raw(t):
        return [sum(inv[i][j] * t[j] for j in range(3)) for i in range(3)]

    scale = 1 / max(raw([1, 1, 1]))
    d = [max(0.0, v * scale) for v in raw(target)]
    top = max(d)
    return [v / top for v in d] if top > 1 else d


class RgbLed:
    """Common-anode RGB LED: the long leg on 3.3 V, one GPIO pin per colour, pin LOW = on.

    The colour is `settings["led_rgb"]` (the camera settings dict, so it is saved with every
    picture). Each colour is dimmed by PWM: the pin flicks on and off pwm_frequency times a
    second. At 0 or 1 there is no flicker. With a calibration (see Controller.calibrate_led)
    led_rgb is the colour the camera sees, not the raw pin duty."""

    def __init__(self, pins, mock, settings, active_low=True, pwm_frequency=1000):
        self.settings = settings
        self.parts = {c: Output(f"LED {c}", pins[c], mock, pwm=True, pwm_frequency=pwm_frequency,
                                active_high=not active_low)
                      for c in LED_COLOURS}
        self.lit = False
        self.calibration = None  # {"matrix": [[...]], ...} or None
        self._raw = None         # fixed duties that bypass the colour (calibration, hwtest)
        self.effect = None       # {"name": "pulse", ...} while an effect runs
        self._hold = False       # True = effect paused, show the fixed colour (pictures)
        self._fx = None
        self._fx_stop = threading.Event()
        self._pins = threading.Lock()  # effect thread and normal calls both write the pins

    def target(self):
        return list(self.settings["led_rgb"])

    def duties(self, target=None):
        """PWM duty per colour for a colour (default: the colour setting), whether lit or not."""
        t = self.target() if target is None else target
        if self.calibration:
            try:
                return dict(zip(LED_COLOURS, calibrated_duties(t, self.calibration["matrix"])))
            except (ValueError, ZeroDivisionError):
                log.warning("LED calibration unusable - using raw colour")
        return dict(zip(LED_COLOURS, t))

    @property
    def value(self):
        """1 if the LED is on (the old single-LED interface)."""
        return 1.0 if any(o.value for o in self.parts.values()) else 0.0

    def levels(self):
        """What each pin really does right now: 0 = off, 1 = fully on, in between = dimmed."""
        return {c: round(o.value, 3) for c, o in self.parts.items()}

    def refresh(self):
        """Send the current colour (or raw duties) to the pins."""
        with self._pins:
            if self._raw is not None:
                d = self._raw
            elif self.effect and not self._hold:
                return  # the effect thread drives the pins
            else:
                d = self.duties() if self.lit else {}
            for c, o in self.parts.items():
                o.set(d.get(c, 0))

    def set_on(self, on):
        if not on:
            self.stop_effect()
        self.lit = bool(on)
        self.refresh()

    def start_pulse(self, period_s=4.0, hue_s=40.0, low=0.2):
        """Breathe darker and brighter every `period_s` seconds while slowly going round the
        colour wheel (once per `hue_s` seconds). Never darker than `low` (0..1)."""
        self.stop_effect()
        self.effect = {"name": "pulse", "period_s": max(0.5, float(period_s)),
                       "hue_s": max(2.0, float(hue_s)), "low": max(0.05, min(1.0, float(low)))}
        self.lit = True
        self._fx_stop.clear()
        self._fx = threading.Thread(target=self._pulse_loop, name="led-pulse", daemon=True)
        self._fx.start()
        log.info("LED pulse on: %s", self.effect)

    def stop_effect(self):
        if self._fx:
            self._fx_stop.set()
            self._fx.join()
            self._fx = None
            log.info("LED pulse off")
        self.effect = None

    def _pulse_loop(self):
        fx, t0 = self.effect, time.time()
        while not self._fx_stop.wait(1 / 30):
            t = time.time() - t0
            # Smooth breathing between `low` and full, and a slow trip round the hues.
            v = fx["low"] + (1 - fx["low"]) * (0.5 - 0.5 * math.cos(2 * math.pi * t / fx["period_s"]))
            rgb = colorsys.hsv_to_rgb((t / fx["hue_s"]) % 1, 1, v)
            d = self.duties(list(rgb))
            with self._pins:
                if self._raw is not None or self._hold:
                    continue
                for c, o in self.parts.items():
                    o.set(d[c], quiet=True)

    def hold(self, on):
        """Pause an effect and show the fixed colour (for a picture), or resume it."""
        self._hold = bool(on)
        self.refresh()

    def set_raw(self, duties):
        """Drive the pins directly, e.g. {"red": 1}. None goes back to the colour setting."""
        self._raw = None if duties is None else {c: float(duties.get(c, 0)) for c in LED_COLOURS}
        self.refresh()

    def set_colour(self, name):
        """Switch on in a named colour from LED_PRESETS, or "off"."""
        self.stop_effect()
        if name == "off":
            return self.set_on(False)
        if name not in LED_PRESETS:
            raise ValueError(f"unknown LED colour {name!r}, use one of off, {', '.join(LED_PRESETS)}")
        self.settings["led_rgb"] = [float(v) for v in LED_PRESETS[name]]
        self.set_on(True)

    def set(self, value):
        self.set_on(value)

    def on(self, colour=None):
        if colour:
            self.set_colour(colour)
        else:
            self.set_on(True)

    def off(self):
        self.set_raw(None)
        self.set_on(False)

    def close(self):
        self.stop_effect()
        for o in self.parts.values():
            o.close()


def _rgb(v):
    v = [max(0.0, min(1.0, float(x))) for x in v]
    if len(v) != 3:
        raise ValueError("led_rgb needs 3 values")
    return v


# Camera settings that can be changed from the web UI, with their types.
SETTING_TYPES = {
    "exposure_us": int,          # 0 = auto exposure
    "analogue_gain": float,
    "awb": bool,                 # auto white balance; off = use the colour gains below
    "colour_gain_red": float,
    "colour_gain_blue": float,
    "brightness": float,         # -1..1, 0 = normal
    "contrast": float,           # 0..32, 1 = normal
    "saturation": float,         # 0..32, 1 = normal, 0 = greyscale
    "sharpness": float,          # 0..16, 1 = normal, 0 = no sharpening
    "noise_reduction": str,      # off | fast | high_quality
    "led_rgb": _rgb,             # LED colour [r, g, b] 0..1 (PWM), for live view and pictures
    "led_settle_s": float,
    "save_dng": bool,
}
# libcamera NoiseReductionMode values
NOISE_REDUCTION = {"off": 0, "fast": 1, "high_quality": 2}


class Camera:
    """Raspberry Pi HQ camera via picamera2, or a mock that draws fake particles."""

    def __init__(self, cfg, mock):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.picam = None
        self.mock = mock
        self.error = None
        if not mock:
            self.start()

    def start(self):
        """Start (or restart) the real camera. On failure, fall back to fake images."""
        with self.lock:
            if self.picam:
                try:
                    self.picam.stop()
                    self.picam.close()
                except Exception:
                    pass
                self.picam = None
            try:
                from picamera2 import Picamera2
                self.picam = Picamera2()
                config = self.picam.create_still_configuration(
                    main={"size": tuple(self.cfg["resolution"])}, buffer_count=1
                )
                self.picam.configure(config)
                self.picam.start()
                self.mock = False
                self.error = None
                self._apply_controls()
                time.sleep(1.0)
                log.info("Camera started: %s", self.picam.camera_properties.get("Model"))
            except Exception as e:  # keep running so the rest can still be debugged
                log.exception("Camera start failed - using fake images")
                self.error = f"{type(e).__name__}: {e}"
                self.picam = None
                self.mock = True

    def set_exposure(self, exposure_us, gain):
        self.apply_settings({"exposure_us": exposure_us, "analogue_gain": gain})

    def settings(self):
        """The settings you can change in the web UI (also saved with every picture)."""
        return {k: self.cfg[k] for k in SETTING_TYPES}

    def apply_settings(self, new):
        """Change settings (only known keys, converted to the right type) and send them to the camera."""
        for k, v in new.items():
            if k in SETTING_TYPES and v is not None:
                self.cfg[k] = SETTING_TYPES[k](v)
        if self.cfg["noise_reduction"] not in NOISE_REDUCTION:
            self.cfg["noise_reduction"] = "high_quality"
        with self.lock:
            self._apply_controls()

    def _apply_controls(self):
        if not self.picam:
            return
        c = self.cfg
        ctrl = {
            "Brightness": c["brightness"],
            "Contrast": c["contrast"],
            "Saturation": c["saturation"],
            "Sharpness": c["sharpness"],
            "NoiseReductionMode": NOISE_REDUCTION.get(c["noise_reduction"], 2),
        }
        if c["exposure_us"] > 0:
            ctrl.update(AeEnable=False, ExposureTime=c["exposure_us"], AnalogueGain=c["analogue_gain"])
        else:
            ctrl["AeEnable"] = True
        if c["awb"]:
            ctrl["AwbEnable"] = True
        else:
            ctrl.update(AwbEnable=False, ColourGains=(c["colour_gain_red"], c["colour_gain_blue"]))
        self.picam.set_controls(ctrl)

    def capture(self, path, dng_path=None, thumb_path=None):
        """Save a full-resolution image to `path` (+ optional raw DNG and small JPEG thumbnail).
        Returns capture metadata."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            if self.picam:
                # flush=True: only a frame that started after this call (so after the LED came on).
                # New settings take a few frames to apply, so skip frames until the exposure matches.
                want = self.cfg["exposure_us"]
                for skipped in range(6):
                    req = self.picam.capture_request(flush=True)
                    md = req.get_metadata()
                    got = md.get("ExposureTime", want)
                    if want <= 0 or abs(got - want) <= max(100, want * 0.05) or skipped == 5:
                        break
                    req.release()
                try:
                    img = req.make_image("main")
                    if dng_path:
                        req.save_dng(str(dng_path))
                finally:
                    req.release()
                keep = ("ExposureTime", "AnalogueGain", "DigitalGain", "Lux", "ColourTemperature",
                        "SensorTemperature", "ColourGains", "FocusFoM", "FrameDuration")
                meta = {k: md[k] for k in keep if k in md}
                meta["frames_skipped"] = skipped
            else:
                img = self._mock_image(full=True)
                meta = {"mock": True}
        img = img.convert("RGB")
        img.save(path, compress_level=1)  # lossless PNG; low compression = faster on a Pi
        if thumb_path:
            thumb = img.copy()
            thumb.thumbnail((400, 400))
            thumb.save(thumb_path, "JPEG", quality=80)
        meta["size"] = list(img.size)
        return meta

    def grab(self, exposure_us, gain):
        """One frame at a fixed exposure with auto white balance off (colour gains from the
        settings), as a float R, G, B array (0..255), every 4th pixel. For calibration and
        auto setup. Mock: the fake picture, lit by the simulated LED."""
        import numpy as np
        c = self.cfg
        with self.lock:
            if not self.picam:
                time.sleep(0.4 + exposure_us / 1e6)  # about as slow as a real frame
                base = np.asarray(self._mock_image(full=False), dtype=np.float32) / 170
                light = np.array(self.mock_light(), dtype=np.float32) * exposure_us / 5000 * gain
                return np.clip(base * light * 255, 0, 255)[::2, ::2]
            self.picam.set_controls({"AeEnable": False, "ExposureTime": int(exposure_us),
                                     "AnalogueGain": float(gain), "AwbEnable": False,
                                     "ColourGains": (c["colour_gain_red"], c["colour_gain_blue"])})
            try:
                for skipped in range(8):
                    req = self.picam.capture_request(flush=True)
                    got = req.get_metadata().get("ExposureTime", exposure_us)
                    if abs(got - exposure_us) <= max(100, exposure_us * 0.05) or skipped == 7:
                        break
                    req.release()
                try:
                    arr = req.make_array("main")
                finally:
                    req.release()
            finally:
                self._apply_controls()
        arr = arr[::4, ::4, :3].astype(np.float32)
        if self.picam.camera_config["main"]["format"] in ("RGB888", "XRGB8888"):
            arr = arr[:, :, ::-1]  # stored B, G, R
        return arr

    def measure_rgb(self, exposure_us, gain):
        """Average linear R, G, B (0..1) of the middle of one frame at a fixed exposure, plus
        the share of clipped pixels per channel. Used by the LED calibration."""
        arr = self.grab(exposure_us, gain)
        h, w = arr.shape[:2]
        mid = arr[h // 4:3 * h // 4, w // 4:3 * w // 4].reshape(-1, 3)
        lin = (mid / 255) ** 2.2  # undo the camera's gamma (roughly) so light adds up
        return {"mean": [round(float(v), 5) for v in lin.mean(axis=0)],
                "clipped": [round(float(v), 4) for v in (mid >= 250).mean(axis=0)]}

    def mock_light(self):
        """Mock camera only: linear R, G, B the sensor sees at 5000 us. Set by Hardware."""
        return [0.0, 0.0, 0.0]

    def preview_jpeg(self):
        width = int(self.cfg.get("preview_width", 1014))
        with self.lock:
            if self.picam:
                arr = self.picam.capture_array("main")
            else:
                arr = None
                img = self._mock_image(full=False)
        if arr is not None:
            import numpy as np  # comes with picamera2; not needed in mock mode
            # Downscale by skipping pixels instead of resizing the full 12 MP image with PIL.
            # Much faster on a Pi 3; some aliasing is fine for a preview.
            step = max(1, -(-arr.shape[1] // width))
            small = arr[::step, ::step, :3]
            if self.picam.camera_config["main"]["format"] in ("RGB888", "XRGB8888"):
                small = small[:, :, ::-1]  # these formats are stored B, G, R
            img = Image.fromarray(np.ascontiguousarray(small))
        img = img.convert("RGB")
        img.thumbnail((width, width))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        return buf.getvalue()

    def _mock_image(self, full):
        # Mock images are 1/4 resolution to keep things fast on a laptop.
        w, h = self.cfg["resolution"]
        w, h = (w // 4, h // 4)
        img = Image.effect_noise((w, h), 12).point(lambda v: 170 + (v - 128) // 4).convert("RGB")
        draw = ImageDraw.Draw(img)
        for _ in range(random.randint(5, 30)):
            r = random.uniform(3, 12)
            x, y = random.uniform(0, w), random.uniform(0, h)
            shade = random.randint(60, 130)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(shade, shade - 10, shade - 30),
                         outline=(40, 40, 40))
        for _ in range(random.randint(10, 40)):  # dust specks
            x, y = random.uniform(0, w), random.uniform(0, h)
            draw.point((x, y), fill=(30, 30, 30))
        light = self.mock_light()
        if any(light):  # tint the fake picture with the simulated LED light
            top = max(light)
            img = Image.merge("RGB", [ch.point(lambda v, k=0.25 + 0.75 * l / top: int(v * k))
                                      for ch, l in zip(img.split(), light)])
        return img.filter(ImageFilter.GaussianBlur(0.8))

    def close(self):
        if self.picam:
            try:
                self.picam.stop()
                self.picam.close()
            except Exception:
                pass


class Hardware:
    def __init__(self, cfg, mock):
        self.mock = mock
        pins = cfg["pins"]
        log.info("Hardware mode: %s", "MOCK" if mock else "REAL")
        self.stepper = Stepper(pins["stepper"], cfg["stepper"], mock)
        self.fan = Output("fan", pins["fan"], mock, pwm=cfg["fan"]["pwm"],
                          pwm_frequency=cfg["fan"]["pwm_frequency"])
        self.camera = Camera(cfg["camera"], mock)
        # The LED colour lives in the camera settings, so it is saved with every picture.
        self.led = RgbLed(pins["led"], mock, cfg["camera"], active_low=pins["led_active_low"],
                          pwm_frequency=pins["led_pwm_frequency"])
        self.camera.mock_light = self._mock_light  # only used while there is no real camera

    # Made-up camera response to each LED colour (rows: camera R, G, B; columns: LED r, g, b),
    # with crosstalk like a real Bayer sensor and a little room light. Mock mode only.
    MOCK_RESPONSE = [[0.50, 0.08, 0.02], [0.05, 0.90, 0.20], [0.01, 0.10, 0.35]]
    MOCK_AMBIENT = [0.02, 0.02, 0.015]

    def _mock_light(self):
        d = self.led.levels()
        duty = [d[c] for c in LED_COLOURS]
        return [a + sum(m * x for m, x in zip(row, duty))
                for row, a in zip(self.MOCK_RESPONSE, self.MOCK_AMBIENT)]

    def all_off(self):
        self.fan.off()
        self.led.off()
        self.stepper.release()

    def close(self):
        for part in (self.fan, self.led, self.stepper, self.camera):
            try:
                part.close()
            except Exception:
                log.exception("Error closing %s", part)
