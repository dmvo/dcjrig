# Build guide

## What the board does

The rig lets a DEC DCJ11-AE processor talk to a serial terminal through its
built-in ODT console. This gives you a quick way to check whether the CPU
starts and responds. It does not test every CPU function.

| Part | Job |
|---|---|
| U1 — DCJ11-AE | Processor under test |
| U2 — DC319A DLART | Serial interface |
| U3 — SN74AHCT14N | Reset and clock-signal inversion |
| U4 — 74F821SPC | Holds address and control bits during a bus cycle |
| U5 — 74AHCT541 | Supplies the startup settings for ODT |
| U6 — GAL16V8 | Selects the UART and controls bus transfers |
| Y1 — 4 MHz HC-49S crystal | CPU clock |
| Y2 — VF154, 614.4 kHz | UART clock |

The board is 160 × 100 mm, with four copper layers and a 1.6 mm thickness.
The outer layers carry signals. The inner layers carry ground and 5 V.

## Open the design

Open `kicad/rig/rig.kicad_pro` in KiCad 10. The project includes its custom
symbols, footprints and 3D models. Install KiCad's standard libraries too.

The picture in the main README is a render of this board in KiCad. Some
library models show empty IC sockets, and the slide switch has no model.
Run `bash docs/render.sh` to make the picture again.

## Fit the processor

The two Textool 264-4493 sockets hold the CPU in their **inner rows**.
Use the middle 30 contacts of each row. Leave one contact empty at each end.
Follow the board's pin 1 mark. Turn power off before inserting or removing
the processor.

Parts under the CPU must be **no more than 11 mm above the PCB**. Include
sockets and any gap below the component in that measurement. Check the
assembled height of U4 and U5 before inserting the CPU.

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

U6 needs a programmed GAL. The [GAL guide](../logic/gal/README.md) includes
the source, a programming file and instructions for galette and minipro
on Linux. The logic has not been tested on real hardware.

## Before relying on a result

The design has not yet been tested on a built board. First check the rig
with a known-good CPU. A silent console alone is not enough to reject a CPU.
A useful quick test includes both the ODT prompt and a response to a command.

Two timing details still need checking on the hardware: startup data must
stay valid long enough after its buffer turns off, and the CPU's data-valid
input is held HIGH. The render also cannot confirm real component heights.
