# 7. Test and calibrate

**At the end of this step:** every part checked in its place, a sharp picture of the tape,
and the tape moving the right distance each cycle.

Power on the Pi, wait a minute and open **http://pollen-01.local:8080**.

> [!NOTE]
> 📷 **Screenshot to add:** the whole web page, with the cards used below marked (Claude can make this from mock mode).

## Check every part

In the **Hardware checks** card:

- [ ] **Run checks**: power, camera and wiring are all OK.
- [ ] **Coil test (LEDs A→D)**: the 4 small LEDs on the driver board light up one by one, A, B, C, D.

In the **Manual control** card:

- [ ] Fan **On**: it blows down on the tape. **Off** again.
- [ ] Jog the tape **Forward** a little: the spool winds the tape in, and the tape stays flat over the camera.
  If it goes the wrong way, set `invert_direction: true` under `stepper:` in `config.yaml`.

## Get a sharp picture

1. Put something small on the tape over the camera, for a test: a hair, or a pinch of flour.
2. In the **LED colour** card, press **🎯 Auto setup**. It tries colours and exposures for about
   30 seconds and keeps the sharpest picture.
3. Look at the **Live preview**. You should see the hair or the grains as dark shadows.
4. Press **Capture full-res** and write a note, for example "first test, flour".

Run Auto setup again whenever something changes: new tape, the light moved, the room got darker.

> [!NOTE]
> 📷 **Picture to add:** an example of a good test picture (flour or a hair), from the real sampler.

## Calibrate the tape distance

Each cycle, the tape must move so the piece that was under the fan ends up over the camera.
The fan and the camera are **46.2 mm** apart along the tape (from the 3D model).

1. **mm per step.** In **Manual control**, jog **4096** steps forward. Measure how far the tape
   moved, in mm. mm per step = that distance ÷ 4096.
2. **Pitch.** Pick how many cycles it takes from the fan to the camera, *N*. Then the pitch is
   46.2 ÷ *N* mm. For example *N* = 5 gives 9.24 mm per cycle.
3. **Steps per cycle.** `pitch_steps` = pitch ÷ mm per step. Round to a whole number.
4. In `config.yaml`, under `cycle:`, set `pitch_steps` and `camera_offset_cycles` (= *N*).
   Restart the service: `sudo systemctl restart pollen`.
5. **Check.** Put a pen dot on the tape right under the middle of the fan. Press
   **Skip section (1 pitch, no fan)** *N* times. The dot should now be in the middle of the
   camera picture. If not, adjust `pitch_steps` a little and try again.
6. Press **Reset tracking** after any manual jogging.

> [!WARNING]
> The motor turns the take-up spool directly. As tape winds up, the spool gets fatter and the tape
> moves a bit further per step. Check the pen dot again now and then.
