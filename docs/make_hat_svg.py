"""Generates docs/hat.svg: where every part goes on the Proto HAT (run: python3 make_hat_svg.py).

The board is drawn from the top, the 40-pin header at the top, like docs/hat.md.
All positions are in hole pitches (2.54 mm) from the board's top left corner.
"""
from pathlib import Path

P = 34                 # pixels per hole pitch (2.54 mm)
BX, BY = 40, 150       # board top left corner on the page
BW, BH = 25.6, 22.25   # board size in pitches (65 x 56.5 mm)
W, H = 1530, 960

out = []
a = out.append


def X(p): return BX + p * P
def Y(p): return BY + p * P


def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=13, anchor="start", weight="normal", fill="var(--ink)", rot=None):
    tr = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    a(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
      f'fill="{fill}"{tr}>{esc(s)}</text>')


# ---------------- board geometry (measured from a photo of the board) ----------------
BRK = ["SDA", "SCL", "TXD", "RXD", "#4", "#17", "#18", "#27", "#22", "#23", "#24", "#25", "MOSI",
       "MISO", "CLK", "CE0", "CE1", "#5", "#6", "#12", "#13", "#16", "#19", "#20", "#21"]
def brk(name): return 1.15 + BRK.index(name)      # x of a GPIO breakout hole
BRK_Y = 3.15
HDR_X0, HDR_Y_EVEN, HDR_Y_ODD = 3.4, 0.88, 1.88  # 2x20 header, pin 1 = square, bottom left
RAIL3V3_Y, RAILGND_TOP_Y = 5.5, 6.5
UP_ROWS = [7.5 + k for k in range(5)]
def U(n): return 3.04 + (n - 1)                     # upper strips 1..23
LOW_ROWS = [13.7 + k for k in range(5)]             # rows 1..5 of the lower strips
def L(n): return 3.04 + (n - 1) if n <= 15 else 19.04 + (n - 16)  # lower strips 1..15, then 16..22 right of the slot
def r(n): return LOW_ROWS[n - 1]
RAIL5V_Y, RAILGND_Y = 18.7, 19.7

BOARD, MASK_EDGE, TIN, HOLE, SILK = "#1d2024", "#0e1012", "#bdb8a8", "#0b0c0e", "#f1f1ee"
C = {"5V": "#d62728", "GND": "#111111", "SIG": "#9b59d0", "DATA": "#1f8fd6", "M1": "#ff7f0e",
     "M2": "#e3b400", "M3": "#2ca02c", "M4": "#1f77b4"}


def hole(px, py, ring="#cfc7ad"):
    a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="{0.27 * P:.1f}" fill="{ring}"/>')
    a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="{0.15 * P:.1f}" fill="{HOLE}"/>')


def strip_v(px, y0, y1):
    a(f'<rect x="{X(px) - 0.38 * P:.1f}" y="{Y(y0) - 0.42 * P:.1f}" width="{0.76 * P:.1f}" '
      f'height="{(y1 - y0 + 0.84) * P:.1f}" rx="3" fill="{TIN}" opacity="0.55"/>')


def strip_h(x0, x1, py):
    a(f'<rect x="{X(x0) - 0.42 * P:.1f}" y="{Y(py) - 0.38 * P:.1f}" width="{(x1 - x0 + 0.84) * P:.1f}" '
      f'height="{0.76 * P:.1f}" rx="3" fill="{TIN}" opacity="0.55"/>')


