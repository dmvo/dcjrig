# CPU checks through console ODT

These scripts check a DCJ11 in the rig through its built-in console ODT.
The rig has no memory, so no program runs. Every check is an ODT command
sent over the serial port. A pass shows that the tested registers and
bus paths work. It does not prove that every part of the CPU works.

You need Python 3 on Linux. No extra packages are used.

## Results

On 8 November 2026, five DCJ11 CPUs passed in the
assembled rig. Each one ran three full passes with 15114 checks and no
failures. The negative control and the reset check passed for each CPU.

## Run

Set the rig to 38400 baud (J1: close 1–2, 3–4 and 5–6). Connect a 5 V
USB-to-TTL adapter to J2, power the rig and check for the `@` prompt.
Then run from this directory:

```sh
./run_cpu.sh 1 results/cpu1
```

The first argument is your label for the CPU. Results go to the given
directory; `results/` here is ignored by Git. `run_cpu.sh` does three
things:

1. Runs the full suite three times. One pass takes about 75 seconds.
2. Runs a negative control. It checks a deliberately wrong value and
   passes only when that error is detected.
3. Runs the reset check. When it prints `ACTION: PRESS RESET (SW1)`,
   press SW1 once.

Add `--wait-banner` as the third argument to wait for the start-up
message first. Use it when you start the script before turning on
the rig.

Each run writes a `.json` report and a `.serial.log` with every byte
sent and received. The exit code is 0 only when all steps pass.

For other ports or speeds, call `suite.py` directly:

```sh
python3 suite.py --cpu 1 --out results/cpu1 --port /dev/ttyUSB1 --passes 1
```

## What the suite checks

| Test | Checks |
|---|---|
| console | ODT replies `?` to a bare CR and to an odd address. LF steps R6→R7→R0 and I/O addresses by 2. |
| gpr_set0, gpr_set1 | R0–R5 in both register sets. Each takes 38 patterns: all 0s, all 1s, 125252, 052525, 146314, 031463, and walking 1 and walking 0. |
| regset_isolation | Both register sets hold different values at the same time. |
| pc | R7 with the same 38 patterns. |
| stack_pointers | KSP, SSP and USP, selected by PSW mode bits. Each takes all patterns and keeps its own value. |
| psw | Only bits 174757 can be written. ODT cannot set the T bit. Bits 10:8 read zero. |
| par | All 48 page address registers, 16 bits wide. |
| pdr | All 48 page descriptor registers. Writable bits are 177416; W (bit 6) clears on a write. |
| mmu_unique | Different values in all 96 MMU registers, then read back. This finds address aliasing. |
| mmr0_mmr3 | MMR0 bits 15:13 and 0 can be written. Bits 6:1 are read-only status. MMR3 bits 5:0. |
| pirq | All 128 requests in PIRQ bits 15:9. The CPU must report the highest level in bits 7:5 and 3:1. |
| ccr | Cache control register bits 003377. |
| readonly | CPU error and hit/miss registers read zero and ignore writes. |
| bus_write | Each byte 000–377 is deposited in the DLART transmit buffer (17777566). The same byte must arrive at the serial port. This tests DAL<7:0>, the GAL write decode and the DLART. |
| bus_read | RBUF (17777562) holds the last typed character, `/`. Values typed with every octal digit read back. |
| info | Records reads from locations with no device. The data bus floats there, so these values are for information only. |

The reset check first loads marker values into the registers. After SW1,
INIT must clear PSW, PIRQ, MMR3, CCR and the writable MMR0 bits. The
start-up message must show the PC. The general registers and MMU
registers keep their values; the report records them.

## Limits

- No instruction runs. ALU, floating point, microcode paths for
  instructions, interrupts, traps and memory management translation
  are not tested.
- Bus tests use only the DLART and the low data byte. DAL<15:8> is
  tested only through internal registers.
- ODT accepts more than six digits and keeps the low 16 bits.
- The expected masks follow the DCJ11 register descriptions. They were
  measured on the first CPU and matched on all five. Another J11 revision
  may differ.
