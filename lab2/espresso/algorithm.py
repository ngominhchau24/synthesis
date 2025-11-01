from __future__ import annotations
from typing import List, Set, Dict, Tuple

# ---- Basic predicates on cubes/inputs ----

def implicant_covers_input(cube: str, xb: str) -> bool:
    return all(c == '-' or c == x for c, x in zip(cube, xb))


def implicant_covers_implicant(a: str, b: str) -> bool:
    """Return True if implicant a absorbs implicant b (a >= b).
    That is, whenever a is '-' or equals b at each position.
    """
    for ca, cb in zip(a, b):
        if ca != '-' and ca != cb:
            return False
    return True


# ---- Tiny QMC-style prime implicant generator for minterms (no '-') ----

def _merge_pair(a: str, b: str) -> Tuple[bool, str]:
    diff = 0
    out = []
    for ca, cb in zip(a, b):
        if ca == cb:
            out.append(ca)
        else:
            # merge allowed only if both are fixed and different
            if ca in '01' and cb in '01':
                diff += 1
                if diff > 1:
                    return False, ''
                out.append('-')
            else:
                return False, ''
    return (diff == 1, ''.join(out))


def _reduce_absorb(cubes: List[str]) -> List[str]:
    uniq = sorted(set(cubes))
    keep: List[str] = []
    for i, c in enumerate(uniq):
        if not any(i != j and implicant_covers_implicant(uniq[j], c) for j in range(len(uniq))):
            keep.append(c)
    return keep


def derive_prime_implicants(minterms: List[str]) -> List[str]:
    """Generate a set of prime implicants from plain minterms (no '-').

    This is a lightweight Quine–McCluskey style combiner sufficient for the
    sizes used in the labs. It intentionally avoids external dependencies.
    """
    if not minterms:
        return []

    groups: Dict[int, Set[str]] = {}
    for m in set(minterms):
        groups.setdefault(m.count('1'), set()).add(m)

    used: Set[str] = set()
    primes: Set[str] = set()
    while groups:
        keys = sorted(groups.keys())
        next_groups: Dict[int, Set[str]] = {}
        merged_any = False
        used.clear()
        for k in keys:
            g1 = groups.get(k, set())
            g2 = groups.get(k + 1, set())
            for a in g1:
                merged_here = False
                for b in g2:
                    ok, merged = _merge_pair(a, b)
                    if ok:
                        merged_here = True
                        merged_any = True
                        used.add(a)
                        used.add(b)
                        next_groups.setdefault(merged.count('1'), set()).add(merged)
                if not merged_here and a not in used:
                    primes.add(a)
        # add any untouched implicants
        for k in keys:
            for a in groups.get(k, set()):
                if a not in used:
                    primes.add(a)
        groups = next_groups if merged_any else {}

    return _reduce_absorb(list(primes))


# ---- Espresso REI primitives ----

def build_off_cover(inputs_bits: List[str], onset_bits: Set[str], dcare_bits: Set[str]) -> List[str]:
    """Prime implicants of the OFF-set, used to constrain expansion."""
    off_bits = list(set(inputs_bits) - (onset_bits | dcare_bits))
    if not off_bits:
        return []
    return derive_prime_implicants(off_bits)


def blocking_matrix_rows(cube: str) -> List[Tuple[int, str]]:
    """Rows = literals that could be raised during expansion."""
    return [(i, b) for i, b in enumerate(cube) if b in '01']


def _blocking_cell_is_one(row: Tuple[int, str], off_cube: str) -> bool:
    pos, pol = row
    ob = off_cube[pos]
    if ob == '-':
        return False
    return ob != pol


def _greedy_min_rows_cover(all_rows: List[Tuple[int, str]], off_cover: List[str]) -> Set[int]:
    if not off_cover:
        return set()
    cols = list(range(len(off_cover)))
    cover_map: Dict[int, Set[int]] = {}
    for r_idx, row in enumerate(all_rows):
        cover_map[r_idx] = {j for j, oc in enumerate(off_cover) if _blocking_cell_is_one(row, oc)}
    uncovered = set(cols)
    picked: Set[int] = set()
    while uncovered:
        best, gain = None, 0
        for r_idx, colset in cover_map.items():
            if r_idx in picked:
                continue
            g = len(colset & uncovered)
            if g > gain:
                best, gain = r_idx, g
        if best is None:
            # fallback: pick any remaining row if stuck
            remaining = [r for r in range(len(all_rows)) if r not in picked]
            if not remaining:
                break
            best = remaining[0]
        picked.add(best)
        uncovered -= cover_map.get(best, set())
        if gain == 0 and not uncovered:
            break
    return picked


def _apply_raises(cube: str, keep_positions: Set[int]) -> str:
    out = list(cube)
    for i, b in enumerate(out):
        if b in '01' and i not in keep_positions:
            out[i] = '-'
    return ''.join(out)


