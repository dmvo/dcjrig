# Sources and credits

## Design inspiration

The circuit was inspired by Peter Schranz's
[Modular DCJ11 SBC](https://www.5volts.ch/pages/dcj11sbc/).
His hardware and GAL downloads credit **Peter Schranz / cbscpe** and
**Netzwerk & Design GmbH**. Those archives stay local.
[Reference links](references/README.md) point to his site and downloads.

## GAL logic

[ODT bridge](logic/gal/README.md) was written for this board using DEC and
Lattice specifications. Its source, programming file, scripts and explanation
use the [MIT license](logic/gal/LICENSE). The
[design notes](logic/gal/design.md) explain and prove the equations.

The logic has not been tested on real hardware.

## KiCad libraries

The design uses parts from the KiCad library contributors.
`DCJRig:SN74AHCT14N` adapts KiCad's `74xx:74HC14` symbol for the TI part.
Its name, description, keywords and datasheet link are different.

The KiCad parts and their adaptations keep **CC BY-SA 4.0 with the KiCad
design exception**. See the [upstream notice](licenses/KiCad-libraries-LICENSE.md),
[license text](https://creativecommons.org/licenses/by-sa/4.0/legalcode) and
[KiCad's explanation](https://www.kicad.org/libraries/license/).
The exception covers circuit designs. Library collections must keep the
license and credits. The source library is
[kicad-symbols](https://gitlab.com/kicad/libraries/kicad-symbols).

The CPU, UART, latch and GAL20V8A symbols were drawn for this project.
The custom socket and crystal parts have Python generators in `mechanical/`.

## Datasheets

We don't publish datasheets because we don't know what licenses cover them.
The [source notes](datasheets/README.md) give download links and page ranges.
[SHA256 checksums](datasheets/SHA256SUMS.txt) identify our copies.
Re-exporting an excerpt can change its hash without changing its contents.
The socket assembly PDF under `mechanical/` is our own drawing.

## Reusing project files

You may copy and adapt [AGENTS.md](AGENTS.md) for your own projects.
The files in `logic/gal/` use MIT. No license has been chosen for the other
original project files.
The third-party licenses above still apply to their respective parts.
