# Two ZIF sockets for one DCJ11

U1 uses two 64-contact Textool 264-4493 ZIF sockets.
The footprint is `DCJRig:DCJ11_DIP60_2xTextool_264-4493_ZIF`.

## Insert the CPU

Use the **two inner rows**, which are 33.02 mm apart. The CPU takes the
middle 30 contacts in each row. Leave **one empty contact at both ends**.
The outer rows stay unused.

The sockets face opposite ways: the template shows one lever at the upper
left, the other at the lower right. Follow the board's square pad and pin 1
mark. Turn power off before changing CPUs.

## Dimensions

| Feature | Size |
|---|---:|
| Pin pitch | 2.54 mm |
| CPU row spacing | 33.02 mm |
| Row spacing within each socket | 22.86 mm |
| Distance between socket centers | 55.88 mm |
| Socket body | 100.6 × 33.0 mm |
| Drill diameter | 1.4 mm |
| Copper pad | 3.2 × 2.2 mm |
| Clear width between the socket placement outlines | 21.88 mm |
| Maximum component height under the CPU | 11 mm |

All 128 socket leads have plated holes. Pads 1–60 connect to the CPU.
The other 68 pads are unnumbered and have no electrical connection.
[pad-map.csv](pad-map.csv) lists each hole and its CPU pin, where used.
The long pads leave room for hand soldering.

The sockets used here have rectangular solder tails measuring 0.9 × 0.5 mm.
Their diagonal is 1.03 mm. The 1.4 mm holes allow for insertion clearance
and the [JLCPCB hole diameter tolerance](https://jlcpcb.com/capabilities/pcb-capabilities)
of +0.13/−0.08 mm. The nominal copper ring is at least 0.40 mm wide.

Body dimensions and pin spacing come from the
[3M socket drawing](../../datasheets/3M_Textool_264-4493_TS-0365.source.txt)
and [DEC package drawing](../../datasheets/DEC_DCJ11_Mechanical_Dimensions_1987_E4.source.txt).
Check the actual sockets against the [full-size template](assembly-1to1.pdf).
Print it at 100% and check its 50 mm scale with a ruler.

## Use the space under the CPU

Each socket has its own KiCad courtyard. Components can occupy the gap.

Keep the mounted height at or below **11 mm**, including sockets and spacers.
A 74F821 in a low DIP socket can fit: the
[3M example](../../datasheets/3M_DIP_Socket_4800_TS1099.source.txt) gives a
combined height of about 10.3 mm. Measure your own parts.

Set each component's `Height_mm` to its maximum assembled height. Run:

```sh
python3 mechanical/zif/check_height.py kicad/rig/rig.kicad_pcb
```

This needs KiCad 10's Python module. It checks `Height_mm` in
`DCJ11_UNDER_CPU_H11`; missing values and heights above 11 mm fail.
Only Y1 has a declared height. Measure the other nine parts.
It does not measure 3D models.

## Assembly and models

Fit low parts and DIP sockets before the large ZIF sockets. Solder the ZIF
sockets with their contacts **open**, as the
[3M catalog](../../datasheets/3M_Textool_Test_and_Burn-In_Socket_Catalog.source.txt)
instructs. Keep both bodies flat against the board while soldering.

Hide the CPU model in KiCad's 3D settings to see the parts underneath.
Lever bends and contact jaws are approximate.

To regenerate the footprint, models, pin map and SVG drawing:

```sh
python3 mechanical/zif/generate.py
```

The generator uses Python's standard library. It writes library files;
it does not update the placed footprint on the board. Re-export
[assembly-1to1.svg](assembly-1to1.svg) to PDF if you change the drawing.
