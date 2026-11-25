#!/usr/bin/env bash
# Makes the 3D pictures for the build guide (docs/build/img/). Run from this folder:
#   nix shell nixpkgs#openscad -c ./make_guide_renders.sh
set -euo pipefail
cd "$(dirname "$0")"
OUT=../../docs/build/img
mkdir -p "$OUT"
SIZE=1400,900
SCHEME=Tomorrow   # light background

shot() {  # file, camera (rot_x,rot_y,rot_z), extra -D args...
  local file=$1 rot=$2; shift 2
  openscad --quiet --imgsize=$SIZE --colorscheme=$SCHEME --projection=p \
    --camera=0,0,0,$rot,0 --viewall --autocenter "$@" -o "$OUT/$file" "${SRC:-assembly_steps.scad}"
}

FRONT=60,0,200   # from the front, a bit from above and the right
BACK=60,0,20     # from behind

# one picture per assembly step
for s in 1 3 4 5 6 7; do shot "step$s.png" $FRONT -D step=$s; done
shot step2.png $BACK -D step=2

# each printed part alone, in its print orientation
for p in frame tray led_tower camera_plug takeup_spool motor_pin; do
  SRC=tape_deck.scad shot "part-$p.png" 55,0,25 -D "part=\"$p\""
done

# finished unit
SRC=tape_deck.scad shot assembled.png $FRONT -D 'part="assembly"'
echo "done: $OUT"