def board():
    # outline with the notch on the left side (for the display cable)
    x0, y0, x1, y1, nx, ny0, ny1, rr = X(0), Y(0), X(BW), Y(BH), X(1.6), Y(7.3), Y(14.4), 0.9 * P
    d = (f"M{x0 + rr},{y0} H{x1 - rr} Q{x1},{y0} {x1},{y0 + rr} V{y1 - rr} Q{x1},{y1} {x1 - rr},{y1} "
         f"H{x0 + rr} Q{x0},{y1} {x0},{y1 - rr} V{ny1} H{nx} V{ny0} H{x0} V{y0 + rr} Q{x0},{y0} {x0 + rr},{y0} Z")
    a(f'<path d="{d}" fill="{BOARD}" stroke="{MASK_EDGE}" stroke-width="2"/>')
    for mx, my in ((1.38, 1.38), (24.2, 1.38), (1.38, 20.67), (24.2, 20.67)):
        a(f'<circle cx="{X(mx)}" cy="{Y(my)}" r="{0.55 * P}" fill="#c9c9c9"/>')
        a(f'<circle cx="{X(mx)}" cy="{Y(my)}" r="{0.38 * P}" fill="var(--bg)"/>')
    # 2x20 header
    a(f'<rect x="{X(HDR_X0 - 0.55):.1f}" y="{Y(HDR_Y_EVEN - 0.55):.1f}" width="{20.1 * P:.1f}" '
      f'height="{2.1 * P:.1f}" fill="none" stroke="{SILK}" stroke-width="1.2"/>')
    for i in range(20):
        hole(HDR_X0 + i, HDR_Y_EVEN)
        hole(HDR_X0 + i, HDR_Y_ODD)
    a(f'<rect x="{X(HDR_X0) - 5:.1f}" y="{Y(HDR_Y_ODD) - 5:.1f}" width="10" height="10" fill="none" stroke="{SILK}"/>')
    # GPIO breakout row + labels
    a(f'<rect x="{X(0.6):.1f}" y="{Y(BRK_Y - 0.5):.1f}" width="{(BW - 1.15) * P:.1f}" height="{P:.1f}" '
      f'fill="none" stroke="{SILK}" stroke-width="1.2"/>')
    for name in BRK:
        hole(brk(name), BRK_Y)
        text(X(brk(name)) + 3.5, Y(BRK_Y + 0.62), name, 9.5, "end", "700", SILK, rot=-90)
    # top rails
    for py, lab in ((RAIL3V3_Y, "+3V3"), (RAILGND_TOP_Y, "GND")):
        strip_h(U(1), U(23), py)
        for n in range(1, 24):
            hole(U(n), py)
        text(X(U(1) - 0.6), Y(py) + 4, lab, 11, "end", "700", SILK)
    # upper strips
    for n in range(1, 24):
        strip_v(U(n), UP_ROWS[0], UP_ROWS[-1])
        for py in UP_ROWS:
            hole(U(n), py)
    text(X(21.3), Y(12.75), "upper area: free for later parts", 10, "middle", fill="#8b9097")
    # lower strips
    for n in list(range(1, 16)) + list(range(16, 23)):
        strip_v(L(n), r(1), r(5))
        for py in LOW_ROWS:
            hole(L(n), py)
    # slot for the camera cable
    a(f'<rect x="{X(17.45):.1f}" y="{Y(13.3):.1f}" width="{0.9 * P:.1f}" height="{5.5 * P:.1f}" rx="{0.45 * P}" fill="var(--bg)"/>')
    # bottom rails
    for py, lab in ((RAIL5V_Y, "+5V"), (RAILGND_Y, "GND")):
        strip_h(L(3), L(15), py)
        for n in range(3, 16):
            hole(L(n), py)
        text(X(L(3) - 0.6), Y(py) + 4, lab, 11, "end", "700", SILK)
    # EEPROM area
    a(f'<rect x="{X(19.0):.1f}" y="{Y(18.3):.1f}" width="{3.6 * P:.1f}" height="{2.6 * P:.1f}" rx="4" '
      f'fill="none" stroke="#6c7178" stroke-dasharray="4 3"/>')
    text(X(20.8), Y(19.55), "EEPROM pads", 9.5, "middle", fill="#9aa0a6")
    text(X(20.8), Y(19.95), "leave empty", 9.5, "middle", fill="#9aa0a6")
    # strip numbers (lower area) and row numbers
    for n in range(1, 16):
        text(X(L(n)), Y(21.55), n, 11, "middle", "800", "#f6d365")
    for k in range(1, 6):
        text(X(BW + 0.35), Y(r(k)) + 4, f"row {k}", 11, "start", "700", "var(--mut)")


# ---------------- parts ----------------
def wire(pts, col, w=0.2):
    d = " ".join(f"{X(px):.1f},{Y(py):.1f}" for px, py in pts)
    a(f'<polyline points="{d}" fill="none" stroke="#ffffff" stroke-width="{w * P + 3:.1f}" '
      f'stroke-linejoin="round" stroke-linecap="round" opacity="0.9"/>')
    a(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{w * P:.1f}" '
      f'stroke-linejoin="round" stroke-linecap="round"/>')
    for px, py in (pts[0], pts[-1]):
        a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="{0.17 * P:.1f}" fill="{col}" stroke="#fff" stroke-width="1.5"/>')


BANDS = {"220": ["#d62728", "#d62728", "#8b4513"], "100k": ["#8b4513", "#111", "#f2d32b"],
         "330": ["#ff8c1a", "#ff8c1a", "#8b4513"]}


