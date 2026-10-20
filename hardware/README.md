# Hardware

3D models and the parts list.

- [bom.md](bom.md): everything you need to buy.
- [../docs/mechanical-ideas.md](../docs/mechanical-ideas.md): design ideas and printing tips.
- [../docs/wiring.md](../docs/wiring.md): how to wire the electronics.

## Folders

Put the 3D files here, one folder per part:

```
hardware/
  base/            the base plate everything mounts on
    base.stl       ready to print
    base.step      source (or .f3d, .FCStd, .scad)
  fan-nozzle/
  camera-mount/
  tape-spools/
  ...
```

For each part, include:

- The **STL** (what people print).
- The **source file** (so others can change it). STEP works in most CAD programs.
- A short note in the folder's README if it needs special print settings
  (material, supports, infill, orientation).

When a part changes a lot, keep the old version in the iteration folder in `iterations/`
instead of here, so this folder always has the current design.
