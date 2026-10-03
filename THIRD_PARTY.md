# Sources and credits

## Design inspiration

The circuit was inspired by Peter Schranz's
[Modular DCJ11 SBC](https://www.5volts.ch/pages/dcj11sbc/).
His hardware and GAL downloads credit **Peter Schranz / cbscpe** and
**Netzwerk & Design GmbH**. Those archives stay local.
[Reference links](references/README.md) point to his site and downloads.

## GAL logic

[ODT bridge](logic/gal/README.md) is written for this board from its wiring
and the DEC and Lattice device specifications. Its source, programming file,
build scripts and explanation are included under the
[MIT license](logic/gal/LICENSE). The [design notes](logic/gal/design.md)
show how the equations follow from those specifications.

The logic has not been tested on real hardware.

## KiCad libraries

The design uses parts from the KiCad library contributors.
`DCJRig:SN74AHCT14N` adapts KiCad's `74xx:74HC14` symbol for the stocked TI part.
Its name, description, keywords and datasheet link are different.

The KiCad parts and their adaptations keep **CC BY-SA 4.0 with the KiCad
design exception**. See the [upstream notice](licenses/KiCad-libraries-LICENSE.md),
[license text](https://creativecommons.org/licenses/by-sa/4.0/legalcode) and
[KiCad's explanation](https://www.kicad.org/libraries/license/).
The exception covers use in circuit designs; sharing library collections has
separate requirements. The source library is
[kicad-symbols](https://gitlab.com/kicad/libraries/kicad-symbols).

The CPU, UART and latch symbols were drawn for this project. So were the
socket and crystal footprints and their 3D models. Their Python generators
are included under `mechanical/`.

## Datasheets

We don't publish datasheets because we don't know what licenses cover them.
We provide [download links](datasheets/README.md) and
[SHA256 checksums](datasheets/SHA256SUMS.txt) so you can get the documents
we use and check that you have the same copies.
The socket assembly PDF under `mechanical/` is our own drawing.

## Reusing project files

You may copy and adapt [AGENTS.md](AGENTS.md) for your own projects.
The files in `logic/gal/` use MIT. No license has been chosen for the other
original project files.
The third-party licenses above still apply to their respective parts.
