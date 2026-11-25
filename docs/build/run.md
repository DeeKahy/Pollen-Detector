# 8. Run it

**At the end of this step:** the sampler takes a sample and a picture every 30 minutes by itself.

## Start the schedule

After a reboot the schedule is **paused**, so a prototype never starts blowing unattended.

1. Open **http://pollen-01.local:8080**.
2. In **Sampling cycle**, press **Run one cycle now** once and watch: fan on, tape moves, light on, picture.
3. Press **Resume schedule**.

Each cycle: the fan blows for 10 minutes, the tape moves one pitch, and the camera photographs
the piece that is now over it. Change the timing in `config.yaml` under `cycle:`
(`interval_min`, `blow_s`).

## Where the pictures go

- On the Pi: in `~/Pollen-Detector/device/data/`, and under **Recent captures** in the web page.
  Each picture has a `.json` file next to it with the time, settings and your note.
- Each picture is about 10-20 MB. A 32 GB card fills up in a few weeks. Copy them off, or turn on uploads.

**Uploading (optional).** The pictures can be uploaded to a server when the Pi has internet.
Ask us for a token, then set `upload:` in `config.yaml` (`enabled: true`, `server_url`, `token`).

## Placing it

- Indoors next to an open window is fine for a first test.
- Outside it needs a roof over it: this prototype has no rain protection yet.
- Keep the power supply and the Pi dry.

## Share what you learned

Make a folder in [`iterations/`](https://github.com/DeeKahy/Pollen-Detector/tree/main/iterations)
with photos of your build, some example pictures and notes on what worked and what didn't.
Copy `iterations/_template.md` to start. Or open an issue on GitHub.
