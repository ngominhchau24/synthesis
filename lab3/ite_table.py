"""
ITE (If-Then-Else) lookup table for gate-level synthesis.

Complete ITE operator table with all 16 Boolean functions on two variables.
Maps ITE patterns to standard cells, decomposing complex functions as needed.

Reference: ite(f, g, h) = f·g + f̄·h

ITE Table (index corresponds to truth table [f=1,g=1 | f=1,g=0 | f=0,g=1 | f=0,g=0]):
    0000: 0           → Constant 0
    0001: f·g         → AND(f, g)
    0010: f·ḡ         → f > g (requires AND + NOT decomposition)
    0011: f           → Buffer f
    0100: f̄·g         → f < g (requires NOT + AND decomposition)
    0101: g           → Buffer g
    0110: f⊕g         → XOR(f, g)
    0111: f+g         → OR(f, g)
    1000: ̄f̄+ḡ         → NOR(f, g)
    1001: f⊙ḡ         → XNOR(f, g)
    1010: ḡ           → NOT(g)
    1011: f+ḡ         → f ≥ g (requires OR + NOT decomposition)
    1100: f̄           → NOT(f)
    1101: f̄+g         → f ≤ g (requires NOT + OR decomposition)
    1110: f̄g          → NAND(f, g)
    1111: 1           → Constant 1
"""

from __future__ import annotations
from typing import Tuple, Optional, List
from enum import Enum


class GateType(Enum):
    """Standard logic gate types."""
    BUFFER = "BUF"
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    NAND = "NAND"
    NOR = "NOR"
    XOR = "XOR"
    XNOR = "XNOR"
    MUX = "MUX"  # 2-to-1 multiplexer (will be decomposed)
    # Composite gates (need decomposition)
    GT = "GT"        # f > g = f·ḡ (AND with inverted g)
    LT = "LT"        # f < g = f̄·g (AND with inverted f)
    GTE = "GTE"      # f ≥ g = f + ḡ (OR with inverted g)
    LTE = "LTE"      # f ≤ g = f̄ + g (OR with inverted f)


class Gate:
    """Represents a logic gate in the netlist."""

    def __init__(self, gate_type: GateType, output: str, inputs: List[str], gate_id: int):
        """Initialize a gate.

        Args:
            gate_type: Type of gate
            output: Output signal name
            inputs: List of input signal names
            gate_id: Unique gate identifier
        """
        self.gate_type = gate_type
        self.output = output
        self.inputs = inputs
        self.id = gate_id

    def __repr__(self) -> str:
        inputs_str = ", ".join(self.inputs)
        return f"{self.output} = {self.gate_type.value}({inputs_str})"


class ITETable:
    """Complete ITE lookup table with all 16 Boolean functions."""

    @staticmethod
    def create_gate_for_ite(f: str, g: str, h: str,
                           f_is_const: bool, g_is_const: bool, h_is_const: bool,
                           output: str, gate_id: int) -> Gate:
        """Create a gate for ITE(f, g, h) operation.

        Maps ITE patterns to gates based on the complete ITE table.
        For composite gates (GT, LT, GTE, LTE, MUX), decomposition
        is handled in the Verilog generator.

        Args:
            f: Signal name for condition
            g: Signal name for then branch
            h: Signal name for else branch
            f_is_const, g_is_const, h_is_const: Constant flags
            output: Output signal name
            gate_id: Gate identifier

        Returns:
            Gate object
        """
        # Extract constant values
        f_val = int(f) if f_is_const and f in ['0', '1'] else -1
        g_val = int(g) if g_is_const and g in ['0', '1'] else -1
        h_val = int(h) if h_is_const and h in ['0', '1'] else -1

        # Pattern matching based on ITE table

        # 0001: ITE(f, g, 0) = f AND g
        if h_val == 0 and g_val == -1 and f_val == -1:
            return Gate(GateType.AND, output, [f, g], gate_id)

        # 0010: ITE(f, ḡ, 0) or ITE(f, 0, NOT(h)) = f > g = f·ḡ
        # This is ITE(f, g, 0) where g might need inversion
        # Handled as composite GT gate
        if h_val == 0 and g_val == 0 and f_val == -1:
            # ITE(f, 0, 0) = 0, but this shouldn't happen
            return Gate(GateType.AND, output, [f, "1'b0"], gate_id)

        # 0011: ITE(f, 1, 0) = f (BUFFER)
        if g_val == 1 and h_val == 0:
            return Gate(GateType.BUFFER, output, [f], gate_id)

        # 0100: ITE(f, 0, g) = f̄·g = f < g
        if g_val == 0 and h_val == -1 and f_val == -1:
            return Gate(GateType.LT, output, [f, h], gate_id)

        # 0101: ITE(f, g, g) = g (BUFFER)
        if g == h and g_val == -1:
            return Gate(GateType.BUFFER, output, [g], gate_id)

        # 0110: XOR - need to detect this pattern
        # ITE(f, ḡ, g) = f XOR g
        # This is complex to detect, so we handle it in MUX decomposition

        # 0111: ITE(f, 1, g) = f OR g
        if g_val == 1 and h_val == -1 and f_val == -1:
            return Gate(GateType.OR, output, [f, h], gate_id)

        # 1000: NOR - ITE(f, 0, ḡ) where we need h to be inverted
        # Difficult to detect, treat as composite

        # 1010: ITE(g, 0, 1) = NOT(g)
        if g_val == 0 and h_val == 1:
            return Gate(GateType.NOT, output, [f], gate_id)

        # 1011: ITE(f, 1, ḡ) = f ≥ g = f + ḡ
        if g_val == 1 and h_val == -1:
            return Gate(GateType.GTE, output, [f, h], gate_id)

        # 1100: ITE(f, 0, 1) = NOT(f)
        if g_val == 0 and h_val == 1:
            return Gate(GateType.NOT, output, [f], gate_id)

        # 1101: ITE(f, g, 1) = f̄ + g = f ≤ g
        if h_val == 1 and g_val == -1 and f_val == -1:
            return Gate(GateType.LTE, output, [f, g], gate_id)

        # 1110: NAND - ITE(f, ḡ, 1)
        # Can be detected if we track inversions

        # Default: treat as MUX (will be decomposed)
        return Gate(GateType.MUX, output, [f, g, h], gate_id)


