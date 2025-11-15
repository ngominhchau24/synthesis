"""
Binary Decision Diagram (BDD) implementation with ITE operations.

This module provides:
- BDD node structure with unique table for canonical representation
- Shannon expansion for BDD construction
- ITE (If-Then-Else) operation for Boolean manipulation
- Conversion from truth tables to BDD
"""

from __future__ import annotations
from typing import Dict, Tuple, Optional, Set, List


class BDDNode:
    """Represents a node in a Binary Decision Diagram.

    A BDD node represents the Shannon expansion:
        f = var ? high : low

    Terminal nodes (0 and 1) have var = -1.
    """

    def __init__(self, var: int, low: 'BDDNode', high: 'BDDNode', node_id: int):
        """Initialize a BDD node.

        Args:
            var: Variable index (-1 for terminal nodes)
            low: Low (else) child when var=0
            high: High (then) child when var=1
            node_id: Unique identifier for this node
        """
        self.var = var
        self.low = low
        self.high = high
        self.id = node_id

    def is_terminal(self) -> bool:
        """Check if this is a terminal node (0 or 1)."""
        return self.var == -1

    def __repr__(self) -> str:
        if self.is_terminal():
            return f"Terminal({self.id})"
        return f"Node(id={self.id}, var=x{self.var}, low={self.low.id}, high={self.high.id})"


