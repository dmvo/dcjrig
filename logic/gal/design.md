# ODT bridge: design and proof

**This logic has not been tested on real hardware.** This proof covers
steady Boolean levels. Propagation delays, startup transients and bus
timing still need checking on a built board.

The equations are written from this board's connections and the device
specifications below. Signal names beginning with `n` mean active LOW.
`AIO3:0`, `BS1:0` and `ADDR0` come from U4 and remain stable during a
transfer. `nBUF` and `nSCTL` come directly from the CPU.

## Sources

- DEC *Digital Semiconductor Databook*, Volume 1, 1987, DCJ11 chapter:
  Table 2 (transaction codes), Table 3 (bank codes), data control signals,
  and the read, write and GP-read cycle descriptions. Printed pages
  1-254–257 and 1-277–281.
  [Source and local filename](../../datasheets/DEC_DCJ11_1987_Databook.source.txt).
- DEC DC319-AA: pin functions on page 3-29 and bus timing in Figure 7
  and Table 9 on page 3-39. Its corrected first page identifies it as
  a DLART. [Source notes](../../datasheets/DC319-and-74F821-sources.txt).
- Lattice GAL16V8, May 2001: simple mode and fuse layout, pages 8–9.
  [Source notes](../../datasheets/Lattice_GAL16V8.source.txt).

## Pin assignments

| U6 pin | Source name | Connection |
|---|---|---|
| 1–4 | AIO3, AIO2, AIO1, AIO0 | U4 latched transaction code |
| 5, 6 | BS0, BS1 | U4 latched bank code |
| 7 | nSCTL | CPU /SCTL |
| 8 | nBUF | CPU /BUFCTL; also U5 enable pin 1 |
| 9 | ADDR0 | Latched address bit 0; also DLART A0 |
| 10, 20 | GND, VCC | Supply |
| 11 | NC | Board holds this input HIGH; equations do not use it |
| 12 | nREAD | DLART /RD, via net /OE |
| 15 | nWRITE | DLART /WLB, via net /WEL |
| 18 | nSELECT | DLART /CS, via net /IO |
| 19 | nBOOT | U5 enable pin 19, via net /GPREAD |
| 13, 14, 16, 17 | PARK13, PARK14, PARK16, PARK17 | Unconnected; outputs held LOW |

The CPU's /MISS and /CONT inputs connect directly to GND. The GAL does
not drive them. This selects stretched reads and adds no external wait.

## Required behavior

Let `a` be the four-bit transaction code, `b` the two-bit bank code,
`q = ADDR0`, `u = nBUF`, and `s = nSCTL`. The numbers below are hexadecimal.

| Output is LOW exactly when… | Meaning |
|---|---|
| `b = 2` | Select the external-I/O bank |
| `a ∈ {8,9,A,B,C}` and `u = 0` | Read during the CPU's released-bus interval |
| `a ∈ {0,1,2,3}`, `q = 0`, and `s = 0` | Write a DLART low byte at an even address |
| `a = E` | Select the startup buffer for a GP read |

The DLART requires both /CS and the appropriate read or write control.
The startup buffer requires both its enables LOW. Thus its actual bus
enable also requires `u = 0`.

There is one device in the external-I/O bank. The board decodes only the
bank and address bits 2:0, so the DLART registers repeat every eight bytes
within that bank. The fixed startup word serves GP reads; the board has
no floating-point unit or other GP-read device.

## Derivation

Use `¬` for NOT, `∧` for AND and `∨` for OR. Write the transaction bits
as `a3…a0`, and bank bits as `b1,b0`. Define the active conditions:

```text
select = b1 ∧ ¬b0
read   = ¬u ∧ a3 ∧ (¬a2 ∨ (¬a1 ∧ ¬a0))
write  = ¬a3 ∧ ¬a2 ∧ ¬q ∧ ¬s
boot   = a3 ∧ a2 ∧ a1 ∧ ¬a0
```

Each physical output is the complement of its active condition.

1. `b1 ∧ ¬b0` is true only for bank code `10`, DEC's external-I/O bank.
2. For reads, `a3 ∧ ¬a2` selects codes `8…B`. The remaining product
   `a3 ∧ ¬a1 ∧ ¬a0` selects `8` and `C`. Their union is exactly
   `{8,9,A,B,C}`. Multiplying by `¬u` limits reads to a released DAL bus.
3. `¬a3 ∧ ¬a2` selects exactly codes `0…3`: bus word and byte writes.
   The DLART writes its low byte only with A0 LOW. `¬q` supplies that
   condition; `¬s` supplies the stretched write phase.
4. All four bits in `boot` are specified, so it selects only code `E`.

Distributing the read expression gives the two product terms in the
source. The other expressions each need one. These cover every input
combination; no undefined cases are used to simplify the equations.

The read and write code sets are disjoint. GP read is also outside both
sets. Therefore read and write cannot overlap, and the DLART and startup
buffer cannot drive the bus together at steady inputs. Both read paths
require `u = 0`, so neither is enabled while the CPU drives DAL.

## Check the programming file

`check_bridge.py` builds its expected results from numeric code sets.
It separately evaluates the source and the JEDEC fuse array for all
`16 × 4 × 2 × 2 × 2 = 512` combinations. Repeating with pin 11 LOW and
HIGH gives 1024 cases and proves that this input has no effect.

The fuse decoder follows Lattice's simple-mode layout:

- Fuses 0–2047 are 64 product rows, each 32 columns wide.
- Row-enable fuses start at 2128. A connected signal and its complement
  make a row false. Otherwise, connected literals are ANDed.
- Eight rows feed each output, in pin order 19 down to 12.
- Polarity fuses 2048–2055 select the physical output level.
- Fuses 2192 and 2193 must be `1,0`; fuses 2120–2127 must all be zero.
  This gives always-enabled combinatorial outputs without registers.

The checker rejects feedback, checks both JEDEC checksums, and verifies
the source pin order. `make check-wiring` also checks the saved schematic's
control connections and the CPU's grounded inputs.

These checks establish the specified Boolean behavior of the equations
and programming data. They do not establish that the complete rig works.
