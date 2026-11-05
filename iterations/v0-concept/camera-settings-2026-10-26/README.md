# Camera settings tests (2026-10-26)

First real pictures with the HQ camera in lensless mode, to find out which settings work.
We changed one setting at a time and took a picture of the same spot on the tape.

**Note on dates:** the Pi has no clock battery and no internet here, so the image files
and JSON say 2026-10-07. The real date is 2026-10-26.

## What we did

- **Series 1 (pictures 03 to 12):** room light on. The LED pointed away from the tape,
  so all light came from the room.
- **Series 2 (pictures 13 to 23):** room dark, LED pointed at the tape. Same settings as
  series 1, so each picture has a partner (13 goes with 03, 14 with 04, and so on).
  Picture 23 is an extra.
- **Own tests (01, 02):** blue light and desk lamp.
- The IR-cut filter (the blue glass in the lens mount) was removed around this time.
  TODO: note whether that was before or after series 2.

## What we learned

- Auto exposure picked **5195 µs at gain 1** with room light and **9976 µs at gain 1.9**
  with the LED. So the LED gives about 3 to 4 times less light than the room.
  The default 2000 µs is too dark for LED pictures.
- Picture 23 is the best guess for a good LED picture: 19000 µs, gain 1, no sharpening,
  no noise reduction, fixed white balance, raw DNG saved.
- Fixed bug: before this, a picture could be an old frame from before a settings change
  or before the LED came on. Fixed in the device software (`frames_skipped` in the JSON).
- Ideas for later: blue or green LED (better contrast for yellow-brown pollen), RGB LED
  with one picture per colour, a microscope coverslip over the sensor to protect it.

## Files

- `pictures/NN.jpg`: the whole picture, made smaller (1500 px wide).
- `pictures/NN-crop.jpg`: 800 × 600 px from the middle at full resolution (1 pixel = 1.55 µm).
  Use this to judge detail.
- `pictures/NN.json`: everything about the picture: note, settings asked for, and what the
  sensor reported.
