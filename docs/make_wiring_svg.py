"""Generates docs/wiring.svg (run: python3 make_wiring_svg.py). Edit pins here if the wiring changes."""
from pathlib import Path

W, H = 1440, 810
C = {  # wire colours
    "5V": "#d62728", "GND": "var(--gnd)", "IN1": "#ff7f0e", "IN2": "#d4a600", "IN3": "#2ca02c",
    "IN4": "#1f77b4", "FAN": "#9467bd", "OPT": "#8c8c8c",
    "3V3": "#e67e22", "RED": "#d64541", "GREEN": "#2a9d4a", "BLUE": "#2f6fd6",
}
PIN_NAMES = {
    1: "3V3", 2: "5V", 3: "GPIO2 SDA", 4: "5V", 5: "GPIO3 SCL", 6: "GND", 7: "GPIO4", 8: "GPIO14 TXD",
    9: "GND", 10: "GPIO15 RXD", 11: "GPIO17", 12: "GPIO18", 13: "GPIO27", 14: "GND", 15: "GPIO22",
    16: "GPIO23", 17: "3V3", 18: "GPIO24", 19: "GPIO10", 20: "GND", 21: "GPIO9", 22: "GPIO25",
    23: "GPIO11", 24: "GPIO8", 25: "GND", 26: "GPIO7", 27: "ID_SD", 28: "ID_SC", 29: "GPIO5", 30: "GND",
    31: "GPIO6", 32: "GPIO12", 33: "GPIO13", 34: "GND", 35: "GPIO19", 36: "GPIO16", 37: "GPIO26",
    38: "GPIO20", 39: "GND", 40: "GPIO21",
}
USED = {  # pin -> (colour key, function)
    2: ("5V", "→ driver board +"), 4: ("5V", "→ fan"), 6: ("GND", "→ driver board −"),
    14: ("GND", "→ fan MOSFET"), 17: ("3V3", "→ LED long leg"),
    11: ("IN1", "driver IN1"), 13: ("IN2", "driver IN2"),
    15: ("IN3", "driver IN3"), 16: ("IN4", "driver IN4"), 12: ("FAN", "fan MOSFET"),
    18: ("RED", "LED red"), 22: ("GREEN", "LED green"), 29: ("BLUE", "LED blue"),
    1: ("OPT", "BME280 (optional)"), 3: ("OPT", "BME280 (optional)"), 5: ("OPT", "BME280 (optional)"),
    9: ("OPT", "BME280 (optional)"),
}

out = []
a = out.append


def text(x, y, s, size=13, anchor="start", weight="normal", fill="var(--ink)", cls=""):
    s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    a(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
      f'fill="{fill}" class="{cls}">{s}</text>')


