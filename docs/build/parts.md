# 1. Parts and tools

> [!NOTE]
> **Photo to add:** all the parts laid out on a table, before building.

## Electronics

| Part | Notes |
|---|---|
| A Raspberry Pi 3 or 4 | Anything that supports your hat and the camera probably works |
| A Raspberry Pi HQ Camera (IMX477) | Used without its lens so do not buy it with the lens |
| The Camera ribbon cable | Comes with the camera |
| One 28BYJ-48 5 V stepper motor + ULN2003 driver board | Sold together |
| A 5 V fan, 30 × 30 mm | A Pi case fan. Measure it: some are 25 mm |
| NeoPixel string (WS2811 or WS2812, 5 V) | Sold as "Christmas lights". Only one pixel is used |
| A Proto HAT for the Pi ("RPi Proto HAT w/EEP") | Must have strips like [the drawing](hat.md) |
| The 2 × 20 female header (socket) for the hat | Often comes with the HAT |
| Male pin headers (a strip you can break) | 4 + 3 + 2 +  2 |
| A IRLZ44N MOSFET |  |
| One Resistor 220 Ω (red red brown) | |
| One Resistor 100 kΩ (brown black yellow) | |
| One Resistor 330 Ω (orange orange brown) | 220 to 470 Ω also works |
| A Diode 1N5819 or 1N4148 | |
| ~30 cm thin insulated wire | 2 colours helps (red and black) |
| ~10 female jumper wires (Dupont) | To connect the driver board, if your parts don't have plugs |
| One 5.1 V 2.5 A micro USB power supply | Use a proper one. Weak supplies make the Pi crash |
| A microSD card, 32 GB or more | Pictures are big |


> [!WARNING]
> Parts list is TBD and there will be changes before this project is finished.

## Other parts

| Part | Notes |
|---|---|
| A few rolls of clear tape | The cheap "Crystal clear" type, not frosted. The roll's core must be about 26 mm inside |
| ~200 g PLA or PETG filament | PLA is fine indoors. PETG is probably better outside. The LED tower should be **black** |

## Tools

- 3D printer
- Soldering iron and solder
- Side cutters and a way to strip wires
- Electrical tape or masking tape (holds parts while you solder)
- Small screwdriver set (for the camera)
- Laptop with an SD card reader
- A ruler or calipers

## Measure before you print

The 3D model has a few sizes you should check against your own parts. They are listed in
[Print the parts](print.md#check-your-sizes-first). Have the tape roll, fan and camera at hand.