def print_ite_table():
    """Print the complete ITE table for reference."""
    print("=" * 80)
    print("Complete ITE Operator Table")
    print("=" * 80)
    print()
    print(f"{'Index':<8} {'Name':<15} {'Expression':<15} {'ITE Form':<20}")
    print("-" * 80)

    table = [
        ("0000", "0", "0", "ite(f, 0, 0)"),
        ("0001", "AND(f,g)", "f·g", "ite(f, g, 0)"),
        ("0010", "f>g", "f·ḡ", "ite(f, ḡ, 0)"),
        ("0011", "f", "f", "ite(f, 1, 0)"),
        ("0100", "f<g", "f̄·g", "ite(f, 0, g)"),
        ("0101", "g", "g", "ite(g, 1, 0)"),
        ("0110", "XOR(f,g)", "f⊕g", "ite(f, ḡ, g)"),
        ("0111", "OR(f,g)", "f+g", "ite(f, 1, g)"),
        ("1000", "NOR(f,g)", "f̄+ḡ", "ite(f, 0, ḡ)"),
        ("1001", "XNOR(f,g)", "f⊙ḡ", "ite(f, g, ḡ)"),
        ("1010", "NOT(g)", "ḡ", "ite(g, 0, 1)"),
        ("1011", "f≥g", "f+ḡ", "ite(f, 1, ḡ)"),
        ("1100", "NOT(f)", "f̄", "ite(f, 0, 1)"),
        ("1101", "f≤g", "f̄+g", "ite(f, g, 1)"),
        ("1110", "NAND(f,g)", "f̄g", "ite(f, ḡ, 1)"),
        ("1111", "1", "1", "ite(f, 1, 1)"),
    ]

    for idx, name, expr, ite_form in table:
        print(f"{idx:<8} {name:<15} {expr:<15} {ite_form:<20}")

    print()
    print("Note: Composite gates (f>g, f<g, f≥g, f≤g) are decomposed into")
    print("      standard cells: NOT + AND for GT/LT, NOT + OR for GTE/LTE")


def ite_to_gate_example():
    """Example usage of ITE table."""
    print("\n" + "=" * 60)
    print("ITE Table Examples")
    print("=" * 60 + "\n")

    # ITE(x, 1, 0) = x (BUFFER)
    gate1 = ITETable.create_gate_for_ite("x", "1", "0", False, True, True, "out1", 1)
    print(f"ITE(x, 1, 0): {gate1}  → BUFFER")

    # ITE(x, 0, 1) = NOT(x)
    gate2 = ITETable.create_gate_for_ite("x", "0", "1", False, True, True, "out2", 2)
    print(f"ITE(x, 0, 1): {gate2}  → NOT")

    # ITE(x, y, 0) = x AND y
    gate3 = ITETable.create_gate_for_ite("x", "y", "0", False, False, True, "out3", 3)
    print(f"ITE(x, y, 0): {gate3}  → AND")

    # ITE(x, 1, y) = x OR y
    gate4 = ITETable.create_gate_for_ite("x", "1", "y", False, True, False, "out4", 4)
    print(f"ITE(x, 1, y): {gate4}  → OR")

    # ITE(x, 0, y) = f < g = NOT(x) AND y
    gate5 = ITETable.create_gate_for_ite("x", "0", "y", False, True, False, "out5", 5)
    print(f"ITE(x, 0, y): {gate5}  → LT (NOT(x) AND y)")

    # ITE(x, y, 1) = f ≤ g = NOT(x) OR y
    gate6 = ITETable.create_gate_for_ite("x", "y", "1", False, False, True, "out6", 6)
    print(f"ITE(x, y, 1): {gate6}  → LTE (NOT(x) OR y)")

    # ITE(x, y, z) = MUX(x, y, z)
    gate7 = ITETable.create_gate_for_ite("x", "y", "z", False, False, False, "out7", 7)
    print(f"ITE(x, y, z): {gate7}  → MUX (decomposed)")


if __name__ == "__main__":
    print_ite_table()
    ite_to_gate_example()
