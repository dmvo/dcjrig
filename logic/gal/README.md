# ODT bridge

U6, a Lattice **GAL20V8A-15LP**, connects the DCJ11 bus to the DC319A DLART
and startup buffer. The source and build files use the [MIT license](LICENSE).

**The logic has not been tested on hardware.** The checks below verify
Boolean behavior and the programming file. They do not test electrical timing.

- [odt_bridge.pld](odt_bridge.pld) — equations and pin assignments.
- [odt_bridge.jed](odt_bridge.jed) — programming file, built with galette 0.3.0.
- [design.md](design.md) — requirements, derivation and proof.
- [check_bridge.py](check_bridge.py) — independent source and fuse checks.
- [prove_minimal.py](prove_minimal.py) — exact minimum-cover check.

Four working equations use five product terms and 17 literals: the proven
minimum for the full truth table in one GAL stage. Four constant assignments
hold unused outputs LOW. There are no registers or feedback paths.

## Build on Linux

You need Python 3, Make and [galette](https://github.com/simon-frankau/galette).
To install the compiler with Rust and Cargo:

```sh
cargo install --git https://github.com/simon-frankau/galette \
  --rev af529870729b1da8794b002cd522f5bf2d53f230 --locked
```

From the project root, run:

```sh
make -C logic/gal
```

This needs KiCad 10. It rebuilds `build/odt_bridge.jed`, checks it, and
compares it byte for byte with the supplied file. A fresh netlist checks
the schematic connections; ERC is not run. The logic check covers 16384
input combinations, varies the five grounded inputs, and proves the minimum.

Use `make -C logic/gal check` for the same logic checks without KiCad.

## Program with a T48

Use [minipro](https://gitlab.com/DavidGriffith/minipro) with T48 support
(version 0.7.4 is suitable). After the check above passes, run from the
project root with the **GAL20V8A-15LP** in the programmer:

```sh
minipro -p GAL20V8A -w logic/gal/odt_bridge.jed
```

Minipro verifies after writing. Both steps must succeed before fitting U6.
This verifies programming, not operation in the rig.

DEC calls this chip a **DLART**, a DL11-compatible asynchronous
receiver/transmitter. See DC319-AA, printed page 3-27, in the
[DEC document](../../datasheets/DC319-and-74F821-sources.txt).
