"""
SystemVerilog code generation from gate-level netlist.

Generates:
1. Structural SystemVerilog module from netlist
2. Testbench for exhaustive simulation
"""

from __future__ import annotations
from typing import List, TextIO

# Handle both module import and direct execution
try:
    from lab3.netlist import Netlist
    from lab3.ite_table import Gate, GateType
except ModuleNotFoundError:
    from netlist import Netlist
    from ite_table import Gate, GateType


class VerilogGenerator:
    """Generates SystemVerilog code from netlist."""

    def __init__(self, netlist: Netlist, module_name: str = "circuit", output_name: str = "out"):
        """Initialize generator.

        Args:
            netlist: Gate-level netlist
            module_name: Name for the SystemVerilog module
            output_name: Name for the output port (default: "out")
        """
        self.netlist = netlist
        self.module_name = module_name
        self.output_name = output_name

    def generate_module(self, filename: str):
        """Generate SystemVerilog module file.

        Args:
            filename: Output .sv file path
        """
        with open(filename, 'w') as f:
            self._write_module_header(f)
            self._write_wire_declarations(f)
            self._write_gate_instances(f)
            self._write_module_footer(f)

        print(f"Generated SystemVerilog module: {filename}")

    def _write_module_header(self, f: TextIO):
        """Write module header with ports."""
        f.write(f"// Generated SystemVerilog module from BDD netlist\n")
        f.write(f"// Inputs: {', '.join(self.netlist.var_names)}\n")
        f.write(f"// Gates: {len(self.netlist.gates)}\n\n")

        f.write(f"module {self.module_name} (\n")

        # Input ports
        for i, var in enumerate(self.netlist.var_names):
            f.write(f"    input  logic {var},\n")

        # Output port
        f.write(f"    output logic {self.output_name}\n")
        f.write(");\n\n")

    def _write_wire_declarations(self, f: TextIO):
        """Write internal wire declarations."""
        # Collect all internal wires (n0, n1, n2, ...)
        wires = set()
        for gate in self.netlist.gates:
            # Output wire
            if gate.output.startswith('n'):
                wires.add(gate.output)
            # Input wires (excluding primary inputs and constants)
            for inp in gate.inputs:
                if inp.startswith('n'):
                    wires.add(inp)

        if wires:
            f.write("    // Internal wires\n")
            for wire in sorted(wires):
                f.write(f"    logic {wire};\n")
            f.write("\n")

        # Assign constants if used
        has_const_0 = any("1'b0" in gate.inputs for gate in self.netlist.gates)
        has_const_1 = any("1'b1" in gate.inputs for gate in self.netlist.gates)

        if has_const_0 or has_const_1:
            f.write("    // Constants\n")
        if has_const_0:
            f.write("    logic const_0 = 1'b0;\n")
        if has_const_1:
            f.write("    logic const_1 = 1'b1;\n")
        if has_const_0 or has_const_1:
            f.write("\n")

    def _write_gate_instances(self, f: TextIO):
        """Write gate instances."""
        f.write("    // Gate instances\n")

        for i, gate in enumerate(self.netlist.gates):
            self._write_gate_instance(f, gate, i)

        f.write("\n")

    def _write_gate_instance(self, f: TextIO, gate: Gate, index: int):
        """Write a single gate instance.

        Args:
            f: File handle
            gate: Gate to instantiate
            index: Gate index for unique naming
        """
        # Replace constants with signal names
        inputs = []
        for inp in gate.inputs:
            if inp == "1'b0":
                inputs.append("const_0")
            elif inp == "1'b1":
                inputs.append("const_1")
            else:
                inputs.append(inp)

        if gate.gate_type == GateType.BUFFER:
            f.write(f"    assign {gate.output} = {inputs[0]};\n")

        elif gate.gate_type == GateType.NOT:
            f.write(f"    assign {gate.output} = ~{inputs[0]};\n")

        elif gate.gate_type == GateType.AND:
            f.write(f"    assign {gate.output} = {inputs[0]} & {inputs[1]};\n")

        elif gate.gate_type == GateType.OR:
            f.write(f"    assign {gate.output} = {inputs[0]} | {inputs[1]};\n")

        elif gate.gate_type == GateType.NAND:
            f.write(f"    assign {gate.output} = ~({inputs[0]} & {inputs[1]});\n")

        elif gate.gate_type == GateType.NOR:
            f.write(f"    assign {gate.output} = ~({inputs[0]} | {inputs[1]});\n")

        elif gate.gate_type == GateType.XOR:
            f.write(f"    assign {gate.output} = {inputs[0]} ^ {inputs[1]};\n")

        elif gate.gate_type == GateType.XNOR:
            f.write(f"    assign {gate.output} = ~({inputs[0]} ^ {inputs[1]});\n")

        elif gate.gate_type == GateType.MUX:
            # MUX: out = sel ? in1 : in0
            # ITE(sel, in1, in0)
            sel, in1, in0 = inputs[0], inputs[1], inputs[2]
            f.write(f"    assign {gate.output} = {sel} ? {in1} : {in0};\n")

    def _write_module_footer(self, f: TextIO):
        """Write module footer."""
        f.write("endmodule\n")

    def generate_testbench(self, filename: str, expected_outputs: List[int]):
        """Generate SystemVerilog testbench with exhaustive testing.

        Args:
            filename: Output testbench .sv file path
            expected_outputs: Expected output for each input combination
        """
        with open(filename, 'w') as f:
            self._write_tb_header(f)
            self._write_tb_signals(f)
            self._write_tb_dut(f)
            self._write_tb_test(f, expected_outputs)
            self._write_tb_footer(f)

        print(f"Generated SystemVerilog testbench: {filename}")

    def _write_tb_header(self, f: TextIO):
        """Write testbench header."""
        f.write(f"// Testbench for {self.module_name}\n")
        f.write(f"// Exhaustive simulation of all {2 ** self.netlist.num_inputs} input combinations\n\n")
        f.write(f"module {self.module_name}_tb;\n\n")

    def _write_tb_signals(self, f: TextIO):
        """Write testbench signals."""
        f.write("    // Testbench signals\n")
        for var in self.netlist.var_names:
            f.write(f"    logic {var};\n")
        f.write(f"    logic {self.output_name};\n")
        f.write("    logic expected;\n")
        f.write("    int errors = 0;\n\n")

    def _write_tb_dut(self, f: TextIO):
        """Write DUT instantiation."""
        f.write("    // DUT instantiation\n")
        f.write(f"    {self.module_name} dut (\n")
        for i, var in enumerate(self.netlist.var_names):
            f.write(f"        .{var}({var}),\n")
        f.write(f"        .{self.output_name}({self.output_name})\n")
        f.write("    );\n\n")

    def _write_tb_test(self, f: TextIO, expected_outputs: List[int]):
        """Write test stimulus and checking.

        Args:
            f: File handle
            expected_outputs: Expected output for each input combination
        """
        f.write("    // Test stimulus\n")
        f.write("    initial begin\n")
        f.write("        $display(\"Starting exhaustive test...\");\n")
        f.write(f"        $display(\"Testing {2 ** self.netlist.num_inputs} input combinations\");\n")
        f.write("        $display(\"\");\n\n")

        # Header
        output_col_name = self.output_name if len(self.output_name) <= 3 else "out"
        header = f"        $display(\"  " + "  ".join(self.netlist.var_names) + f"  | {output_col_name} | exp | status\");\n"
        f.write(header)
        f.write("        $display(\"  " + "-" * (len(self.netlist.var_names) * 4 + 20) + "\");\n\n")

        # Test each combination
        num_inputs = self.netlist.num_inputs
        for i in range(2 ** num_inputs):
            # Generate input pattern
            pattern = format(i, f'0{num_inputs}b')

            # Set inputs
            f.write("        // Test case {}\n".format(i))
            for j, bit in enumerate(pattern):
                f.write(f"        {self.netlist.var_names[j]} = 1'b{bit};\n")

            # Expected output
            exp_out = expected_outputs[i] if i < len(expected_outputs) else 0
            f.write(f"        expected = 1'b{exp_out};\n")
            f.write("        #10;\n\n")

            # Check result
            f.write(f"        if ({self.output_name} !== expected) begin\n")
            f.write("            errors++;\n")

            # Format output display
            input_display = "  ".join([f"%b" for _ in range(num_inputs)])
            f.write(f"            $display(\"  {input_display}  |  %b  |  %b  | FAIL\", " +
                   ", ".join(self.netlist.var_names) + f", {self.output_name}, expected);\n")
            f.write("        end else begin\n")
            f.write(f"            $display(\"  {input_display}  |  %b  |  %b  | PASS\", " +
                   ", ".join(self.netlist.var_names) + f", {self.output_name}, expected);\n")
            f.write("        end\n\n")

        # Final report
        f.write("        $display(\"\");\n")
        f.write("        if (errors == 0)\n")
        f.write("            $display(\"*** TEST PASSED: All test cases passed! ***\");\n")
        f.write("        else\n")
        f.write("            $display(\"*** TEST FAILED: %0d errors detected ***\", errors);\n\n")

        f.write("        $finish;\n")
        f.write("    end\n\n")

    def _write_tb_footer(self, f: TextIO):
        """Write testbench footer."""
        f.write("endmodule\n")


def example_verilog():
    """Example: Generate Verilog for f = x0 AND x1."""
    try:
        from lab3.bdd import BDD
        from lab3.netlist import Netlist
    except ModuleNotFoundError:
        from bdd import BDD
        from netlist import Netlist

    print("Example: Generate SystemVerilog for f = x0 AND x1\n")

    # Build BDD
    bdd = BDD(num_vars=2)
    truth_table = [0, 0, 0, 1]
    var_names = ["x0", "x1"]
    root = bdd.build_from_truth_table(truth_table, var_names)

    # Generate netlist
    netlist = Netlist(num_inputs=2, var_names=var_names)
    netlist.build_from_bdd(bdd, root, output_name="out")

    # Generate Verilog
    vgen = VerilogGenerator(netlist, module_name="and_gate")
    vgen.generate_module("and_gate.sv")
    vgen.generate_testbench("and_gate_tb.sv", truth_table)


if __name__ == "__main__":
    example_verilog()
