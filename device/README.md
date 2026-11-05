# Pollen device software

Runs on the Raspberry Pi. It drives the stepper, fan, LED and camera, runs the sampling
cycle on a schedule, serves a **debug web UI** on port 8080, and uploads images to the
server in `../server` (queued locally, so network outages are fine).

```
pollen_device/
  config.py     defaults + YAML loading
  hardware.py   Stepper (28BYJ-48/ULN2003), Output (fan via MOSFET), RgbLed (3 pins, active low), Camera (picamera2) + mocks
  cycle.py      the sampling cycle, tape tracking, manual actions
  storage.py    images on disk + SQLite (samples, captures, upload queue, state)
  uploader.py   background upload + heartbeat
  web.py        debug web UI and JSON API
  hwtest.py     interactive test of each part right after wiring
  checks.py     hardware checks shown in the web UI (power, camera, wiring)
  main.py       wires it all together
```

## Install on the Pi

1. Flash **Raspberry Pi OS (Bookworm or newer)** with Raspberry Pi Imager. Set hostname
   (e.g. `pollen-01`), user, Wi-Fi and enable SSH in the imager settings.
2. Plug the HQ camera ribbon in **with the Pi powered off**.
3. Copy this `device/` folder to the Pi (e.g. `scp -r device pi@pollen-01.local:~/pollen`) and run:
   ```bash
   cd ~/pollen && ./install.sh
   ```
   This installs apt packages, creates `config.yaml` and a systemd service `pollen`.
4. Check the camera: `rpicam-hello --list-cameras` should list `imx477`.
5. Test the wiring part by part: `python3 -m pollen_device.hwtest` (or `--only fan`).
6. Start: `sudo systemctl start pollen`, open `http://pollen-01.local:8080`.

Logs: `journalctl -u pollen -f` (also in the web UI and `data/pollen.log`).

## Hardware checks in the web UI

The web page has a **Hardware checks** card. **Run checks** looks at:

- Power: whether the Pi has seen low voltage since boot (weak power supply).
- CPU temperature.
- Camera: whether it was found at boot and whether the app is using it.
- Wiring: whether the four motor wires are connected, and whether a wire sits on a pin the software doesn't use (a wire one pin off).

**Coil test** turns on the motor driver inputs one by one. The LEDs A, B, C, D on the driver
board should light up in order. **Retry camera** restarts the camera without rebooting.

The fan and LED can't be checked electrically. Switch them on in the web page and look.

**LED colour** has a colour wheel (hue and saturation), an intensity slider and R G B boxes.
The colour is used for live view and pictures. **Calibrate with the camera**: take the tape
out, point the LED at the camera, dim the room, press Calibrate. It photographs the LED off,
red, green and blue at one exposure, and stores what the camera saw (a 3×3 matrix). After
that the picker means what the camera sees: white comes out white, and the pins are mixed to
match. The calibration is only valid for the camera settings it was made with (white balance).
A progress bar shows the try, the picture and the time left. If a try is too bright or too
dark it starts again at half or double the exposure.

**🎯 Auto setup** tries blue, green, red and white. For each it finds the exposure that puts
the background at about 60 % brightness (no clipping), then scores how crisp the darkest edges
are. It keeps the best one (colour, exposure, gain, auto white balance off). About 15 s. Run it
again whenever the sample, the LED position or the room light changes.

**✨ Pulse** breathes the LED darker and brighter (never below "lowest") while slowly going
round the colours. Picking a colour or turning the LED off stops it. Pictures taken while it
runs pause it and use the fixed colour. It uses about 12 % CPU on a Pi 3 B+.

## Run on a laptop (mock mode)

```bash
pip install -r requirements-dev.txt
cp config.example.yaml config.yaml
python3 -m pollen_device --config config.yaml --mock
```
Everything works with fake hardware; the camera produces synthetic images with fake particles.

## The sampling cycle (blowing prototype)

```
supply spool -> [FAN blows] -> ...N pitches... -> [CAMERA + LED] -> take-up spool
```
Each cycle: fan on for `blow_s` -> advance `pitch_steps` -> LED on in the colour `camera.led_rgb`, photograph, LED back as it was.
`camera_offset_cycles` = distance fan->camera in pitches. Each image is stored with the
sample (blow period: start/end time, duration) it belongs to. Images of tape that has
not been tracked through the fan get kind `untracked` (useful as clean-tape references).

Image kinds: `sample` (linked to a blow period), `untracked`, `manual`.

### Calibrating pitch and offset
1. Measure the tape path distance from the centre of the fan opening to the centre of the camera sensor, *D* mm.
2. In the web UI, jog e.g. 4096 steps and measure how many mm the tape moved -> mm/step.
   (If the motor drives the take-up spool directly, this changes as the spool fills - re-check, or use a capstan.)
3. Choose a pitch a bit larger than the blown spot (e.g. 8–10 mm) and set
   `camera_offset_cycles = D / pitch` (make the mechanics so this is a whole number,
   or tweak pitch so it is).
4. Put a pen dot on the tape under the fan, press *Skip section* N times, and check the dot is centred in the preview.
5. Press *Reset tracking* after any manual jogging.

## Web UI / API

| | |
|---|---|
| `GET /` | debug page: live preview, manual control, cycle control, status, recent captures, log |
| `GET /api/status` | everything as JSON |
| `POST /api/fan` `{"value":1}` | switch the fan |
| `POST /api/led` `{"rgb":[1,0.5,0],"on":true}` or `{"colour":"white"}` / `{"colour":"off"}` | set the RGB LED colour (0..1, PWM) and switch it |
| `POST /api/led` `{"effect":"pulse","period_s":4,"hue_s":40,"low":0.2}` / `{"effect":null}` | pulse effect on / off |
| `POST /api/led/auto` | auto setup: best LED colour + exposure for what is on the tape now |
| `POST /api/led/calibrate` / `/api/led/calibration/clear` | measure the camera's response to each LED colour (LED pointed at the camera) |
| `POST /api/jog` `{"steps":500}` | move tape (negative = back) |
| `POST /api/skip` | advance one pitch without blowing (keeps tracking) |
| `POST /api/capture` | full-res capture (LED on in `led_rgb`; the JSON records the colour, pin duties and whether it was calibrated) |
| `POST /api/exposure` `{"exposure_us":2000,"analogue_gain":1}` | camera exposure (0 = auto) |
| `POST /api/cycle/run|pause|resume|abort|reset-tracking` | cycle control |
| `POST /api/cycle/settings` `{"blow_s":300}` | change cycle timing until restart |
| `POST /api/upload/now` | upload queue now |
| `GET /api/preview.jpg`, `/api/captures`, `/api/logs`, `/images/<path>` | data |

The UI has no login by default (LAN debugging). Set `web.password` before putting a device on an untrusted network.

## Notes
- Images are saved as lossless PNG (+ `.thumb.jpg`). Optional raw DNG (`camera.save_dng`) for later lensless reconstruction.
- Full-res PNG on a Pi 3B+ takes a few seconds and ~10–20 MB each. At 48 cycles/day that is ~1 GB/day. Use a big SD card or `upload.delete_after_upload: true`.
- The scheduler starts **paused** after boot (`cycle.start_paused`) so a rebooting prototype doesn't start blowing unattended. Set it to `false` for real deployments.
