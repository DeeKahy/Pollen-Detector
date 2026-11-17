// Pollen sampler prototype frame (simple version). Public domain (CC0), see hardware/LICENSE.
//
// One flat wall ("frame") that everything hangs off, standing in a tray:
//   front of the wall: tape roll peg, fan shelf, camera box, take-up spool
//   back of the wall:  motor, and on the tray the breadboard (the Pi just sits behind it for now)
//
// Parts (export one with -D 'part="..."'):
//   assembly      everything together with dummy parts
//   frame         the wall. Print lying on its back: everything sticks straight up, no supports
//   tray          the frame stands in its groove. The breadboard goes behind the frame
//   led_tower     stands on the camera box, the tape runs through under it. Print in black
//   camera_plug   cap over the front of the camera box, with a slit for the ribbon
//   takeup_spool  on the motor shaft
//   motor_pin     x2: hold the motor's ears to the wall
//   tape_check    should come out EMPTY: anything solid in the space above the sticky side
//
// No glue, screws or nuts: everything is a press fit or a snap fit. If a fit is too tight
// or too loose on your printer, change `press`, `clip`, `fit` or `shaft_fit`.
//
// Coordinates: x = the way the tape moves (roll on the left), y = out of the wall (front is +y),
// z = up. The front face of the wall is y = 0, the bottom of the wall is z = 0.

part = "assembly";

// ---- measure these -------------------------------------------------------
tape_w    = 19;     // tape width
roll_od   = 58;     // full tape roll, outside
peg_d     = 26;     // peg the roll slots onto (26 works for Tesafilm / Scotch plastic cores)
fan_size  = 30;     // fan frame, square. Pi case fans are mostly 30 (some 25). Thickness doesn't matter
cam_board = 38;     // Pi HQ camera board, square
board_t   = 1.4;    // its thickness (official drawing). The connector under it is 2.75 mm tall
sensor_h  = 2.0;    // board top to sensor glass top, lens mount off (check!)
gap       = 1.0;    // tape underside to sensor glass top
bb_size   = [165, 55]; // full-size breadboard (a half-size one: 83 x 55)

// ---- design ---------------------------------------------------------------
t        = 2.4;     // wall and plate thickness
fit      = 0.3;     // sliding fits (camera)
press    = 0.1;     // press fits on long edges (frame in tray, breadboard)
clip     = 0.2;     // parts that hug something (fan rim, LED tower, camera plug). Plastic shrinks
shaft_fit = 0.3;    // extra on the motor shaft hole (5 x 3 mm shaft). Bigger = looser
peg_tilt = 4;       // degrees up, so the roll slides back against the collar
cam_gap  = 5;       // free space between the fan shelf and the LED tower
fan_up   = 8;       // fan bottom above the tape (the shelf underside is 5.6 mm above it)
tape_clear = 2;     // free space beside the tape where it runs through the LED tower
motor_ear = 35;     // 28BYJ-48 ear holes, centre to centre
motor_off = 8;      // 28BYJ-48 shaft offset from the body centre
$fn = 64;

// ---- derived ----------------------------------------------------------------
roll_r = roll_od / 2;
tape_y = cam_board / 2 + fit;          // tape centre: the camera board touches the wall
tape_y0 = tape_y - tape_w / 2;         // inner tape edge (collar length)
z_axle = roll_r + 6;                   // peg and motor shaft height
z_tape = z_axle - 4;                   // tape surface: a bit above the roll bottoms, so it bends down over the edges
x_sup  = roll_r + 3;
x_fan  = x_sup + roll_r + 4 + fan_size / 2;
box_in = cam_board + 2;                // camera box inside width (x) and depth (y)
skirt  = 1.6;                          // thickness of the parts that clip over the box
box_out = box_in / 2 + t;              // camera box, centre to outside of the wall
x_cam  = x_fan + fan_size / 2 + 2 + cam_gap + box_out + clip + skirt;
fan_cam = x_cam - x_fan;               // use this for the tape pitch in the device config
x_tak  = x_cam + box_in / 2 + t + 4 + roll_r;
L      = x_tak + roll_r + 3;
H      = z_axle + roll_r + 2;
board_top = z_tape - gap - sensor_h;
roof_t = 1.6;
box_bot = board_top - board_t - 3;         // bottom of the box side walls
echo(str("Frame ", L, " x ", H, " mm. Tape at z = ", z_tape, ", tape centre ", tape_y, " mm from the wall, fan to camera ", fan_cam, " mm"));

