"""Entry point: `python -m llvmgen`.

Pass selection and label naming are randomised.  Setting
NIXON_LLVM_SEED pins the RNG so a build is reproducible -- used by
the shadow-build smoke job, where an unpinned run is a fuzz test and
a rare invalid-IR seed fails the job for a reason unrelated to the
change under test.
"""
import os
import random

if os.environ.get("NIXON_LLVM_SEED"):
    try:
        random.seed(int(os.environ["NIXON_LLVM_SEED"], 0))
    except ValueError:
        pass

from .codegen import main  # noqa: E402

main()
