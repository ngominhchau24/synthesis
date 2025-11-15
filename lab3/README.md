# Lab 3: BDD-based Netlist Generation

**Convert Boolean functions to BDD trees and generate gate-level netlists with SystemVerilog simulation.**

## Overview

This lab implements a complete synthesis flow from Boolean function specifications to gate-level netlists using Binary Decision Diagrams (BDDs):

1. **Parse** Boolean function specification (minterm format)
2. **Build BDD** using Shannon expansion and ITE operations
3. **Generate netlist** by applying ITE-to-gate lookup table
4. **Synthesize SystemVerilog** module and exhaustive testbench
5. **Simulate** with any SystemVerilog-compatible simulator

## Key Concepts

### Binary Decision Diagram (BDD)

A BDD is a canonical representation of a Boolean function using a directed acyclic graph. Each node represents a Shannon expansion:

```
f = x_i ? f_high : f_low
```

BDDs provide:
- **Canonical representation**: Same function → same BDD (with fixed variable ordering)
- **Efficient operations**: All Boolean ops via ITE (If-Then-Else)
- **Compact representation**: Shared subgraphs reduce size

### ITE (If-Then-Else) Operations

The fundamental BDD operation: `ITE(f, g, h) = f ? g : h`

All Boolean operations can be expressed using ITE:
- `NOT(f) = ITE(f, 0, 1)`
- `AND(f, g) = ITE(f, g, 0)`
- `OR(f, g) = ITE(f, 1, g)`
- `XOR(f, g) = ITE(f, NOT(g), g)`

### ITE-to-Gate Mapping

Each BDD node's ITE operation maps to standard logic gates:

| ITE Pattern | Gate | Description |
|-------------|------|-------------|
| `ITE(f, 1, 0)` | `BUFFER` | Identity |
| `ITE(f, 0, 1)` | `NOT` | Inverter |
| `ITE(f, g, 0)` | `AND` | Conjunction |
| `ITE(f, 1, g)` | `OR` | Disjunction |
| `ITE(f, g', g)` | `XOR` | Exclusive-OR |
| `ITE(f, g, h)` | `MUX` | 2-to-1 Multiplexer |

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  Boolean Specification                      │
│              f = sum{0,1,7} d{4}                           │
└────────────────┬───────────────────────────────────────────┘
                 │
                 │ parse (reuse lab1/truth_table.py)
                 ▼
┌────────────────────────────────────────────────────────────┐
│                     Truth Table                             │
│  x0 x1 x2 | f     (2^n rows)                               │
└────────────────┬───────────────────────────────────────────┘
                 │
                 │ build_from_truth_table (bdd.py)
                 │ • Shannon expansion
                 │ • Unique table (canonical form)
                 │ • Reduction (redundancy elimination)
                 ▼
┌────────────────────────────────────────────────────────────┐
│                  Binary Decision Diagram                    │
│                                                             │
│          ┌─── x0 ───┐                                      │
│          │           │                                      │
│        x1          x2                                       │
│        / \         / \                                      │
│       0   1       1   1                                     │
│                                                             │
└────────────────┬───────────────────────────────────────────┘
                 │
                 │ build_from_bdd (netlist.py)
                 │ • Post-order traversal
                 │ • ITE-to-gate mapping (ite_table.py)
                 ▼
┌────────────────────────────────────────────────────────────┐
│                   Gate-Level Netlist                        │
│                                                             │
│   n0 = MUX(x1, 1'b1, 1'b0)  // x1                          │
│   n1 = MUX(x2, 1'b1, 1'b1)  // 1                           │
│   f  = MUX(x0, n1, n0)      // x0 ? 1 : x1                 │
│                                                             │
└────────────────┬───────────────────────────────────────────┘
                 │
                 │ generate_module + generate_testbench
                 │ (verilog_gen.py)
                 ▼
┌────────────────────────────────────────────────────────────┐
│                   SystemVerilog Files                       │
│                                                             │
│  • module.sv        - Structural netlist                    │
│  • module_tb.sv     - Exhaustive testbench                  │
│                                                             │
└────────────────┬───────────────────────────────────────────┘
                 │
                 │ iverilog / verilator / commercial sim
                 ▼
