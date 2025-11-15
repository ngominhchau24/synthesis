"""
Netlist generation from BDD using ITE decomposition.

Converts BDD nodes to gate-level netlist by traversing the BDD
and applying ITE-to-gate mappings.
"""

from __future__ import annotations
from typing import Dict, List, Set
import sys
import os

# Handle both module import and direct execution
try:
    from lab3.bdd import BDD, BDDNode
    from lab3.ite_table import Gate, GateType, ITETable
except ModuleNotFoundError:
    from bdd import BDD, BDDNode
    from ite_table import Gate, GateType, ITETable


class Netlist:
    """Represents a gate-level netlist."""

    def __init__(self, num_inputs: int, var_names: List[str]):
        """Initialize netlist.

        Args:
            num_inputs: Number of input variables
            var_names: List of input variable names
        """
        self.num_inputs = num_inputs
        self.var_names = var_names
        self.gates: List[Gate] = []
        self.next_gate_id = 0
        self.next_wire_id = 0

        # Signal naming: node_id -> signal_name
        self.signal_map: Dict[int, str] = {}

    def add_gate(self, gate: Gate):
        """Add a gate to the netlist."""
        self.gates.append(gate)

    def get_wire_name(self) -> str:
        """Generate a new internal wire name."""
        name = f"n{self.next_wire_id}"
        self.next_wire_id += 1
        return name

    def get_gate_id(self) -> int:
        """Generate a new gate ID."""
        gate_id = self.next_gate_id
        self.next_gate_id += 1
        return gate_id

    def build_from_bdd(self, bdd: BDD, root: BDDNode, output_name: str = "out"):
        """Build netlist from BDD using post-order traversal.

        Each BDD node represents: if var then high else low
        Which maps to: ITE(var, high, low)

        Args:
            bdd: BDD manager
            root: Root node of the BDD
            output_name: Name for the output signal
        """
        # Initialize signal map for terminals and inputs
        self.signal_map[0] = "1'b0"  # Terminal 0
        self.signal_map[1] = "1'b1"  # Terminal 1

        # Traverse BDD in post-order (bottom-up)
        visited: Set[int] = set()
        self._traverse_and_build(root, visited)

        # Map output
        if root.id in self.signal_map:
            # If root maps to a signal, create buffer to output
            root_signal = self.signal_map[root.id]
            if root_signal not in ["1'b0", "1'b1"]:
                gate = Gate(GateType.BUFFER, output_name, [root_signal], self.get_gate_id())
                self.add_gate(gate)
            else:
                # Constant output
                self.signal_map[root.id] = output_name

    def _traverse_and_build(self, node: BDDNode, visited: Set[int]):
        """Recursively traverse BDD and build gates.

        Args:
            node: Current BDD node
            visited: Set of visited node IDs
        """
        if node.id in visited:
            return

        visited.add(node.id)

        # Terminal nodes already mapped
        if node.is_terminal():
            return

        # Recursively process children
        self._traverse_and_build(node.low, visited)
        self._traverse_and_build(node.high, visited)

        # Get signal names for children
        low_signal = self.signal_map.get(node.low.id)
        high_signal = self.signal_map.get(node.high.id)
        var_signal = self.var_names[node.var]

        # Create wire for this node's output
        node_output = self.get_wire_name()
        self.signal_map[node.id] = node_output

        # Determine if operands are constants
        low_is_const = low_signal in ["1'b0", "1'b1"]
        high_is_const = high_signal in ["1'b0", "1'b1"]
        var_is_const = False  # Variables are never constant

        # Create gate: ITE(var, high, low)
        gate = ITETable.create_gate_for_ite(
            f=var_signal,
            g=high_signal,
            h=low_signal,
            f_is_const=var_is_const,
            g_is_const=high_is_const,
            h_is_const=low_is_const,
            output=node_output,
            gate_id=self.get_gate_id()
        )

        self.add_gate(gate)

    def print_netlist(self):
        """Print netlist in human-readable format."""
        print("\n=== Gate-Level Netlist ===")
        print(f"Inputs: {', '.join(self.var_names)}")
        print(f"Gates: {len(self.gates)}\n")

        for i, gate in enumerate(self.gates, 1):
            print(f"  {i}. {gate}")

    def get_stats(self) -> Dict[str, int]:
        """Get netlist statistics.

        Returns:
            Dictionary with gate type counts
        """
        stats = {gate_type.value: 0 for gate_type in GateType}
        for gate in self.gates:
            stats[gate.gate_type.value] += 1
        return stats

    def print_stats(self):
        """Print netlist statistics."""
        stats = self.get_stats()
        print("\n=== Netlist Statistics ===")
        print(f"Total gates: {len(self.gates)}")
        for gate_type, count in sorted(stats.items()):
            if count > 0:
                print(f"  {gate_type}: {count}")


def example_netlist():
    """Example: Generate netlist for f = x0 AND x1."""
    try:
        from lab3.bdd import BDD
    except ModuleNotFoundError:
        from bdd import BDD

    print("Example: Generate netlist for f = x0 AND x1")
    print("Truth table: [0, 0, 0, 1] for inputs [00, 01, 10, 11]\n")

    # Build BDD
    bdd = BDD(num_vars=2)
    truth_table = [0, 0, 0, 1]
    var_names = ["x0", "x1"]
    root = bdd.build_from_truth_table(truth_table, var_names)

    # Generate netlist
    netlist = Netlist(num_inputs=2, var_names=var_names)
    netlist.build_from_bdd(bdd, root, output_name="f")

    # Print results
    netlist.print_netlist()
    netlist.print_stats()


if __name__ == "__main__":
    example_netlist()
