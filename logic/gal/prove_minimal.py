#!/usr/bin/env python3
"""Exact minimum SOP covers for the ODT bridge's fixed pin-level contract.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Dimitri Varpusvuori

Enumerates all cubes, then solves the prime-implicant cover exactly. Both
output polarities are free choices on a GAL. No third-party solver is used.
"""

from functools import lru_cache
from itertools import product


def minimum_cover(values):
    """Return the minimum (product terms, literals), in that priority order."""
    count = len(values)
    width = (count - 1).bit_length()
    assert count == 1 << width
    target = sum(1 << i for i, value in enumerate(values) if value)
    if not target:
        return (0, 0)

    # A cube specifies 0, 1, or don't-care for every essential input.
    valid = {}
    for cube in product((None, 0, 1), repeat=width):
        cover = sum(1 << i for i in range(count)
                    if all(v is None or (i >> bit) & 1 == v
                           for bit, v in enumerate(cube)))
        if cover & ~target == 0:
            valid[cube] = cover

    # Every non-prime cube can be enlarged without adding a term or a
    # literal. Thus an optimum always has a cover made only of primes.
    primes = []
    for cube, cover in valid.items():
        parents = [cube[:i] + (None,) + cube[i + 1:]
                   for i, value in enumerate(cube) if value is not None]
        if not any(parent in valid for parent in parents):
            primes.append((cover, sum(v is not None for v in cube)))

    @lru_cache(None)
    def solve(remaining):
        if remaining == 0:
            return (0, 0)
        # Every cover must include a prime covering this particular minterm.
        first = remaining & -remaining
        choices = []
        for cover, literals in primes:
            if cover & first:
                terms, rest_literals = solve(remaining & ~cover)
                choices.append((1 + terms, literals + rest_literals))
        return min(choices)

    return solve(target)


def source_cost(equation):
    """Count effective SOP terms and literals, excluding constant-false rows."""
    _, terms = equation
    count, literals = 0, 0
    for term in terms:
        if any((name == 'GND' and not neg) or (name == 'VCC' and neg)
               for name, neg in term):
            continue
        signals = [(name, neg) for name, neg in term if name not in ('GND', 'VCC')]
        if any((name, not neg) in signals for name, neg in signals):
            continue
        count += 1
        literals += len(signals)
    return count, literals


def prove_minimum(contract, names, equations, products, fuses):
    """Check minimum costs of the source and separately decoded fuse rows."""
    table = [contract({p: (i >> (p - 1)) & 1 for p in range(1, 10)})
             for i in range(512)]
    total = (0, 0)
    for pin in (15, 18, 21, 22):
        values = [row[pin] for row in table]
        support = [bit for bit in range(9)
                   if any(values[i] != values[i ^ (1 << bit)] for i in range(512))]
        reduced = [values[sum(((i >> j) & 1) << bit for j, bit in enumerate(support))]
                   for i in range(1 << len(support))]
        costs = {1: minimum_cover(reduced),
                 0: minimum_cover([1 - v for v in reduced])}
        optimum = min(costs.values())
        source_polarity = int(not equations[pin][0])
        cell = 22 - pin
        fuse_polarity = fuses[2560 + cell]
        rows = [p for p in products[8 * cell:8 * cell + 8] if p is not None]
        actual = (len(rows), sum(len(row) for row in rows))
        if not (source_cost(equations[pin]) == actual == optimum
                == costs[source_polarity] == costs[fuse_polarity]):
            raise ValueError(f'Output {pin} is not minimal: source={source_cost(equations[pin])}, '
                             f'fuses={actual}, polarity costs={costs}')
        total = tuple(a + b for a, b in zip(total, optimum))
        print(f'MIN {names[pin - 1]}: {optimum[0]} terms, {optimum[1]} literals '
              f'(opposite polarity: {costs[1 - fuse_polarity]}).')

    for pin in (16, 17, 19, 20):
        cell = 22 - pin
        if (source_cost(equations[pin]) != (0, 0)
                or any(p is not None for p in products[8 * cell:8 * cell + 8])):
            raise ValueError(f'Unused output {pin} consumes an effective product term')
    if total != (5, 17):
        raise ValueError(f'Contract minimum changed: {total}')
    print('MINIMUM: four functional equations, five product terms, 17 literals; '
          'four constant outputs use zero effective terms. No feedback or registers.')
