"""
Lab 3: BDD-based Netlist Generation and SystemVerilog Synthesis.

This module provides tools for converting Boolean functions to BDD
representation and generating gate-level netlists with SystemVerilog
simulation.
"""

from lab3.bdd import BDD, BDDNode
from lab3.netlist import Netlist
from lab3.ite_table import Gate, GateType, ITETable
from lab3.verilog_gen import VerilogGenerator

__all__ = [
    'BDD',
    'BDDNode',
    'Netlist',
    'Gate',
    'GateType',
    'ITETable',
    'VerilogGenerator',
]
