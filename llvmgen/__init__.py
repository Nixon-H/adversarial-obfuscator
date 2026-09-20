from .lower import lower_ir_to_llvm
from .passes import apply_bcf, apply_fla, apply_sub, apply_all
from .integrity import inject_integrity_check
from .assemble import assemble
from .codegen import main

if __name__ == "__main__":
    main()