def resistor(x0, x1, py, value):
    a(f'<line x1="{X(x0):.1f}" y1="{Y(py):.1f}" x2="{X(x1):.1f}" y2="{Y(py):.1f}" stroke="#d9d9d9" stroke-width="2.5"/>')
    for px in (x0, x1):
        a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="4" fill="#d9d9d9"/>')
    mid, bl, bh = (X(x0) + X(x1)) / 2, 2.0 * P, 0.62 * P
    a(f'<rect x="{mid - bl / 2:.1f}" y="{Y(py) - bh / 2:.1f}" width="{bl:.1f}" height="{bh:.1f}" rx="{bh / 2:.1f}" '
      f'fill="#e8d3a2" stroke="#6b5a35" stroke-width="1"/>')
    for i, col in enumerate(BANDS[value] + ["#c9a227"]):
        bx = mid - bl / 2 + bl * (0.2 + 0.17 * i) + (0.1 * bl if i == 3 else 0)
        a(f'<rect x="{bx:.1f}" y="{Y(py) - bh / 2:.1f}" width="{0.1 * bl:.1f}" height="{bh:.1f}" fill="{col}"/>')


def diode(x_anode, x_cathode, py):
    a(f'<line x1="{X(x_anode):.1f}" y1="{Y(py):.1f}" x2="{X(x_cathode):.1f}" y2="{Y(py):.1f}" stroke="#d9d9d9" stroke-width="2.5"/>')
    for px in (x_anode, x_cathode):
        a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="4" fill="#d9d9d9"/>')
    mid, bl, bh = (X(x_anode) + X(x_cathode)) / 2, 1.9 * P, 0.66 * P
    a(f'<rect x="{mid - bl / 2:.1f}" y="{Y(py) - bh / 2:.1f}" width="{bl:.1f}" height="{bh:.1f}" rx="3" fill="#202020" stroke="#777"/>')
    sx = mid + bl / 2 - 0.22 * bl if x_cathode > x_anode else mid - bl / 2 + 0.1 * bl
    a(f'<rect x="{sx:.1f}" y="{Y(py) - bh / 2:.1f}" width="{0.12 * bl:.1f}" height="{bh:.1f}" fill="#e0e0e0"/>')


def mosfet(xg, py):
    """IRLZ44N standing, seen from above. Metal tab toward the top of the board, printed side toward the rails."""
    x0, x1 = X(xg - 1.0), X(xg + 3.0)
    a(f'<rect x="{x0:.1f}" y="{Y(py - 1.05):.1f}" width="{x1 - x0:.1f}" height="{0.42 * P:.1f}" fill="#a9adb3" stroke="#555"/>')
    a(f'<rect x="{x0:.1f}" y="{Y(py - 0.65):.1f}" width="{x1 - x0:.1f}" height="{1.05 * P:.1f}" rx="2" fill="#151515" stroke="#888"/>')
    text((x0 + x1) / 2, Y(py - 0.15), "IRLZ44N", 10, "middle", "700", "#eee")
    for i, lab in enumerate("GDS"):
        a(f'<circle cx="{X(xg + i):.1f}" cy="{Y(py):.1f}" r="5" fill="#d9d9d9" stroke="#333"/>')
        text(X(xg + i), Y(py + 0.62), lab, 11, "middle", "800", "#fff")


def header(px, rows, labels, side):
    """Male pin header standing up. rows = y of each pin. labels drawn on the left or right."""
    a(f'<rect x="{X(px) - 0.45 * P:.1f}" y="{Y(rows[0]) - 0.48 * P:.1f}" width="{0.9 * P:.1f}" '
      f'height="{(rows[-1] - rows[0] + 0.96) * P:.1f}" rx="2" fill="#111" stroke="#fff" stroke-width="1.2"/>')
    for py, lab in zip(rows, labels):
        a(f'<rect x="{X(px) - 4:.1f}" y="{Y(py) - 4:.1f}" width="8" height="8" fill="#e6c35c"/>')
        if lab:
            tx = X(px) - 0.62 * P if side == "left" else X(px) + 0.62 * P
            w = 7 + 8 * len(lab)
            bx = tx - w + 2 if side == "left" else tx - 2
            a(f'<rect x="{bx:.1f}" y="{Y(py) - 9:.1f}" width="{w:.1f}" height="18" rx="4" fill="#111"/>')
            text(tx - 2 if side == "left" else tx + 2, Y(py) + 4.5, lab, 12,
                 "end" if side == "left" else "start", "800", "#fff")


