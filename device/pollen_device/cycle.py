"""The sampling cycle and all actions that move hardware.

Tape layout (blowing approach, current prototype):

    supply spool -> [FAN blows here] -> ... N pitches ... -> [CAMERA] -> take-up spool

One cycle:
  1. fan blows on the tape section currently under the fan for `blow_s` seconds
  2. tape advances one pitch (`pitch_steps`)
  3. LED on, photograph the section now over the camera, LED off

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
        led_was_on = self.hw.led.value > 0
        self.hw.led.on()
        try:
            time.sleep(float(cam_cfg["led_settle_s"]))
            cam_meta = self.hw.camera.capture(path, dng, self.store.thumb_path(rel))
        finally:
            if not led_was_on:
                self.hw.led.off()
        meta = {
            "device_id": self.cfg["device_id"],
            "ts": iso(ts),
            "kind": kind,
            "sample_id": sample_id,
            "tape_steps": self.hw.stepper.position,
            "camera": cam_meta,
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

    def set_led(self, value):
        self.hw.led.set(value)  # harmless at any time

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
            "cycle": {k: c[k] for k in ("interval_min", "blow_s", "pitch_steps", "camera_offset_cycles")},
        }
