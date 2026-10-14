# ODT bridge: design and minimum logic

**This logic has not been tested on hardware.** The proof covers steady
Boolean levels. Delays, startup transients and bus timing need measurements.

U6 is a Lattice GAL20V8A-15LP in simple combinatorial mode.
The equations follow the wiring and specifications below. Names beginning
with `n` mean active LOW.
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
- Lattice GAL20V8A/B, May 1992: simple mode and fuse layout, printed
  pages 2-32–33; commercial A timing, page 2-37; input buffers, page 2-44.
  [Source notes](../../datasheets/Lattice_GAL20V8A_B_1992.source.txt).
- Timing also uses DEC's [corrected tables](../../datasheets/DEC_Semiconductor_Databook_Vol1_1987_Errata.source.txt),
  National's [74F821](../../datasheets/DC319-and-74F821-sources.txt), and TI's
  [AHCT14](../../datasheets/TI_SN74AHCT14.source.txt) and
  [AHCT541](../../datasheets/TI_SN74AHCT541.source.txt) switching limits.

## Pin assignments

| U6 pin | Source name | Connection |
|---|---|---|
| 1–4 | AIO3, AIO2, AIO1, AIO0 | U4 latched transaction code |
| 5, 6 | BS0, BS1 | U4 latched bank code |
| 7 | nSCTL | CPU /SCTL |
| 8 | nBUF | CPU /BUFCTL; also U5 enable pin 1 |
| 9 | ADDR0 | Latched address bit 0; also DLART A0 |
| 12, 24 | GND, VCC | Supply |
| 10, 11, 13, 14, 23 | TIE10, TIE11, TIE13, TIE14, TIE23 | Unused inputs; directly grounded |
| 15 | nREAD | DLART /RD, via net /OE |
| 18 | nWRITE | DLART /WLB, via net /WEL |
| 21 | nSELECT | DLART /CS, via net /IO |
| 22 | nBOOT | U5 enable pin 19, via net /GPREAD |
| 16, 17, 19, 20 | PARK16, PARK17, PARK19, PARK20 | Unconnected; outputs held LOW |

Pins 1 and 13 are ordinary inputs in this mode. No clock or external
output-enable signal is required. The A part has no input pull-ups.
The four unused output pins must stay physically unconnected.

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

Read, write and GP-read codes do not overlap. With steady inputs, read and
write cannot coincide, nor can the DLART and startup buffer drive together.
Both read paths require `u = 0`, when the CPU releases DAL.

## Check the programming file

`check_bridge.py` builds its expected results from numeric code sets.
It separately evaluates the source and the JEDEC fuse array for all
`16 × 4 × 2 × 2 × 2 = 512` combinations. It also varies all five grounded
inputs independently: `512 × 32 = 16384` cases. This proves that they have
no effect on any output.

The fuse decoder follows Lattice's simple-mode layout:

- Fuses 0–2559 are 64 product rows, each 40 columns wide.
- Row-enable fuses start at 2640. A connected signal and its complement
  make a row false. Otherwise, connected literals are ANDed.
- Eight rows feed each output, in pin order 22 down to 15.
- Polarity fuses 2560–2567 select the physical output level.
- Fuses 2704 and 2705 must be `1,0`; fuses 2632–2639 must all be zero.
  This gives always-enabled combinatorial outputs without registers.

The checker rejects feedback, checks both JEDEC checksums, and verifies
the source pin order. `make check-wiring` also checks the saved schematic's
control connections, grounded inputs and DV inverter path.

These checks prove the specified Boolean behavior, not that the rig works.

## What "minimum" means

Keep the pin assignments and the complete truth table above. Use one
combinatorial GAL stage, without feedback or registers. First minimize
product terms; among equal term counts, minimize literals. A literal is
one input used either directly or inverted. Both output polarities are
available at no extra term cost.

The minimum applies to these constraints. Changing the wiring or ignoring
input states is outside the proof.

| Output | Minimum terms | Literals at that minimum | Opposite polarity: terms / literals |
|---|---:|---:|---:|
| nREAD | 2 | 7 | 4 / 6 |
| nWRITE | 1 | 4 | 4 / 4 |
| nSELECT | 1 | 2 | 2 / 2 |
| nBOOT | 1 | 4 | 4 / 4 |
| **Total** | **5** | **17** | |

Four different nonconstant outputs need four equations. The other four
outputs are held LOW, using zero effective terms and no literals.

The read function has five asserted cases over its essential inputs. A
single product covers a power-of-two number of cases, so one cannot cover
exactly those five. Its only prime implicants are the two products in the
source. They require three and four literals. Each other active condition
is one cube; dropping any literal includes a forbidden input combination.

[prove_minimal.py](prove_minimal.py) checks this independently of the source.
It derives each output's essential inputs from the numeric contract,
enumerates every cube, and finds an exact minimum cover for both polarities.
It can discard non-prime cubes: enlarging one never increases its cost.
It then checks that both the source and the decoded JEDEC reach that bound.
Inputs outside an output's essential set cannot improve its optimum:
dropping such a restriction keeps the cube valid and removes a literal.
Each output has its own eight product rows, so rows cannot be shared.
The sum of the four individual minima is therefore the overall minimum
within the stated implementation style.

All outputs respond in parallel. The -15 part's input-to-output delay is
at most 15 ns under Lattice's stated conditions. Fewer terms do not guarantee
a shorter delay.

## Timing assumptions

The board uses a 4 MHz CPU crystal and an AHCT14 inverter to make
`DV = NOT(/SCTL)`. The read controls still follow /BUFCTL. A late DV capture
therefore occurs while the DLART or startup buffer is driving DAL.
DEC's corrected Tables 35, 36 and 38 place /SCTL release at T6, the DV
deadline at T6.5, and /BUFCTL release at T7 for an eight-clock cycle.

With 100–150 ns clock half-periods, the specified device loads, and an
assumed extra displacement of up to 20 ns per path, the calculated minimum
setup is 160 ns for the DLART and 413 ns for the startup buffer. Hold is
166 ns for both. These exceed the conservative 35 ns requirement.
The DV deadline margin is 36 ns.

These are conditional calculations. The actual oscillator waveform, load,
DV fall time (15 ns maximum), and wiring effects still need checking on
hardware. The Boolean proof above does not establish those conditions.
