# Wiring (Raspberry Pi 3 B+)

![wiring diagram](wiring.svg)

`wiring.svg` is made by `make_wiring_svg.py`. If you change a pin, change it there and run the script again.

## Which wire goes where

| Pi pin | Name | Goes to |
|---|---|---|
| 2 | 5V | driver board `+` |
| 4 | 5V | fan red wire |
| 6 | GND | driver board `−` |
| 11 | GPIO17 | driver board IN1 |
| 13 | GPIO27 | driver board IN2 |
| 15 | GPIO22 | driver board IN3 |
| 16 | GPIO23 | driver board IN4 |
| 12 | GPIO18 | fan MOSFET, through a 220 Ω resistor |
| 14 | GND | fan MOSFET |
| 17 | 3.3V | RGB LED long leg (shared +) |
| 18 | GPIO24 | RGB LED red leg, through a 220 Ω resistor |
| 22 | GPIO25 | RGB LED green leg, through a 100 Ω resistor |
| 29 | GPIO5 | RGB LED blue leg, through a 47 Ω resistor |
| CAMERA port | | HQ camera ribbon, blue side facing the USB ports |
| 1, 3, 5, 9 | | BME280 sensor (optional) |

The numbers in `device/config.yaml` are GPIO numbers (17, 27, ...), not pin numbers.

## The motor

The motor plugs into the driver board. The driver board gets 5V, GND and four wires from the Pi.
If the motor only buzzes and doesn't turn, the four IN wires are in the wrong order.

## The fan

The fan needs more current than a GPIO pin can give, so a MOSFET switches it.

- Fan red wire to 5V (pin 4). Fan black wire to the MOSFET's D leg.
- MOSFET S leg to GND (pin 14).
- GPIO18 (pin 12) to a 220 Ω resistor, then to the MOSFET's G leg.
- A 100 kΩ resistor from the G leg to GND. This keeps the fan off while the Pi starts.
- A diode across the fan, with the stripe on the 5V side. This protects the MOSFET.

## The LED

The LED is a 5 mm RGB LED with 4 legs, **common anode**: the long leg is the shared + side.
It goes straight on three GPIO pins, no MOSFET.

Legs, with the long leg second from the left:

| Leg | Colour | Goes to | Resistor |
|---|---|---|---|
| single leg next to the long leg | red | GPIO24 (pin 18) | 220 Ω |
| long leg | shared + | 3.3V (pin 17) | none |
| next to the long leg, other side | green | GPIO25 (pin 22) | 100 Ω |
| furthest out | blue | GPIO5 (pin 29) | 47 Ω |

Because the long leg is on 3.3V, the pins work the other way round: **pin low = colour on,
pin high = colour off**. The GPIO pin acts as the ground for that colour. The software knows
this (`led_active_low: true` in `config.yaml`).

The software can dim each colour (PWM: the pin flicks on and off 1000 times a second). This
does not harm the LED; each pulse has the same current as fully on. Green looks much brighter
to the eye than red, so a plain 100/100/100 "white" looks greenish. Use the calibration in the
web UI (LED colour card) to make white come out white for the camera. Below 100 % use an exposure in
whole milliseconds, or the camera can show faint stripes.

Measured with a multimeter (diode test): red 1.72 V, green 2.28 V, blue 2.48 V. With the
resistors above each colour draws roughly 6 to 9 mA, well under what one pin can give.
Blue is on 47 Ω because with 100 Ω it was barely visible. A blue LED needs about 3 V at
real current, so from 3.3 V only a little is left for the resistor and the LED limits its own
current. Check it once: volts across the 47 Ω ÷ 47 = current. Keep it under about 12 mA
(0.56 V). Do not use 47 Ω on red, it would draw far too much.

While the Pi boots, the LED can glow faintly (green and a bit of red). That is the pins'
built-in pull resistors, before the software sets them. It is harmless.

The LED sits about 30 cm above the tape in the current tests. Further away, or a pinhole
under it (foil poked with a needle), makes the lensless pictures sharper.

Resistor colour codes are in [resistors.svg](resistors.svg).

## What to buy

| Part | How many | Notes |
|---|---|---|
| ULN2003 driver board | 1 | usually comes with the motor |
| Logic-level MOSFET | 1 | IRLZ44N or AO3400. Not the blue IRF520 boards, they don't work at 3.3 V |
| 220 Ω resistor | 1 | fan MOSFET |
| 100 kΩ resistor | 1 | fan MOSFET |
| 1N5819 or 1N4148 diode | 1 | across the fan |
| 5 mm RGB LED, common anode | 1 | plus 220 Ω (red), 100 Ω (green) and 47 Ω (blue) |
| 5.1 V 2.5 A micro USB power supply | 1 | a weak supply makes the Pi crash at random |
| Breadboard and jumper wires | | |
| microSD card, 32 GB or more | 1 | the pictures are big |
| BME280 sensor (optional) | 1 | logs temperature and humidity |

## Before you power on

1. Wire it all with the Pi unplugged.
2. Check that no 5V wire goes to a GPIO pin. 5V on a GPIO pin kills it.
3. Connect all GND wires together.
4. Power on and run `python3 -m pollen_device.hwtest`. It tests the LED, fan, motor and camera one at a time.
   It lights the LED red, green, blue and then white. If a colour is wrong, two wires are swapped.
