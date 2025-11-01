Espresso REI (Reduce–Expand–Irredundant)

This folder implements a compact Espresso-style optimization loop that follows the slide-19 pseudocode:

- Initialize F from primes of ON ∪ DC, filtered against OFF
- Expand(F, D); Irredundant(F, D)
- Repeat until |F| stops decreasing:
  - Reduce(F, D); Expand(F, D); Irredundant(F, D)
- Make_Sparse(F) via absorption/uniqueness

Entry point for the lab: `wa/synthesis/lab2/main.py`.
It reuses Lab1 I/O (sum-of-minterms parsing, truth table printing, PLA writer).

