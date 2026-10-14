# Build guide

## What the board does

The rig uses the DCJ11-AE's built-in ODT console to check that the CPU
starts and responds. It does not test every CPU function.

| Part | Job |
|---|---|
| U1 — DCJ11-AE | Processor under test |
| U2 — DC319A DLART | Serial interface |
| U3 — SN74AHCT14N | Reset, latch clock and late data capture |
| U4 — 74F821SPC | Holds address and control bits during a bus cycle |
| U5 — SN74AHCT541N | Supplies the startup settings for ODT |
| U6 — GAL20V8A-15LP | Selects the UART and controls bus transfers |
| Y1 — 4 MHz HC-49S crystal | CPU clock |
| Y2 — VF154, 614.4 kHz | UART clock |

## PCB files and KiCad

The [JLCPCB package](../dcjrig-jlcpcb-3ac8660.zip) contains Gerbers and drill
files. Order **4-layer FR-4, 160 × 100 mm, 1.6 mm, 1 oz copper on all layers**.
Layer order: front signals, 5 V, ground, back signals.

Open `kicad/rig/rig.kicad_pro` in KiCad 10. The project includes its custom
symbols, footprints and 3D models. Install KiCad's standard libraries too.

Run `bash docs/render.sh` to recreate the README picture. Some models show
empty IC sockets; the slide switch has no model.

## Fit the processor

Turn power off before inserting or removing the CPU. Follow the board's
pin 1 mark. Use the middle 30 contacts in each **inner row** of the Textool
264-4493 sockets, leaving one contact empty at each end.

Parts under the CPU must be **no more than 11 mm above the PCB**, including
sockets and gaps. Measure the assembled height of U4 and U5.

The [socket guide](../mechanical/zif/README.md) has dimensions, a printable
template and a height checker. The [crystal guide](../mechanical/crystal_hc49s/README.md)
describes the low HC-49S case.

## Connect power and a terminal

Use an external, regulated **5 V** supply at J3. Its center contact is positive.
SW2 switches power; SW1 resets the rig. J2 carries serial signals, not power.

Use a USB-to-TTL serial adapter with levels suitable for the 5 V DC319.
Connect these three pins:

| Rig connector | Adapter |
|---|---|
| J2 pin 1 — GND | GND |
| J2 pin 4 — RX | TX |
| J2 pin 5 — TX | RX |

Leave J2 pins 2, 3 and 6 unconnected. This is a TTL interface; do not connect
an RS-232 port directly.

For **9600 baud, 8N1**, close J1 pairs **1–2 and 5–6**. Leave 3–4 open.
The startup settings are wired for ODT entry.

## GAL programming

Program U6 before fitting it. The [GAL guide](../logic/gal/README.md) includes
the source, programming file and Linux instructions for galette and minipro.

## Before relying on a result

**The board and GAL logic have not been tested on hardware.** First check
the rig with a known-good CPU. Look for the ODT prompt and a response to a
command. A silent console alone is not enough to reject a CPU.

The CPU's DV input receives an inverted /SCTL pulse for late data capture.
The [timing notes](../logic/gal/design.md#timing-assumptions) give the
calculated margins and assumptions. Measure the clock and DV edge on the
built board. Test point labels are on the back. The render cannot confirm
real component heights.