def expand_one_cube(cube: str, off_cover: List[str]) -> str:
    rows = blocking_matrix_rows(cube)
    if not rows or not off_cover:
        return '-' * len(cube)
    keep_row_ids = _greedy_min_rows_cover(rows, off_cover)
    keep_positions = {rows[r][0] for r in keep_row_ids}
    return _apply_raises(cube, keep_positions)


def irredundant(cover: List[str], inputs_bits: List[str], on_indices: Set[int]) -> List[str]:
    """Remove cubes whose ON coverage is contained in others."""
    cov: Dict[str, Set[int]] = {c: set() for c in cover}
    for c in cover:
        for i in on_indices:
            if implicant_covers_input(c, inputs_bits[i]):
                cov[c].add(i)
    keep: List[str] = []
    for i, c in enumerate(cover):
        others = set()
        for j, d in enumerate(cover):
            if i == j:
                continue
            others |= cov[d]
        if not cov[c] <= others:
            keep.append(c)
    return keep


def reduce_cover(cover: List[str], inputs_bits: List[str], on_indices: Set[int]) -> List[str]:
    """Reduce(F,D): shrink cubes to what is required to keep uniquely
    covered ON minterms covered by that cube. This operation never expands a
    cube; it adds literals (replaces '-' with fixed bits) based on the
    consensus of ON minterms that only this cube covers.
    """
    if not cover:
        return []

    # Build coverage map: for each ON index -> which cubes cover it
    covers_of_on: Dict[int, Set[int]] = {i: set() for i in on_indices}
    for idx, c in enumerate(cover):
        for i in on_indices:
            if implicant_covers_input(c, inputs_bits[i]):
                covers_of_on[i].add(idx)

    reduced: List[str] = []
    for idx, c in enumerate(cover):
        # ON minterms uniquely covered by this cube
        essential_ons = [i for i in on_indices if idx in covers_of_on[i] and len(covers_of_on[i]) == 1]
        if not essential_ons:
            # nothing forces this cube yet; leave it as is (it may be dropped by Irredundant)
            reduced.append(c)
            continue

        # Meet (bitwise consensus) of the essential minterms
        meet = list(inputs_bits[essential_ons[0]])
        for i in essential_ons[1:]:
            xb = inputs_bits[i]
            for p in range(len(meet)):
                if meet[p] != xb[p]:
                    meet[p] = '-'
        # Ensure we do not expand beyond the original cube: intersect with c
        for p in range(len(meet)):
            if c[p] in '01' and meet[p] == '-':
                # keep original fixed literal if original was more specific
                meet[p] = c[p]
        reduced.append(''.join(meet))

    return reduced


# ---- Driver: Espresso REI loop (slide 19) ----

def espresso_minimize_for_output(
    inputs_bits: List[str],
    outputs_trits: List[str],
    which_output: int,
    *,
    max_iters: int = 20,
) -> List[str]:
    """Return minimized cover (list of PCN cubes) for output index.

    F is initialized from primes over ON∪DC and filtered against OFF.
    Then follows: Expand; Irredundant; repeat { cost=|F|; Reduce; Expand; Irredundant } until |F|<cost no longer holds.
    A final absorption pass acts as Make_Sparse.
    """
    onset_bits: Set[str] = {x for x, y in zip(inputs_bits, outputs_trits) if y[which_output] == '1'}
    dcare_bits: Set[str] = {x for x, y in zip(inputs_bits, outputs_trits) if y[which_output] == '-'}
    on_indices: Set[int] = {i for i, (_, y) in enumerate(zip(inputs_bits, outputs_trits)) if y[which_output] == '1'}

    # Start with ON-set cover as minterms (per pseudocode: F = ON-SET cover)
    cover = sorted(onset_bits)
    off_bits = set(inputs_bits) - (onset_bits | dcare_bits)

    off_cover = build_off_cover(inputs_bits, onset_bits, dcare_bits)

    # First Expand + Irredundant (as in the pseudocode)
    cover = [expand_one_cube(c, off_cover) for c in cover]
    cover = irredundant(cover, inputs_bits, on_indices)

    # REI loop with cost = number of cubes
    iters = 0
    while iters < max_iters:
        iters += 1
        cost = len(cover)
        cover = reduce_cover(cover, inputs_bits, on_indices)
        cover = [expand_one_cube(c, off_cover) for c in cover]
        cover = irredundant(cover, inputs_bits, on_indices)
        if len(cover) < cost:
            continue
        break

    # Make_Sparse: absorption and uniqueness
    cleaned: List[str] = []
    for i, c in enumerate(cover):
        if not any(i != j and implicant_covers_implicant(cover[j], c) for j in range(len(cover))):
            cleaned.append(c)
    cover = sorted(set(cleaned))
    return cover