def tag(px, py, s, dx=0.0, dy=0.0, fill="#ffffff", ink="#111"):
    """Part name box, drawn at (px+dx, py+dy)."""
    w = 8 + 7.2 * len(s)
    cx, cy = X(px + dx), Y(py + dy)
    a(f'<rect x="{cx - w / 2:.1f}" y="{cy - 9:.1f}" width="{w:.1f}" height="18" rx="9" fill="{fill}" stroke="#111" stroke-width="1"/>')
    text(cx, cy + 4.5, s, 11.5, "middle", "800", ink)


def parts():
    # long wires from the GPIO breakout row
    xa = brk("#17") - 0.5
    wire([(brk("#17"), BRK_Y), (xa, BRK_Y + 0.4), (xa, 12.25), (L(2), 12.25), (L(2), r(1))], C["SIG"])
    tag(xa, 9.6, "W1")
    xb = brk("MOSI") + 0.5
    wire([(brk("MOSI"), BRK_Y), (xb, BRK_Y + 0.4), (xb, 12.25), (L(11), 12.25), (L(11), r(1))], C["DATA"])
    tag(xb, 9.6, "W2")
    # short links to the rails
    wire([(L(8), r(5)), (L(8), RAIL5V_Y), (L(8), RAILGND_Y)], C["GND"], 0.17)
    tag(L(8), 20.6, "K1")
    wire([(L(10), r(5)), (L(10), RAILGND_Y)], C["GND"], 0.17)
    tag(L(10), 20.6, "K2")
    wire([(L(12), r(5)), (L(12), RAIL5V_Y)], C["5V"], 0.17)
    tag(L(12), 18.2, "K3", dx=0.85)
    # resistors and diode
    resistor(L(2), L(6), r(3), "220"); tag(L(4), r(3), "R1 220 Ω", dy=-0.62)
    resistor(L(6), L(10), r(4), "100k"); tag(L(8), r(4), "R2 100 kΩ", dx=1.3, dy=0.6)
    resistor(L(11), L(15), r(2), "330"); tag(L(13), r(2), "R3 330 Ω", dy=0.62)
    diode(L(7), L(12), r(3)); tag(L(9.5), r(3), "D1", dy=-0.62)
    # MOSFET
    mosfet(L(6), r(1)); tag(L(7), r(1), "Q1", dx=-2.65, dy=-0.4)
    # headers in the rails
    header(L(7), [r(5), RAIL5V_Y], ["−", "+"], "left"); tag(L(7), r(5), "J1 fan", dx=-2.4)
    header(L(15), [r(5), RAIL5V_Y, RAILGND_Y], ["DIN", "5V", "GND"], "left"); tag(L(15), 20.6, "J2 light")
    header(L(4), [RAIL5V_Y, RAILGND_Y], ["+", "−"], "left"); tag(L(4), 20.6, "J3 motor power")
    # motor pins in the breakout holes
    for name, key, lab in (("#18", "M1", "IN1"), ("#27", "M2", "IN2"), ("#22", "M3", "IN3"), ("#23", "M4", "IN4")):
        bx = brk(name)
        a(f'<rect x="{X(bx) - 0.45 * P:.1f}" y="{Y(BRK_Y) - 0.45 * P:.1f}" width="{0.9 * P:.1f}" height="{0.9 * P:.1f}" '
          f'rx="2" fill="#111" stroke="{C[key]}" stroke-width="3"/>')
        a(f'<rect x="{X(bx) - 4:.1f}" y="{Y(BRK_Y) - 4:.1f}" width="8" height="8" fill="#e6c35c"/>')
    # J4 labels above the board, with leader lines
    xs = [brk(n) for n in ("#18", "#27", "#22", "#23")]
    for i, (px, key, lab) in enumerate(zip(xs, ("M1", "M2", "M3", "M4"), ("IN1", "IN2", "IN3", "IN4"))):
        lx = 5.2 + i * 1.6
        a(f'<polyline points="{X(px):.1f},{Y(BRK_Y) - 0.45 * P:.1f} {X(px):.1f},{Y(-0.6):.1f} {X(lx):.1f},{Y(-1.1):.1f}" '
          f'fill="none" stroke="{C[key]}" stroke-width="2.5"/>')
        a(f'<rect x="{X(lx) - 22:.1f}" y="{Y(-1.1) - 20:.1f}" width="44" height="20" rx="10" fill="{C[key]}"/>')
        text(X(lx), Y(-1.1) - 6, lab, 11.5, "middle", "800", "#fff")
    text(X(11.6), Y(-1.1) - 6, "J4 motor pins: a 4-pin header in the #18, #27, #22 and #23 holes", 13, "start", "700")


