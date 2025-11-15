"""
ITE (If-Then-Else) lookup table for gate-level synthesis.

Maps ITE operations to standard logic gates:
- ITE(f, 1, 0) = f (BUFFER)
- ITE(f, 0, 1) = NOT(f)
- ITE(f, g, 0) = f AND g
- ITE(f, 1, g) = f OR g
- ITE(f, g', g) = f XOR g
- ITE(f, g, h) = (f AND g) OR (NOT(f) AND h) (MUX)
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
    MUX = "MUX"  # 2-to-1 multiplexer


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
    """Lookup table for converting ITE operations to gates."""

    @staticmethod
    def identify_pattern(f_is_const: bool, g_is_const: bool, h_is_const: bool,
                         f_val: Optional[int], g_val: Optional[int], h_val: Optional[int]) -> Optional[GateType]:
        """Identify gate pattern from ITE(f, g, h) operand types.

        Args:
            f_is_const: True if f is a constant
            g_is_const: True if g is a constant
            h_is_const: True if h is a constant
            f_val: Value if f is constant (0 or 1)
            g_val: Value if g is constant (0 or 1)
            h_val: Value if h is constant (0 or 1)

        Returns:
            GateType if pattern matches, None otherwise
        """
        # ITE(f, 1, 0) = f (BUFFER)
        if g_is_const and h_is_const and g_val == 1 and h_val == 0:
            return GateType.BUFFER

        # ITE(f, 0, 1) = NOT(f)
        if g_is_const and h_is_const and g_val == 0 and h_val == 1:
            return GateType.NOT

        # ITE(f, g, 0) = f AND g
        if h_is_const and h_val == 0 and not g_is_const:
            return GateType.AND

        # ITE(f, 1, g) = f OR g
        if g_is_const and g_val == 1 and not h_is_const:
            return GateType.OR

        # ITE(f, 0, g) = NOT(f) AND g = AND(NOT(f), g)
        # This is more complex, handled in netlist generation

        # ITE(f, g, 1) = NOT(f) OR g = OR(NOT(f), g)
        # This is more complex, handled in netlist generation

        # General case: MUX
        if not g_is_const and not h_is_const:
            return GateType.MUX

        return None

    @staticmethod
    def create_gate_for_ite(f: str, g: str, h: str,
                           f_is_const: bool, g_is_const: bool, h_is_const: bool,
                           output: str, gate_id: int) -> Gate:
        """Create a gate for ITE(f, g, h) operation.

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
        # Extract constant values if applicable
        f_val = int(f) if f_is_const and f in ['0', '1'] else None
        g_val = int(g) if g_is_const and g in ['0', '1'] else None
        h_val = int(h) if h_is_const and h in ['0', '1'] else None

        pattern = ITETable.identify_pattern(f_is_const, g_is_const, h_is_const,
                                           f_val, g_val, h_val)

        if pattern == GateType.BUFFER:
            return Gate(GateType.BUFFER, output, [f], gate_id)

        elif pattern == GateType.NOT:
            return Gate(GateType.NOT, output, [f], gate_id)

        elif pattern == GateType.AND:
            return Gate(GateType.AND, output, [f, g], gate_id)

        elif pattern == GateType.OR:
            return Gate(GateType.OR, output, [f, h], gate_id)

        elif pattern == GateType.MUX:
            # MUX: out = f ? g : h
            return Gate(GateType.MUX, output, [f, g, h], gate_id)

        else:
            # Default: treat as MUX
            return Gate(GateType.MUX, output, [f, g, h], gate_id)


def ite_to_gate_example():
    """Example usage of ITE table."""
    # ITE(x, 1, 0) = x
    gate1 = ITETable.create_gate_for_ite("x", "1", "0", False, True, True, "out1", 1)
    print(f"ITE(x, 1, 0): {gate1}")

    # ITE(x, 0, 1) = NOT(x)
    gate2 = ITETable.create_gate_for_ite("x", "0", "1", False, True, True, "out2", 2)
    print(f"ITE(x, 0, 1): {gate2}")

    # ITE(x, y, 0) = x AND y
    gate3 = ITETable.create_gate_for_ite("x", "y", "0", False, False, True, "out3", 3)
    print(f"ITE(x, y, 0): {gate3}")

    # ITE(x, 1, y) = x OR y
    gate4 = ITETable.create_gate_for_ite("x", "1", "y", False, True, False, "out4", 4)
    print(f"ITE(x, 1, y): {gate4}")

    # ITE(x, y, z) = MUX(x, y, z)
    gate5 = ITETable.create_gate_for_ite("x", "y", "z", False, False, False, "out5", 5)
    print(f"ITE(x, y, z): {gate5}")


if __name__ == "__main__":
    ite_to_gate_example()