┌────────────────────────────────────────────────────────────┐
│                  Simulation Results                         │
│                                                             │
│   x0 x1 x2 | out | exp | status                            │
│   ─────────────────────────────────                         │
│    0  0  0 |  0  |  0  | PASS                              │
│    0  0  1 |  1  |  1  | PASS                              │
│    ...                                                      │
│   *** TEST PASSED: All test cases passed! ***              │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Module Structure

```
lab3/
├── __init__.py         - Package exports
├── main.py             - CLI orchestrator
├── bdd.py              - BDD data structure & ITE operations
├── ite_table.py        - ITE-to-gate lookup table
├── netlist.py          - Gate-level netlist generation
├── verilog_gen.py      - SystemVerilog code generator
└── README.md           - This file

output/                 - Generated files (auto-created)
├── *.sv                - SystemVerilog modules
└── *_tb.sv             - SystemVerilog testbenches
```

## Usage

### Command Line Interface

```bash
# Generate random specification and synthesize
python3 lab3/main.py random [N] [M] [on_ratio] [dc_ratio]

# Synthesize from existing specification file
python3 lab3/main.py spec.txt [N]
```

**Parameters:**
- `N`: Number of input variables (default: 4 for random, 3 for spec)
- `M`: Number of output functions (default: 1)
- `on_ratio`: Fraction of ON minterms (default: 0.35, max: 0.5)
- `dc_ratio`: Fraction of don't-care minterms (default: 0.15)

### Examples

#### Example 1: Random 3-input, 1-output function

```bash
python3 lab3/main.py random 3 1 0.5 0.2
```

Output:
```
Generated random spec: random_spec.txt

============================================================
LAB 3: BDD-based Netlist Generation
============================================================

Step 1: Parsing specification file...
  Inputs: 3 variables: x0, x1, x2
  Outputs: 1 functions: f

Truth Table:
  x0 x1 x2 | f
  ─────────────
   0  0  0 | 1
   0  0  1 | 0
   0  1  0 | 1
   ...

------------------------------------------------------------
Processing output: f
------------------------------------------------------------
  ON-set: [0, 2, 5, 7]
  DC-set: [1, 3]

Step 2: Building BDD for f...
  BDD nodes (total): 5
  BDD nodes (non-terminal): 3

Step 3: Generating gate-level netlist for f...

=== Gate-Level Netlist ===
Inputs: x0, x1, x2
Gates: 4

  1. n0 = MUX(x2, 1'b1, 1'b0)
  2. n1 = MUX(x2, 1'b1, n0)
  3. n2 = MUX(x1, n1, n0)
  4. f = MUX(x0, 1'b1, n2)

=== Netlist Statistics ===
Total gates: 4
  MUX: 4

Step 4: Generating SystemVerilog for f...
Generated SystemVerilog module: output/random_spec_f.sv
Generated SystemVerilog testbench: output/random_spec_f_tb.sv
```

#### Example 2: Spec file

Create `example.txt`:
```
f = sum{0,1,2,7,9,11,12,15} d{4,10}
```

Run synthesis:
```bash
python3 lab3/main.py example.txt 4
```

### Simulation

Simulate generated SystemVerilog with Icarus Verilog:

```bash
cd output

# Compile and simulate
iverilog -g2012 -o sim example_f.sv example_f_tb.sv
./sim
```

Expected output:
```
Starting exhaustive test...
Testing 16 input combinations

  x0  x1  x2  x3  | out | exp | status
  -------------------------------------
  0   0   0   0   |  1  |  1  | PASS
  0   0   0   1   |  1  |  1  | PASS
  0   0   1   0   |  1  |  1  | PASS
  ...
  1   1   1   1   |  1  |  1  | PASS

*** TEST PASSED: All test cases passed! ***
```

## Algorithm Details

### BDD Construction (Shannon Expansion)