def line(pts, col, w=3, dash=None):
    d = " ".join(f"{x},{y}" for x, y in pts)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    a(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"{extra}/>')


def box(x, y, w, h, title=None, fill="var(--card)", r=8, stroke="var(--line)"):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    if title:
        text(x + 14, y + 24, title, 15, weight="700")


def tag(x, y, pin, key, w=150, anchor="right"):
    """Coloured label meaning 'this wire goes to Pi pin N'. (x,y) = wire end point."""
    col = C[key]
    bx = x - w if anchor == "right" else x
    a(f'<rect x="{bx}" y="{y - 11}" width="{w}" height="22" rx="11" fill="{col}"/>')
    label = f"Pi pin {pin} · {PIN_NAMES[pin]}"
    text(bx + w / 2, y + 4.5, label, 12, "middle", "600", "#fff")


def dot(x, y, col="var(--ink)"):
    a(f'<circle cx="{x}" cy="{y}" r="4" fill="{col}"/>')


def resistor(x, y, vertical, label, col):
    """Small resistor body centred on (x,y)."""
    if vertical:
        a(f'<rect x="{x - 7}" y="{y - 18}" width="14" height="36" rx="3" fill="var(--card)" stroke="{col}" stroke-width="2.5"/>')
        text(x + 14, y + 4, label, 12)
    else:
        a(f'<rect x="{x - 18}" y="{y - 7}" width="36" height="14" rx="3" fill="var(--card)" stroke="{col}" stroke-width="2.5"/>')
        text(x, y - 13, label, 12, "middle")


def mosfet(x, y, label):
    """MOSFET as a labelled block: D top-centre, S bottom-centre, G left-middle. (x,y)=top-left. 70x80."""
    box(x, y, 70, 80, None, fill="var(--chip)", r=6, stroke="var(--ink)")
    text(x + 38, y + 34, "N-MOS", 12, "middle", "700")
    text(x + 80, y + 36, "logic-level", 11, "start", fill="var(--mut)")
    text(x + 80, y + 52, label, 11, "start", fill="var(--mut)")
    text(x + 35, y + 16, "D", 11, "middle", "700")
    text(x + 35, y + 74, "S", 11, "middle", "700")
    text(x + 6, y + 56, "G", 11, "start", "700")
    return (x + 35, y), (x + 35, y + 80), (x, y + 40)  # D, S, G


def diode_vertical(x, y1, y2, col):
    """Diode, cathode (stripe) at the top (y1)."""
    m = (y1 + y2) / 2
    line([(x, y1), (x, m - 10)], col, 2.5)
    line([(x, m + 10), (x, y2)], col, 2.5)
    a(f'<polygon points="{x - 10},{m + 10} {x + 10},{m + 10} {x},{m - 8}" fill="var(--ink)"/>')
    line([(x - 11, m - 9), (x + 11, m - 9)], "var(--ink)", 3)


def fan_circuit(x0, y0, w, h):
    """Fan switched by a MOSFET: 5V -> fan -> D, S -> GND, G <- 220R <- GPIO18, 100k G -> GND."""
    box(x0, y0, w, h, "Fan (switched by a MOSFET)")
    lx = x0 + 280
    top = y0 + 70
    tag(lx - 40, top, 4, "5V", 150)
    line([(lx - 40, top), (lx, top), (lx, top + 30)], C["5V"])
    y = top + 30
    ly = y + 40
    a(f'<circle cx="{lx}" cy="{ly}" r="30" fill="var(--card)" stroke="var(--ink)" stroke-width="2.5"/>')
    a(f'<path d="M{lx},{ly} q-14,-22 0,-24 q8,6 0,24 q22,-6 22,8 q-10,4 -22,-8 q-6,24 -18,14 q4,-10 18,-14z" fill="var(--mut)"/>')
    text(lx - 44, ly - 4, "red wire", 11, "end", fill="var(--mut)")
    text(lx - 44, ly + 26, "black wire", 11, "end", fill="var(--mut)")
    line([(lx, y), (lx, ly - 30)], C["5V"])
    dx = lx + 70
    dot(lx, y)
    line([(lx, y), (dx, y)], C["5V"], 2.5)
    diode_vertical(dx, y, ly + 52, "var(--ink)")
    line([(dx, ly + 52), (lx, ly + 52)], "var(--ink)", 2.5)
    dot(lx, ly + 52)
    text(dx + 16, ly + 8, "1N5819", 12)
    text(dx + 16, ly + 24, "stripe up", 11, fill="var(--mut)")
    line([(lx, ly + 30), (lx, ly + 70)], "var(--ink)")
    text(lx - 44, ly + 56, "5 V fan", 12, "end", "600")
    d, s, g = mosfet(lx - 35, ly + 70, "e.g. IRLZ44N")
    gy = s[1] + 40
    line([s, (s[0], gy)], C["GND"])
    gx = x0 + 170
    line([(s[0], gy), (gx, gy)], C["GND"])
    tag(gx, gy, 14, "GND", 150)
    gate_y = g[1]
    line([(gx, gate_y), (g[0], gate_y)], C["FAN"])
    resistor(gx + 30, gate_y, False, "220 Ω", C["FAN"])
    tag(gx, gate_y, 12, "FAN", 150)
    px = g[0] - 22
    dot(px, gate_y)
    line([(px, gate_y), (px, gate_y + 8)], C["FAN"], 2.5)
    resistor(px, gate_y + 26, True, "", "var(--ink)")
    text(px - 12, gate_y + 30, "100 kΩ", 12, "end")
    line([(px, gate_y + 44), (px, gy)], C["GND"], 2.5)
    dot(px, gy)
    ny = gy + 34
    for n in ("The diode protects the MOSFET when the fan turns off.",
              "The 100 kΩ keeps the fan off while the Pi starts up."):
        text(x0 + 14, ny, n, 12, fill="var(--mut)")
        ny += 17


def led_circuit(x0, y0, w, h):
    """Common-anode RGB LED: 3.3V -> long leg, each colour -> resistor -> its GPIO pin (low = on)."""
    box(x0, y0, w, h, "RGB LED (straight from GPIO pins)")
    rx = x0 + 40
    top = y0 + 64
    tag(rx, top, 17, "3V3", 150, anchor="left")
    rows = [("red", 18, "RED", "220 Ω"), ("green", 22, "GREEN", "100 Ω"), ("blue", 29, "BLUE", "47 Ω")]
    ys = [y0 + 130 + 80 * i for i in range(3)]
    line([(rx, top), (rx, ys[-1])], C["3V3"])
    for (name, pin, key, ohm), ly in zip(rows, ys):
        lx = x0 + 110
        dot(rx, ly, C["3V3"])
        line([(rx, ly), (lx - 14, ly)], C["3V3"])
        a(f'<polygon points="{lx - 14},{ly - 16} {lx - 14},{ly + 16} {lx + 14},{ly}" fill="{C[key]}" stroke="var(--ink)" stroke-width="2"/>')
        line([(lx + 15, ly - 17), (lx + 15, ly + 17)], "var(--ink)", 3)
        text(lx, ly + 34, name, 12, "middle", "600")
        line([(lx + 15, ly), (x0 + 240, ly)], C[key])
        resistor(x0 + 190, ly, False, ohm, C[key])
        tag(x0 + 240, ly, pin, key, 150, anchor="left")
    ny = ys[-1] + 66
    for n in ("One LED with 4 legs. The long leg is the shared + (anode).",
              "Pin LOW = that colour on. Pin HIGH = off.",
              "All three on = white."):
        text(x0 + 14, ny, n, 12, fill="var(--mut)")
        ny += 17


# ---------------- document ----------------
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
  f'font-family="system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif">')
