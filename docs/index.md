# Build a pollen sampler

This guide shows how to build one pollen sampler: a small machine that blows outdoor air onto
sticky tape, moves the tape over a camera and takes pictures of what got caught.

![The finished sampler (3D model)](build/img/assembled.png)

> [!NOTE]
> 📷 **Photo to add:** the real finished sampler, from the front, on a plain table.

> [!WARNING]
> This is a prototype. Parts of it will change, and some steps have only been done once or twice.
> If something does not match your parts, write down what you changed and tell us
> (see [Run it](build/run.md#share-what-you-learned)).

## What you need

- About **€135-150** of parts. See [Parts and tools](build/parts.md).
- A **3D printer**, or someone who can print about 200 g of PLA or PETG for you.
- A **soldering iron**, and some practice soldering through-hole parts.
- A **laptop** on the same network as the Pi (Wi-Fi or a cable).
- Time: about one day of work, plus the printing time.

You do not need to know Python or Linux. You will type a few commands that are written out for you.

## The build at a glance

![The order of the build](build/img/stages.svg)

Start the printer first. The prints take several hours. While it prints, set up the Pi
and build the HAT.

| Step | What you do | Result |
|---|---|---|
| [1. Parts and tools](build/parts.md) | Get everything on the list | All parts on the table |
| [2. Print the parts](build/print.md) | Print 6 plastic parts | Frame, tray, LED tower, spool, 2 pins |
| [3. Set up the Pi](build/pi-setup.md) | Put the software on an SD card and the Pi | The web page opens on your laptop |
| [4. Build the HAT](build/hat.md) | Solder the board that sits on top of the Pi | A HAT that passes the beep test |
| [5. Prepare the camera](build/camera.md) | Take the lens mount off the camera | A bare, clean camera sensor |
| [6. Put it together](build/assembly.md) | Fit parts, plug in cables, thread the tape | A finished sampler |
| [7. Test and calibrate](build/first-run.md) | Check every part and measure the tape | Sharp pictures, correct settings |
| [8. Run it](build/run.md) | Start the schedule | Pictures every 30 minutes |

Stuck? See [Troubleshooting](build/troubleshooting.md).

## How it works

![How the tape runs](build/img/tape-path.svg)

1. The **fan** blows air down onto the sticky side of the tape. Pollen sticks to it.
2. The **motor** pulls the tape along, so that piece of tape moves over the **camera**.
3. A **light** above the tape shines through it. The camera has no lens: the tape lies right on
   the sensor, and the pollen casts tiny shadows on it.
4. The Pi saves the picture and, if you want, uploads it.

Every part is printed and pressed or clipped together. No glue and no screws.

All files are public domain (CC0). Build it, change it, share it.