```python
def build_bdd(truth_table, var):
    if all values are 0: return Terminal_0
    if all values are 1: return Terminal_1

    # Split truth table by var
    low_half  = truth_table[var=0]
    high_half = truth_table[var=1]

    # Recursively build children
    low_bdd  = build_bdd(low_half, var+1)
    high_bdd = build_bdd(high_half, var+1)

    # Create node with reduction
    return make_node(var, low_bdd, high_bdd)
```

**Reduction rule**: If `low == high`, return `low` (eliminate redundant test)

### Netlist Generation (Post-order Traversal)

```python
def build_netlist(bdd_node):
    if is_terminal(bdd_node):
        return constant_signal

    # Process children first (post-order)
    low_signal  = build_netlist(bdd_node.low)
    high_signal = build_netlist(bdd_node.high)

    # Create gate for this node: ITE(var, high, low)
    gate = create_gate(bdd_node.var, high_signal, low_signal)

    return gate.output_signal
```

## Implementation Notes

### BDD Node Sharing

The `unique_table` ensures canonical representation:
```python
unique_table: (var, low_id, high_id) -> BDDNode
```

If a node with the same `(var, low, high)` tuple exists, reuse it.

### ITE Cache

The `ite_cache` memoizes ITE operations:
```python
ite_cache: (f_id, g_id, h_id) -> BDDNode
```

This dramatically speeds up BDD operations by avoiding recomputation.

### Gate Types

Generated netlists use these SystemVerilog primitives:
- `assign out = in;` (BUFFER)
- `assign out = ~in;` (NOT)
- `assign out = a & b;` (AND)
- `assign out = a | b;` (OR)
- `assign out = sel ? a : b;` (MUX)

## Testing

Each module can be tested individually:

```bash
# Test BDD construction
python3 -m lab3.bdd

# Test ITE table
python3 -m lab3.ite_table

# Test netlist generation
python3 -m lab3.netlist

# Test Verilog generation
python3 -m lab3.verilog_gen
```

## Comparison with Lab 1 & Lab 2

| Aspect | Lab 1 (QM) | Lab 2 (Espresso) | Lab 3 (BDD) |
|--------|------------|------------------|-------------|
| **Method** | Quine-McCluskey | Espresso REI | Binary Decision Diagram |
| **Output** | Sum-of-Products | Minimized Cubes | Gate-level Netlist |
| **Format** | Boolean algebra + PLA | PLA | SystemVerilog |
| **Optimization** | Exact (small inputs) | Heuristic (scalable) | Canonical (shared BDD) |
| **Simulation** | No | No | Yes (testbench) |

## Key Advantages of BDD Approach

1. **Canonical Representation**: Same function → same BDD structure
2. **Efficient Verification**: Equivalence checking via BDD comparison
3. **Gate-Level Output**: Directly synthesizable netlist
4. **Simulation Ready**: Includes exhaustive testbenches
5. **Scalability**: Polynomial in BDD size (not truth table size)

## Limitations

- **Variable Ordering Sensitivity**: BDD size depends critically on variable order
  - Good ordering: Linear size
  - Bad ordering: Exponential size
- **No Variable Reordering**: Current implementation uses fixed ordering (x0, x1, x2, ...)
- **Multiplexer Dominance**: May generate more MUXes than optimal AND/OR gates

## Future Enhancements

1. **Dynamic Variable Reordering**: Implement sifting algorithm
2. **Technology Mapping**: Map to specific gate library (NAND, NOR, etc.)
3. **Multi-Output Optimization**: Shared BDD nodes across outputs
4. **Area/Delay Optimization**: Minimize gate count or critical path
5. **Commercial Format Export**: BLIF, EDIF, Verilog structural netlist

## References

- Bryant, R.E. (1986). "Graph-Based Algorithms for Boolean Function Manipulation"
- Brace, K.S., et al. (1990). "Efficient Implementation of a BDD Package"
- Minato, S. (1993). "Zero-Suppressed BDDs for Set Manipulation"

## License

Educational use for digital logic synthesis course.