a("""<style>
svg{--gnd:#3d423b;--bg:#f7f8f5;--card:#ffffff;--chip:#eef1ea;--ink:#1d211b;--mut:#646b60;--line:#d6dbd0}
@media (prefers-color-scheme:dark){svg{--gnd:#7d8579;--bg:#141713;--card:#1d211b;--chip:#272c25;--ink:#e6eae2;--mut:#9aa293;--line:#3a4137}}
</style>""")
a(f'<rect width="{W}" height="{H}" fill="var(--bg)"/>')
text(30, 44, "Pollen sampler wiring (Raspberry Pi 3 B+)", 24, weight="700")

# ---- header panel ----
hx, hy = 30, 70
box(hx, hy, 470, 720, "Pi pin header")
cx_odd, cx_even, y0, dy = hx + 215, hx + 255, hy + 92, 30
a(f'<rect x="{cx_odd - 20}" y="{y0 - 18}" width="80" height="{dy * 19 + 36}" rx="6" fill="var(--chip)" stroke="var(--line)"/>')
for i in range(20):
    for pin, cx, side in ((2 * i + 1, cx_odd, -1), (2 * i + 2, cx_even, 1)):
        cy = y0 + i * dy
        used = USED.get(pin)
        col = C[used[0]] if used else "var(--card)"
        shape = (f'<rect x="{cx - 10}" y="{cy - 10}" width="20" height="20" rx="2"' if pin == 1
                 else f'<circle cx="{cx}" cy="{cy}" r="10"')
        a(f'{shape} fill="{col}" stroke="var(--ink)" stroke-width="1.2"/>')
        text(cx, cy + 4, str(pin), 9, "middle", "700", "#fff" if used else "var(--mut)")
        name = PIN_NAMES[pin]
        lab = (f"{name} {used[1]}" if used[1].startswith("→") else f"{name}: {used[1]}") if used else name
        weight = "600" if used and used[0] != "OPT" else "normal"
        fill = "var(--ink)" if used and used[0] != "OPT" else "var(--mut)"
        if side < 0:
            text(cx - 18, cy + 4, lab, 11.5, "end", weight, fill)
        else:
            text(cx + 18, cy + 4, lab, 11.5, "start", weight, fill)

