"""Hardware abstraction: stepper motor, switched outputs (fan, LED) and camera.

Every part falls back to a mock implementation so the whole program can be
developed and tested on a laptop without a Raspberry Pi attached.
"""
import io
import logging
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
    """A GPIO output: the fan (through a MOSFET) or the LED (directly). Value 0..1."""

    def __init__(self, name, pin, mock, pwm=False, pwm_frequency=100):
        self.name = name
        self.pwm = pwm
        self._value = 0.0
        self.dev = None
        if not mock:
            from gpiozero import DigitalOutputDevice, PWMOutputDevice
            if pwm:
                self.dev = PWMOutputDevice(pin, frequency=pwm_frequency, initial_value=0)
            else:
                self.dev = DigitalOutputDevice(pin, initial_value=False)

    @property
    def value(self):
        return self._value

    def set(self, value):
        value = max(0.0, min(1.0, float(value)))
        if not self.pwm:
            value = 1.0 if value > 0 else 0.0
        if self.dev is not None:
            self.dev.value = value
        if value != self._value:
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
                self.set_exposure(self.cfg["exposure_us"], self.cfg["analogue_gain"])
                time.sleep(1.0)
                log.info("Camera started: %s", self.picam.camera_properties.get("Model"))
            except Exception as e:  # keep running so the rest can still be debugged
                log.exception("Camera start failed - using fake images")
                self.error = f"{type(e).__name__}: {e}"
                self.picam = None
                self.mock = True

    def set_exposure(self, exposure_us, gain):
        self.cfg["exposure_us"] = int(exposure_us)
        self.cfg["analogue_gain"] = float(gain)
        if not self.picam:
            return
        if int(exposure_us) > 0:
            self.picam.set_controls({
                "AeEnable": False,
                "ExposureTime": int(exposure_us),
                "AnalogueGain": float(gain),
            })
        else:
            self.picam.set_controls({"AeEnable": True})

    def capture(self, path, dng_path=None, thumb_path=None):
        """Save a full-resolution image to `path` (+ optional raw DNG and small JPEG thumbnail).
        Returns capture metadata."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock:
            if self.picam:
                req = self.picam.capture_request()
                try:
                    img = req.make_image("main")
                    if dng_path:
                        req.save_dng(str(dng_path))
                    md = req.get_metadata()
                finally:
                    req.release()
                keep = ("ExposureTime", "AnalogueGain", "DigitalGain", "Lux",
                        "SensorTemperature", "ColourGains", "FocusFoM")
                meta = {k: md[k] for k in keep if k in md}
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

    def preview_jpeg(self):
        width = int(self.cfg.get("preview_width", 1014))
        with self.lock:
            if self.picam:
                img = self.picam.capture_image("main")
            else:
                img = self._mock_image(full=False)
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
        self.led = Output("led", pins["led"], mock)
        self.camera = Camera(cfg["camera"], mock)

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
