import argparse
import sys
import os

from .lower import lower_ir_to_llvm
from .passes import apply_all
from .integrity import inject_integrity_check
from .assemble import assemble


def main():
    parser = argparse.ArgumentParser(
        description="Nixon Shadow Compiler Stage 3: LLVM Codegen + Obfuscation"
    )
    parser.add_argument("input", nargs="?", help="Path to .ir file (reads from stdin if omitted)")
    parser.add_argument("-o", "--output", default="a.out",
                        help="Output object file path (default: a.out)")
    parser.add_argument("-O", "--ollvm-passes", nargs="+",
                        default=[],
                        choices=["bcf", "bogus", "fla", "flatten", "sub", "substitute"],
                        help="OLLVM obfuscation passes to apply")
    parser.add_argument("--module-name", default="nixon_module",
                        help="LLVM module name (default: nixon_module)")
    parser.add_argument("--integrity", action="store_true", default=True,
                        help="Inject .text integrity check (default: True)")
    parser.add_argument("--no-integrity", action="store_false", dest="integrity",
                        help="Skip .text integrity check injection")
    parser.add_argument("--emit-llvm", action="store_true",
                        help="Emit LLVM IR to stdout instead of assembling")
    parser.add_argument("--keep-ll", action="store_true",
                        help="Keep intermediate .ll file alongside output")

    args = parser.parse_args()

    if args.input:
        if not os.path.exists(args.input):
            print(f"Error: input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        with open(args.input, "r") as f:
            ir_text = f.read()
    else:
        ir_text = sys.stdin.read()

    if not ir_text.strip():
        print("Error: empty input", file=sys.stderr)
        sys.exit(1)

    try:
        llvm_ir = lower_ir_to_llvm(ir_text, module_name=args.module_name)
    except (SyntaxError, ValueError) as e:
        print(f"Error lowering IR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.ollvm_passes:
        llvm_ir = apply_all(llvm_ir, args.ollvm_passes)

    if args.integrity:
        llvm_ir = inject_integrity_check(llvm_ir)

    if args.emit_llvm:
        print(llvm_ir)
        return

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    if args.keep_ll:
        ll_path = args.output + ".ll" if not args.output.endswith(".o") else args.output[:-2] + ".ll"
        with open(ll_path, "w") as f:
            f.write(llvm_ir)
        print(f"LLVM IR saved to {ll_path}", file=sys.stderr)

    try:
        obj_path = assemble(llvm_ir, args.output)
        print(f"Object file: {obj_path}", file=sys.stderr)
    except RuntimeError as e:
        print(f"Assembly failed: {e}", file=sys.stderr)
        print("\n--- LLVM IR output for debugging ---", file=sys.stderr)
        print(llvm_ir[:5000], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
