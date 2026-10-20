# Pollen Detector

A cheap, 3D-printable pollen sampler built around a Raspberry Pi.

A fan blows outdoor air onto a strip of clear sticky tape. A small motor moves the tape
along until that piece sits over a camera, and the camera takes a picture. Later, software
will count and recognise the pollen grains in the pictures.

The goal is to place many of these around Denmark (and further) and give better pollen
forecasts, the way [Sensor.Community](https://sensor.community) did for fine dust.
Today pollen is only counted at a few places, by hand, with expensive traps.

**Status:** early prototype. The software runs, the electronics are being wired, and the
3D printed parts are being designed. Nothing is calibrated yet.

![wiring diagram](docs/wiring.svg)

## How it works

```
 tape roll ──► [ fan blows here ] ──► [ camera + LED ] ──► used tape roll
```

1. The fan blows on a fresh piece of tape for a while (for example 10 minutes).
2. The motor moves the tape along.
3. The LED turns on and the camera takes a picture of the tape.
4. The picture is saved and uploaded to a server.
5. Repeat.

The camera has no lens. The tape sits right on top of the camera sensor and the LED shines
through it from above. Pollen grains show up as small shadows.

## Build one yourself

Start with the [build guide](docs/build-guide.md). In short:

| Step | Where |
|---|---|
| Buy the parts | [hardware/bom.md](hardware/bom.md) |
| Print the parts | [hardware/](hardware/) |
| Wire it | [docs/wiring.md](docs/wiring.md) |
| Install the software | [device/README.md](device/README.md) |
| Set up a server for the pictures (optional) | [server/README.md](server/README.md) |

## What's in this repo

| Folder | What |
|---|---|
| `device/` | Software for the Raspberry Pi: controls the motor, fan, LED and camera, and has a web page for testing |
| `server/` | Small server that receives pictures from the devices |
| `hardware/` | 3D models (STL and source files) and the parts list |
| `docs/` | Wiring diagram, build guide, design ideas, links to research |
| `iterations/` | Photos and notes from each version we build |
| `ml/` | Pollen recognition (not started yet) |
| `report/` | Our project report in LaTeX. See [report/README.md](report/README.md) |
| `CLAUDE.md` | Full project notes and decisions. Also used as context for AI assistants |

## Contributing

Ideas, test results and photos are very welcome. If you build one, add a folder in
`iterations/` with photos and what you learned, and open a pull request.

## Related work

- [osaukh/pollenpub](https://github.com/osaukh/pollenpub): an affordable automatic pollen
  monitor from ETH Zurich and TU Graz, with open hardware, code and data.
- More in [docs/references.md](docs/references.md).

## License

- **Software** (everything except `hardware/` and `report/`): [GNU AGPL v3](LICENSE).
  You can use, change and share it. If you share it, or run a changed version as a
  service others use over a network, you must also share your source under the AGPL.
- **3D models and hardware files** (`hardware/`): public domain, [CC0 1.0](hardware/LICENSE).
  Do whatever you want with them. No credit needed.
- **Report** (`report/`): built on the AAU template (BSD 3-Clause, `report/LICENSE-template`).
  The license for our own text is not decided yet.
