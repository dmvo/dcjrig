# HC-49S crystal

Y1 uses a low, through-hole 4 MHz crystal in an HC-49S case.
Its footprint is `DCJRig:Crystal_HC49S_Vertical`.

| Feature | Size |
|---|---:|
| Lead spacing | 4.88 mm |
| Drill diameter | 0.8 mm |
| Pad diameter | 2 mm |
| Body outline | 11.4 × 4.8 mm |
| Model height | 3.5 mm |
| Declared mounted height | 4.0 mm |

The 4 mm height allows a 0.5 mm gap under the body. Check the actual part
when fitting it. A crystal has no polarity.

The package dimensions follow the DIP drawing in
[Elecsound's HC49S sheet](../../datasheets/Elecsound_HC49S_Quartz_Crystal_Resonator.source.txt).
This is a size reference; it does not identify the maker of the stocked crystal.

To regenerate the 3D model:

```sh
python3 mechanical/crystal_hc49s/generate_model.py
```
