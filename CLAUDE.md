# Pollen: low-cost automated pollen monitor

> Context file for Claude sessions. Read this first. Project status: **early prototyping**. Electronics wired, first camera tests done, RGB LED wired but not yet supported in software (as of 2026-10-27).
> Repo: https://github.com/DeeKahy/Pollen-Detector
> Keep this file updated when decisions are made. Move items from "Open questions" to "Decisions log".
> **Writing style for docs and diagrams:** plain and simple, short sentences, no em dashes.

## 1. Goal

Build a cheap, 3D-printable, open-hardware pollen sampler that:

1. Pulls/blows outdoor air onto a strip of clear adhesive tape,
2. Advances the tape over a camera and photographs what was caught,
3. Detects and classifies pollen grains in the image (on-device or server-side),
4. Reports counts (grains/m³ per pollen type per time window) to a central server,

so that many units can be spread across Denmark (and beyond) to build a dense network
that feeds better **pollen forecasts**, the way Sensor.Community (originally luftdaten.info,
Stuttgart) did for particulate matter (PM2.5/PM10) with cheap SDS011 sensors, but
specifically for pollen *types*, which particle counters cannot tell apart.

Biologists / aerobiologists and reference data are needed for labelling and calibration.

## 2. How this relates to existing systems

| System | What it is | Relevance |
|---|---|---|
| **Hirst / Burkard 7-day volumetric trap** | The decades-old reference standard (EN 16868). Pump sucks 10 L/min through a 14×2 mm slit onto adhesive-coated Melinex tape on a drum moving 2 mm/h. Tape is stained and counted by hand under a microscope. | Our design is essentially a **miniature, automated Hirst trap**. Copy its principles (known airflow, impaction slit, slow-moving tape). |
| Astma-Allergi Danmark | Runs the Danish pollen counts (Burkard traps in Copenhagen and Viborg). | Best partner for **co-location calibration** and expert labelling. |
| Swisens Poleno, Helmut Hund BAA500, Plair | Commercial automated pollen monitors (holography / fluorescence / image recognition). €50k–150k+. | Proof that automated ID works; we aim for ~€100–150 per unit. |
| Ozcan lab (UCLA) "c-Air" (Wu et al., 2018) | Phone-based **lens-free holographic** bioaerosol sampler with deep-learning ID. | Closest academic precedent to our lensless idea. Read this. |
| Sensor.Community | Citizen network of cheap PM sensors. | Model for the *network/community* side (open data, DIY kits, map). |

## 3. Hardware on hand

| Part | Notes |
|---|---|
| **28BYJ-48 5 V stepper** | Geared ~1:64 → ~2048 steps/rev (full-step) / ~4096 (half-step). Slow, weak, some backlash. Fine for tape advance. Needs a **ULN2003** driver board (usually bundled). 4 GPIO pins. |
| **JZK 5 V brushless sleeve-bearing fan** | Low static pressure. Cannot be powered directly from a GPIO pin. Switch via logic-level MOSFET (or NPN transistor) + flyback diode; PWM for speed. Sleeve bearings wear faster outdoors than ball bearings. |
| **Raspberry Pi 3 B+** (others available) | Enough for capture + scheduling + upload. Marginal for on-device CNN inference on full-res HQ images (1 GB RAM). Pi 4/5 recommended if inference runs on device. |
| **Raspberry Pi HQ Camera (IMX477, CS mount)** | 12.3 MP, 1.55 µm pixels, sensor ~6.29 × 4.71 mm. Colour (Bayer) sensor. Lens off. **IR-cut filter removed** (after the 2026-10-26 tests). The sensor still has its own bonded cover glass. Sensor now exposed: plan is a #1 microscope **coverslip** (~0.15 mm) lying on the sensor cover glass as a dust cover. 22×22 mm likely won't fit down the mount opening: measure it first, or take the mount housing off. |
| **RGB LED, 5 mm, common anode** (4 legs) | Replaces the single LED. Long leg = shared + to 3.3V (pin 17). Red GPIO24 / 220 Ω, green GPIO25 / 100 Ω, blue GPIO5 / 100 Ω. Pin LOW = on. Diode test: R 1.72 V, G 2.28 V, B 2.48 V. See `docs/wiring.md`. **Software still treats GPIO24 as a normal active-high LED**, so red is lit whenever the software thinks the LED is off. |
| Clear adhesive tape (roll) | Initial collection medium. |
| Multimeter (Biltema, autoranging) | Diode test: dial on Ω/CAP, MODE until ▶|, black in COM, red in VΩ. |

