# Component checks

These T48 tests of individual chips were recorded on 25 October 2026.
The assembled rig has since passed an [ODT register check](../../docs/assembly.md)
and the [ODT test suite](../odt/README.md).
The component tests do not measure bus timing.

| Chip | Coverage | Result |
|---|---|---|
| GAL20V8A | All 16384 input combinations, eight outputs; 2706 fuse bits read back | Passed |
| 74F821SPC | All 1024 words; capture, hold and output enable; 11268 vectors | Passed |
| SN74AHCT14N | All 64 input combinations in both orders; 128 vectors | Passed |
| SN74AHCT541N | All 256 words and four enable combinations; 1792 vectors | Passed |
| DC319A | Reset, registers and MAINT loopback of A5/5A; 1994 vectors | Partial check |

These are slow functional tests at a requested 5 V. They do not measure
nanosecond delays, input thresholds, output current or temperature margins.
T48 samples outputs with both pull polarities to distinguish H, L and Z.
The measured XML needs a separate comparison; a successful export alone
does not mean that its values are correct.

## DC319 limitation

The programmer supplied slow clock steps, outside DEC's continuous
614.4 kHz condition. Serial frames and internal receive data agreed.
RTCLK77 followed inverted CLK in the sampled states instead of showing
the expected divide-by-8 output. The cause is unresolved. Check this output
again with the normal clock; these data do not establish a chip fault.
These T48 tests did not cover external serial reception at normal baud rates.

## Recheck the saved data

Run from the repository root with Python 3. No programmer is needed:

```sh
python3 tests/components/verify.py
```

This checks the file hashes, regenerates test vectors and compares the
recorded pin states. It also checks the GAL readback against the shipped
JEDEC file. Generated files go into ignored `build/` directories.
The measured XML and readback are unchanged exports. [SHA256SUMS.txt](SHA256SUMS.txt)
identifies them and the circuit and firmware used for these checks.

## Repeat a component test

The tests used minipro 0.7.4, commit
`3e2f4911fa86f72a57ae0ace777342e75da5e7cc`, with T48 firmware 00.1.34.
Minipro warned about partial T48 support and expected firmware 01.1.39.
All reported supply voltages came from the programmer, not a separate meter.

After running the file check above, fit only the named chip in the T48,
in the correct position and orientation. For example, for SN74AHCT14N:

```sh
minipro --logicic tests/components/74ahct14/build/vectors.xml \
  -p SN74AHCT14N_FUNCTION -T \
  --logicic_out tests/components/74ahct14/build/new-measured.xml
python3 tests/components/74ahct14/check.py \
  --check tests/components/74ahct14/build/new-measured.xml
```

| Directory | Full test profile | Comparison option |
|---|---|---|
| `74ahct14` | `SN74AHCT14N_FUNCTION` | `--check` |
| `74ahct541` | `SN74AHCT541N_FUNCTION` | `--check` |
| `74f821` | `F821_FULL` | `--check` |
| `gal20v8` | `DCJRIG_ODT_EXHAUSTIVE` | `--logic-check` |
| `dc319` | `DC319_RESET`, `DC319_SMOKE`, `DC319_CLOCK` | `--analyze` |

All databases are named `build/vectors.xml`. The GAL test reads an already
programmed ODT bridge; it does not erase or program it. The DC319 profiles
remain preliminary checks with the limits above.

Pin assignments and expectations follow the [manufacturer documents](../../datasheets/README.md)
and the [GAL bus contract](../../logic/gal/design.md).
