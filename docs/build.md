# Build guide

## What the board does

The rig uses the DCJ11-AE's built-in ODT console to check CPU startup and
response. It does not test every CPU function.

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

Open `kicad/rig/rig.kicad_pro` in KiCad 10. Install KiCad's standard libraries;
custom parts and 3D models are included.

Run `bash docs/render.sh` to recreate the README render. See the
[hardware check](assembly.md) for ODT results and assembly photos.

## Fit the processor

Disconnect power before changing CPUs. Follow the board's pin 1 mark.
Use the middle 30 contacts in each **inner row** of the Textool
264-4493 sockets, leaving one contact empty at each end.

Parts under the CPU must be **no more than 11 mm above the PCB**, including
sockets and gaps. Measure the assembled height of U4 and U5.

See the [socket dimensions and template](../mechanical/zif/README.md) and
[HC-49S crystal guide](../mechanical/crystal_hc49s/README.md).

## Connect power and a terminal

Use regulated **5 V**: J3 pin 1 is positive, pin 2 is ground. The J3 footprint
does not fit the jack used in this build; that jack connects by wires.
Verify polarity. SW2 switches power; SW1 resets. J2 carries no power.

Use a USB-to-TTL adapter compatible with 5 V DC319 signals:

| Rig connector | Adapter |
|---|---|
| J2 pin 1 — GND | GND |
| J2 pin 4 — RX | TX |
| J2 pin 5 — TX | RX |

Leave J2 pins 2, 3 and 6 unconnected. This is a TTL interface; do not connect
an RS-232 port directly.

For **38400 baud, 8N1, no flow control**, close all three J1 pairs:
**1–2, 3–4 and 5–6**. Startup settings are wired for ODT entry.

## GAL programming

Program U6 before fitting it. The [GAL guide](../logic/gal/README.md) includes
the source, programming file and Linux instructions for galette and minipro.

## Before trusting a result

**The assembled rig starts ODT and reads back CPU register writes.** See the
[console check](assembly.md) and [component checks](../tests/components/README.md).
Five DCJ11 CPUs passed the [ODT test suite](../tests/odt/README.md).
A silent console alone is not enough to reject a CPU.

For a power-only check without a CPU, remove U2–U6 with power disconnected.
Otherwise /ALE, /SCTL and /BUFCTL leave CMOS inputs undriven. Check the 5 V
rail before fitting the chips. Then check ODT with a known-good CPU if available.

DV receives inverted /SCTL for late data capture. See the
[timing assumptions and margins](../logic/gal/design.md#timing-assumptions).
Measure the clock and DV edge on the board. Test point labels are on the back.
