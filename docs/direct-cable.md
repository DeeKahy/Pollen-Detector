# Connect to the Pi with a cable (no network)

Use this when the Pi cannot join a Wi-Fi or LAN, for example at school or out in the field.
Plug an ethernet cable straight from the Pi into your laptop. A USB ethernet adapter is fine.
No router and no internet are needed.

The examples use the hostname `pollen-01`. Use your own Pi's hostname.

## 0. Set up the Pi once (do this while it still has a network)

On a bare cable nobody answers the Pi's DHCP request. By default NetworkManager gives up
after 45 seconds, resets the port and tries again. After 4 tries (about 3 minutes after
boot) it shuts the port down for 5 minutes. The Pi keeps running, but you cannot reach it.
It looks like a power problem, but it is not.

Fix it once, on the Pi:

```bash
sudo nmcli con mod "Wired connection 1" ipv4.dhcp-timeout infinity ipv4.link-local fallback
sudo nmcli -w 0 con up "Wired connection 1"
```

Now the Pi waits for DHCP forever and uses a `169.254.x.x` address meanwhile. At home with a
router it still gets a normal address. Check the name of the connection with `nmcli con show`
if yours is different.

## 1. SSH into the Pi

With no router, the Pi and the laptop give themselves link-local addresses (`169.254.x.x`
and IPv6 `fe80::`). The Pi announces its name, so this works:

```bash
ssh pi@pollen-01.local
```

If you see `Host key verification failed`, your laptop knows the Pi's key under its old IP
address. Tell SSH to use that saved key (replace the IP with the one you used before):

```bash
ssh -o HostKeyAlias=192.168.8.150 pi@pollen-01.local
```

If the name is not found, check the cable and wait a minute after boot. On a Mac you can
list devices on the cable with `ping6 -c 2 ff02::1%en10` (find the adapter name, here
`en10`, with `ifconfig`). The Pi's MAC address starts with `b8:27:eb`, `dc:a6:32`, `e4:5f:01`
or `2c:cf:67`.

## 2. Open the web UI

With the setup from step 0, just open http://pollen-01.local:8080. The first load can take
a few seconds while the laptop looks up the name.

Without step 0 the Pi has no IPv4 address, and the web UI only listens on IPv4. Then use an
SSH tunnel instead:

```bash
ssh -f -N -L 8080:localhost:8080 pi@pollen-01.local
```

Then open http://localhost:8080 in your browser. Add the `HostKeyAlias` flag from step 1 if
you needed it there. The tunnel stops when the Pi reboots, you unplug the cable or you restart the laptop. Run
the command again to get it back.

## 3. Share your laptop's internet with the Pi (optional)

The Pi needs internet to install packages or upload images. Your laptop can share its own
connection over the cable. The laptop must be online itself.

### macOS

1. Open **System Settings → General → Sharing**.
2. Click **ⓘ** next to **Internet Sharing**.
3. Set "Share your connection from" to **Wi-Fi** (or whatever gives your Mac internet).
4. Under "To devices using", turn on your **USB ethernet adapter**
   (often called "USB 10/100/1000 LAN" or similar).
5. Click **Done** and turn **Internet Sharing** on.

The Mac now gives the Pi an IPv4 address, usually `192.168.2.x`. Unplug and replug the
cable if the Pi does not pick it up. A VPN on the Mac (for example Proton VPN) can block
sharing. Turn it off if the Pi gets no internet.

### Linux (NetworkManager)

In the wired connection settings for the cable, set IPv4 method to **Shared to other
computers**. Or run:

```bash
nmcli connection modify "Wired connection 1" ipv4.method shared
```

### Windows

Open the adapter settings, right-click your Wi-Fi adapter, choose **Properties → Sharing**
and allow other users to connect through it, using the ethernet adapter.

### Check it

```bash
ssh pi@pollen-01.local 'ip -4 addr show eth0; ping -c 2 1.1.1.1'
```

When sharing is on, the Pi has an IPv4 address, so `http://pollen-01.local:8080` opens
directly and you no longer need the tunnel.
