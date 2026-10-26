# Hardware check

**ODT works on the assembled rig with a DCJ11-AE fitted.** On 26 October 2026,
writes to R0–R3 read back correctly: `111111`, `000000`, `052525`, `125252`
(octal). This checks startup, serial communication and register access.
It does not test every CPU function or measure timing margins.

![ODT writes and reads back CPU registers R0–R3](images/odt-register-check.png)

The screenshot is cropped to the terminal output; its pixels are unchanged.
The assembly photos below were taken before fitting the CPU. Their backgrounds
were masked out; retained board pixels are unchanged.

![Assembled DCJ11 test rig with empty ZIF sockets](images/board-assembled.png)

![DC319, GAL and oscillator on the assembled board](images/board-serial-detail.png)

The power jack connects by wires because its footprint did not fit the part.
See the [build guide](build.md) for connections and the
[component checks](../tests/components/README.md) for test results and limits.
