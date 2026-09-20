"""
__init__.py

Purpose:
Package initializer for the IR generation and transformation module.
Compiles Python source into a custom intermediate representation (IR),
applies optimization passes, and provides obfuscation transforms such as
bit-slicing, chaff circuits, mutation, watermarking, and TEE partitioning.

Architectural Role:
Central IR pipeline. All higher-level transformations (VM compilation,
LLVM codegen, binary encryption) consume IR produced by this module.
The compile() and optimize() functions form the base of the pipeline.

Security Relevance:
Provides the foundational IR-level obfuscation primitives. Each
transform (bitslice, chaff, mutation, watermark, TEE partition)
operates at the IR level, making them composable and architecture-
independent.

Exports:
  - compile_py_to_ir, ir_module_to_text, optimize
  - IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType
"""

from .compile import compile_py_to_ir, ir_module_to_text, IrModule, IrFunction, IrBlock, IrInstruction, IrValue, IrType
from .optimize import optimize

__all__ = [
    "compile_py_to_ir", "ir_module_to_text", "optimize",
    "IrModule", "IrFunction", "IrBlock", "IrInstruction", "IrValue", "IrType",
]


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Nixon IR Compiler - compile obfuscated Python to Custom IR"
    )
    parser.add_argument("input", help="Input Python source file")
    parser.add_argument("-o", "--output", default=None, help="Output IR file")
    parser.add_argument("-O", "--optimize", type=int, default=2, choices=[0, 1, 2],
                        help="Optimization level (default: 2)")

    args = parser.parse_args()

    with open(args.input, "r") as f:
        source = f.read()

    module = compile_py_to_ir(source)
    if args.optimize > 0:
        module = optimize(module, level=args.optimize)

    ir_text = ir_module_to_text(module)

    if args.output:
        with open(args.output, "w") as f:
            f.write(ir_text)
        print(f"IR written to {args.output}")
    else:
        print(ir_text)


if __name__ == "__main__":
    main()
