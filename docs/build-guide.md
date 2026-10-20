# Build guide

How to build a pollen detector from scratch. This is a prototype, so expect to adjust
things along the way. Write down what you change and add it to `iterations/`.

## 1. Get the parts

See [hardware/bom.md](../hardware/bom.md). You need a Raspberry Pi, the HQ camera, a small
stepper motor with driver board, a 5 V fan, a few resistors, one MOSFET, a diode, an LED,
clear tape and a 3D printer.

## 2. Print the parts

The 3D files are in [hardware/](../hardware/). Print in PETG if it will go outside
(PLA goes soft in the sun). Design ideas and tips are in [mechanical-ideas.md](mechanical-ideas.md).

## 3. Prepare the camera

The camera is used without a lens.

1. Unscrew the lens mount from the HQ camera board.
2. Take out the IR filter if you want more light (optional).
3. Keep the sensor covered whenever you're not using it. Dust on the sensor shows up in every picture.

## 4. Wire the electronics

Follow [wiring.md](wiring.md) and the diagram [wiring.svg](wiring.svg).
Resistor colours are in [resistors.svg](resistors.svg).
Wire everything with the Pi unplugged.

## 5. Install the software

1. Flash Raspberry Pi OS (Bookworm or newer) with Raspberry Pi Imager. In the settings,
   set a hostname (for example `pollen-01`), your Wi-Fi and turn on SSH.
2. Copy the `device/` folder to the Pi and run `./install.sh`.
3. Test each part: `python3 -m pollen_device.hwtest`.
4. Start it: `sudo systemctl start pollen`.
5. Open `http://pollen-01.local:8080` in a browser. Press **Run checks** to check the
   camera and wiring.

Details in [device/README.md](../device/README.md).

## 6. Load the tape

1. Put the tape roll on the supply side, sticky side up.
2. Lead it past the fan, over the camera and onto the take-up roll.
3. It should be tight and flat over the camera.

## 7. Calibrate

1. In the web page, move the tape 4096 steps and measure how many mm it moved.
2. Measure the distance from the middle of the fan to the middle of the camera.
3. Set `pitch_steps` and `camera_offset_cycles` in `config.yaml`.
   See "Calibrating pitch and offset" in [device/README.md](../device/README.md).
4. Put a pen dot on the tape under the fan and check that it ends up in the middle of the camera picture.

## 8. Test with real pollen

Before running it outside, put some known pollen on the tape (shake a flowering plant or
catkin over it) and check that you can see the grains in the pictures. Adjust the
exposure in the web page until they're clear.

## 9. Run it

Press **Resume schedule** in the web page. The device now samples every 30 minutes
(change it in `config.yaml`).

## 10. Share what you learned

Make a folder in `iterations/` with photos of your build, example pictures from the
camera and notes on what worked and what didn't. See [iterations/README.md](../iterations/README.md).
