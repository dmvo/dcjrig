# ODT bridge

The GAL16V8 at U6 connects the DCJ11 bus to the DC319A DLART and the
startup buffer. This directory contains everything needed to build and
program it, under the [MIT license](LICENSE).

**The logic has not been tested on real hardware.** The checks below prove
its Boolean behavior and check the programming file. They do not test
electrical timing or a working board.

- [odt_bridge.pld](odt_bridge.pld) — equations and pin assignments.
- [odt_bridge.jed](odt_bridge.jed) — programming file, built with galette 0.3.0.
- [design.md](design.md) — requirements, derivation and proof.
- [check_bridge.py](check_bridge.py) — independent source and fuse checks.

## Build on Linux

You need Python 3, Make and [galette](https://github.com/simon-frankau/galette).
To install the compiler with Rust and Cargo:

```sh
cargo install --git https://github.com/simon-frankau/galette \
  --rev af529870729b1da8794b002cd522f5bf2d53f230 --locked
```

From the project root, run:

```sh
make -C logic/gal check
```

This rebuilds `build/odt_bridge.jed`, checks it and the supplied file, then
compares them byte for byte. Each check covers all 512 board input
combinations. It also varies the tied input to prove the logic ignores it.

With KiCad 10 installed, also check the pin assignments against the saved
schematic:

```sh
make -C logic/gal check-wiring
```

This exports a netlist. It does not run ERC or change the schematic.

## Program with a T48

Use [minipro](https://gitlab.com/DavidGriffith/minipro) with T48 support
(version 0.7.4 is suitable). Select the device by the marking on your chip.
For a **GAL16V8D**, run from the project root:

```sh
python3 logic/gal/check_bridge.py
minipro -p GAL16V8D -w logic/gal/odt_bridge.jed
```

Minipro verifies after writing. Check that both steps succeed before
fitting U6. Programming verification does not mean the logic has been
tested in the rig.

DEC calls the serial chip a **DLART**: a DL11-compatible asynchronous
receiver/transmitter. The [DEC document](../../datasheets/DC319-and-74F821-sources.txt)
uses the full part name DC319-AA, on printed page 3-27.