### Scale sanity check
Pollen grains are ~10–100 µm (birch ~22 µm, grass ~25–40 µm, mugwort ~20 µm, pine ~60+ µm).
At 1.55 µm/pixel in contact/1:1 imaging, a 22 µm birch grain ≈ **14 px across**. Detectable,
but fine morphology (pores, surface texture) used by biologists for ID is at the limit.
Field of view at 1:1 ≈ 6.3 × 4.7 mm, so the **deposition trace must fit inside ~6 mm**.

## 4. Proposed mechanism (current concept)

```
 supply spool ──► [ impaction station ] ──► [ imaging station ] ──► take-up spool
                     air inlet + slit          LED above tape
                     fan pulls air             camera sensor below
                     through slit onto
                     the sticky side
```

Cycle (example, tune later):
1. Advance tape so a fresh section sits under the inlet slit.
2. Run fan for *T* minutes (e.g. 10–60 min) → particles impact on the adhesive.
3. Advance tape by a fixed distance so that section is over the camera.
4. Turn on LED, capture image(s) (possibly several exposures / focus positions).
5. Run detection + classification → counts → upload with timestamp & metadata.
6. Repeat. Used tape is kept on the take-up spool (physical archive for verification).

### Key design recommendations (from planning discussion)

1. **Suck, don't blow (long-term).** Put the fan *downstream* of the tape, pulling air through a narrow
   **slit** that faces the adhesive (an impactor). Blowing open air at tape gives an unknown,
   wind-dependent sample. A slit jet gives a defined deposition trace and a calculable
   collection efficiency.
   **Decision for the prototype: BLOWING** (simpler to build). Middle ground: a printed funnel/nozzle
   from the fan to a few mm above the tape, see `docs/mechanical-ideas.md` §4. Revisit sucking later.
2. **Measure the airflow.** To report grains/m³ you need sampled volume = flow × time.
   Calibrate each design revision's flow (anemometer/flow meter, or bag-fill test) and ideally
   monitor fan RPM (tach wire, if the fan has one) to detect degradation/clogging.
   The 5 V fan's low static pressure may limit how narrow the slit can be. Test this early;
   a small blower (centrifugal) or diaphragm pump may be needed.
3. **Slit size vs. camera FOV.** Make the slit ≤ ~5 mm long across the tape so the whole
   trace fits in one image. Width ~1–2 mm; jet-to-tape distance roughly 1–2 × slit width.
4. **Don't trust motor steps for tape position.** On a spool, distance per step changes as
   the roll diameter changes. Options: drive the tape with a **capstan + pinch roller**
   (constant distance/step), and/or use the camera for registration (detect the trace edge
   or printed fiducial marks on the tape).
5. **Sticky side must face the slit and stay clean.** Route the tape so the adhesive never
   touches rollers (or only the backing touches them). Consider tape with backing removed
   on-the-fly, or a non-stick (PTFE) guide. Reference traps use silicone-coated Melinex, a
   possible later upgrade if packing tape adhesive gives problems (temperature, dust, ageing).
6. **Illumination is half the imaging problem.** Transmitted light: LED above the tape,
   sensor below. For lensless/holographic imaging use a small LED behind a pinhole
   (~50–100 µm) several cm away to get partially coherent light.
7. **Weatherproofing.** Rain hood over inlet, insect screen coarse enough to pass pollen
   (> ~1 mm mesh), drain holes, condensation management, UV-resistant filament (PETG/ASA,
   not PLA), cable glands. Inlet height and orientation matter (reference traps sit on
   rooftops, ~10–20 m, and use a wind vane to face the inlet into the wind).

