// Pictures for the build guide: one per assembly step. Public domain (CC0), see hardware/LICENSE.
// Parts already fitted are grey, the part you add in this step is orange and pulled out a little
// along the way it goes on. Run make_guide_renders.sh to make all the PNGs.
//
//   openscad -D step=3 -o step3.png assembly_steps.scad
//
// Uses tape_deck.scad for every size, so the pictures follow the design.

include <tape_deck.scad>
part = "none";   // stop tape_deck.scad drawing its own part
step = 1;

done = "Gainsboro";
new  = "DarkOrange";
function c(k) = k == step ? new : done;
function off(k, v) = k == step ? v : [0, 0, 0];

module motor_dummy() {
    translate([x_tak, -t, z_axle + motor_off]) rotate([90, 0, 0]) cylinder(d = 28, h = 19);
    translate([x_tak - motor_ear / 2 - 3.5, -t - 1, z_axle + motor_off - 3.5]) cube([motor_ear + 7, 1, 7]);
    translate([x_tak, -t, z_axle]) rotate([90, 0, 0]) cylinder(d = 9, h = 0.1);
    translate([x_tak, 0.5, z_axle]) rotate([-90, 0, 0]) cylinder(d = 5, h = 8);   // shaft through the wall
}
module motor_pins() for (dx = [-1, 1])
    translate([x_tak + dx * motor_ear / 2, -t - 1 - 1.6, z_axle + motor_off]) rotate([-90, 0, 0]) motor_pin_part();

module fan_dummy() difference() {
    translate([x_fan - fan_size / 2, tape_y - fan_size / 2, z_tape + fan_up]) cube([fan_size, fan_size, 7]);
    translate([x_fan, tape_y, z_tape + fan_up - 1]) cylinder(d = fan_size - 4, h = 9);
}
module camera_dummy() {
    translate([x_cam - cam_board / 2, 0, board_top - board_t]) cube([cam_board, cam_board, board_t]);
    translate([x_cam - 4, tape_y - 4, board_top]) cube([8, 8, sensor_h]);           // sensor
    translate([x_cam - 9, -12, board_top - board_t - 1]) cube([18, 12, 0.3]);       // ribbon out the back
}
module roll_dummy() translate([x_sup, tape_y0, z_axle]) difference() { ycyl(roll_od, tape_w); translate([0, -1, 0]) ycyl(peg_d + 1, tape_w + 2); }
module tape_path() {
    x0 = x_fan - fan_size / 2 - 6;
    x1 = x_cam + box_out + 2;
    for (s = [[[x_sup + 10, z_axle - roll_r + 1], [x0, z_tape]],
              [[x0, z_tape], [x1, z_tape]],
              [[x1, z_tape], [x_tak - 8, z_axle - 10]]])
        hull() for (p = s) translate([p[0], tape_y0, p[1]]) cube([0.01, tape_w, 0.4]);
}
module pixel_dummy() translate([x_cam, tape_y, z_tape + led_h]) { cylinder(d = 12, h = 6); translate([0, 0, 6]) cylinder(d = 4, h = 40); }

// step 1: frame into the tray groove
color(done) tray_part();
color(c(1)) translate(off(1, [0, 0, 35])) frame_part();
// step 2: motor on the back with two pins
if (step >= 2) {
    color(c(2)) translate(off(2, [0, -25, 0])) motor_dummy();
    color(c(2)) translate(off(2, [0, -45, 0])) motor_pins();
}
// step 3: take-up spool on the shaft
if (step >= 3) color(c(3)) translate(off(3, [0, 30, 0])) translate([x_tak, spool_len, z_axle]) rotate([90, 0, 0]) takeup_spool_part();
// step 4: fan into the rim on the shelf
if (step >= 4) color(c(4)) translate(off(4, [0, 0, 30])) fan_dummy();
// step 5: camera slides into the box from the front
if (step >= 5) color(c(5)) translate(off(5, [0, 55, 0])) camera_dummy();
// step 6: tape roll on the peg, tape threaded to the spool
if (step >= 6) {
    color(c(6)) translate(off(6, [0, 35, 0])) roll_dummy();
    color(step == 6 ? "DeepSkyBlue" : "LightSkyBlue") tape_path();
}
// step 7: LED tower with the NeoPixel snaps onto the camera box
if (step >= 7) color(c(7)) translate(off(7, [0, 0, 35])) {
    translate([x_cam, 0, z_tape]) led_tower_part();
    pixel_dummy();
}
// step 8: the Pi with its HAT drops onto the 4 pins behind the wall (ribbon already through the slot)
if (step >= 8) translate(off(8, [0, 0, 30])) pi_dummy(step == 8 ? new : undef);
