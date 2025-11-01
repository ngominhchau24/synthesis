from __future__ import annotations
import os
import sys
from io import StringIO
from contextlib import redirect_stdout
from typing import List, Optional

# Make Lab1 helpers importable (same I/O contract)
_HERE = os.path.dirname(__file__)
_LAB1 = os.path.abspath(os.path.join(_HERE, "..", "lab1"))
if _LAB1 not in sys.path:
    sys.path.insert(0, _LAB1)

from truth_table import (
    parse_sum_of_minterms_file,
    build_outputs_from_minterm_indices,
    print_truth_table,
    print_truth_table_markdown,
    generate_random_spec_file,
)
from pla import build_full_pla

from espresso import espresso_minimize_for_output


def _safe_stem(path: str) -> str:
    base = os.path.basename(path)
    if "." in base:
        return ".".join(base.split(".")[:-1]) or base
    return base or "run"


def _save_truth_table_markdown(
    inputs_bits: List[str],
    outputs_trits: List[str],
    input_names: List[str],
    output_names: List[str],
    out_path: str,
) -> None:
    buf = StringIO()
    with redirect_stdout(buf):
        print_truth_table_markdown(inputs_bits, outputs_trits, input_names, output_names)
    md = buf.getvalue()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)


def _cube_to_sop_term(cube: str, var_names: List[str]) -> str:
    parts = []
    for b, n in zip(cube, var_names):
        if b == '1':
            parts.append(n)
        elif b == '0':
            parts.append(n + "'")
    return ''.join(parts) if parts else "1"


def _cubes_for_pla(selected_cubes: List[str], n_outputs: int, which_output: int) -> List[str]:
    rows = []
    for cube in selected_cubes:
        y = ['0'] * n_outputs
        y[which_output] = '1'
        rows.append(f"{cube} {''.join(y)}")
    return rows


def run_from_sum_file(
    path: str,
    n_inputs: int,
    input_names: Optional[List[str]] = None,
    use_markdown: bool = False,
) -> str:
    spec = parse_sum_of_minterms_file(path)
    inputs_bits, outputs_trits, out_names = build_outputs_from_minterm_indices(n_inputs, spec)

    if input_names is None:
        input_names = [f"x{i+1}" for i in range(n_inputs)]
    output_names = out_names

    print("Truth table (plain):")
    print_truth_table(inputs_bits, outputs_trits, input_names, output_names)

    if use_markdown:
        stem = _safe_stem(path)
        md_path = f"{stem}_truth_table.md"
        _save_truth_table_markdown(inputs_bits, outputs_trits, input_names, output_names, md_path)
        print(f"[i] Markdown truth table saved to: {md_path}")

    all_pla_rows: List[str] = []
    for k, out_name in enumerate(output_names):
        es_cubes: List[str] = espresso_minimize_for_output(
            inputs_bits=inputs_bits,
            outputs_trits=outputs_trits,
            which_output=k,
        )

        sop_terms = [_cube_to_sop_term(c, input_names) for c in es_cubes]
        sop_str = " + ".join(sop_terms) if sop_terms else "0"

        print(f"\n=== {out_name} ===")
        print("PIs:", es_cubes)
        print("SOP:", sop_str)

        all_pla_rows.extend(_cubes_for_pla(es_cubes, n_outputs=len(output_names), which_output=k))

    pla_text = build_full_pla(inputs_bits, outputs_trits, all_pla_rows, input_names, output_names)
    print("\nPLA:")
    print(pla_text)

    return pla_text


def print_usage():
    print(
        "Usage:\n"
        "  python3 main.py random [N] [M] [on_ratio] [dc_ratio]\n"
        "      -> Generate random_spec.txt then run it.\n"
        "         Defaults: N=4, M=2, on_ratio=0.35 (<=0.5), dc_ratio=0.15\n"
        "\n"
        "  python3 main.py spec.txt [N]\n"
        "      -> Run with provided spec file (supports d{...}); default N=3.\n"
    )


def main():
    args = sys.argv[1:]
    if not args:
        print_usage()
        return

    mode = args[0].strip()
    use_markdown = True

    if mode.lower() == "random":
        try:
            N = int(args[1]) if len(args) >= 2 else 4
            M = int(args[2]) if len(args) >= 3 else 2
            on = float(args[3]) if len(args) >= 4 else 0.35
            dc = float(args[4]) if len(args) >= 5 else 0.15
        except ValueError:
            print("Error: parameters must be numeric (N,M ints; on_ratio, dc_ratio floats).")
            return

        if on > 0.5:
            print("Warning: on_ratio > 0.5 is clamped to 0.5.")
            on = 0.5

        out_path = "random_spec.txt"
        generate_random_spec_file(
            out_path, n_inputs=N, n_outputs=M, on_ratio=on, dc_ratio=dc, ensure_on=True, seed=None
        )
        print(f"[i] Generated random spec -> {out_path}")
        run_from_sum_file(path=out_path, n_inputs=N, use_markdown=use_markdown)
        return

    # spec file: python3 main.py spec.txt [N]
    path = mode
    try:
        N = int(args[1]) if len(args) >= 2 else 3
    except ValueError:
        print("Error: N must be an integer.")
        return

    run_from_sum_file(path=path, n_inputs=N, use_markdown=use_markdown)


if __name__ == "__main__":
    main()