module rbox(s, r = 2) hull() for (x = [r, s[0] - r], y = [r, s[1] - r]) translate([x, y, 0]) cylinder(r = r, h = s[2]);
module ycyl(d, h) rotate([-90, 0, 0]) cylinder(d = d, h = h);

// ---- frame ------------------------------------------------------------------
module frame_part() {
    difference() {
        union() {
            // the wall. Its bottom edge sits in the tray groove
            translate([0, -t, 0]) cube([L, t, H]);
            // supply peg: collar, then a hollow peg tilted up a little
            translate([x_sup, 0, z_axle]) {
                ycyl(peg_d + 8, tape_y0 - 0.5);
                translate([0, tape_y0 - 0.6, 0]) rotate([peg_tilt, 0, 0]) difference() {
                    ycyl(peg_d, tape_w + 4);
                    translate([0, -1, 0]) ycyl(peg_d - 4, tape_w + 6);
                }
            }
            // fan shelf above the tape, and a ledge under the tape for the air to push against
            translate([x_fan - fan_size / 2 - 2, 0, z_tape + fan_up - t]) cube([fan_size + 4, tape_y + fan_size / 2 + 2, t]);
            // rim the fan presses into
            translate([x_fan, tape_y, z_tape + fan_up]) difference() {
                translate([-fan_size / 2 - clip - 1.6, -fan_size / 2 - clip - 1.6, 0]) cube([fan_size + 2 * clip + 3.2, fan_size + 2 * clip + 3.2, 4]);
                translate([-fan_size / 2 - clip, -fan_size / 2 - clip, -1]) cube([fan_size + 2 * clip, fan_size + 2 * clip, 6]);
                translate([-3, -fan_size / 2 - 3, 1]) cube([6, 4, 4]);   // notch for the fan wire, wall side
            }
            translate([x_fan - fan_size / 2, 0, z_tape - t]) cube([fan_size, tape_y + tape_w / 2 + 3, t]);
            // camera box: two side walls, roof (the tape runs over it), rails for the board
            for (s = [-1, 1]) translate([x_cam + s * (box_in / 2 + t / 2) - t / 2, 0, box_bot]) cube([t, box_in, z_tape - box_bot]);
            translate([x_cam - box_in / 2 - t, 0, z_tape - roof_t]) cube([box_in + 2 * t, box_in, roof_t]);
            for (s = [-1, 1]) translate([x_cam + s * (box_in / 2 - 1) - 1, 0, board_top - board_t - 1.5]) cube([2, box_in, 1.5]);
        }
        // fan opening
        translate([x_fan - (fan_size - 4) / 2, tape_y - (fan_size - 4) / 2, z_tape]) cube([fan_size - 4, fan_size - 4, fan_up + 1]);
        // window over the sensor, open to the front so the sensor can slide in under the roof
        translate([x_cam - 6, tape_y - 6, z_tape - roof_t - 1]) cube([12, box_in, roof_t + 2]);
        // motor: shaft boss hole, and holes for the two motor pins (tight)
        translate([x_tak, -t - 1, z_axle]) ycyl(9.5, t + 2);
        for (dx = [-1, 1]) translate([x_tak + dx * motor_ear / 2, -t - 1, z_axle + motor_off]) ycyl(pin_d, t + 2);
        // camera ribbon straight through the wall behind the box, just under the board
        // (slide the camera in connector first). The plug slit is the other option.
        translate([x_cam - 9, -t - 1, board_top - board_t - 3]) cube([18, t + 2, 3]);
        // holes for cables: fan, camera ribbon (next to the box), LED (over the box)
        translate([x_fan - 3, -t - 1, z_tape + fan_up + 4.5]) rotate([-90, 0, 0]) rbox([6, 4, t + 2], 1);
        translate([x_cam - box_in / 2 - t - 6, -t - 1, box_bot]) cube([4, t + 2, 18]);
        translate([x_cam + box_in / 2 + t + 1, -t - 1, z_tape + 6]) rotate([-90, 0, 0]) rbox([5, 4, t + 2], 1);
    }
}

