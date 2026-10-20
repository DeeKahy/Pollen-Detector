# v0: concept

**Date:** 2026-10

## What we did

- Tested putting clear tape with pollen on it over the camera. Pollen grains could be seen.
- Planned the design: fan blows on tape, motor moves the tape over the camera, camera takes a picture.
- Picked the parts we already had: Raspberry Pi 3 B+, HQ camera, 28BYJ-48 stepper motor, 5 V fan.
- Wrote the first version of the Pi software and the server.
- Made the wiring diagram.

## Photos

Add photos of the first test here (the tape over the camera, and the camera picture of the pollen).

## Decisions

- Blow air at the tape for now, instead of sucking it through a slot. Simpler to build.
- Use the camera without a lens.
- The LED runs straight from a GPIO pin. Only the fan needs a MOSFET.

## Next

- Wire the electronics and run the hardware test.
- Print a first tape deck.
- Test the fan nozzle and see how big the pollen spot on the tape is.