# ---- ULN2003 + stepper ----
ux, uy = 530, 70
box(ux, uy, 440, 270, "Stepper motor and driver board")
bx, by = ux + 210, uy + 50
a(f'<rect x="{bx}" y="{by}" width="110" height="190" rx="6" fill="#1b6e3a" stroke="var(--ink)"/>')
text(bx + 55, by + 22, "ULN2003", 13, "middle", "700", "#fff")
pins = [("IN1", 11, "IN1"), ("IN2", 13, "IN2"), ("IN3", 15, "IN3"), ("IN4", 16, "IN4")]
for k, (lab, pin, key) in enumerate(pins):
    py = by + 46 + k * 24
    text(bx + 8, py + 4, lab, 11, fill="#fff")
    line([(bx - 40, py), (bx, py)], C[key])
    tag(bx - 40, py, pin, key, 150)
py = by + 46 + 4 * 24 + 10
text(bx + 8, py + 4, "+  5V", 11, fill="#fff")
line([(bx - 40, py), (bx, py)], C["5V"]); tag(bx - 40, py, 2, "5V", 150)
py += 24
text(bx + 8, py + 4, "−  GND", 11, fill="#fff")
line([(bx - 40, py), (bx, py)], C["GND"]); tag(bx - 40, py, 6, "GND", 150)
mx, my = bx + 110 + 60, by + 95
line([(bx + 110, my - 6), (mx - 32, my - 6)], "#3a7bd5", 6)
a(f'<circle cx="{mx}" cy="{my}" r="32" fill="#9aa6b2" stroke="var(--ink)" stroke-width="2"/>')
a(f'<circle cx="{mx}" cy="{my - 12}" r="6" fill="#d9d9d9" stroke="var(--ink)"/>')
text(mx, my + 52, "28BYJ-48", 12, "middle", "700")

# ---- camera + power ----
cx0, cy0 = 990, 70
box(cx0, cy0, 420, 270, "Camera and power")
a(f'<rect x="{cx0 + 20}" y="{cy0 + 50}" width="90" height="90" rx="6" fill="#1b6e3a" stroke="var(--ink)"/>')
a(f'<circle cx="{cx0 + 65}" cy="{cy0 + 95}" r="26" fill="#333" stroke="#999" stroke-width="3"/>')
text(cx0 + 65, cy0 + 158, "HQ Camera", 12, "middle", "700")
a(f'<rect x="{cx0 + 110}" y="{cy0 + 86}" width="90" height="18" fill="#e8d9a8" stroke="var(--ink)"/>')
text(cx0 + 215, cy0 + 82, "Ribbon goes in the CAMERA port", 12, weight="600")
text(cx0 + 215, cy0 + 99, "Blue side faces the USB ports.", 11.5, fill="var(--mut)")
text(cx0 + 215, cy0 + 114, "Only plug it in with the", 11.5, fill="var(--mut)")
text(cx0 + 215, cy0 + 129, "power off.", 11.5, fill="var(--mut)")
text(cx0 + 20, cy0 + 195, "Power: 5.1 V, 2.5 A micro USB supply into the Pi.", 12, weight="600")

# ---- fan + LED ----
fan_circuit(530, 360, 440, 430)
led_circuit(990, 360, 420, 430)


a("</svg>")
Path(__file__).with_name("wiring.svg").write_text("\n".join(out))
print("wrote wiring.svg")