// ---- tray -------------------------------------------------------------------
// Behind the wall: the breadboard right next to it, so the motor, fan and LED wires are short.
bb_out = [bb_size[0] + 2 * press + 3.2, bb_size[1] + 2 * press + 3.2];  // breadboard pocket, outside
bb_x0  = (L - bb_out[0]) / 2;
bb_y0  = -t - press - 4 - bb_out[1];
back   = -bb_y0 + 4 - t;                          // tray depth behind the frame
front  = tape_y + tape_w / 2 + 6;                 // tray depth in front of the frame (under the rolls)
module tray_part() {
    rib = 6;
    difference() {
        translate([0, -t - back, -t]) rbox([L, back + t + front, t], 3);
        // weight saving: under the tape rolls, and under the breadboard (it rests on a 6 mm ledge)
        for (x = [x_sup, x_tak]) translate([x - 15, 4, -t - 1]) rbox([30, front - 10, t + 2], 3);
        translate([bb_x0 + 1.6 + 6, bb_y0 + 1.6 + 6, -t - 1]) rbox([bb_size[0] - 12, bb_size[1] - 12, t + 2], 3);
    }
    // groove the frame presses into
    for (y = [-t - press - 2, press]) translate([0, y, 0]) cube([L, 2, rib]);
    // pocket the breadboard presses into
    translate([bb_x0, bb_y0, 0]) difference() {
        cube([bb_out[0], bb_out[1], 4]);
        translate([1.6, 1.6, -1]) cube([bb_size[0] + 2 * press, bb_size[1] + 2 * press, 6]);
    }
}

