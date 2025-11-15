"""
Lab 3: BDD-based netlist generation and SystemVerilog synthesis.

Convert Boolean functions to BDD, then generate gate-level netlist
and SystemVerilog simulation.

Usage:
    python3 main.py random [N] [M] [on_ratio] [dc_ratio]
    python3 main.py spec.txt [N]
"""

from __future__ import annotations
import sys
import os

# Add parent directory to path to import lab1 modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import List, Optional, Dict, Tuple, Set
from lab1.truth_table import (
    parse_sum_of_minterms_file,
    build_outputs_from_minterm_indices,
    print_truth_table,
    generate_random_spec_file,
)
from lab3.bdd import BDD, BDDNode
from lab3.netlist import Netlist
from lab3.verilog_gen import VerilogGenerator


def _safe_stem(path: str) -> str:
    """Extract filename stem without extension."""
    base = os.path.basename(path)
    if "." in base:
        return ".".join(base.split(".")[:-1]) or base
    return base or "run"


def run_bdd_synthesis(
    path: str,
    n_inputs: int,
    output_dir: str = "output",
    input_names: Optional[List[str]] = None,
) -> None:
    """Run complete BDD synthesis flow: parse → BDD → netlist → Verilog.

    Args:
        path: Path to specification file
        n_inputs: Number of input variables
        output_dir: Directory for output files
        input_names: Optional custom input names
    """
    print("=" * 60)
    print("LAB 3: BDD-based Netlist Generation")
    print("=" * 60)
    print()

    # 1. Parse spec and build truth table
    print("Step 1: Parsing specification file...")
    spec = parse_sum_of_minterms_file(path)
    inputs_bits, outputs_trits, out_names = build_outputs_from_minterm_indices(n_inputs, spec)

    if input_names is None:
        input_names = [f"x{i}" for i in range(n_inputs)]

    print(f"  Inputs: {n_inputs} variables: {', '.join(input_names)}")
    print(f"  Outputs: {len(out_names)} functions: {', '.join(out_names)}")
    print()

    # Print truth table
    print("Truth Table:")
    print_truth_table(inputs_bits, outputs_trits, input_names, out_names)
    print()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Process each output function
    for output_idx, output_name in enumerate(out_names):
        print("-" * 60)
        print(f"Processing output: {output_name}")
        print("-" * 60)

        # Extract ON-set and DC-set for this output
        on_set, dc_set = _extract_sets_for_output(inputs_bits, outputs_trits, output_idx)

        print(f"  ON-set: {sorted(on_set)}")
        print(f"  DC-set: {sorted(dc_set)}")
        print()

        # 2. Build BDD from truth table
        print(f"Step 2: Building BDD for {output_name}...")
        bdd = BDD(num_vars=n_inputs)
        root = bdd.build_from_minterm_spec(n_inputs, on_set, dc_set)

        print(f"  BDD nodes (total): {bdd.get_node_count()}")
        print(f"  BDD nodes (non-terminal): {bdd.get_non_terminal_count()}")
        print()

        # Optional: Print BDD structure (for small circuits)
        if bdd.get_non_terminal_count() <= 10:
            print("  BDD Structure:")
            bdd.print_bdd(root, indent=2)
            print()

        # 3. Generate netlist from BDD
        print(f"Step 3: Generating gate-level netlist for {output_name}...")
        netlist = Netlist(num_inputs=n_inputs, var_names=input_names)
        netlist.build_from_bdd(bdd, root, output_name=output_name)

        netlist.print_netlist()
        netlist.print_stats()
        print()

        # 4. Generate SystemVerilog
        print(f"Step 4: Generating SystemVerilog for {output_name}...")

        module_name = f"{_safe_stem(path)}_{output_name}"
        sv_module_file = os.path.join(output_dir, f"{module_name}.sv")
        sv_tb_file = os.path.join(output_dir, f"{module_name}_tb.sv")

        vgen = VerilogGenerator(netlist, module_name=module_name, output_name=output_name)

        # Generate module
        vgen.generate_module(sv_module_file)

        # Generate testbench with expected outputs
        expected_outputs = _build_expected_outputs(inputs_bits, outputs_trits, output_idx)
        vgen.generate_testbench(sv_tb_file, expected_outputs)

        print(f"  Module: {sv_module_file}")
        print(f"  Testbench: {sv_tb_file}")
        print()

    print("=" * 60)
    print("Synthesis Complete!")
    print(f"Output files in: {output_dir}/")
    print("=" * 60)
    print()
    print("To simulate with a SystemVerilog simulator:")
    print(f"  cd {output_dir}")
    for output_name in out_names:
        module_name = f"{_safe_stem(path)}_{output_name}"
        print(f"  # For {output_name}:")
        print(f"    iverilog -g2012 -o sim {module_name}.sv {module_name}_tb.sv")
        print(f"    ./sim")
        print()


