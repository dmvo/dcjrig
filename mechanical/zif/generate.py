#!/usr/bin/env python3
"""Generate the DCJ11 / two Textool 264-4493 assembly. Standard library only.

Dimensions: 3M drawing 3U-0010-0999-3 rev E; DEC 1987 databook fig E.4.
PCB and model coordinates share one source. Model details not dimensioned by
3M (screws, moulding, contact jaws, handle shape) are visual approximations.
"""
from pathlib import Path
from collections import defaultdict
import csv
import math

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LIB = ROOT / 'kicad/rig/DCJRig.pretty'
MODELS = ROOT / 'kicad/rig/DCJRig.3dshapes'
NAME = 'DCJ11_DIP60_2xTextool_264-4493_ZIF'
PITCH = 2.54
CPU_ROW = 33.02
SOCKET_ROW = 22.86
CX = (CPU_ROW + SOCKET_ROW) / 2  # 27.94; socket centres at +/-CX
HALF_SPAN = 31 * PITCH / 2
YMIN = -HALF_SPAN - 12.8       # lever end, special 64-contact dimension
YMAX = YMIN + 100.6            # Socket body length from 3M revision E.
WIDTH = 33.0
TOP = 11.9
DRILL = 1.1
PAD_X = 3.2  # Extra soldering land across the rows, preserving the 2.54 mm pitch.
PAD_Y = 1.9


def sockets():
    # Second identical physical socket is rotated 180 degrees, NOT mirrored.
    return [('L', -CX, 1), ('R', CX, -1)]


def contact_table():
    out = []
    for side, cx, direction in sockets():
        for row in [-1, 1]:
            for i in range(32):
                x = cx + direction * row * SOCKET_ROW / 2
                y = direction * (-HALF_SPAN + i * PITCH)
                number = ''
                if row == 1 and 1 <= i <= 30:
                    number = str(i if side == 'L' else 30 + i)
                # Row and station are local to the socket, counted from lever.
                out.append((side, 'inner' if row == 1 else 'outer', i + 1,
                            x, y, number))
    return out


CONTACTS = contact_table()


