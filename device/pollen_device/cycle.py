"""The sampling cycle and all actions that move hardware.

Tape layout (blowing approach, current prototype):

    supply spool -> [FAN blows here] -> ... N pitches ... -> [CAMERA] -> take-up spool

One cycle:
  1. fan blows on the tape section currently under the fan for `blow_s` seconds
  2. tape advances one pitch (`pitch_steps`)
  3. LED on (colour from camera.led_rgb), photograph the section now over the camera, LED back

`camera_offset_cycles` (N) = how many pitches separate fan and camera. With N=1 the
section that was just blown is photographed right away. With N>1 several blown
sections are "in transit"; the controller keeps a persistent queue (`pipeline`)
so every image is linked to the sample (blow period) it came from.

Only one hardware action runs at a time (guarded by a lock). Manual actions from the
web UI fail with Busy while a cycle runs; use Abort to interrupt a cycle.
"""
import logging
import threading
import time
from contextlib import contextmanager

from .storage import iso, utcnow

log = logging.getLogger("pollen.cycle")


class Busy(Exception):
    pass


class Controller:
    def __init__(self, cfg, hw, store):
        self.cfg = cfg
        self.hw = hw
        self.store = store
        self.paused = bool(cfg["cycle"]["start_paused"])
        self.activity = "idle"
        self.next_run = time.time()
        self.last_cycle = None
        self.led_cal_progress = None  # set while an LED calibration runs
        self.auto_progress = None     # set while the LED auto setup runs
        self._busy = threading.Lock()
        self._abort = threading.Event()
        self._stop = threading.Event()
        self.hw.stepper.position = int(store.get_state("tape_steps", 0))

    # ---------- helpers ----------
    @contextmanager
    def _action(self, name, wait=False):
        if not self._busy.acquire(blocking=wait):
            raise Busy(f"busy: {self.activity}")
        self._abort.clear()
        self.activity = name
        try:
            yield
        finally:
            self.activity = "idle"
            self._busy.release()

    def _advance(self, steps):
        moved = self.hw.stepper.move(steps, self._abort)
        self.store.set_state("tape_steps", self.hw.stepper.position)
        return moved

    def _pipeline(self):
        return self.store.get_state("pipeline", [])

    def _capture(self, kind, sample_id=None, note=""):
        cam_cfg = self.cfg["camera"]
        ts = utcnow()
        rel = self.store.new_image_path(ts)
        path = self.store.abs_path(rel)
        dng = path.with_suffix(".dng") if cam_cfg["save_dng"] else None
        led_was_on = self.hw.led.lit
        self.hw.led.hold(True)  # a running pulse effect pauses; pictures use the fixed colour
        self.hw.led.lit = True
        self.hw.led.refresh()
        led = {"rgb": self.hw.led.target(), "duty": self.hw.led.levels(),
               "calibrated": self.hw.led.calibration is not None}
        try:
            time.sleep(float(cam_cfg["led_settle_s"]))
            cam_meta = self.hw.camera.capture(path, dng, self.store.thumb_path(rel))
        finally:
            self.hw.led.lit = led_was_on
            self.hw.led.hold(False)
        meta = {
            "device_id": self.cfg["device_id"],
            "ts": iso(ts),
            "kind": kind,
            "sample_id": sample_id,
            "tape_steps": self.hw.stepper.position,
            "camera": cam_meta,
            "led": led,
            "led_pwm_hz": self.cfg["pins"]["led_pwm_frequency"],
            "note": note,
            "camera_settings": {**self.hw.camera.settings(), "resolution": cam_cfg["resolution"]},
            "mock": self.hw.mock or self.hw.camera.mock,
        }
        if sample_id is not None:
            meta["sample"] = self.store.get_sample(sample_id)
        cid = self.store.add_capture(ts, rel, kind, sample_id, meta)
        self.store.write_sidecar(cid, rel, meta)
        log.info("Captured #%d (%s, sample %s) -> %s", cid, kind, sample_id, rel)
        return {"id": cid, "path": str(rel), "kind": kind, "sample_id": sample_id}

    def _shift_pipeline(self, entry):
        """Tape moved one pitch: `entry` (sample id or None) leaves the fan.
        Returns what is now over the camera (sample id or None)."""
        pipeline = self._pipeline()
        pipeline.append(entry)
        n = int(self.cfg["cycle"]["camera_offset_cycles"])
        at_camera = pipeline.pop(0) if len(pipeline) >= n else None
        self.store.set_state("pipeline", pipeline)
        return at_camera

    # ---------- the cycle ----------
    def run_cycle(self, wait=False):
        c = self.cfg["cycle"]
        with self._action("cycle: blowing", wait):
            duty = float(self.cfg["fan"]["duty"]) if self.cfg["fan"]["pwm"] else 1.0
            start = utcnow()
            sid = self.store.new_sample(start, duty, self.hw.stepper.position)
            log.info("Cycle start: sample %d, blowing %ss", sid, c["blow_s"])
            t0 = time.monotonic()
            self.hw.fan.on(duty)
            try:
                aborted = self._abort.wait(float(c["blow_s"]))
            finally:
                self.hw.fan.off()
            self.store.finish_sample(sid, utcnow(), round(time.monotonic() - t0, 1), aborted)
            if aborted:
                log.warning("Cycle aborted while blowing. Sample %d stays under the fan, marked aborted. "
                            "Use 'Skip section' to move past it.", sid)
                self.last_cycle = {"sample_id": sid, "aborted": True, "ts": iso(utcnow())}
                return self.last_cycle

            self.activity = "cycle: advancing"
            pitch = int(c["pitch_steps"])
            moved = self._advance(pitch)
            if moved != pitch:
                log.error("Advance incomplete (%d/%d) - tracking reset", moved, pitch)
                self.store.set_state("pipeline", [])
                self.last_cycle = {"sample_id": sid, "aborted": True, "ts": iso(utcnow())}
                return self.last_cycle
            at_camera = self._shift_pipeline(sid)

            self.activity = "cycle: imaging"
            cap = self._capture("sample" if at_camera is not None else "untracked", at_camera)
            self.last_cycle = {"sample_id": sid, "captured": cap, "aborted": False, "ts": iso(utcnow())}
            log.info("Cycle done")
            return self.last_cycle

    def loop(self):
        """Scheduler thread."""
        while not self._stop.wait(1.0):
            c = self.cfg["cycle"]
            if self.paused or not c["enabled"] or time.time() < self.next_run:
                continue
            self.next_run = time.time() + float(c["interval_min"]) * 60
            try:
                self.run_cycle(wait=True)
            except Exception:
                log.exception("Cycle failed")
                self.hw.all_off()

    # ---------- manual actions (web UI) ----------
    def pause(self):
        self.paused = True
        log.info("Scheduler paused")

    def resume(self):
        self.paused = False
        self.next_run = time.time()
        log.info("Scheduler resumed - next cycle starts now")

    def abort(self):
        self._abort.set()
        log.warning("Abort requested")

    def jog(self, steps):
        with self._action(f"jog {steps}"):
            moved = self._advance(steps)
        log.warning("Manual jog moves tape off the pitch grid - press 'Reset tracking' when done.")
        return moved

    def skip_section(self):
        """Advance exactly one pitch without blowing (keeps tracking consistent)."""
        with self._action("skip section"):
            moved = self._advance(int(self.cfg["cycle"]["pitch_steps"]))
            self._shift_pipeline(None)
        return moved

    def manual_capture(self, note=""):
        with self._action("capture"):
            return self._capture("manual", note=note)

    def set_fan(self, value):
        with self._action("fan"):
            self.hw.fan.set(value)

    def set_led(self, on):
        self.hw.led.set_on(on)  # harmless at any time

    def calibrate_led(self):
        """Measure what the camera sees from each LED colour, so a chosen colour (and white)
        comes out right in the pictures. Point the LED at the camera (no tape, room dark).

        Takes a frame with the LED off, then red, green and blue fully on, at one fixed
        exposure. If a colour clips, the exposure is halved; if it is too dark, doubled.
        Result: matrix[i][j] = camera channel i's response to LED colour j (minus the dark frame)."""
        from .hardware import LED_COLOURS, _inverse3
        cam, led = self.hw.camera, self.hw.led
        exposure = int(cam.cfg["exposure_us"]) or 5000
        gain = float(cam.cfg["analogue_gain"])
        frames = ["off", *LED_COLOURS]
        prog = {}

        def shoot(colour):
            t = time.time()
            led.set_raw({} if colour == "off" else {colour: 1})
            if colour != "off":
                time.sleep(float(cam.cfg["led_settle_s"]))
            m = cam.measure_rgb(exposure, gain)
            dt = time.time() - t
            prog["frame_s"] = dt if prog["frame_s"] is None else 0.7 * prog["frame_s"] + 0.3 * dt
            prog["frame"] += 1
            prog["frame_t"] = time.time()
            return m

        with self._action("LED calibration"):
            # Progress for the web UI: which try, which picture, and how long a picture takes.
            prog.update({"try": 1, "exposure_us": exposure, "frame": 0, "frames": len(frames),
                         "frame_s": None, "note": "", "started": time.time(),
                         "frame_t": time.time(), "colours": frames})
            self.led_cal_progress = prog
            try:
                for attempt in range(8):
                    prog.update({"try": attempt + 1, "exposure_us": exposure, "frame": 0,
                                 "frame_t": time.time()})
                    dark = shoot("off")
                    seen = {c: shoot(c) for c in LED_COLOURS}
                    clipped = max(max(m["clipped"]) for m in seen.values())
                    signal = min(max(m["mean"]) - max(dark["mean"]) for m in seen.values())
                    log.info("LED calibration at %d us: clipped %.3f, weakest signal %.4f",
                             exposure, clipped, signal)
                    if clipped > 0.01 and exposure > 100:
                        exposure = max(100, exposure // 2)
                        prog["note"] = f"too bright at {prog['exposure_us']} µs, trying {exposure} µs"
                    elif signal < 0.02 and exposure < 500000:
                        exposure *= 2
                        prog["note"] = f"too dark at {prog['exposure_us']} µs, trying {exposure} µs"
                    else:
                        break
                else:
                    raise RuntimeError("could not find a usable exposure - is the LED pointing at the camera?")
            finally:
                led.set_raw(None)
                self.led_cal_progress = None
            matrix = [[max(0.0, seen[c]["mean"][i] - dark["mean"][i]) for c in LED_COLOURS]
                      for i in range(3)]
            _inverse3(matrix)  # raises ValueError if the colours can't be told apart
            cal = {"matrix": [[round(v, 5) for v in row] for row in matrix],
                   "dark": dark["mean"], "exposure_us": exposure, "analogue_gain": gain,
                   "colour_gains": [cam.cfg["colour_gain_red"], cam.cfg["colour_gain_blue"]],
                   "mock": cam.mock, "ts": iso(utcnow())}
            led.calibration = cal
            led.refresh()
            self.store.set_state("led_calibration", cal)
            log.info("LED calibrated: %s", cal["matrix"])
            return cal

    AUTO_COLOURS = ("blue", "green", "red", "white")
    AUTO_LEVEL = 150  # target brightness of the bright background (95th percentile, 0..255)

    def auto_setup(self):
        """Try each LED colour, find the exposure that puts the background at AUTO_LEVEL,
        and score how much detail (sharp dark edges) the picture has. Returns the results,
        best first. The caller applies the best one. Uses whatever is on the tape now."""
        import numpy as np
        from .hardware import LED_COLOURS, LED_PRESETS
        cam, led = self.hw.camera, self.hw.led
        exposure, gain = int(cam.cfg["exposure_us"]) or 1000, 1.0
        results = []
        with self._action("LED auto setup"):
            prog = {"step": 0, "steps": len(self.AUTO_COLOURS), "colour": None, "try": 0,
                    "exposure_us": exposure, "started": time.time(), "step_s": None, "step_t": time.time()}
            self.auto_progress = prog
            try:
                for name in self.AUTO_COLOURS:
                    rgb = np.array(LED_PRESETS[name], dtype=np.float32)
                    prog.update({"colour": name, "try": 0})
                    led.set_raw(dict(zip(LED_COLOURS, rgb.tolist())))
                    time.sleep(float(cam.cfg["led_settle_s"]))
                    for t in range(8):
                        prog.update({"try": t + 1, "exposure_us": exposure})
                        # Only the channels this colour lights (others just add noise).
                        ch = (cam.grab(exposure, gain) * rgb).sum(axis=2) / rgb.sum()
                        level = float(np.percentile(ch, 95))
                        if 0.85 * self.AUTO_LEVEL <= level <= 1.1 * self.AUTO_LEVEL:
                            break
                        factor = 0.4 if level >= 250 else min(4.0, max(0.25, self.AUTO_LEVEL / max(level, 1)))
                        want = exposure * factor
                        if want > 200000:  # longer than 0.2 s: use gain instead
                            gain, exposure = min(8.0, gain * want / 200000), 200000
                        else:
                            if gain > 1 and factor < 1:
                                gain = max(1.0, gain * factor)
                            else:
                                exposure = max(30, int(want))
                    results.append({"colour": name, "rgb": rgb.tolist(), "exposure_us": exposure,
                                    "analogue_gain": round(gain, 2), "level": round(level),
                                    "detail": round(self._detail(ch), 4)})
                    log.info("Auto setup %s: %s", name, results[-1])
                    now = time.time()
                    dt = now - prog["step_t"]
                    prog["step_s"] = dt if prog["step_s"] is None else (prog["step_s"] + dt) / 2
                    prog.update({"step": prog["step"] + 1, "step_t": now})
            finally:
                led.set_raw(None)
                self.auto_progress = None
        return sorted(results, key=lambda r: -r["detail"])

    @staticmethod
    def _detail(ch):
        """How sharp the darkest edges are: the strongest gradients (99.5th percentile) of a
        lightly smoothed picture, relative to the background. Higher = crisper shadows."""
        import numpy as np
        sm = (ch[:-2, :-2] + ch[1:-1, :-2] + ch[2:, :-2] + ch[:-2, 1:-1] + ch[1:-1, 1:-1]
              + ch[2:, 1:-1] + ch[:-2, 2:] + ch[1:-1, 2:] + ch[2:, 2:]) / 9  # 3x3 blur vs noise
        g = np.hypot(np.diff(sm, axis=0)[:, :-1], np.diff(sm, axis=1)[:-1, :])
        return float(np.percentile(g, 99.5) / max(np.median(ch), 1))

    def _auto_status(self):
        p = self.auto_progress
        if not p:
            return None
        now = time.time()
        step_s = p["step_s"] or 4.0  # guess until the first colour is done
        left = max(0.0, (p["steps"] - p["step"]) * step_s - (now - p["step_t"]))
        return {"step": p["step"], "steps": p["steps"], "colour": p["colour"], "try": p["try"],
                "exposure_us": p["exposure_us"], "elapsed_s": round(now - p["started"], 1),
                "left_s": round(left, 1), "step_s": round(step_s, 2)}

    def _led_cal_status(self):
        """Calibration progress with times relative to now (the Pi's clock may be wrong)."""
        p = self.led_cal_progress
        if not p:
            return None
        now = time.time()
        frame_s = p["frame_s"] or 1.0  # guess until the first picture is done
        left = max(0.0, (p["frames"] - p["frame"]) * frame_s - (now - p["frame_t"]))
        return {"try": p["try"], "exposure_us": p["exposure_us"], "frame": p["frame"],
                "frames": p["frames"], "colours": p["colours"], "note": p["note"],
                "elapsed_s": round(now - p["started"], 1), "try_left_s": round(left, 1),
                "frame_s": round(frame_s, 2)}

    def clear_led_calibration(self):
        self.hw.led.calibration = None
        self.hw.led.refresh()
        self.store.set_state("led_calibration", None)

    def reset_tracking(self):
        self.store.set_state("pipeline", [])
        log.info("Tracking reset: sections between fan and camera are now 'untracked'")

    def shutdown(self):
        self._stop.set()
        self._abort.set()
        self.hw.all_off()

    def status(self):
        c = self.cfg["cycle"]
        return {
            "activity": self.activity,
            "paused": self.paused,
            "next_run": None if self.paused else max(0, round(self.next_run - time.time())),
            "tape_steps": self.hw.stepper.position,
            "pipeline": self._pipeline(),
            "last_cycle": self.last_cycle,
            "led_calibration": self._led_cal_status(),
            "auto_setup": self._auto_status(),
            "cycle": {k: c[k] for k in ("interval_min", "blow_s", "pitch_steps", "camera_offset_cycles")},
        }