## 5. Imaging options (decision pending)

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. Lensless contact / shadow** | Remove lens (and IR filter), tape as close to the sensor as possible, point-ish LED above. | Cheapest, no focus, huge FOV. | Sensor cover glass puts sample ~0.5–1 mm away → blurred diffraction patterns; only ~14 px per birch grain; Bayer filter mixes colours. Risk of contaminating sensor. |
| **A+. Lensless holographic** | Same as A but with pinhole LED + numerical back-propagation (Ozcan-style) to reconstruct in-focus images. | Better resolution from same hardware; proven in literature. | More software complexity; needs coherence/geometry control. |
| **B. Cheap microscope optics** | e.g. reversed M12/CS lens, or a 4×/10× finite-conjugate microscope objective on an extension tube. | Much better morphology → better species ID. | Small FOV (must scan or narrow slit), focus depth sensitive to tape flatness, more alignment, more cost. |

Recommendation: **start with A/A+ since early tests showed pollen is visible**, collect a
dataset, and in parallel run a small B prototype to compare classification accuracy.
Choose based on data, not intuition.

### First imaging results (2026-10-26)

Test object: a light brown hair on the tape. Lensless, IR filter still in, ~11.5 mm air gap
between tape and sensor (filter + mount walls), LED ~30 cm above the tape.
- **Room light beat the blue LED.** Hair clearly visible in most room-light pictures; best was
  greyscale (#09). With the (single, blue) LED only a few were usable; best was contrast ×2 (#21).
  Blue LED in greyscale (#19) was almost black.
- Likely reasons: pure blue only reaches 1 in 4 Bayer pixels; the user thinks a lighter blue
  with white mixed in is needed (hence the RGB LED). The 11.5 mm gap blurs edges by ~0.1 mm
  (source size × gap / distance), so 1:1 crops are soft. Reducing the gap matters most.
- Auto exposure: room light 5195 µs gain 1; blue LED 9976 µs gain 1.9. Default 2000 µs too dark for LED.
- Pictures + per-picture JSON (note, settings, sensor metadata): `iterations/v0-concept/camera-settings-2026-10-26/`
  (on branch `camera-settings-tests` until merged). Full-size originals: GitHub release `data-2026-10-26`.
- Bug fixed: captures could return a stale frame (before a settings change or before the LED
  came on). Now `capture_request(flush=True)` and frames are skipped until exposure matches.

## 6. Software / ML plan

- **OS / capture:** Raspberry Pi OS (Bookworm or newer), `picamera2` / `rpicam-apps`.
  Save raw/lossless images (DNG or PNG), not just JPEG. Compression destroys small features.
- **Control:** Python service (systemd) driving stepper (ULN2003), fan (MOSFET PWM), LED,
  scheduling, and a local queue that survives network outages.
- **Pipeline:**
  1. Preprocess (flat-field / background subtraction using an image of clean tape,
     optional holographic reconstruction).
  2. **Detect** candidate particles (classical blob detection at first, later a detector
     such as a small YOLO/U-Net).
  3. **Classify** each crop: pollen vs. not-pollen (dust, soot, fungal spores, insects, bubbles,
     tape defects) first; then pollen type.
  4. Aggregate → counts per type per sampling window → convert to grains/m³ using flow.
- **Target classes (Danish forecast relevance):** birch (*Betula*), grass (Poaceae),
  mugwort (*Artemisia*), alder (*Alnus*), hazel (*Corylus*), elm (*Ulmus*), plus ragweed
  (*Ambrosia*, emerging) and fungal spores *Alternaria* & *Cladosporium* (also forecast in DK).
  Realistic expectation: genus/family level, not species. Grasses are indistinguishable from
  each other even for experts. That's fine, forecasts group them.
- **Data:** every image + metadata (unit ID, GPS, timestamps, fan run time, flow, temp/RH
  if a sensor is added) uploaded to a central store. Unlabelled data is still valuable.
- **Labelling:** build a simple web labelling tool for biologists. Also create reference
  images by placing *known* pollen (collected from flowering plants/catkins in season) on tape.
- **Inference location:** start server-side (simpler, Pi 3 B+ is enough); move on-device
  later if bandwidth/cost requires.

## 7. Validation & calibration plan

1. **Bench:** known pollen on tape → is it detectable/classifiable with our imaging?
2. **Flow:** measure sampled volume; estimate collection efficiency vs. particle size.
3. **Co-location:** run units next to a reference Burkard trap (Astma-Allergi Danmark) for
   at least one full season (birch Apr–May, grass Jun–Jul, mugwort Jul–Aug); regress our
   counts against official daily counts. This calibration factor is what makes the data
   scientifically usable.
4. **Unit-to-unit consistency:** several identical units side by side.
5. Keep the used tape spools. They allow manual microscope verification later.

## 8. Roadmap (phases)

- **Phase 0 – Feasibility (now):** imaging tests with known pollen; decide lensless vs. optics;
  measure what the 5 V fan can actually pull through a slit.
- **Phase 1 – Bench prototype:** tape transport (capstan), impaction slit, LED + camera,
  Python control loop, image capture to disk. 3D printed, indoor.
- **Phase 2 – Outdoor prototype:** enclosure, rain hood, power, networking, upload pipeline,
  start collecting a dataset continuously.
- **Phase 3 – Recognition:** labelling tool, detector + classifier v1, metrics per class.
- **Phase 4 – Calibration season:** co-location with reference trap, unit-to-unit tests.
- **Phase 5 – Network:** build guide, BOM, firmware images, central server + public map/API,
  recruit hosts; feed data to forecasters.

## 9. Open questions

- Lensless vs. lens? (Section 5) What resolution do biologists need for our target classes?
- Can the 5 V fan generate enough flow through a narrow slit, or do we need a blower/pump?
- Which tape? Packing tape vs. Melinex + silicone; behaviour in cold/heat/humidity; how long
  does a roll last at the chosen advance rate?
- Sampling interval (resolution in time vs. tape use vs. pollen per image).
- Power: mains/USB vs. solar + battery (Pi 3 B+ draws ~2.5–5 W; Pi Zero 2 W far less).
- Connectivity: Wi-Fi at host vs. LTE/LoRa (images are big; LoRa only fits counts).
- Which Pi for deployment (3 B+, 4, 5, Zero 2 W)?
- Who are the biology/aerobiology partners? (Astma-Allergi Danmark, university botany/
  aerobiology groups, DMI for forecasting.)
- Licensing for docs, photos and collected data (code and hardware are decided)?

## 10. Decisions log

| Date | Decision | Reason |
|---|---|---|
| 2026-10-03 | Project concept defined; this file created. | |
| 2026-10-03 | Prototype uses the **blowing** approach (fan above tape), not suction through a slit. | Slit mounting is fiddly; it's a prototype. Funnel/nozzle suggested as a compromise. |
| 2026-10-03 | Team designs the 3D model themselves (they already have a semi-simple design); Claude gives ideas in `docs/mechanical-ideas.md`. | |
| 2026-10-03 | Pin assignment (BCM): stepper IN1-4 = GPIO17/27/22/23, fan MOSFET = GPIO18, LED = GPIO24. | See `docs/wiring.md`. |
| 2026-10-07 | LED runs straight from GPIO24 through a 47 Ω resistor (150 Ω for red/green) to GND pin 20. No MOSFET for the LED. Only the fan uses a MOSFET. | Simpler. A dim LED is fine, use longer exposure. |
| 2026-10-20 | Project moved to GitHub (DeeKahy/Pollen-Detector). Added README, build guide, parts list, iterations log. | So others can build it. |
| 2026-10-20 | License: software AGPL-3.0 (`LICENSE`), 3D models and hardware files in `hardware/` public domain CC0 1.0 (`hardware/LICENSE`). | Keep the code open, including when run as a service. Let anyone reuse the 3D files freely. |
| 2026-10-20 | Report moved from Overleaf to `report/` in this repo. Write via PRs; CI builds the PDF. | Easier for two people to write in parallel and review changes. |
| 2026-10-26 | Every capture gets a JSON sidecar (note, requested settings, sensor metadata, an `about` text) so people and AI tools can read it. Web UI can edit notes and delete pictures; more camera settings, kept across restarts. | Getting a good picture takes many tries; the data should explain itself. |
| 2026-10-26 | Full-size images stay out of git. Git gets 1500 px JPEGs, 1:1 crops and JSON; originals go in a GitHub release (`data-YYYY-MM-DD`). | 18.5 MB per PNG. |
| 2026-10-27 | IR-cut filter removed. Single LED replaced by a common-anode RGB LED (GPIO24/25/5, pins active low). | IR filter only added gap; blue-only light gave poor pictures. |
| 2026-10-27 | Nix dev shell (`flake.nix`, `.envrc`): Python for mock mode + TeX Live for the report. Report CI skips the build when `report/` is unchanged (the `build` check stays required, so the job always runs). | |
| 2026-10-27 | No "Generated with Claude Code" or co-author lines in PRs or commits. | User preference. |
| 2026-10-03 | Software: Python, apt packages only on the Pi (no venv), Flask debug UI on :8080, SQLite queue, HTTP upload with per-device bearer token to a minimal Flask server. Mock mode for laptop dev. Inference server-side later. | Simple, debuggable, robust to network outages. |

## 11. Repo layout

- `device/`: Pi control software (`pollen_device` package). See `device/README.md`.
  - `hardware.py` stepper/fan/LED/camera (+ mocks) · `cycle.py` sampling cycle & tape tracking ·
    `storage.py` SQLite + images · `uploader.py` · `web.py` debug UI/API · `hwtest.py` wiring test ·
    `checks.py` hardware self-checks in the web UI (power, camera, wiring probe via `pinctrl`, coil test)
  - Run on laptop: `python3 -m pollen_device --config config.yaml --mock`
  - Cycle: blow `blow_s` → advance `pitch_steps` → LED + capture. `camera_offset_cycles` = fan→camera
    distance in pitches; a persistent `pipeline` queue links each image to its sample (blow period).
    Image kinds: `sample`, `untracked`, `manual`.
- `server/`: minimal Flask ingest server (`POST /api/v1/upload`, `/api/v1/heartbeat`, overview page).
- `docs/`: `build-guide.md`, `wiring.md` + `wiring.svg` (generated by `make_wiring_svg.py`), `resistors.svg` (colour codes), `direct-cable.md` (SSH, web UI and internet sharing over a laptop cable), `mechanical-ideas.md`, `references.md`.
- `hardware/`: `bom.md` parts list. CAD (STL + source), one folder per part. To be added by the team.
- `iterations/`: one folder per built version with photos, example pictures and notes (`_template.md`).
- `ml/`: recognition plan. Not started. Large datasets stay out of git.
- `flake.nix` / `.envrc`: Nix dev shell (`nix develop`). `pi-backups/`: local copies of the Pi's data dir (git-ignored).
- `report/`: the project report (LaTeX, AAU template). Files in `report/chapters/` are auto-included in number order (`1.0-intro.tex`, `1.1-...`, `2.0-...`) by `report/latexmkrc`. CI (`.github/workflows/report.yml`) builds the PDF on every PR and links it in a comment. `main` is protected.
- `README.md`: public front page of the repo.

## 12. Next steps

0. **RGB LED in software:** three active-low outputs (GPIO24 red, 25 green, 5 blue) instead of one LED;
   web UI switches per colour; captures record which colours were on (JSON); colour presets for a
   test series (red / green / blue / white); update `make_wiring_svg.py`/`wiring.svg` and `hwtest`.
   Then repeat the hair test per colour and fill the report's *Test 2*.
0. Fit a coverslip over the sensor (measure the mount opening first).
1. Buy the missing electronics (`docs/wiring.md` shopping list), wire on a breadboard, run `hwtest`.
2. Install the software, check the camera and LED give usable lensless images (tune exposure in the web UI).
3. Measure mm/step, set `pitch_steps` and `camera_offset_cycles` (calibration in `device/README.md`).
4. Print nozzle variants; test deposition spot size vs. camera field of view.
5. Run indoors/outdoors for days; collect the first dataset; set up the server.
