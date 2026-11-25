# Troubleshooting

## Pi and software

| Problem | Try this |
|---|---|
| `pollen-01.local` not found | Wait 2 minutes after power on. Check the Pi is on the same Wi-Fi. On a cable see [Direct cable](../direct-cable.md) |
| Web page does not open | `ssh` in and run `journalctl -u pollen -n 50` to see the error |
| Pi crashes or restarts at random | Weak power supply. **Run checks** shows a power warning. Use a proper 5.1 V 2.5 A supply |
| Settings changes do nothing | Restart after editing `config.yaml`: `sudo systemctl restart pollen` |
| `hwtest` says a pin is busy | Stop the service first: `sudo systemctl stop pollen` |

## HAT and wiring

| Problem | Look at |
|---|---|
| Nothing works, the Pi gets hot | A short between +5V and GND. **Unplug at once.** Do the [beep test](hat.md#beep-test-before-power) again |
| Fan never turns off | Q1 turned the wrong way, or R2 missing |
| Fan never turns on | W1 in the wrong hole (`#4` instead of `#17`), R1 and R2 swapped, or the fan plug turned around |
| Pi resets when the fan starts | D1 the wrong way round, or a weak power supply |
| Motor only buzzes | IN1-IN4 in the wrong order on the driver board |
| Coil test: LEDs light in the wrong order | IN wires swapped. They must go IN1 to IN4 in the same order as J4 |
| Light does not turn on | NeoPixel plugged in at the wrong end (use the input end). `led: type: neopixel` in `config.yaml`. SPI on: `ls /dev/spidev0.0` must show a file |
| Light shows wrong colours | Set `order: GRB` under `led:` in `config.yaml` |
| Light flickers or shows random colours | The 3.3 V data signal is too weak for the pixel. Put a diode (1N4001) in the string's +5V wire. See [Old breadboard wiring](../wiring.md#neopixel-string-instead-of-the-rgb-led) |
| HAT does not go on the Pi | The socket is one row or one pin off. Take it off and line it up again (see [the drawing](hat.md#put-the-hat-on-the-pi)) |

## Camera and pictures

| Problem | Try this |
|---|---|
| Camera not found | Ribbon not fully in, or the wrong way round, at either end. Power off, reseat both ends. Then **Retry camera** |
| Dark spots in the same place in every picture | Dust on the sensor. Blow it off |
| Everything blurred | The tape must lie flat on the camera box roof. Run **🎯 Auto setup**. Try a smaller pinhole (foil) |
| Faint stripes in the picture | Exposure not in whole milliseconds while the light is dimmed. Auto setup avoids this |

## Mechanics

| Problem | Try this |
|---|---|
| A part is too tight or too loose | Change the fit settings and print it again. See [Print the parts](print.md#if-a-fit-is-too-tight-or-too-loose) |
| Spool slips on the motor shaft | Lower `shaft_fit` and print the spool again |
| Tape sticks to something | Something touches the sticky side. Check the tape path and that the tower's legs are beside the tape, not over it |
| Tape winds the wrong way | Set `invert_direction: true` under `stepper:` in `config.yaml` |