def _extract_sets_for_output(
    inputs_bits: List[str],
    outputs_trits: List[str],
    output_idx: int
) -> Tuple[Set[int], Set[int]]:
    """Extract ON-set and DC-set for a specific output.

    Args:
        inputs_bits: List of input combinations (binary strings)
        outputs_trits: List of output values (trit strings with '0', '1', '-')
        output_idx: Index of the output to extract

    Returns:
        (on_set, dc_set) - sets of minterm indices
    """
    on_set = set()
    dc_set = set()

    for i, out_trit in enumerate(outputs_trits):
        if output_idx < len(out_trit):
            val = out_trit[output_idx]
            if val == '1':
                on_set.add(i)
            elif val == '-':
                dc_set.add(i)

    return on_set, dc_set


def _build_expected_outputs(
    inputs_bits: List[str],
    outputs_trits: List[str],
    output_idx: int
) -> List[int]:
    """Build expected output values for testbench.

    Args:
        inputs_bits: List of input combinations
        outputs_trits: List of output values
        output_idx: Index of the output

    Returns:
        List of expected values (0 or 1), DC treated as 0
    """
    expected = []
    for out_trit in outputs_trits:
        if output_idx < len(out_trit):
            val = out_trit[output_idx]
            if val == '1':
                expected.append(1)
            else:
                expected.append(0)  # '0' or '-' (DC)
        else:
            expected.append(0)

    return expected


def print_usage():
    """Print CLI usage information."""
    print(
        "LAB 3: BDD-based Netlist Generation\n"
        "\n"
        "Usage:\n"
        "  python3 main.py random [N] [M] [on_ratio] [dc_ratio]\n"
        "      -> Generate random_spec.txt then synthesize to netlist.\n"
        "         Defaults: N=4, M=2, on_ratio=0.35, dc_ratio=0.15\n"
        "\n"
        "  python3 main.py spec.txt [N]\n"
        "      -> Synthesize from specification file; default N=3.\n"
        "\n"
        "Output:\n"
        "  - BDD statistics and structure\n"
        "  - Gate-level netlist\n"
        "  - SystemVerilog module (.sv)\n"
        "  - SystemVerilog testbench (_tb.sv)\n"
        "\n"
        "Examples:\n"
        "  python3 main.py random 3 1 0.5 0.2\n"
        "  python3 main.py spec.txt 4\n"
    )


def main():
    """Main entry point."""
    args = sys.argv[1:]
    if not args:
        print_usage()
        return

    mode = args[0].strip()

    if mode.lower() == "random":
        # Random generation mode
        try:
            N = int(args[1]) if len(args) >= 2 else 4
            M = int(args[2]) if len(args) >= 3 else 1  # Default 1 output for clarity
            on = float(args[3]) if len(args) >= 4 else 0.35
            dc = float(args[4]) if len(args) >= 5 else 0.15
        except ValueError:
            print("Error: parameters must be numeric (N, M ints; on_ratio, dc_ratio floats).")
            return

        if on > 0.5:
            print("Warning: on_ratio > 0.5 is clamped to 0.5.")
            on = 0.5

        out_path = "random_spec.txt"
        generate_random_spec_file(
            out_path, n_inputs=N, n_outputs=M,
            on_ratio=on, dc_ratio=dc, ensure_on=True, seed=None
        )
        print(f"Generated random spec: {out_path}\n")

        run_bdd_synthesis(path=out_path, n_inputs=N, output_dir="output")
        return

    # Spec file mode
    path = mode
    try:
        N = int(args[1]) if len(args) >= 2 else 3
    except ValueError:
        print("Error: N must be an integer.")
        return

    if not os.path.exists(path):
        print(f"Error: Specification file '{path}' not found.")
        return

    run_bdd_synthesis(path=path, n_inputs=N, output_dir="output")


if __name__ == "__main__":
    main()