# ---------------- side panel ----------------
def panel():
    px0, py0 = X(BW) + 90, 95
    a(f'<rect x="{px0}" y="{py0}" width="{W - px0 - 30}" height="{H - py0 - 30}" rx="10" fill="var(--card)" stroke="var(--line)"/>')
    x, y = px0 + 22, py0 + 36
    text(x, y, "Parts", 17, weight="800")
    rows = [
        ("J4", "4-pin male header", "holes #18 #27 #22 #23 (motor IN1-IN4)"),
        ("—", "2x20 female socket", "underneath, solder on top"),
        ("K1", "short wire (black)", "strip 8 row 5 → bottom GND rail"),
        ("K2", "short wire (black)", "strip 10 row 5 → bottom GND rail"),
        ("K3", "short wire (red)", "strip 12 row 5 → +5V rail"),
        ("R1", "220 Ω resistor", "strip 2 → strip 6, row 3"),
        ("R2", "100 kΩ resistor", "strip 6 → strip 10, row 4"),
        ("R3", "330 Ω resistor", "strip 11 → strip 15, row 2"),
        ("D1", "1N5819 / 1N4148 diode", "strip 7 → strip 12, row 3, stripe right"),
        ("W1", "wire (purple)", "#17 hole → strip 2 row 1"),
        ("W2", "wire (blue)", "MOSI hole → strip 11 row 1"),
        ("J1", "2-pin male header", "strip 7 row 5 + the +5V rail below"),
        ("J2", "3-pin male header", "strip 15 row 5 + both rails below"),
        ("J3", "2-pin male header", "both rails under strip 4"),
        ("Q1", "IRLZ44N MOSFET", "strips 6, 7, 8 row 1, tab to the top"),
    ]
    y += 12
    for pid, part, where in rows:
        y += 25
        text(x, y, pid, 12.5, weight="800")
        text(x + 38, y, part, 12.5, weight="600")
        text(x + 215, y, where, 12, fill="var(--mut)")
    text(x, y + 22, "Solder in this order: low parts first, Q1 last.", 12, fill="var(--mut)")

    y += 62
    text(x, y, "What plugs in where", 17, weight="800")
    plugs = [
        ("J1 fan", "red wire on +, black wire on − (top pin)"),
        ("J2 light", "NeoPixel string: DIN top, 5V middle, GND bottom"),
        ("J3 motor power", "driver board + and − (5–12V pins)"),
        ("J4 motor pins", "driver board IN1, IN2, IN3, IN4"),
        ("slot", "camera ribbon goes through the slot"),
    ]
    for name, what in plugs:
        y += 25
        text(x, y, name, 12.5, weight="800")
        text(x + 120, y, what, 12.5, fill="var(--ink)")

    y += 46
    text(x, y, "Good to know", 17, weight="800")
    notes = [
        "Each lower strip is 5 holes joined from top to bottom.",
        "Strips are not joined to each other or to the rails.",
        "Holes in the same rail are all joined.",
        "Q1: printed side faces you when you look from the rails.",
        "Legs then go G, D, S from left to right.",
        "Upper rails (+3V3, GND) and upper strips are not used yet.",
    ]
    for n in notes:
        y += 22
        text(x, y, "• " + n, 12.5, fill="var(--ink)")


# ---------------- document ----------------
a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
  f'font-family="system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif">')
a("""<style>
svg{--bg:#f7f8f5;--card:#ffffff;--ink:#1d211b;--mut:#646b60;--line:#d6dbd0}
@media (prefers-color-scheme:dark){svg{--bg:#141713;--card:#1d211b;--ink:#e6eae2;--mut:#9aa293;--line:#3a4137}}
</style>""")
a(f'<rect width="{W}" height="{H}" fill="var(--bg)"/>')
text(40, 44, "Pollen sampler Proto HAT: where each part goes", 24, weight="800")
text(40, 68, "Top view, 40-pin header at the top. Every dot is a hole (2.54 mm apart). Steps: docs/hat.md", 13.5, fill="var(--mut)")
board()
parts()
panel()
a("</svg>")
Path(__file__).with_name("hat.svg").write_text("\n".join(out))
print("wrote hat.svg")