def footprint():
    lines = [f'(footprint "{NAME}"', '  (version 20241229)',
             '  (generator "dcjrig_zif_generator")', '  (layer "F.Cu")',
             '  (descr "DCJ11 60-pin 33.02mm rows in inner rows of two Textool 264-4493 ZIF sockets. Long pads 3.2x1.9mm, drill 1.1mm. 128 holes, 60 CPU pads, 68 isolated unnumbered pads. See mechanical/zif/README.md.")',
             '  (tags "DEC DCJ11 DIP60 1300mil ZIF Textool 264-4493")',
             '  (attr through_hole)',
             '  (property "Reference" "REF**" (at 0 -43) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.2))))',
             f'  (property "Value" "{NAME}" (at 0 68) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))']

    def line(a, b, layer='F.SilkS', width=0.15):
        lines.append(f'  (fp_line (start {a[0]:.4f} {a[1]:.4f}) (end {b[0]:.4f} {b[1]:.4f}) (stroke (width {width}) (type solid)) (layer "{layer}"))')

    def rect(x0, y0, x1, y1, layer='F.Fab', width=0.1):
        lines.append(f'  (fp_rect (start {x0:.4f} {y0:.4f}) (end {x1:.4f} {y1:.4f}) (stroke (width {width}) (type solid)) (fill none) (layer "{layer}"))')

    def txt(s, x, y, size=1, layer='F.SilkS'):
        lines.append(f'  (fp_text user "{s}" (at {x:.4f} {y:.4f}) (layer "{layer}") (effects (font (size {size} {size}) (thickness 0.15))))')

    for side, cx, d in sockets():
        ya, yb = sorted([d * YMIN, d * YMAX])
        rect(cx - WIDTH/2, ya, cx + WIDTH/2, yb)
        rect(cx - WIDTH/2 - .15, ya - .15, cx + WIDTH/2 + .15, yb + .15, 'F.SilkS', .15)
        # Closed lever is on the outside of the assembly. Its operating space
        # is included in the courtyard; the central space remains free of it.
        lx = cx - d * 15.8
        pivot = d * (-HALF_SPAN - 2.67)
        tip = d * (YMIN - 12.2)
        line((lx, pivot), (lx, tip + d * 3), 'F.Fab', 1.2)
        rect(lx-2.4, min(tip, tip+d*6), lx+2.4, max(tip, tip+d*6))
        rect(lx-2.65, min(pivot, tip)-.15, lx+2.65, max(pivot, tip)+.15, 'F.SilkS', .15)
        txt('TEXTOOL 264-4493', cx, d * (YMAX - 3), .9, 'F.Fab')
        txt('EMPTY', cx - d * SOCKET_ROW / 2, -d * 43.2, .85)
        txt(side, cx, 0, 2, 'F.Fab')

    # Two separate courtyards reserve only the sockets and their levers.
    # The suspended CPU does NOT occupy the PCB plane in the central gap.
    # Physical gap 22.88 mm; 21.88 mm remains after the two 0.5 mm margins.
    left_outline = [(-44.94,-52.67),(-47.14,-52.67),(-47.14,-65.37),
                    (-40.34,-65.37),(-40.34,-52.67),(-10.94,-52.67),
                    (-10.94,48.93),(-44.94,48.93)]
    for d in (1,-1):
        outline = [(d*x,d*y) for x,y in left_outline]
        for a,b in zip(outline, outline[1:] + outline[:1]):
            line(a,b,'F.CrtYd',.05)

    # Processor outline is on fabrication, leaving its central gap readable.
    rect(-1.288*25.4/2, -38.1, 1.288*25.4/2, 38.1)
    # Keep the freed component-placement area clear of silkscreen lettering.
    txt('DCJ11', 0, -3, 2, 'F.Fab')
    rect(-10.94, -39, 10.94, 39, 'Dwgs.User', .1)
    txt('UNDER CPU: H <= 11 mm', 0, -41, .9, 'Dwgs.User')
    txt('PIN 1', -10.6, -36.83, .9)
    txt('60', 12.6, -36.83, .9)
    txt('30', -12.6, 36.83, .9)
    txt('31', 12.6, 36.83, .9)
    txt('1 EMPTY AT EACH END', 0, 44, .9, 'F.Fab')
    # Permanent index triangle, visible in the open centre of the socket pair.
    for a,b in [((-13.55,-37.53),(-14.35,-36.83)),
                ((-14.35,-36.83),(-13.55,-36.13)),
                ((-13.55,-36.13),(-13.55,-37.53))]:
        line(a,b)

    for _,_,_,x,y,n in CONTACTS:
        shape = 'rect' if n == '1' else 'oval'
        lines.append(f'  (pad "{n}" thru_hole {shape} (at {x:.4f} {y:.4f}) (size {PAD_X} {PAD_Y}) (drill {DRILL}) (layers "*.Cu" "*.Mask") (remove_unused_layers no))')
    # A non-blocking named area follows the footprint when moved/rotated.
    # Used by check_height.py. It does not forbid components, pads or routing.
    lines.append('''  (zone (net 0) (net_name "") (layer "F.Cu")
    (name "DCJ11_UNDER_CPU_H11") (hatch edge 0.5)
    (connect_pads (clearance 0)) (min_thickness 0.25)
    (keepout (tracks allowed) (vias allowed) (pads allowed)
             (copperpour allowed) (footprints allowed))
    (fill (thermal_gap 0.3) (thermal_bridge_width 0.3))
    (polygon (pts (xy -11.44 -39) (xy 11.44 -39)
                  (xy 11.44 39) (xy -11.44 39))))''')
    for filename in [NAME, 'DCJ11_seated_in_Textool']:
        lines.append(f'  (model "${{KIPRJMOD}}/DCJRig.3dshapes/{filename}.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
    lines.append(')')
    (LIB / (NAME + '.kicad_mod')).write_text('\n'.join(lines) + '\n')


COLORS = {'body': (.075,.35,.32), 'base': (.055,.25,.23),
          'dark': (.03,.11,.10), 'gold': (.72,.53,.20),
          'metal': (.62,.65,.67), 'ceramic': (.88,.87,.78),
          'lid': (.65,.50,.21), 'ink': (.11,.12,.11)}


class Mesh:
    def __init__(self):
        self.parts = defaultdict(lambda: [[],[]])

    def poly(self, points, faces, material):
        verts, idx = self.parts[material]
        start = len(verts)
        verts.extend(points)
        idx.extend([[start+i for i in f] for f in faces])

    def box(self, x0,y0,z0,x1,y1,z1,material):
        self.poly([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
                   (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],
                  [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],material)

    def extrude(self, outline, z0,z1, material):
        # Convex outlines only; bottom/top triangulate as a fan.
        n=len(outline)
        pts=[(x,y,z) for z in (z0,z1) for x,y in outline]
        faces=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        faces += [(0,i+1,i) for i in range(1,n-1)]
        faces += [(n,n+i,n+i+1) for i in range(1,n-1)]
        self.poly(pts,faces,material)

    def rounded(self,x0,y0,x1,y1,z0,z1,r,material):
        p=[]
        for cx,cy,a in [(x1-r,y1-r,0),(x0+r,y1-r,90),
                        (x0+r,y0+r,180),(x1-r,y0+r,270)]:
            for i in range(7):
                t=math.radians(a+i*15)
                p.append((cx+r*math.cos(t),cy+r*math.sin(t)))
        self.extrude(p,z0,z1,material)

    def cylinder(self,x,y,z,r,h,material,axis='z',segments=24):
        p=[]
        for dz in (0,h):
            for i in range(segments):
                a=2*math.pi*i/segments
                v=(r*math.cos(a),r*math.sin(a),dz)
                if axis=='y': v=(v[0],v[2],v[1])
                p.append((x+v[0],y+v[1],z+v[2]))
        n=segments
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        self.poly(p,faces,material)

    def transform_append(self,other,cx,d):
        for mat,(pts,faces) in other.parts.items():
            self.poly([(cx+d*x,d*y,z) for x,y,z in pts],faces,mat)

    def save(self,path):
        # KiCad VRML units are 0.1 inch. PCB Y points down; model Y points up.
        s=['#VRML V2.0 utf8', '# Generated by mechanical/zif/generate.py',
           '# Coordinates in 0.1 inch units; scale 1 in KiCad.']
        for mat,(pts,faces) in self.parts.items():
            rgb=' '.join(str(v) for v in COLORS[mat])
            shine=.6 if mat in ('gold','metal','lid') else .15
            s.append(f'Shape {{ appearance Appearance {{ material Material {{ diffuseColor {rgb} specularColor 0.3 0.3 0.3 shininess {shine} }} }}')
            s.append('geometry IndexedFaceSet { solid FALSE creaseAngle 0.6 coord Coordinate { point [')
            s.extend(f'{x/2.54:.6f} {-y/2.54:.6f} {z/2.54:.6f},' for x,y,z in pts)
            s.append('] } coordIndex [')
            # Y reflection reverses winding.
            s.extend(','.join(map(str,reversed(f)))+',-1,' for f in faces)
            s.append('] } }')
        path.write_text('\n'.join(s)+'\n')


# Simple native geometry lettering; no font/model downloads required.
FONT = {
 'T':['11111','00100','00100','00100','00100','00100','00100'],
 'E':['11111','10000','10000','11110','10000','10000','11111'],
 'X':['10001','10001','01010','00100','01010','10001','10001'],
 'O':['01110','10001','10001','10001','10001','10001','01110'],
 'L':['10000','10000','10000','10000','10000','10000','11111'],
 'D':['11110','10001','10001','10001','10001','10001','11110'],
 'C':['01111','10000','10000','10000','10000','10000','01111'],
 'J':['00111','00010','00010','00010','00010','10010','01100'],
 '1':['00100','01100','00100','00100','00100','00100','01110'],
 '2':['01110','10001','00001','00010','00100','01000','11111'],
 '3':['11110','00001','00001','01110','00001','00001','11110'],
 '4':['00010','00110','01010','10010','11111','00010','00010'],
 '6':['01110','10000','10000','11110','10001','10001','01110'],
 '9':['01110','10001','10001','01111','00001','00001','01110'],
 '-':['00000','00000','00000','11111','00000','00000','00000'],
}


def text_mesh(m,text,x,y,z,size,mat):
    pix=size/7
    x-=len(text)*6*pix/2
    for k,c in enumerate(text):
        for r,row in enumerate(FONT[c]):
            for col,v in enumerate(row):
                if v=='1':
                    xx=x+(k*6+col)*pix
                    yy=y+r*pix-size/2
                    m.box(xx,yy,z,xx+pix*.92,yy+pix*.92,z+.025,mat)


def socket_mesh():
    m=Mesh()
    # Underside, seam and lower contact carrier.
    m.rounded(-16.5,YMIN,16.5,YMAX,.51,7.8,1,'base')
    m.rounded(-16.35,YMIN+.1,16.35,YMAX-.1,7.8,8.1,.9,'dark')
    m.rounded(-16.5,YMIN,16.5,YMAX,8.1,8.7,1,'body')
    for x in (-13.5,13.5):
        for y in (YMIN+3,YMAX-3):
            m.cylinder(x,y,0,1.5,.55,'body')
    # Top plate, with 64 genuinely recessed rectangular contact windows.
    slot_half=3.0
    end=HALF_SPAN+1.05
    for a,b in [(-16.5,-11.43-slot_half),(-11.43+slot_half,11.43-slot_half),(11.43+slot_half,16.5)]:
        m.box(a,YMIN,8.7,b,YMAX,TOP,'body')
    for x in (-11.43,11.43):
        m.box(x-slot_half,YMIN,8.7,x+slot_half,-end,TOP,'body')
        m.box(x-slot_half,end,8.7,x+slot_half,YMAX,TOP,'body')
        for i in range(32):
            y=-HALF_SPAN+i*PITCH
            m.box(x-.38,y-.15,-2.8,x+.38,y+.15,9.1,'gold')
            m.box(x-2.8,y-.72,8.72,x+2.8,y+.72,8.82,'dark')
            # Pair of contact jaws below the insertion aperture.
            m.box(x-2.5,y-.63,8.85,x+2.5,y-.33,9.22,'gold')
            m.box(x-2.5,y+.33,8.85,x+2.5,y+.63,9.22,'gold')
            if i<31:
                m.box(x-slot_half,y+1.05,8.7,x+slot_half,y+PITCH-1.05,TOP,'body')
    # Seven screw heads match the photographed vintage moulding; decorative.
    for x,y in [(x,y) for y in (YMIN+3.6,YMAX-3.6) for x in (-13.7,0,13.7)]+[(0,0)]:
        m.cylinder(x,y,TOP,1.05,.13,'metal')
        m.box(x-.7,y-.16,TOP+.13,x+.7,y+.16,TOP+.15,'dark')
        m.box(x-.16,y-.7,TOP+.13,x+.16,y+.7,TOP+.15,'dark')
    # Lever closed, facing away from the CPU. The grip envelope follows the
    # manufacturer's 12.2 mm extension; bends/knob contour are illustrative.
    lx=-15.8
    py=-HALF_SPAN-2.67
    tip=YMIN-12.2
    m.cylinder(lx,py,6.0,.7,3.5,'metal')
    m.cylinder(lx,tip+4.5,9.5,.7,py-tip-4.5,'metal',axis='y')
    m.rounded(lx-2.35,tip,lx+2.35,tip+6,7.3,11.7,1.8,'body')
    text_mesh(m,'TEXTOOL',0,-7,TOP+.02,1.8,'base')
    text_mesh(m,'264-4493',0,7,TOP+.02,1.6,'base')
    return m


def cpu_mesh():
    m=Mesh()
    bottom=TOP+.1
    ceramic_top=bottom+1.78
    # Body dimensions from DEC; lid and leg shapes approximate the drawing.
    m.box(-16.3576,-38.1,bottom,16.3576,38.1,ceramic_top,'ceramic')
    for y in (-19.05,19.05):
        m.box(-12.2,y-12.1,ceramic_top,12.2,y+12.1,bottom+5.1,'lid')
    for side in (-1,1):
        for i in range(30):
            y=-36.83+i*2.54
            x=side*16.51
            m.box(x-.127,y-.2286,bottom-4.445,x+.127,y+.2286,bottom+.6,'gold')
    text_mesh(m,'DCJ11',0,0,ceramic_top+.02,2.4,'ink')
    m.cylinder(-14.1,-35.5,ceramic_top,.7,.03,'ink')
    return m


def svg():
    # A4, with the hole pattern at actual millimetre scale. Do not fit-to-page.
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">',
       '<rect width="210" height="297" fill="white"/>',
       '<g font-family="sans-serif" fill="#172b30">',
       '<text x="20" y="18" font-size="5">DCJ11 / 2 x TEXTOOL 264-4493</text>',
       '<text x="20" y="25" font-size="3">1:1 assembly and hole template - print at 100%, no fit to page</text>',
       '<g transform="translate(105 112)">']
    for side,cx,d in sockets():
        ya,yb=sorted([d*YMIN,d*YMAX])
        s.append(f'<rect x="{cx-16.5}" y="{ya}" width="33" height="{yb-ya}" rx="1" fill="#d9ede7" stroke="#41685c" stroke-width=".3"/>')
        lx=cx-d*15.8
        s.append(f'<path d="M {lx} {d*(-HALF_SPAN-2.67)} V {d*(YMIN-12.2)}" stroke="#41685c" stroke-width="1.5"/>')
    s.append('<rect x="-16.3576" y="-38.1" width="32.7152" height="76.2" fill="#eee9ce" fill-opacity=".65" stroke="#8b7136" stroke-width=".3"/>')
    s.append('<rect x="-10.94" y="-39" width="21.88" height="78" fill="#9fdccd" fill-opacity=".35" stroke="#207962" stroke-width=".25" stroke-dasharray="1,1"/>')
    for _,_,_,x,y,n in CONTACTS:
        color='#b24a24' if n else '#68767a'
        radius = 0 if n == '1' else PAD_Y / 2
        s.append(f'<rect x="{x-PAD_X/2:.4f}" y="{y-PAD_Y/2:.4f}" width="{PAD_X}" height="{PAD_Y}" rx="{radius}" fill="{color}"/>')
        s.append(f'<circle cx="{x}" cy="{y}" r="{DRILL/2}" fill="white"/>')
        if n:
            tx=x+(2 if x<0 else -2)
            anchor='start' if x<0 else 'end'
            s.append(f'<text x="{tx}" y="{y+.5}" text-anchor="{anchor}" font-size="1.7">{n}</text>')
    s.append('<text x="0" y="0" text-anchor="middle" font-size="4">DCJ11</text>')
    s.append('<text x="0" y="6" text-anchor="middle" font-size="2.2">FREE WIDTH 21.88 mm</text>')
    s.append('<text x="0" y="10" text-anchor="middle" font-size="2.2">HEIGHT MAX 11 mm</text>')
    s.append('</g>')
    for i,t in enumerate(['128 plated holes, drill 1.1 mm; pads 3.2 x 1.9 mm; pitch 2.54 mm.',
                           '60 numbered pads = CPU pins. 68 blank pads = unused socket pins.',
                           'CPU uses contacts 2-31 of each INNER row (one empty at each end).',
                           'Left lever at top left; right lever at bottom right. Do not mirror.',
                           'Socket body length: 100.6 mm (3M revision E).',
                           'Compare with the physical sockets before ordering the board.']):
        s.append(f'<text x="20" y="{193+6*i}" font-size="3">{t}</text>')
    s += ['<path d="M 20 247 v -4 M 20 245 h 50 M 70 247 v -4" stroke="#172b30" stroke-width=".3"/>',
          '<text x="20" y="254" font-size="3">50 mm print scale check</text>', '</g></svg>']
    (HERE/'assembly-1to1.svg').write_text('\n'.join(s)+'\n')


def main():
    LIB.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)
    assert len(CONTACTS)==128
    assert sorted(int(p[5]) for p in CONTACTS if p[5])==list(range(1,61))
    assert sum(not p[5] for p in CONTACTS)==68
    footprint()
    m=Mesh()
    one=socket_mesh()
    for _,cx,d in sockets(): m.transform_append(one,cx,d)
    m.save(MODELS/(NAME+'.wrl'))
    cpu_mesh().save(MODELS/'DCJ11_seated_in_Textool.wrl')
    with (HERE/'pad-map.csv').open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['socket','row','station_from_lever','x_mm','y_mm','cpu_pin'])
        for side,row,station,x,y,n in CONTACTS:
            w.writerow([side,row,station,f'{x:.4f}',f'{y:.4f}',n])
    svg()
    print(f'Generated {NAME}: 128 holes, CPU pins 1-60, 68 unnumbered pads.')


if __name__=='__main__': main()