// ---- LED tower ----------------------------------------------------------------
// Pushed straight down onto the camera box, after the tape is threaded. It holds in two ways:
//  - snap hooks: the four skirts reach down past the bottom edge of the box side walls and
//    click under it. Each skirt has a pull tab at the bottom.
//  - top hook: a tab reaches over the top edge of the wall, with a lip down the back. It stops
//    the tower tipping forward.
// To take it off: pull the tabs outward (the skirts bend about 1 mm) and lift. Nothing of the
// tower is under the tape, so it comes off without unthreading the tape.
led_h = 38;     // LED above the tape
hook  = 0.8;    // how far each snap hook reaches in under the box wall (catches hook - clip)
tsk   = 1.4;    // skirt thickness. Thinner = easier to snap on and off
use_plug = false;                                           // camera plug not used: ribbon goes out the back
leg_back  = [0, tape_y0 - tape_clear];                      // leg against the wall (y from, to)
leg_front = [tape_y + tape_w / 2 + tape_clear, box_in];     // leg at the front
plug_tab  = 4.5;                                            // how far the plug's side tabs reach back
box_drop  = z_tape - box_bot;                               // tape (top of the box) to the bottom of its walls
module led_tower_part() {
    // The tape runs straight through under this part. Nothing may cross the space between the
    // legs: the sticky side faces up here. Check with part = "tape_check".
    top = 13;   // thick enough for the body pocket, the nipple and the cones
    sk = box_out + clip;                    // inside face of the skirts: clip off the box walls
    zr = -box_drop - clip;                  // top face of the hooks, just under the box walls
    zh = zr - 1.5 * hook - 0.6;             // bottom of the skirts
    front_end = use_plug ? box_in - plug_tab - 0.5 : box_in;
    wall_top = H - z_tape;                  // top of the frame wall, above the tape
    difference() {
        union() {
            translate([-12, 0, led_h - top]) cube([24, box_in, top]);
            for (leg = [leg_back, leg_front]) {
                d = leg[1] - leg[0];
                translate([-12, leg[0], 0]) cube([24, d, led_h]);
                hull() {  // widens at 45 degrees towards the skirts, so it prints upside down without support
                    translate([-sk - tsk, leg[0], 0]) cube([2 * sk + 2 * tsk, d, 4]);
                    translate([-12, leg[0], 0]) cube([24, d, 4 + sk + tsk - 12]);
                }
            }
            for (sx = [-1, 1]) mirror([sx < 0 ? 1 : 0, 0, 0]) {
                // skirts only beside the legs, never across the tape
                for (r = [leg_back, [leg_front[0], front_end]]) {
                    translate([sk, r[0], zh]) cube([tsk, r[1] - r[0], 4 - zh]);
                    // snap hook: flat top catches under the box wall, slope underneath pushes the skirt out
                    translate([0, r[0], 0]) rotate([90, 0, 0]) mirror([0, 0, 1])
                        linear_extrude(r[1] - r[0]) polygon([[sk + 0.01, zr], [sk - hook, zr], [sk + 0.01, zr - 1.5 * hook]]);
                }
                // pull tab under each skirt: sticks out 3 mm, sloped so it prints. Only beside the
                // legs, nothing under the tape, so the tower lifts straight off over threaded tape.
                for (r = [leg_back, [leg_front[0], front_end]])
                    translate([0, r[0], 0]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(r[1] - r[0])
                        polygon([[sk, zh], [sk + tsk + 3, zh], [sk + tsk + 3, zh + 1.2], [sk + tsk, zh + 4.2], [sk, zh + 4.2]]);
            }
            // top hook over the wall: tab clears the wall top, lip goes down the back
            translate([-8, -t - clip - 1.6, wall_top + clip]) cube([16, t + clip + 1.6 + 1, led_h - wall_top - clip]);
            translate([-8, -t - clip - 1.6, wall_top - 5]) cube([16, 1.6, led_h - wall_top + 5]);
            translate([0, tape_y, 4]) cylinder(d = 18, h = led_h - 4);
        }
        translate([0, tape_y, 3]) cylinder(d = 12, h = led_h - top - 3 + 0.5);
        led_socket(top);
    }
}
// The NeoPixel, nipple (its lens) down. The nipple goes into a hole of its own size, and the
// wider body sits in a short pocket at the top, held by friction. A small foil disc with a
// pinhole can go in first: the nipple presses it into the cone over the aperture.
// Every step down is a 45 degree cone, so it prints top down without flat bridges.
aperture = 2.5;   // bottom of the cone under the light
pinhole  = 1.5;   // the hole the light shines through, in the 0.5 mm lip under the cone. Smaller =
                  // sharper shadows but less light. Below ~0.5 mm many printers close it: poke a needle through
nipple_d = 7.7;   // NeoPixel lens ("nipple"), widest (measured)
nipple_l = 7;     // its length (measured, approx.)
body_d   = 12;    // NeoPixel body (fits the 12 mm tube, measure to be sure)
body_in  = 3;     // how deep the body sits in its pocket
module led_socket(top) {
    nb = nipple_d + 0.3;                     // printed holes come out small
    bb = body_d + clip;
    lip = led_h - top + 1.0;                 // top of the thin lip around the aperture (0.5 mm thick)
    cone = (nb - aperture) / 2;              // 45 degree cone from the nipple hole down to the aperture
    step = (bb - nb) / 2;                    // 45 degree step from the body pocket to the nipple hole
    translate([0, tape_y, led_h - body_in]) cylinder(d = bb, h = body_in + 1);              // body pocket
    translate([0, tape_y, led_h - body_in - step]) cylinder(d1 = nb, d2 = bb, h = step + 0.01);
    translate([0, tape_y, lip + cone - 0.01]) cylinder(d = nb, h = led_h - body_in - step - lip - cone + 0.02);
    translate([0, tape_y, lip]) cylinder(d1 = aperture, d2 = nb, h = cone);
    // pinhole. The step from the cone to it is under 1 mm wide, small enough to print without support
    translate([0, tape_y, led_h - top - 0.01]) cylinder(d = pinhole, h = lip - (led_h - top) + 0.02, $fn = 24);
}

// ---- camera plug ----------------------------------------------------------------
// A cap over the front of the box: side tabs hug the outside of the box walls, so nothing has
// to get past the camera rails.
plug_w = 2 * (box_out + clip + skirt);
module camera_plug_part() {
    h = z_tape - box_bot;
    board_z = board_top - board_t - box_bot;    // underside of the camera board, from the plug's bottom
    difference() {
        union() {
            cube([plug_w, t, h]);                                                // cover plate
            for (x = [0, plug_w - skirt]) translate([x, -plug_tab, 0]) cube([skirt, plug_tab, h]);  // side tabs
            translate([plug_w / 2 - 12, -1.7, board_z]) cube([24, 1.7, board_t]);    // keeps the board against the wall
        }
        // slit for the ribbon, just under the board
        translate([plug_w / 2 - 8.5, -1, board_z - 2.3]) cube([17, t + 2, 2.2]);
    }
}

// ---- take-up spool ----------------------------------------------------------------
spool_len = tape_y + tape_w / 2 + 2;
module takeup_spool_part() {  // print flange down
    difference() {
        union() {
            cylinder(d = 22, h = spool_len);
            cylinder(d = 40, h = 1.6);
        }
        translate([0, 0, spool_len - 6]) intersection() { cylinder(d = 5 + shaft_fit, h = 7); cube([3 + shaft_fit, 7, 20], center = true); }  // motor shaft
        translate([0, 0, -1]) cylinder(d = 14, h = spool_len - 8);     // hollow
        translate([4, -0.5, 3]) cube([8, 1, spool_len - 10]);         // tuck the tape end in here
    }
}

// ---- motor pin ---------------------------------------------------------------------
// Pushed from the back through a motor ear (4.2 mm hole) into the wall, where it is a tight fit.
pin_d = 4.0;
module motor_pin_part() {
    cylinder(d = 7, h = 1.6);                      // head, holds the ear
    cylinder(d = pin_d, h = 1.6 + 1 + t + 1);      // through ear (about 1 mm) and wall
    translate([0, 0, 1.6 + 1 + t + 1]) cylinder(d1 = pin_d, d2 = pin_d - 1, h = 0.8);  // lead-in
}

// ---- assembly --------------------------------------------------------------------
module assembly() {
    color("Gainsboro") frame_part();
    color("Wheat") tray_part();
    color("DimGray") translate([x_cam, 0, z_tape]) led_tower_part();
    if (use_plug) color("SteelBlue") translate([x_cam - plug_w / 2, box_in, box_bot]) camera_plug_part();
    color("Orange") translate([x_tak, spool_len, z_axle]) rotate([90, 0, 0]) takeup_spool_part();
    // dummies
    color("LightSkyBlue", 0.5) translate([x_sup, tape_y0, z_axle]) ycyl(roll_od, tape_w);
    color("DeepSkyBlue") translate([x_fan - fan_size / 2 - 6, tape_y0, z_tape]) cube([x_tak - x_fan - 10, tape_w, 0.3]);
    color("DimGray") translate([x_fan - fan_size / 2, tape_y - fan_size / 2, z_tape + fan_up]) cube([fan_size, fan_size, 7]);
    color("DarkGreen") translate([x_cam - cam_board / 2, 0, board_top - board_t]) cube([cam_board, cam_board, board_t]);
    color("Silver") translate([x_tak, -t, z_axle + motor_off]) rotate([90, 0, 0]) cylinder(d = 28, h = 19);
    color("White") translate([bb_x0 + 1.6 + press, bb_y0 + 1.6 + press, 0]) cube([bb_size[0], bb_size[1], 9]);
}

// ---- tape check --------------------------------------------------------------------
// The space the sticky side needs: 2 mm above the tape along its whole path, from the bottom of
// the roll, over the ledge and the box roof, down to the spool. Must not contain anything solid.
module tape_seg(a, b) hull() for (p = [a, b]) translate([p[0], tape_y0, p[1] + 0.05]) cube([0.01, tape_w, 2]);
module tape_space() {
    x0 = x_fan - fan_size / 2;              // where the tape reaches the ledge
    x1 = x_cam + box_out;                   // where it leaves the box roof
    tape_seg([x_sup + 8, z_axle - roll_r + 1], [x0, z_tape]);
    tape_seg([x0, z_tape], [x1, z_tape]);
    tape_seg([x1, z_tape], [x_tak - 5, z_axle - 11]);
}
module tape_check() intersection() {
    tape_space();
    union() {
        frame_part();
        translate([x_cam, 0, z_tape]) led_tower_part();
        if (use_plug) translate([x_cam - plug_w / 2, box_in, box_bot]) camera_plug_part();
    }
}

// ---- print orientations ----------------------------------------------------------------
if (part == "assembly") assembly();
else if (part == "section") intersection() { assembly(); translate([-10, tape_y, -10]) cube([L + 20, 60, 120]); }
else if (part == "frame") translate([0, 0, t]) rotate([90, 0, 0]) frame_part();          // lying on its back
else if (part == "tray") translate([0, 0, t]) tray_part();
else if (part == "led_tower") translate([0, 0, led_h]) rotate([180, 0, 0]) led_tower_part();
else if (part == "camera_plug") translate([0, 0, t]) rotate([-90, 0, 0]) camera_plug_part();  // cover plate down
else if (part == "takeup_spool") takeup_spool_part();
else if (part == "motor_pin") motor_pin_part();
else if (part == "tape_check") tape_check();
// must be EMPTY. The tower is lifted 0.01 mm so faces that only touch (back on the wall, legs on the roof) don't count
else if (part == "tower_clash") intersection() { frame_part(); translate([x_cam, 0.01, z_tape + 0.01]) led_tower_part(); }