class BDD:
    """Binary Decision Diagram manager.

    Maintains unique table for canonical representation and provides
    operations for BDD construction and manipulation.
    """

    def __init__(self, num_vars: int):
        """Initialize BDD manager.

        Args:
            num_vars: Number of Boolean variables
        """
        self.num_vars = num_vars
        self.next_id = 2  # 0 and 1 are reserved for terminals

        # Terminal nodes
        self.zero = BDDNode(-1, None, None, 0)  # type: ignore
        self.one = BDDNode(-1, None, None, 1)   # type: ignore

        # Unique table: (var, low_id, high_id) -> BDDNode
        self.unique_table: Dict[Tuple[int, int, int], BDDNode] = {}

        # ITE cache: (f_id, g_id, h_id) -> BDDNode
        self.ite_cache: Dict[Tuple[int, int, int], BDDNode] = {}

        # All nodes for traversal
        self.all_nodes: Dict[int, BDDNode] = {0: self.zero, 1: self.one}

    def make_node(self, var: int, low: BDDNode, high: BDDNode) -> BDDNode:
        """Create or retrieve a BDD node (with reduction).

        Implements the fundamental BDD reduction rule:
        If low == high, return low (redundancy elimination).

        Args:
            var: Variable index
            low: Low child
            high: High child

        Returns:
            Canonical BDD node
        """
        # Reduction: if low == high, eliminate redundant node
        if low.id == high.id:
            return low

        # Check unique table
        key = (var, low.id, high.id)
        if key in self.unique_table:
            return self.unique_table[key]

        # Create new node
        node = BDDNode(var, low, high, self.next_id)
        self.next_id += 1
        self.unique_table[key] = node
        self.all_nodes[node.id] = node
        return node

    def ite(self, f: BDDNode, g: BDDNode, h: BDDNode) -> BDDNode:
        """ITE (If-Then-Else) operation: if f then g else h.

        This is the fundamental operation for BDD manipulation.
        All Boolean operations can be expressed using ITE:
        - NOT(f) = ITE(f, 0, 1)
        - AND(f, g) = ITE(f, g, 0)
        - OR(f, g) = ITE(f, 1, g)
        - XOR(f, g) = ITE(f, NOT(g), g)

        Args:
            f: Condition BDD
            g: Then BDD
            h: Else BDD

        Returns:
            BDD representing (f ? g : h)
        """
        # Terminal cases
        if f.id == 1:  # f is TRUE
            return g
        if f.id == 0:  # f is FALSE
            return h
        if g.id == h.id:  # g == h
            return g
        if g.id == 1 and h.id == 0:  # ITE(f, 1, 0) = f
            return f
        if g.id == 0 and h.id == 1:  # ITE(f, 0, 1) = NOT(f)
            return self.ite(f, self.zero, self.one)

        # Check cache
        cache_key = (f.id, g.id, h.id)
        if cache_key in self.ite_cache:
            return self.ite_cache[cache_key]

        # Find top variable (smallest index among non-terminals)
        top_var = self._find_top_var([f, g, h])

        # Shannon expansion
        f_low, f_high = self._cofactors(f, top_var)
        g_low, g_high = self._cofactors(g, top_var)
        h_low, h_high = self._cofactors(h, top_var)

        # Recursive ITE
        low = self.ite(f_low, g_low, h_low)
        high = self.ite(f_high, g_high, h_high)

        # Build result node
        result = self.make_node(top_var, low, high)
        self.ite_cache[cache_key] = result
        return result

    def _find_top_var(self, nodes: List[BDDNode]) -> int:
        """Find the topmost (smallest index) variable among nodes."""
        top_var = float('inf')
        for node in nodes:
            if not node.is_terminal() and node.var < top_var:
                top_var = node.var
        return int(top_var)

    def _cofactors(self, f: BDDNode, var: int) -> Tuple[BDDNode, BDDNode]:
        """Get cofactors of f with respect to var.

        Returns:
            (f|var=0, f|var=1)
        """
        if f.is_terminal() or f.var != var:
            return f, f
        return f.low, f.high

    def build_from_truth_table(self, truth_table: List[int], var_names: List[str]) -> BDDNode:
        """Build BDD from truth table using Shannon expansion.

        Args:
            truth_table: List of output values (0 or 1) for each input combination.
                        Index i corresponds to binary representation of input.
            var_names: List of variable names (for reference)

        Returns:
            Root BDD node representing the function
        """
        if len(truth_table) != 2 ** self.num_vars:
            raise ValueError(f"Truth table size {len(truth_table)} != 2^{self.num_vars}")

        return self._build_recursive(truth_table, 0, 2 ** self.num_vars, 0)

    def _build_recursive(self, truth_table: List[int], start: int, end: int, var: int) -> BDDNode:
        """Recursively build BDD using Shannon decomposition.

        Args:
            truth_table: Full truth table
            start: Start index for this subtable
            end: End index for this subtable
            var: Current variable index

        Returns:
            BDD node for this subtable
        """
        # Check if all values are the same
        values = truth_table[start:end]
        if all(v == 0 for v in values):
            return self.zero
        if all(v == 1 for v in values):
            return self.one

        # Base case: only one variable left
        if var >= self.num_vars:
            # Should not reach here if truth table is consistent
            return self.one if truth_table[start] == 1 else self.zero

        # Shannon expansion: f = x_var * f_high + x_var' * f_low
        mid = start + (end - start) // 2

        # f_low: when var = 0
        f_low = self._build_recursive(truth_table, start, mid, var + 1)

        # f_high: when var = 1
        f_high = self._build_recursive(truth_table, mid, end, var + 1)

        return self.make_node(var, f_low, f_high)

    def build_from_minterm_spec(self, n_inputs: int, on_set: Set[int], dc_set: Set[int]) -> BDDNode:
        """Build BDD from minterm specification (on-set + don't-care set).

        Args:
            n_inputs: Number of input variables
            on_set: Set of minterm indices where function = 1
            dc_set: Set of don't-care minterm indices

        Returns:
            BDD node (don't-cares are treated as 0)
        """
        truth_table = []
        for i in range(2 ** n_inputs):
            if i in on_set:
                truth_table.append(1)
            else:
                truth_table.append(0)  # DC treated as 0 for canonical BDD

        var_names = [f"x{i}" for i in range(n_inputs)]
        return self.build_from_truth_table(truth_table, var_names)

    def get_node_count(self) -> int:
        """Get total number of nodes (including terminals)."""
        return len(self.all_nodes)

    def get_non_terminal_count(self) -> int:
        """Get number of non-terminal nodes."""
        return len([n for n in self.all_nodes.values() if not n.is_terminal()])

    def print_bdd(self, root: BDDNode, indent: int = 0):
        """Print BDD structure for debugging."""
        if root.is_terminal():
            print("  " * indent + f"Terminal({root.id})")
            return

        print("  " * indent + f"Node {root.id}: x{root.var}")
        print("  " * indent + "  LOW:")
        self.print_bdd(root.low, indent + 2)
        print("  " * indent + "  HIGH:")
        self.print_bdd(root.high, indent + 2)


def example_usage():
    """Example: Build BDD for f = x0 AND x1."""
    bdd = BDD(num_vars=2)

    # Truth table for AND: [0, 0, 0, 1] for inputs [00, 01, 10, 11]
    truth_table = [0, 0, 0, 1]
    var_names = ["x0", "x1"]

    root = bdd.build_from_truth_table(truth_table, var_names)

    print("BDD for f = x0 AND x1:")
    bdd.print_bdd(root)
    print(f"\nTotal nodes: {bdd.get_node_count()}")
    print(f"Non-terminal nodes: {bdd.get_non_terminal_count()}")


if __name__ == "__main__":
    example_usage()