- Full-size originals (18.5 MB PNG each, plus 3 raw DNG files, the database and the log)
  are not in git. Download them from the GitHub release
  [data-2026-10-26](https://github.com/DeeKahy/Pollen-Detector/releases/tag/data-2026-10-26)
  (`pollen-originals-2026-10-26.zip`, 267 MB). There is also a copy on the Mac used for the
  tests, in `pi-backups/2026-10-26/` (ignored by git).

## Pictures

| Picture | Series | Changed from baseline | Measured | Why / note |
|---|---|---|---|---|
| [01](pictures/01.jpg) ([crop](pictures/01-crop.jpg), [json](pictures/01.json)) | own test | own test | 1989 µs, gain 1.0 | Under blue light with id like 30 cm distance from the led |
| [02](pictures/02.jpg) ([crop](pictures/02-crop.jpg), [json](pictures/02.json)) | own test | own test | 1989 µs, gain 1.0 | on the desk using just my home light which aims itself diagonally at the table and therefore light |
| [03](pictures/03.jpg) ([crop](pictures/03-crop.jpg), [json](pictures/03.json)) | 1: room light | baseline | 1989 µs, gain 1.0 | Baseline: the current default settings (2000 us, gain 1, auto white balance, normal processing). Every other picture in the series is compared to this one. |
| [04](pictures/04.jpg) ([crop](pictures/04-crop.jpg), [json](pictures/04.json)) | 1: room light | {exposure_us: 500} | 497 µs, gain 1.0 | Short exposure (500 us, 4x shorter than baseline). Checks if bright areas are clipped to white at baseline. If this one shows detail the baseline lost, the baseline is overexposed under room light. |
| [05](pictures/05.jpg) ([crop](pictures/05-crop.jpg), [json](pictures/05.json)) | 1: room light | {exposure_us: 10000} | 9976 µs, gain 1.0 | Long exposure (10000 us = exactly one 50 Hz mains half-cycle). Room lights flicker at 100 Hz in Denmark; with a rolling shutter that can give horizontal bands. Exposures that are multiples of 10 ms average the flicker out. Likely overexposed under room light, but shows if banding is the reason for uneven brightness. |
| [06](pictures/06.jpg) ([crop](pictures/06-crop.jpg), [json](pictures/06.json)) | 1: room light | {exposure_us: 0} | 5195 µs, gain 1.0 | Auto exposure: the camera picks exposure and gain itself. The values it chose (see camera.ExposureTime and AnalogueGain in this file) are a good hint for what a fixed exposure should be under this light. |
| [07](pictures/07.jpg) ([crop](pictures/07-crop.jpg), [json](pictures/07.json)) | 1: room light | {exposure_us: 500, analogue_gain: 4.0} | 497 µs, gain 4.0 | Same brightness as baseline (500 us x gain 4 = 2000 us x gain 1) but reached with gain instead of time. Compare noise with baseline: gain adds grain, so this should look noisier. Shows how much worse gain is than exposure. |
| [08](pictures/08.jpg) ([crop](pictures/08-crop.jpg), [json](pictures/08.json)) | 1: room light | {sharpness: 0, noise_reduction: off} | 1989 µs, gain 1.0 | Baseline exposure with image processing turned off (no sharpening, no noise reduction). Sharpening adds halos around edges and noise reduction can wipe out tiny particles. For measuring grain sizes and shapes the unprocessed image is more honest, even if it looks grainier. |
| [09](pictures/09.jpg) ([crop](pictures/09-crop.jpg), [json](pictures/09.json)) | 1: room light | {saturation: 0} | 1989 µs, gain 1.0 | Greyscale (saturation 0). In lensless mode colour from the Bayer filter mostly adds colour noise. If greyscale looks as informative as colour, detection can work on greyscale, which is simpler. |
| [10](pictures/10.jpg) ([crop](pictures/10-crop.jpg), [json](pictures/10.json)) | 1: room light | {awb: false, colour_gain_red: 2.0, colour_gain_blue: 2.0} | 1989 µs, gain 1.0 | Fixed white balance (red and blue gains 2.0) instead of auto. Auto white balance changes with the light and with what is on the tape, so colours drift between pictures. Fixed gains keep colours comparable across pictures and days. |
| [11](pictures/11.jpg) ([crop](pictures/11-crop.jpg), [json](pictures/11.json)) | 1: room light | {contrast: 2.0} | 1989 µs, gain 1.0 | Contrast 2 (double). Makes faint particles stand out more for the human eye. Downside: dark and bright areas clip sooner. For viewing, not for measuring. |
| [12](pictures/12.jpg) ([crop](pictures/12-crop.jpg), [json](pictures/12.json)) | 1: room light | {sharpness: 0, noise_reduction: off, awb: false, colour_gain_red: 2.0, colour_gain_blue: 2.0, save_dng: true} | 1989 µs, gain 1.0 | Candidate 'measurement' setup: baseline exposure, no processing, fixed white balance, plus the raw sensor data saved as DNG next to this image. The DNG has no processing at all and is what a later lensless (holographic) reconstruction would need. |
| [13](pictures/13.jpg) ([crop](pictures/13-crop.jpg), [json](pictures/13.json)) | 2: dark, LED | baseline | 1989 µs, gain 1.0 | Baseline: the current default settings (2000 us, gain 1, auto white balance, normal processing). Every other picture in the series is compared to this one. |
| [14](pictures/14.jpg) ([crop](pictures/14-crop.jpg), [json](pictures/14.json)) | 2: dark, LED | {exposure_us: 500} | 497 µs, gain 1.0 | Short exposure (500 us, 4x shorter than baseline). With only the LED this is probably very dark. Shows how much LED light reaches the sensor in a short time. |
| [15](pictures/15.jpg) ([crop](pictures/15-crop.jpg), [json](pictures/15.json)) | 2: dark, LED | {exposure_us: 10000} | 9976 µs, gain 1.0 | Long exposure (10000 us, 5x baseline). The LED runs on DC, so there is no mains flicker to worry about now (unlike series 1). A longer exposure simply collects more LED light. Shows if a dim LED can be made up for with time. |
| [16](pictures/16.jpg) ([crop](pictures/16-crop.jpg), [json](pictures/16.json)) | 2: dark, LED | {exposure_us: 0} | 9976 µs, gain 1.9 | Auto exposure: the camera picks exposure and gain itself. The values it chose (camera.ExposureTime and AnalogueGain in this file) show what this LED needs. Compare with the auto choice in series 1 (5195 us, gain 1 under room light). |
| [17](pictures/17.jpg) ([crop](pictures/17-crop.jpg), [json](pictures/17.json)) | 2: dark, LED | {exposure_us: 500, analogue_gain: 4.0} | 497 µs, gain 4.0 | Same brightness as baseline (500 us x gain 4 = 2000 us x gain 1) but reached with gain instead of time. Compare noise with baseline. In the dark, gain noise is usually more visible than with room light. |
| [18](pictures/18.jpg) ([crop](pictures/18-crop.jpg), [json](pictures/18.json)) | 2: dark, LED | {sharpness: 0, noise_reduction: off} | 1989 µs, gain 1.0 | Baseline exposure with image processing turned off (no sharpening, no noise reduction). Sharpening adds halos around edges and noise reduction can wipe out tiny particles. For measuring grain sizes and shapes the unprocessed image is more honest, even if it looks grainier. |
| [19](pictures/19.jpg) ([crop](pictures/19-crop.jpg), [json](pictures/19.json)) | 2: dark, LED | {saturation: 0} | 1989 µs, gain 1.0 | Greyscale (saturation 0). The LED has one colour, so colour carries even less information than under room light. If greyscale looks as informative, detection can work on greyscale. |
| [20](pictures/20.jpg) ([crop](pictures/20-crop.jpg), [json](pictures/20.json)) | 2: dark, LED | {awb: false, colour_gain_red: 2.0, colour_gain_blue: 2.0} | 1989 µs, gain 1.0 | Fixed white balance (red and blue gains 2.0) instead of auto. Auto white balance tries to make the LED colour look white and changes with what is on the tape. Fixed gains keep colours comparable across pictures and days. The LED colour will show as it really is. |
| [21](pictures/21.jpg) ([crop](pictures/21-crop.jpg), [json](pictures/21.json)) | 2: dark, LED | {contrast: 2.0} | 1989 µs, gain 1.0 | Contrast 2 (double). Makes faint particles stand out more for the human eye. Downside: dark and bright areas clip sooner. For viewing, not for measuring. |
| [22](pictures/22.jpg) ([crop](pictures/22-crop.jpg), [json](pictures/22.json)) | 2: dark, LED | {sharpness: 0, noise_reduction: off, awb: false, colour_gain_red: 2.0, colour_gain_blue: 2.0, save_dng: true} | 1989 µs, gain 1.0 | Candidate 'measurement' setup: baseline exposure, no processing, fixed white balance, plus the raw sensor data saved as DNG next to this image. The DNG has no processing at all and is what a later lensless (holographic) reconstruction would need. |
| [23](pictures/23.jpg) ([crop](pictures/23-crop.jpg), [json](pictures/23.json)) | 2: dark, LED | {exposure_us: 19000, sharpness: 0, noise_reduction: off, awb: false, colour_gain_red: 2.0, colour_gain_blue: 2.0, save_dng: true} | 18984 µs, gain 1.0 | Measurement setup like the previous picture, but at the brightness auto exposure chose for this LED (9976 us x gain 1.90), reached with exposure time only and gain 1 to keep noise low. This is the best guess for a properly exposed, unprocessed LED picture. |
