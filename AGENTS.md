# Working on the DCJ11 test rig

## Project

This is a small rig for checking DEC DCJ11-AE processors, P/N 57-19400-09.
It uses the CPU's built-in ODT console and a DC319 UART. The CPU crystal is
4 MHz in an HC-49S case. Power comes from an external 5 V supply.

Keep the rig focused on a quick console check. It does not need external RAM,
interrupts, DMA or a program to run from memory. A working console does not
prove that every part of the CPU works.

## Communication and documents

- Use the user's language in conversation and local-only documents.
- Write public documents in English. Use familiar words and short sentences.
  Write for someone building or exploring the project.
- Public documents describe the current design. Keep old plans, audit logs,
  rejected options and private notes in ignored local files.
- Keep the main README short. It presents this as an example of AI-assisted
  KiCad design, from an empty project to a routed board.
- State the result first. Put detailed evidence in a local report when needed.

## Making changes

- The user gives instructions, AI carries out the work, and the user reviews
  the result. Use tools to do the design work, including an autorouter for
  PCB routing.
- Complete authorized work without asking for the same permission again.
- A request to check a design means inspect it and report. Edit it only when
  the user asks for a fix or change.
- Do not run ERC unless the user asks. Netlist export is allowed.
- The user controls layout decisions. Review or change the board, footprints
  and their assignments only when asked.
- The user chooses the power supply and capacitors. Check their connections
  when relevant, but do not reopen settled choices about current consumption.
- Preserve the user's concurrent edits. Never replace current design files
  with an older copy.

## Checking the design

- Read the saved `kicad/rig/rig.kicad_sch` each time. Export a fresh netlist
  for connection checks. Confirm the file has not changed before reporting.
- Check physical pin numbers, nets, polarity and enable signals. After changing
  symbols, compare every used pin's connection before and after the edit.
- Use DEC and manufacturer documents first, including errata. Match the exact
  part and logic family. Use Peter Schranz's
  [Modular DCJ11 SBC](https://www.5volts.ch/pages/dcj11sbc/) as a second source.
- Check reset, startup bits, clocks, pull resistors, unused inputs and bus
  direction. Give a primary source for any missing connection or pull resistor.
- Keep measured behavior separate from calculations. State timing assumptions
  and margins. A missing guarantee is not proof of a hardware failure.
- For an independent audit, start from the files and primary sources.
  Rediscover and check the reference design when requested.
- Changes to GAL equations need a mathematical proof. Also check the compiled
  JEDEC file independently. The local tools are galette and minipro with a T48.

## Libraries and sources

- Check the user's parts inventory for available components. Inventory is
  not a datasheet.
- Use installed KiCad library parts when suitable. Put custom parts in the
  project libraries. Do not edit the installed libraries.
- Keep symbols readable. Preserve requested pin order and verify pin numbers
  and electrical types against the exact part's datasheet.
- Use the correct local PDF in each symbol's Datasheet field. Look locally
  before downloading another copy.
- Keep downloaded datasheets and reference archives on disk but outside Git
  unless their terms allow redistribution. Record source URLs and file hashes.
- Retain third-party credits and licenses. Check rights for adapted files too.
  Do not choose a project-wide license without the owner's instruction.
- Keep private correspondence, procurement notes and local backups out of Git.
