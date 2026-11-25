# 3. Set up the Pi

**At the end of this step:** the Pi runs the pollen software, and its web page opens on your laptop.

Do this while the printer runs. You only need the Pi, the SD card, the power supply and your laptop.
**Do not put the HAT on yet.** That comes at the very end of [step 4](hat.md).

## Flash the SD card

1. Install **Raspberry Pi Imager** on your laptop (raspberrypi.com/software).
2. Choose the device (**Raspberry Pi 3**), the OS **Raspberry Pi OS Lite (64-bit)** and your SD card.
   Lite has no desktop. You don't need one: everything runs through the web page.
3. When it asks about settings, choose **Edit settings** and set:
   - **Hostname:** `pollen-01` (use a new number for each sampler)
   - **Username and password:** pick your own and write them down
   - **Wi-Fi:** your network name and password, and your country
   - **Services tab:** turn on **SSH** with password login
4. Write the card. Put it in the Pi and plug in the power. The first start takes a few minutes.

> [!NOTE]
> 📷 **Photo to add:** screenshot of the Imager settings window (hostname, Wi-Fi, SSH).

## Log in from your laptop

Open a terminal (on Windows: PowerShell) and type, with your own username:

```bash
ssh yourname@pollen-01.local
```

Type `yes` the first time, then your password. You are now typing commands on the Pi.

> [!TIP]
> No Wi-Fi where you are? Plug a network cable straight from the Pi to your laptop.
> See [Direct cable to a laptop](../direct-cable.md).

## Install the software

On the Pi, copy and paste these lines:

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/DeeKahy/Pollen-Detector.git
cd Pollen-Detector/device
./install.sh
```

This takes 5-15 minutes. It installs what the software needs, turns on SPI (for the light),
makes a settings file `config.yaml` and sets up the `pollen` service, which starts by itself at boot.

## Set it up for the NeoPixel light

Open the settings file:

```bash
nano config.yaml
```

Find the `led:` part and set `type: neopixel`:

```yaml
led:
  type: neopixel
```

Save with **Ctrl+O**, **Enter**, and close with **Ctrl+X**. Then reboot, so SPI and the new settings are used:

```bash
sudo reboot
```

## Check that it works

Wait a minute, then open **http://pollen-01.local:8080** in a browser on your laptop.

> [!NOTE]
> 📷 **Screenshot to add:** the web page right after install (Claude can make this from mock mode).

You will see the web page. Nothing is connected yet, so the camera and motor checks fail. That is fine for now.

- [ ] The web page opens.
- [ ] Under **Hardware checks**, **Run checks** shows no power warning. (A power warning means the power supply is too weak.)

Now **shut the Pi down** before you go on, and unplug it:

```bash
sudo poweroff
```

## Updating the software later

```bash
cd ~/Pollen-Detector && git pull
sudo systemctl restart pollen
```
