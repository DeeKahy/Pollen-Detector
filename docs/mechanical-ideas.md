# Mechanical design ideas (3D printing)

Ideas and rules of thumb for the printed parts. The team designs the CAD itself; this is input,
not a finished design. **Measure your actual parts with calipers**. The dimensions below are typical values.

## 1. Overall layout: a straight "tape deck"

```
 side view (tape sticky side UP the whole way)

        fan + nozzle                LED + pinhole (light-tight tube)
            ||                               |
            vv                               v
 (supply)--idler--[ backing plate ]--...--[ camera window ]--(drive)--(take-up)
   brake            under the nozzle         sensor below tape
```

- Everything in a straight line on one flat base plate: supply spool → idler → fan station →
  camera station → drive → take-up spool.
- **Adhesive faces up the whole way.** Rollers and guides then only ever touch the backing.
  Fan and LED are above the tape, the camera below.
- Keep the fan→camera distance a whole number of "pitches" (see `device/README.md`), e.g. 40 mm
  with a 10 mm pitch → `camera_offset_cycles: 4`. Shorter distance = less tape wasted at start-up.

## 2. Tape

- Use **clear** tape ("crystal clear"), not frosted/matte "magic" tape (it scatters light and ruins images).
- Narrow tape (12–19 mm) suits the ~6 × 4.7 mm camera field of view better than 48 mm packing tape,
  and a roll lasts longer. Packing tape can be slit narrower with a printed jig and a blade.
- Roll life: 33 m roll / 10 mm per cycle = 3300 cycles ≈ 69 days at 48 cycles/day.
- When the take-up spool winds the used tape, the adhesive sticks to the backing of the previous
  layer, just like the original roll. That keeps samples sealed for later checks under a microscope.
- Put the supply roll on so it unwinds with the adhesive facing up. Which side the tape leaves the
  roll from decides this, so mock it up by hand first.

## 3. Tape tension and drive

The tape must stay taut and flat over the nozzle and the camera, or it wanders, sags and drifts out of focus.

- **Supply-side brake:** light friction on the supply spool. Options: felt pad on a printed spring arm,
  an O-ring "belt" around the hub, or a printed leaf spring rubbing the spool flange.
- **Drive, three options (simplest first):**
  - **A. Motor drives the take-up spool directly.** Simplest. But the spool grows, so mm per step
    changes over time (maybe ±30 % over a roll). Fine for the first prototype; recalibrate the
    pitch now and then, or let software correct it.
  - **B. Capstan.** A printed roller with an O-ring tyre, after the camera. The tape wraps about 180°
    around it with the backing on the roller, and a weak take-up (spring or slipping clutch) keeps it
    tight. This gives constant mm per step. Don't use a pinch roller pressing on the sticky side.
  - **C. Odometer wheel.** A free idler roller on the backing side, with a magnet and Hall sensor or a
    slotted disk and photo-interrupter. Software then advances until the wheel has turned X mm.
    This gives precise positioning with option A's simple drive. It needs 1 more GPIO and a software change.
- **28BYJ-48 shaft:** Ø5 mm with two flats 3 mm apart. Print a D-hole hub and add a grub screw or a
  tight press fit. Mounting ears have holes 35 mm apart, Ø4.2. The shaft is off-centre from the motor
  body (~8 mm), so measure before you design around it.
- **Spools:** 608 skateboard bearings (22 mm OD × 7 mm) pressed into printed hubs make smooth axles.
  Or use a printed hub on an M8 bolt.

## 4. Fan station (blowing prototype)

Blowing straight at open tape gives an undefined, wind-dependent deposit. Cheap ways to make it better
without the hassle of sucking through a slit:

- **Funnel and nozzle:** a printed duct from the fan face that narrows into a nozzle (e.g. 5 × 5 mm or
  3 × 8 mm) 2–4 mm above the tape. Particles pile up in a known spot that fits in one camera frame,
  and the airspeed goes up, so more pollen sticks.
