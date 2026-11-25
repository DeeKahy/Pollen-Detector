"""Makes the 2D diagrams for the build guide (run: python3 make_build_svgs.py).

Writes img/connections.svg, img/hat-on-pi.svg, img/tape-path.svg and img/stages.svg.
Same look as ../hat.svg: light and dark mode from the viewer's settings.
Pin orders come from ../hat.md. If the HAT changes, change both.
"""
from pathlib import Path

OUT = Path(__file__).parent / "img"
STYLE = """<style>
svg{--bg:#f7f8f5;--card:#ffffff;--ink:#1d211b;--mut:#646b60;--line:#c9cfc2;--pcb:#1f6f43;--hat:#1d2024}
@media (prefers-color-scheme:dark){svg{--bg:#141713;--card:#1d211b;--ink:#e6eae2;--mut:#9aa293;--line:#3a4137;--pcb:#2b7a4e;--hat:#2a2e33}}
text{font-family:system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif}
</style>"""
RED, BLACK, PURPLE, BLUE, ORANGE = "#d62728", "#6b6b6b", "#9b59d0", "#1f8fd6", "#e8770e"
MOTOR = ["#ff7f0e", "#e3b400", "#2ca02c", "#1f77b4"]


class Svg:
    def __init__(self, w, h, title, sub=""):
        self.w, self.h, self.o = w, h, []
        self.a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">')
        self.a(STYLE)
        self.a(f'<rect width="{w}" height="{h}" fill="var(--bg)"/>')
        self.text(30, 40, title, 22, weight="800")
        if sub:
            self.text(30, 64, sub, 14, fill="var(--mut)")

    def a(self, s): self.o.append(s)

    def text(self, x, y, s, size=13, anchor="start", weight="normal", fill="var(--ink)"):
        s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.a(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{s}</text>')

    def rect(self, x, y, w, h, fill="var(--card)", stroke="var(--line)", rx=6, sw=1.5, extra=""):
        self.a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')

    def line(self, pts, color, w=4, dash=None):
        d = " ".join(f"{x},{y}" for x, y in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.a(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{da}/>')

    def circle(self, x, y, r, fill, stroke="none", sw=0):
        self.a(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def pill(self, x, y, s, color, w=None, anchor="start"):
        w = w or 12 + 7.6 * len(s)
        x0 = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
        self.rect(x0, y - 11, w, 22, fill=color, stroke="none", rx=11)
        self.text(x0 + w / 2, y + 4.5, s, 12, "middle", "700", "#fff")

    def badge(self, x, y, n):
        self.circle(x, y, 13, ORANGE)
        self.text(x, y + 5, n, 14, "middle", "800", "#fff")

    def arrow(self, x0, y0, x1, y1, color="var(--ink)", w=2.5):
        self.line([(x0, y0), (x1, y1)], color, w)
        import math
        ang = math.atan2(y1 - y0, x1 - x0)
        p = [(x1, y1), (x1 - 12 * math.cos(ang - 0.45), y1 - 12 * math.sin(ang - 0.45)),
             (x1 - 12 * math.cos(ang + 0.45), y1 - 12 * math.sin(ang + 0.45))]
        self.a(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in p)}" fill="{color}"/>')

    def save(self, name):
        self.a("</svg>")
        (OUT / name).write_text("\n".join(self.o) + "\n")


def header_pins(s, x, y, labels, colors, side="right"):
    """A vertical male header on the HAT: one square pin per label, label beside it."""
    for i, (lab, col) in enumerate(zip(labels, colors)):
        py = y + i * 26
        s.rect(x - 9, py - 9, 18, 18, fill="#111", stroke="#888", rx=2, sw=1)
        s.rect(x - 4, py - 4, 8, 8, fill="#d9c27a", stroke="none", rx=1)
        if side == "right":
            s.pill(x + 16, py, lab, col, anchor="start")
        else:
            s.pill(x - 16, py, lab, col, anchor="end")


# ---------------------------------------------------------------- connections
def pin(s, x, y):
    s.rect(x - 9, y - 9, 18, 18, fill="#111", stroke="#888", rx=2, sw=1)
    s.rect(x - 4, y - 4, 8, 8, fill="#d9c27a", stroke="none", rx=1)


def connections():
    s = Svg(1200, 800, "What plugs into the HAT",
            "The HAT sits on the Pi. Everything else plugs onto its pin headers. Plug in with the power off.")
    W = "#f1f1ee"
    hx, hy, hw, hh = 440, 110, 360, 470
    s.rect(hx, hy, hw, hh, fill="var(--hat)", stroke="#000", rx=16, sw=2)
    s.text(hx + hw / 2, hy + 30, "Proto HAT, top view", 15, "middle", "700", W)
    s.text(hx + hw / 2, hy + 50, "(40-pin header to the Pi along this edge)", 12, "middle", fill="#b9bdb4")
    s.text(hx + 20, hy + hh - 14, "+5V and GND rails along this edge", 12, "start", fill="#b9bdb4")

    # J4: motor IN1-IN4, near the top
    j4x, j4y = hx + 120, hy + 92
    s.text(j4x + 39, j4y - 18, "J4  motor IN1 IN2 IN3 IN4", 13, "middle", "800", W)
    xs = [j4x + i * 26 for i in range(4)]
    for x in xs:
        pin(s, x, j4y)

    # ULN2003 driver (top left). IN pins on its right edge, + and - on its bottom edge
    dx, dy = 50, 110
    s.rect(dx, dy, 210, 220, fill="var(--pcb)", stroke="#0d3a22", rx=8)
    s.text(dx + 105, dy + 26, "ULN2003 driver", 14, "middle", "700", "#fff")
    for i in range(4):
        y = dy + 60 + i * 26
        s.text(dx + 192, y + 4, f"IN{i + 1}", 12, "end", "700", "#fff")
        s.circle(dx + 210, y, 5, "#d9c27a")
        h = j4y + 34 + i * 14          # nested L routes: no crossings
        v = dx + 330 - i * 14
        s.line([(xs[i], j4y + 9), (xs[i], h), (v, h), (v, y), (dx + 215, y)], MOTOR[i], 4)
    pwr = [("+", RED, dx + 175), ("−", BLACK, dx + 140)]   # + right, so the two wires do not cross
    for lab, col, x in pwr:
        s.circle(x, dy + 220, 5, "#d9c27a")
        s.text(x, dy + 206, lab, 14, "middle", "800", "#fff")
    # motor (left of the driver bottom)
    s.circle(dx + 55, dy + 300, 40, "#b9c0c7", "#7d858c", 2)
    s.circle(dx + 55, dy + 284, 6, "#e9ecef")
    s.line([(dx + 55, dy + 260), (dx + 55, dy + 220)], "#2b6cb0", 6)
    s.text(dx + 55, dy + 360, "28BYJ-48 motor", 13, "middle", "700")
    s.text(dx + 55, dy + 377, "plug only fits one way", 12, "middle", fill="var(--mut)")

    # bottom headers: J3 (motor power), J1 (fan), J2 (light). Pins stack downwards.
    by = hy + hh - 110
    j3x, j1x, j2x = hx + 60, hx + 170, hx + 290
    for x, name in ((j3x, "J3"), (j1x, "J1"), (j2x, "J2")):
        s.text(x, by - 20, name, 14, "middle", "800", W)
    j3 = [("+", RED), ("−", BLACK)]
    j1 = [("−", BLACK), ("+", RED)]
    j2 = [("DIN", BLUE), ("5V", RED), ("GND", BLACK)]
    for k, (lab, _) in enumerate(j3):
        pin(s, j3x, by + k * 26); s.text(j3x + 16, by + k * 26 + 5, lab, 14, "start", "800", W)
    for k, (lab, _) in enumerate(j1):
        pin(s, j1x, by + k * 26); s.text(j1x + 16, by + k * 26 + 5, lab, 14, "start", "800", W)
    for k, (lab, _) in enumerate(j2):
        pin(s, j2x, by + k * 26); s.text(j2x - 16, by + k * 26 + 5, lab, 13, "end", "800", W)
    s.text(j3x, by + 72, "motor power", 11, "middle", fill="#b9bdb4")
    s.text(j1x, by + 72, "fan", 11, "middle", fill="#b9bdb4")
    s.text(j2x - 30, by + 98, "light", 11, "middle", fill="#b9bdb4")

    # driver power -> J3 (down the left, then in from the left)
    for k, (lab, col, x) in enumerate(pwr):
        s.line([(x, dy + 225), (x, by + k * 26), (j3x - 9, by + k * 26)], col, 4)

    # fan (below left) -> J1, coming up between J3 and J1
    fx, fy = 200, 690
    s.rect(fx - 48, fy - 48, 96, 96, fill="var(--card)", stroke="var(--ink)", rx=10, sw=2)
    s.circle(fx, fy, 36, "none", "var(--ink)", 2)
    s.circle(fx, fy, 9, "var(--ink)")
    s.text(fx - 64, fy - 6, "5 V fan", 13, "end", "700")
    s.text(fx - 64, fy + 12, "red +, black −", 12, "end", fill="var(--mut)")
    for k, (lab, col) in enumerate(j1):
        xin = j1x - 40 + k * 12
        s.line([(fx + 48, fy - 12 + k * 20), (xin, fy - 12 + k * 20), (xin, by + k * 26), (j1x - 9, by + k * 26)], col, 4)

    # NeoPixel string (right) -> J2 from the right
    nx, ny = 920, by + 26
    for k, (lab, col) in enumerate(j2):
        xv = 860 + k * 14
        s.line([(j2x + 9, by + k * 26), (xv, by + k * 26), (xv, ny + 60 + k * 14 - 60 + 0), (nx, ny + k * 14)], col, 4)
    for i in range(4):
        x = nx + 30 + i * 58
        s.line([(x - 30 if i else nx, ny + 14), (x, ny + 14)], "var(--mut)", 3)
        s.circle(x + 12, ny + 14, 14, "#f6e7a8" if i == 0 else "var(--card)", "var(--ink)", 2)
    s.text(nx + 42, ny + 48, "pixel 0", 12, "middle", "700")
    s.text(nx + 110, ny - 34, "NeoPixel string, INPUT end", 13, "middle", "700")
    s.text(nx + 110, ny + 72, "arrows on the pixels point away", 12, "middle", fill="var(--mut)")
    s.text(nx + 110, ny + 88, "from this end. Wire colours vary:", 12, "middle", fill="var(--mut)")
    s.text(nx + 110, ny + 104, "read the labels on the first pixel.", 12, "middle", fill="var(--mut)")

    # camera + ribbon into the slot
    sx, sy = hx + hw - 40, hy + 150
    s.rect(sx - 7, sy, 14, 130, fill="var(--bg)", stroke="#000", rx=7)
    s.text(sx - 14, sy + 70, "slot", 12, "end", fill="#b9bdb4")
    cx, cy = 960, 110
    s.rect(cx, cy, 150, 150, fill="var(--pcb)", stroke="#0d3a22", rx=8)
    s.rect(cx + 63, cy + 63, 24, 24, fill="#222", stroke="#555", rx=2)
    s.text(cx + 75, cy + 176, "HQ camera", 13, "middle", "700")
    s.a(f'<path d="M{cx} {cy + 120} C {cx - 70} {cy + 120}, {sx} {sy - 60}, {sx} {sy + 30}" '
        f'fill="none" stroke="#e8dcb5" stroke-width="14" stroke-linecap="round"/>')
    s.text(cx + 75, cy + 194, "ribbon goes down through the", 12, "middle", fill="var(--mut)")
    s.text(cx + 75, cy + 210, "slot to the Pi's CAMERA port", 12, "middle", fill="var(--mut)")

    s.text(30, 785, "Pin order as seen with the 40-pin header at the top. A 2-pin plug turned around swaps + and −: "
                    "check red goes to +.", 13, fill="var(--mut)")
    s.save("connections.svg")


# ---------------------------------------------------------------- HAT on the Pi
def hat_on_pi():
    s = Svg(1200, 600, "Putting the HAT on the Pi",
            "Side view, not to scale. Power off. Do the camera ribbon first: the HAT covers the camera port.")
    # Pi board
    px, py, pw = 140, 430, 620
    s.rect(px, py, pw, 16, fill="var(--pcb)", stroke="#0d3a22", rx=3)
    s.text(px + pw / 2, py + 46, "Raspberry Pi 3 B+", 15, "middle", "700")
    s.rect(px + pw - 120, py - 70, 120, 70, fill="#c9cdd1", stroke="#888", rx=3)   # USB/ethernet block
    s.text(px + pw - 60, py - 30, "USB / LAN", 12, "middle", "700", "#333")
    # Pi header pins
    hx0 = px + 40
    for i in range(20):
        x = hx0 + i * 14
        s.rect(x - 3, py - 34, 6, 34, fill="#d9c27a", stroke="none", rx=1)
    s.rect(hx0 - 8, py - 10, 20 * 14 + 2, 10, fill="#111", stroke="none", rx=1)
    s.text(hx0 + 140, py + 70, "40-pin header (2 rows of 20)", 12, "middle", fill="var(--mut)")
    # camera port on the Pi
    cpx = px + 380
    s.rect(cpx, py - 22, 36, 22, fill="#ddd", stroke="#777", rx=2)
    s.text(cpx + 18, py + 70, "CAMERA port", 12, "middle", fill="var(--mut)")

    # HAT, lifted
    hy = 230
    s.rect(px, hy, 480, 14, fill="var(--hat)", stroke="#000", rx=3)
    s.text(px + 240, hy - 52, "Proto HAT", 15, "middle", "700")
    s.rect(hx0 - 8, hy + 14, 20 * 14 + 2, 44, fill="#111", stroke="none", rx=2)    # socket underneath
    s.text(hx0 + 140, hy + 42, "socket (underneath)", 12, "middle", "700", "#ddd")
    # slot in the HAT
    s.rect(cpx + 6, hy - 1, 24, 16, fill="var(--bg)", stroke="none")
    # ribbon: from camera port up through the slot to the camera
    s.a(f'<path d="M{cpx + 18} {py - 22} L {cpx + 18} {hy - 20} C {cpx + 18} {hy - 90}, {cpx + 150} {hy - 120}, 900 {hy - 120}" '
        f'fill="none" stroke="#e8dcb5" stroke-width="10"/>')
    s.text(910, hy - 115, "to the camera", 13, "start", "700")
    # arrow down
    s.arrow(hx0 + 140, hy + 70, hx0 + 140, py - 46, ORANGE, 4)
    # steps
    steps = [
        (cpx + 18, py - 50, "1", "Ribbon into the Pi's CAMERA port, blue side towards the USB ports. Close the latch."),
        (cpx + 18, hy - 20, "2", "Thread the ribbon up through the slot in the HAT."),
        (hx0 + 140, hy + 120, "3", "Line the socket up over ALL 40 pins, both rows, no pins left over at either end."),
        (px + 500, hy + 7, "4", "Press straight down, evenly, until the socket is fully on. The HAT lies over the Pi; the USB end sticks out."),
    ]
    for i, (x, y, n, t) in enumerate(steps):
        s.badge(x - 24 if n != "4" else x + 20, y, n)
    for i, (_, _, n, t) in enumerate(steps):
        s.badge(820, 250 + i * 62, n)
        words, lines, cur = t.split(), [], ""
        for w in words:
            if len(cur) + len(w) > 40:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        for k, ln in enumerate(lines):
            s.text(842, 246 + i * 62 + k * 16, ln, 12.5)
    s.text(30, 580, "Wrong row or one pin off: 5V can end up on a GPIO pin and kill it. Look along the header from "
                    "both ends before you press.", 13, fill="var(--mut)")
    s.save("hat-on-pi.svg")


# ---------------------------------------------------------------- tape path
def tape_path():
    s = Svg(1200, 520, "How the tape runs (seen from the front)",
            "Sticky side UP the whole way. Only the backing touches plastic. The tape moves right to left.")
    y = 300
    # supply roll (right)
    rx, ry = 1030, 300
    s.circle(rx, ry, 95, "#bfe3f7", "#5aa9d6", 2)
    s.circle(rx, ry, 40, "var(--bg)", "var(--line)", 2)
    s.text(rx, ry + 125, "tape roll on the peg", 13, "middle", "700")
    # take-up spool (left)
    lx, ly = 140, 300
    s.circle(lx, ly, 55, ORANGE, "#a54f05", 2)
    s.circle(lx, ly, 14, "var(--bg)")
    s.text(lx, ly + 125, "take-up spool (motor)", 13, "middle", "700")
    # tape line: from bottom of roll up over the ledge, along, then down onto the spool
    s.line([(rx - 20, ry + 93), (760, y), (330, y), (lx + 40, ly + 38)], "#1f8fd6", 5)
    s.line([(rx - 20, ry + 87), (760, y - 6), (330, y - 6), (lx + 36, ly + 32)], "#f2c14e", 3, "6 5")
    s.text(560, y - 14, "sticky side", 12, "middle", "700", "#c08a00")
    # fan above
    fx = 690
    s.rect(fx - 55, 150, 110, 40, fill="var(--card)", stroke="var(--ink)", rx=4, sw=2)
    s.text(fx, 175, "fan", 14, "middle", "700")
    for k in (-30, 0, 30):
        s.arrow(fx + k, 200, fx + k, y - 18, "#5aa9d6", 2.5)
    s.rect(fx - 60, y + 4, 120, 10, fill="var(--line)", stroke="none", rx=2)
    s.text(fx, y + 34, "ledge under the tape", 12, "middle", fill="var(--mut)")
    s.text(fx + 70, 230, "1. air blows pollen", 13, "start", "700")
    s.text(fx + 70, 248, "onto the sticky side", 13, "start", "700")
    # camera box + LED tower
    cx = 440
    s.rect(cx - 70, y + 4, 140, 10, fill="var(--line)", stroke="none", rx=2)
    s.rect(cx - 50, y + 26, 100, 10, fill="var(--pcb)", stroke="none", rx=2)
    s.rect(cx - 12, y + 16, 24, 10, fill="#333", stroke="none", rx=1)
    s.text(cx, y + 60, "camera sensor, about 1 mm below", 12, "middle", fill="var(--mut)")
    s.rect(cx - 30, 120, 60, 26, fill="#444", stroke="none", rx=3)
    s.text(cx, 112, "NeoPixel", 12, "middle", "700")
    s.a(f'<polygon points="{cx - 8},146 {cx + 8},146 {cx + 2},160 {cx - 2},160" fill="#444"/>')
    s.text(cx + 40, 160, "pinhole", 12, "start", fill="var(--mut)")
    s.a(f'<polygon points="{cx},162 {cx - 40},{y - 10} {cx + 40},{y - 10}" fill="#f6e7a8" opacity="0.55"/>')
    s.text(cx - 160, 210, "2. light shines through", 13, "start", "700")
    s.text(cx - 160, 228, "the tape, the camera", 13, "start", "700")
    s.text(cx - 160, 246, "takes a picture", 13, "start", "700")
    s.arrow(860, 400, 600, 400, "var(--mut)", 2)
    s.text(730, 420, "tape moves", 12, "middle", fill="var(--mut)")
    s.save("tape-path.svg")


# ---------------------------------------------------------------- stages
def stages():
    s = Svg(1200, 330, "The build at a glance", "Start the printer first. While it prints, set up the Pi and build the HAT.")
    boxes = [
        (30, 100, "1  Parts", "order, check the list"),
        (230, 100, "2  Print", "several hours"),
        (230, 210, "3  Pi setup", "SD card, software"),
        (430, 210, "4  HAT", "solder, test"),
        (630, 150, "5  Camera", "lens off, clean"),
        (830, 150, "6  Assemble", "parts, cables, tape"),
        (1030, 150, "7  Test", "checks, calibrate"),
    ]
    for x, y, t, sub in boxes:
        s.rect(x, y, 150, 64, fill="var(--card)", stroke="var(--ink)", rx=10, sw=1.5)
        s.text(x + 75, y + 28, t, 15, "middle", "800")
        s.text(x + 75, y + 48, sub, 12, "middle", fill="var(--mut)")
    s.arrow(180, 132, 226, 132)
    s.arrow(180, 140, 226, 238)
    s.arrow(380, 242, 426, 242)
    s.arrow(380, 132, 626, 175)
    s.arrow(580, 242, 626, 192)
    s.arrow(780, 182, 826, 182)
    s.arrow(980, 182, 1026, 182)
    s.text(1105, 250, "then 8  Run it", 14, "middle", "700")
    s.save("stages.svg")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    connections()
    hat_on_pi()
    tape_path()
    stages()
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.svg"))))
