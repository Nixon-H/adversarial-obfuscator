"""Dead code is a claim you cannot back.

On 2026-10-23 ten Rust modules (4,046 lines) and thirteen native
sources were archived. They were compiled, or compile-tested, and
unreachable: nothing could run them. In this project that was not
merely untidy — the feature report counted "a module with this name
exists" as evidence of a shipped protection, so dead code is what made
the report lie.

These tests make the decision stick:

* every module declared in `runtime/src/lib.rs` must be reachable from
  `init_runtime`;
* nothing in `archive/` may be declared or built;
* `native/` may only contain sources the build actually uses, and each
  one must be referenced by the build.

If you restore something from `archive/`, you must also wire it — that
is the point.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = Path(__file__).resolve().parent.parent

# Sources that are genuinely compiled, linked or tested by the product.
KEPT_NATIVE = {"core.cpp", "whitebox_feistel.cpp", "simd_vm.c", "simd_vm_test.c"}

# Build files that may reference a kept native source.
BUILD_REFERERS = (
    "Makefile",
    "obfuscator/core/c_core_build.py",
    "relay/build.rs",
    "relay/Cargo.toml",
    "scripts/build.py",
    "scripts/phases/phase03_compile.py",
)


def _without_comments(text):
    """Drop whole-line comments so a note about an archived file does not
    look like a build reference."""
    return "\n".join(
        ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
    )


class TestRustReachability:
    def test_every_declared_module_is_reachable(self):
        from scripts.reachability import rust_callgraph as cg
        unreachable = cg.unreachable_modules()
        assert unreachable == set(), (
            "these modules are compiled but unreachable from init_runtime: "
            f"{sorted(unreachable)} — wire them or archive them"
        )

    def test_archived_modules_are_not_declared(self):
        from scripts.reachability import rust_callgraph as cg
        declared = cg.module_declarations()
        archived = {p.stem for p in (ROOT / "archive" / "rust-runtime").glob("*.rs")}
        assert archived, "archive/rust-runtime is empty — did it get deleted?"
        overlap = archived & declared
        assert not overlap, f"archived modules are still compiled: {sorted(overlap)}"

    def test_archive_has_a_readme(self):
        readme = ROOT / "archive" / "rust-runtime" / "README.md"
        assert readme.exists(), "archive without a rationale is just a skip"


class TestNativeCorpus:
    def test_native_holds_only_kept_sources(self):
        present = {p.name for p in (ROOT / "native").glob("*.c")}
        present |= {p.name for p in (ROOT / "native").glob("*.cpp")}
        extra = present - KEPT_NATIVE
        assert not extra, (
            f"native/ contains sources the product does not build: {sorted(extra)}. "
            "Wire them or move them to archive/native/"
        )

    def test_kept_sources_are_referenced_by_the_build(self):
        text = "\n".join(
            (ROOT / rel).read_text(errors="replace")
            for rel in BUILD_REFERERS
            if (ROOT / rel).exists()
        )
        for name in KEPT_NATIVE:
            assert name in text, f"native/{name} is kept but no build file references it"

    def test_archived_sources_are_not_built(self):
        archived = {p.name for p in (ROOT / "archive" / "native").glob("*.c")}
        archived |= {p.name for p in (ROOT / "archive" / "native").glob("*.cpp")}
        assert archived, "archive/native is empty — did it get deleted?"
        text = "\n".join(
            _without_comments((ROOT / rel).read_text(errors="replace"))
            for rel in BUILD_REFERERS
            if (ROOT / rel).exists()
        )
        # A real build path, not a mention: the archive READMEs and the
        # Makefile note deliberately name these files.
        built = [n for n in archived if f"native/{n}" in text]
        assert not built, f"archived sources are still referenced by the build: {sorted(built)}"

    def test_archive_has_a_readme(self):
        readme = ROOT / "archive" / "native" / "README.md"
        assert readme.exists(), "archive without a rationale is just a skip"


class TestNoOpFallbacks:
    def test_lowering_does_not_emit_errors_as_comments(self):
        """A failed instruction used to become `; ERROR: ...` while its
        result stayed in use. Check the source has no such handler."""
        src = (ROOT / "llvmgen" / "lower.py").read_text()
        assert '; ERROR: ' not in src, \
            "a lowering failure is being emitted as a comment again"
