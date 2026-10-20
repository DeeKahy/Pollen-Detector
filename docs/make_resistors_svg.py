"""Generates docs/resistors.svg: colour bands for the resistors used in this project."""
from pathlib import Path
COL = {"black":"#111","brown":"#7b3f12","red":"#d0201a","orange":"#f07a10","yellow":"#f5d000",
       "gold":"#c9a227","green":"#1f9a3a","blue":"#1f5fd0","violet":"#7b3fb0","grey":"#888","white":"#f4f4f4"}
ROWS = [  # value, where used, 4-band, 5-band
 ("220 Ω", "fan: GPIO pin to MOSFET", ["red","red","brown","gold"], ["red","red","black","black","brown"]),
 ("100 kΩ", "fan: MOSFET to GND", ["brown","black","yellow","gold"], ["brown","black","black","orange","brown"]),
 ("47 Ω", "white LED", ["yellow","violet","black","gold"], ["yellow","violet","black","gold","brown"]),
 ("150 Ω", "red or green LED instead", ["brown","green","brown","gold"], ["brown","green","black","black","brown"]),
]
W, H = 1000, 140 + 130*len(ROWS) + 120
o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
'<style>svg{--bg:#f7f8f5;--ink:#1d211b;--mut:#646b60;--line:#d6dbd0;--lead:#9a9a9a}@media (prefers-color-scheme:dark){svg{--bg:#141713;--ink:#e6eae2;--mut:#9aa293;--line:#3a4137;--lead:#777}}</style>',
f'<rect width="{W}" height="{H}" fill="var(--bg)"/>']
def t(x,y,s,size=14,w="normal",fill="var(--ink)",a="start"):
    o.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{a}">{s}</text>')
def res(x,y,bands,body):
    o.append(f'<line x1="{x-40}" y1="{y}" x2="{x+220}" y2="{y}" stroke="var(--lead)" stroke-width="4"/>')
    o.append(f'<rect x="{x}" y="{y-20}" width="180" height="40" rx="18" fill="{body}" stroke="#0004"/>')
    n=len(bands); xs=[x+30+i*24 for i in range(n-1)]+[x+150]
    for bx,b in zip(xs,bands):
        o.append(f'<rect x="{bx-6}" y="{y-20}" width="12" height="40" fill="{COL[b]}" stroke="#0003"/>')
    names=" · ".join(bands); t(x+90,y+42,names,12,fill="var(--mut)",a="middle")
t(30,42,"Resistor colours for the pollen build",24,"700")
t(30,68,"Start reading at the end where the bands are close together. The band on its own at the other end doesn't matter here.",13.5,fill="var(--mut)")
t(320,112,"4 bands (usually beige)",14,"700"); t(640,112,"5 bands (usually blue)",14,"700")
for i,(v,use,b4,b5) in enumerate(ROWS):
    y=170+i*130
    o.append(f'<line x1="30" y1="{y-55}" x2="{W-30}" y2="{y-55}" stroke="var(--line)"/>')
    t(30,y-4,v,26,"700"); t(30,y+20,use,13,fill="var(--mut)")
    res(340,y,b4,"#e6cf9e"); res(660,y,b5,"#7fb4e0")
y=170+len(ROWS)*130-40
o.append(f'<line x1="30" y1="{y}" x2="{W-30}" y2="{y}" stroke="var(--line)"/>')
t(30,y+30,"Easiest check: measure it with a multimeter on the Ω setting before you put it in.",14,"600")
t(30,y+54,"Don't mix up the 220 Ω and the 100 kΩ. If they swap places, the fan never turns on.",14)
t(30,y+78,"Resistors work either way round.",14,fill="var(--mut)")
o.append('</svg>')
Path(__file__).with_name("resistors.svg").write_text("\n".join(o)); print("ok")