- **Make the nozzle a separate, swappable part** (snap or 2 screws). Then you can test sizes and gaps
  quickly. Print 3–4 variants.
- **Backing plate under the tape** at the nozzle. Otherwise the jet pushes the tape away. Give it a
  smooth top surface (print face down on glass, or stick a strip of PTFE tape on it).
- **Fan intake** behind a rain hood and coarse mesh (≥ 1 mm). Put the intake side away from where rain comes from.
- **Later:** turn the fan around so it sucks. The same duct and nozzle then becomes the impactor
  recommended in CLAUDE.md, so design the duct with that in mind.

## 5. Camera station

**Lensless (current plan):**
- Remove the CS lens mount and IR filter to expose the sensor (do it in a clean place, and keep a
  sensor cap on). Mount the HQ camera board face up. The board is 38 × 38 mm with M2.5 holes about
  30 × 30 mm apart. Check yours.
- Print a "sensor saddle" that bolts to those holes. It has a slot or channel that guides the tape a
  fraction of a mm above the sensor glass, with chamfered entry and exit edges so the tape doesn't snag.
- Optionally, a thin glass coverslip in the saddle as a window. It keeps the sensor clean and the tape
  slides on glass, but it adds ~0.15 mm distance.
- **Light-tight hood** over the camera station, with the LED in a tube 3–6 cm above the tape. Stray
  sunlight will swamp a lensless image. Pinhole (foil + needle) under the LED. Print in black, matte.

**With optics (for comparison):** a printed tube holding an M12 lens, or a cheap 4×/10× microscope
objective, with a fine thread or a screw-and-spring for focus. The field of view gets smaller, so the
nozzle spot must too.

## 6. Electronics bay

- Separate compartment from the airflow (dust, condensation).
- **Pi 3 B+:** 85 × 56 mm, M2.5 holes in a 58 × 49 mm rectangle. Use 5–6 mm standoffs and a
  heat-set insert or self-tapping screws.
- ULN2003 board, a small perfboard for the 2 MOSFETs, and an optional BME280. Measure the hole patterns.
- Cable channel to the camera station. The CSI ribbon can be bought in 30–50 cm lengths.
- Openings for USB power and the SD card.

## 7. Making it field-ready (later)

- **Removable cassette:** the whole tape path (spools, stations) on a sled that slides out. You swap
  it in the field and read or archive the used one in the lab.
- **Enclosure:** PETG or ASA, not PLA (PLA creeps in the sun). Add a gasket or overlap lip, drain
  holes, a desiccant pocket in the electronics bay, and cable glands.
- Mount it on a pole or rooftop. Inlet height affects what you measure, so keep it consistent across units.
- Optionally, a wind vane so the inlet turns into the wind, like the Burkard trap. That's probably a
  later version.

## 8. Alternative worth keeping in mind: drum

The Burkard trap wraps tape around a drum that turns slowly, which avoids spool and tension problems
altogether. A printed drum (Ø ~50 mm) on the stepper, with the nozzle and camera both aimed at the drum
surface, is compact. The catch is that imaging a curved, moving surface lensless is hard, because the
sensor can't touch the drum. So it works better with a lens.

## 9. Printing tips

- Holes: add 0.2–0.3 mm clearance. Bearing seats: test-print a ring first.
- Use M3 heat-set inserts wherever screws go in and out repeatedly.
- Keep parts that touch the tape smooth: print them face-down, or sand them.
- Use a parametric CAD tool (FreeCAD, Fusion, OnShape or OpenSCAD) so nozzle size, fan size and
  station distances are variables.

## 10. Small printed helpers

- Tape slitting jig (cut packing tape down to 12–19 mm).
- Calibration strip: a printed ruler to stick next to the tape path for measuring mm per step.
- "Dot jig": marks a pen dot exactly under the nozzle, to check the fan→camera alignment
  (`device/README.md`, calibration step 4).
