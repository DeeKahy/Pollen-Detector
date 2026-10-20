"""Interactive hardware test - use this right after wiring, before running the full service.

    python3 -m pollen_device.hwtest            # uses config.yaml in the current dir
    python3 -m pollen_device.hwtest --only fan

Stop the pollen service first (sudo systemctl stop pollen) so the GPIO pins are free.
"""
import argparse
import time
from pathlib import Path

from .config import load_config
from .hardware import Hardware, resolve_mock


def ask(msg):
    return input(f"{msg} [Enter = yes / n = no] ").strip().lower() != "n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--only", choices=["led", "fan", "stepper", "camera"])
    args = ap.parse_args()
    cfg = load_config(args.config)
    mock = resolve_mock(cfg["mock"])
    print(f"Hardware mode: {'MOCK' if mock else 'REAL'}  pins: {cfg['pins']}")
    hw = Hardware(cfg, mock)
    results = {}
    try:
        if args.only in (None, "led"):
            print("\nLED: on for 3 s")
            hw.led.on(); time.sleep(3); hw.led.off()
            results["led"] = ask("Did the LED light up?")
        if args.only in (None, "fan"):
            print("\nFAN: on for 5 s")
            hw.fan.on(); time.sleep(5); hw.fan.off()
            results["fan"] = ask("Did the fan spin?")
        if args.only in (None, "stepper"):
            n = 4096 if cfg["stepper"]["half_step"] else 2048
            print(f"\nSTEPPER: {n // 4} steps forward (~1/4 turn), then back")
            t = time.time(); hw.stepper.move(n // 4); dt = time.time() - t
            time.sleep(0.5); hw.stepper.move(-(n // 4))
            print(f"  1/4 turn took {dt:.1f} s. If it only buzzed/vibrated: check IN1-IN4 order "
                  f"or increase stepper.step_delay_s")
            results["stepper"] = ask("Did the shaft turn a quarter turn and come back?")
        if args.only in (None, "camera"):
            out = Path("hwtest_capture.png")
            print(f"\nCAMERA: LED on, capturing to {out.resolve()}")
            hw.led.on(); time.sleep(0.5)
            meta = hw.camera.capture(out, thumb_path=Path("hwtest_thumb.jpg"))
            hw.led.off()
            print(f"  metadata: {meta}")
            if hw.camera.error:
                print(f"  CAMERA ERROR: {hw.camera.error}")
            results["camera"] = not hw.camera.mock and out.exists()
    finally:
        hw.close()
    print("\nResults:", ", ".join(f"{k}={'OK' if v else 'FAIL'}" for k, v in results.items()))


if __name__ == "__main__":
    main()
