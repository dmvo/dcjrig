"""Decode the recorded DLART output using supplied clock edges, not elapsed time."""
from pathlib import Path
import xml.etree.ElementTree as ET

from check import profiles

HERE = Path(__file__).resolve().parent
metadata = profiles()['DC319_CLOCK'].meta
vectors = ET.parse(HERE / 'clock-measured.xml').getroot().findall('.//vector')
assert len(metadata) == len(vectors) == 1751

for byte in (0xa5, 0x5a):
    prefix = f'transmit {byte:02x}: CLK '
    samples, divider = [], []
    for meta, vector in zip(metadata, vectors):
        if meta['label'].startswith(prefix) and meta['label'].endswith(' H'):
            states = vector.text.split()
            assert states[31] == '1'
            assert states[29] in 'HL' and states[33] in 'HL'
            samples.append(int(states[29] == 'H'))
            divider.append(int(states[33] == 'H'))
    assert len(samples) == 384
    start = samples.index(0)
    frame = [samples[start + 8 + 16 * k] for k in range(10)]
    assert frame[0] == 0 and frame[-1] == 1
    decoded = sum(frame[bit + 1] << bit for bit in range(8))
    assert decoded == byte
    transitions = sum(a != b for a, b in zip(divider, divider[1:]))
    print(f'SO: 8N1 frame 0x{decoded:02x}, 16 supplied clock cycles per bit.')
    print(f'RTCLK77: {transitions} transitions in samples taken with CLK=1.')

clock_samples = [node.text.split() for meta, node in zip(metadata, vectors)
                 if ': CLK ' in meta['label'] and 'stop' not in meta['label']]
assert len(clock_samples) == 1600
inverted = sum(row[33] == ('H' if row[31] == '0' else 'L') for row in clock_samples)
print(f'RTCLK77 follows inverted CLK in {inverted}/{len(clock_samples)} sampled states.')
print('UNRESOLVED: divide-by-8 operation was not observed under these slow clock steps.')
print('Repeat the clock-output check at a continuous 614.4 kHz; these data do not establish a defect.')
