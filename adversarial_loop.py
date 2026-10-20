#!/usr/bin/env python3
"""
adversarial_loop.py — Automated adversarial training loop for AI obfuscation.

Benchmark → analyze AI deobfuscation → improve obfuscator → rebuild → repeat
until all 4 free models score PROOF 3 consecutive rounds.
"""

import json, logging, os, sys, shutil, subprocess, ast
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("adversarial")

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
BENCHMARK_SCRIPT = ROOT / "scripts" / "evaluation" / "ai_resistance.py"
SOURCE_PAYLOAD = ROOT / "tests" / "test_data" / "test_multi_func.py"
PAYLOAD = BUILD_DIR / f"{SOURCE_PAYLOAD.stem}_obfuscated.py"
BUILD_SCRIPT = ROOT / "scripts" / "build.py"
TRANSFORMS = ROOT / "obfuscator" / "core" / "transforms.py"
DATAFLOW = ROOT / "obfuscator" / "dataflow.py"
DECOY_APIS = ROOT / "obfuscator" / "decoy_apis.py"
ATTN_POISON = ROOT / "obfuscator" / "attention_poison.py"
REASON_TRAPS = ROOT / "obfuscator" / "reasoning_traps.py"

PROOF_THRESHOLD = 80  # score >= 80 = PROOF
CONSECUTIVE_TARGET = 3
MAX_ROUNDS = 50

# ─── Knob state ──────────────────────────────────────────────────────────────

class KnobState:
    def __init__(self):
        self.mba_depth = 3
        self.mba_dataflow_depth = 2
        self.predicate_prob = 0.60
        self.decoy_count = 5
        self.attention_fanout = 0
        self.trap_depth = 5
        self.variable_parts = 2
        self.mba_K_max = 999999
        self.mba_dataflow_K_max = 9999999
        self.non_ascii_safe = True
        self.llm_depth = 15
        self.llm_dead_vars = 50

    def escalate(self, signals: list[str]):
        """Increase knob levels based on what AI succeeded at."""
        for sig in signals:
            if sig == "genuine_deobfuscation":
                self.mba_depth = min(self.mba_depth + 5, 30)
                self.mba_dataflow_depth = min(self.mba_dataflow_depth + 5, 30)
                self.predicate_prob = min(self.predicate_prob + 0.15, 1.0)
            if sig == "decoded_mba":
                self.mba_depth = min(self.mba_depth + 3, 30)
                self.mba_K_max = min(self.mba_K_max * 100, 10**15)
            if sig == "renamed_unicode":
                self.non_ascii_safe = False
            if sig == "simplified_predicates":
                self.predicate_prob = min(self.predicate_prob + 0.2, 1.0)
            if sig == "extracted_imports":
                self.decoy_count = min(self.decoy_count + 5, 50)
            if sig == "untangled_flow":
                self.attention_fanout = min(self.attention_fanout + 20, 200)
            if sig == "followed_traps":
                self.trap_depth = min(self.trap_depth + 5, 30)
            if sig == "split_var_reversed":
                self.variable_parts = min(self.variable_parts + 2, 12)
            if sig == "used_symbolic_exec":
                self.llm_depth = min(self.llm_depth + 20, 200)
                self.llm_dead_vars = min(self.llm_dead_vars + 100, 1000)
        # Generic escalation: turn everything up a notch
        self.mba_depth = min(int(self.mba_depth * 1.3) + 1, 30)
        self.mba_dataflow_depth = min(int(self.mba_dataflow_depth * 1.3) + 1, 30)
        self.predicate_prob = min(self.predicate_prob * 1.1 + 0.05, 1.0)
        self.decoy_count = min(int(self.decoy_count * 1.2) + 1, 50)
        self.attention_fanout = min(int(self.attention_fanout * 1.2) + 2, 200)
        self.trap_depth = min(int(self.trap_depth * 1.2) + 1, 30)
        self.variable_parts = min(int(self.variable_parts * 1.2) + 1, 12)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


# ─── Analysis ────────────────────────────────────────────────────────────────

def _has_deobfuscation_logic(output: str) -> bool:
    """Check if output contains actual deobfuscation/analysis logic."""
    deobf_keywords = ["def ", "class ", "import ", "from ", "=", "lambda",
                      "exec", "eval", "compile", "__import__", "base64",
                      "unmarshal", "zlib", "lzma", "marshal", "decompress"]
    code_keywords = sum(1 for kw in deobf_keywords if kw in output)
    return code_keywords >= 4


def _is_copy_paste(output: str, original: str) -> bool:
    """Check if output is mostly copy-pasted from input."""
    if not output or not original:
        return False
    out_lines = set(output.splitlines())
    orig_lines = set(original.splitlines())
    if not out_lines or not orig_lines:
        return False
    overlap = len(out_lines & orig_lines) / max(len(out_lines), 1)
    return overlap > 0.2


def _is_valid_python(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _is_unrelated_code(output: str, original: str) -> bool:
    """Check if output is valid Python but completely unrelated to original."""
    if not _is_valid_python(output):
        return False
    if _is_copy_paste(output, original):
        return False
    # If output has no overlap with original and is valid Python → unrelated
    out_lines = set(output.splitlines())
    orig_lines = set(original.splitlines())
    overlap = len(out_lines & orig_lines) / max(len(out_lines), 1) if out_lines and orig_lines else 0
    return overlap < 0.05 and len(output.strip()) > 20


def analyze_model_output(model: str, result: dict, original: str) -> list[str]:
    signals = []
    output = result.get("deobfuscated", "") or ""

    if not output:
        return ["no_output"]

    # If model genuinely produced deobfuscated code (low copy, valid Python, has logic)
    if _is_valid_python(output) and not _is_copy_paste(output, original) and _has_deobfuscation_logic(output):
        signals.append("genuine_deobfuscation")
        logger.info("  %s: GENUINE DEOBFUSCATION detected", model)

    # Check specific patterns in output
    if any(p in output for p in ["pow(", "mod=", "opaque", "xor", "lambda"]):
        signals.append("decoded_mba")
    if any(ord(c) > 127 for c in output if c.isalpha()):
        signals.append("renamed_unicode")
    if any(p in output for p in ["while True", "while 1", "if True"]):
        signals.append("simplified_predicates")
    if "exec" in output or "__import__" in output or "importlib" in output:
        signals.append("extracted_imports")
    if "break" in output or "continue" in output:
        signals.append("untangled_flow")
    if "_nx_trap" in output or "trap" in output:
        signals.append("followed_traps")
    if "split" in output or "frag" in output:
        signals.append("split_var_reversed")
    if "z3" in output or "sympy" in output or "solver" in output:
        signals.append("used_symbolic_exec")

    logger.info("  %s signals: %s", model, signals)
    return signals


def is_genuine_deobfuscation(result: dict, original: str) -> bool:
    """True if model genuinely deobfuscated (not copy-paste, not unrelated, not analysis)."""
    output = result.get("deobfuscated", "") or ""
    if not output:
        return False
    if _is_unrelated_code(output, original):
        return False
    if _is_copy_paste(output, original):
        return False
    if not _has_deobfuscation_logic(output):
        return False
    return True


# ─── File Modifications ──────────────────────────────────────────────────────

def _replace_in_file(filepath: Path, old: str, new: str) -> int:
    content = filepath.read_text()
    if old not in content:
        logger.warning("  Pattern not found in %s", filepath.name)
        return 0
    count = content.count(old)
    content = content.replace(old, new)
    filepath.write_text(content)
    logger.info("  Patched %s (%d occurrences)", filepath.name, count)
    return count


BACKUP_DIR = ROOT / ".originals"
SOURCE_FILES = [TRANSFORMS, DATAFLOW, DECOY_APIS, ATTN_POISON, REASON_TRAPS]

def _reset_source_files():
    """Reset obfuscator source files to clean state from backup."""
    for fp in SOURCE_FILES:
        backup = BACKUP_DIR / fp.name
        if backup.exists():
            shutil.copy2(str(backup), str(fp))
    logger.info("Reset obfuscator source files to clean state")


def apply_improvements(knobs: KnobState) -> int:
    """Apply current knob state to obfuscator source files. Returns count of changes."""
    _reset_source_files()
    changes = 0

    # 1. MBA chain call-site depth in visit_BinOp (transforms.py)
    lo = max(1, knobs.mba_depth // 2)
    hi = knobs.mba_depth
    changes += _replace_in_file(TRANSFORMS,
        "depth=random.randint(2, 5)",
        f"depth=random.randint({lo}, {hi})")
    changes += _replace_in_file(TRANSFORMS,
        "depth=random.randint(2, 4)",
        f"depth=random.randint({lo}, {min(hi, lo+2)})")

    # 2. MBA K ranges in transforms.py
    changes += _replace_in_file(TRANSFORMS,
        "random.randint(1000, 999999)",
        f"random.randint(1000, {knobs.mba_K_max})")
    changes += _replace_in_file(TRANSFORMS,
        "random.randint(100, 999999)",
        f"random.randint(100, {knobs.mba_K_max})")
    changes += _replace_in_file(TRANSFORMS,
        "random.randint(1, 999999)",
        f"random.randint(1, {knobs.mba_K_max})")
    changes += _replace_in_file(TRANSFORMS,
        "random.randint(2, min(9999, 9999))",
        f"random.randint(2, min(9999, {knobs.mba_K_max//100}))")
    changes += _replace_in_file(TRANSFORMS,
        "k = random.randint(10, min(999, 999))",
        f"k = random.randint(10, min(999, {knobs.mba_K_max//1000}))")

    # 3. MBA dataflow: call-site depth in mba_encode_value
    lo2 = max(1, knobs.mba_dataflow_depth // 2)
    hi2 = knobs.mba_dataflow_depth
    changes += _replace_in_file(DATAFLOW,
        "depth=_random.randint(1, 2)",
        f"depth=_random.randint({lo2}, {hi2})")

    # 4. MBA dataflow K ranges (uses _rnd, not random)
    changes += _replace_in_file(DATAFLOW,
        "_rnd.randint(1000, 9999999)",
        f"_rnd.randint(1000, {knobs.mba_dataflow_K_max})")
    changes += _replace_in_file(DATAFLOW,
        "_rnd.randint(1, 9999999)",
        f"_rnd.randint(1, {knobs.mba_dataflow_K_max})")
    changes += _replace_in_file(DATAFLOW,
        "_rnd.randint(100, 9999999)",
        f"_rnd.randint(100, {knobs.mba_dataflow_K_max})")
    changes += _replace_in_file(DATAFLOW,
        "_rnd.randint(2, min(9999, 99999))",
        f"_rnd.randint(2, min(9999, {knobs.mba_dataflow_K_max//100}))")

    # 5. Opaque predicate probability (current backup values: 0.60, 0.75)
    o1 = 0.60
    o2 = 0.75
    if knobs.predicate_prob != o1:
        changes += _replace_in_file(TRANSFORMS,
            f"if random.random() < {o1:.2f}:",
            f"if random.random() < {knobs.predicate_prob - 0.15:.2f}:")
    if knobs.predicate_prob != o2:
        changes += _replace_in_file(TRANSFORMS,
            f"if len(node.body) > 2 and random.random() < {o2:.2f}:",
            f"if len(node.body) > 2 and random.random() < {knobs.predicate_prob:.2f}:")

    # 6. BinOp substitution probability (current: 0.47, 0.62)
    sub_prob1 = max(0.05, 0.65 - knobs.predicate_prob * 0.3)
    sub_prob2 = min(0.9, 0.62 + (knobs.predicate_prob - 0.75) * 0.5)
    changes += _replace_in_file(TRANSFORMS,
        "if random.random() > 0.47:",
        f"if random.random() > {sub_prob1:.2f}:")
    changes += _replace_in_file(TRANSFORMS,
        "elif random.random() < 0.62 and isinstance(node.right, ast.Constant) and isinstance(node.right.value, int):",
        f"elif random.random() < {sub_prob2:.2f} and isinstance(node.right, ast.Constant) and isinstance(node.right.value, int):")

    # 7. Decoy API count (current: count: int = 10)
    changes += _replace_in_file(DECOY_APIS,
        "def __init__(self, count: int = 10):",
        f"def __init__(self, count: int = {knobs.decoy_count}):")

    # 8. Attention poison fan-out (current: fan_out: int = 15)
    changes += _replace_in_file(ATTN_POISON,
        "def __init__(self, fan_out: int = 15):",
        f"def __init__(self, fan_out: int = {knobs.attention_fanout}):")

    # 9. Trap depth (current: depth: int = 5)
    changes += _replace_in_file(REASON_TRAPS,
        "def inject_loop(self, tree: ast.AST, depth: int = 5) -> ast.AST:",
        f"def inject_loop(self, tree: ast.AST, depth: int = {knobs.trap_depth}) -> ast.AST:")

    # 10. Variable split parts — signature is multiline, skip for now
    # (can add via build flag or manual edit later)

    # 11. Affine state registers
    changes += _replace_in_file(DATAFLOW,
        "def __init__(self, seed: bytes, num_registers: int = 16):",
        f"def __init__(self, seed: bytes, num_registers: int = {min(knobs.variable_parts * 8, 64)}):")

    # 12. Unicode safe mode
    if not knobs.non_ascii_safe:
        changes += _replace_in_file(TRANSFORMS,
            "self._use_safe_mode = True",
            "self._use_safe_mode = False")

    logger.info("Applied %d obfuscator improvements", changes)
    return changes


def rebuild_payload(knobs: Optional[KnobState] = None) -> bool:
    """Run the build pipeline."""
    logger.info("Rebuilding payload...")
    cmd = [
        sys.executable, str(BUILD_SCRIPT),
        "--payload", str(SOURCE_PAYLOAD),
        "--skip-irgen", "--skip-llvmgen", "--skip-encrypt", "--skip-relay",
        "--mba-subs", "--opaque-predicates",
        "--decoy-apis",
    ]
    if knobs:
        cmd += [f"--decoy-api-count={knobs.decoy_count}",
                f"--attention-poison={knobs.attention_fanout}",
                f"--trap-depth={knobs.trap_depth}"]
    else:
        cmd += ["--decoy-api-count", "5"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        logger.error("Build failed:\n%s", result.stderr[:2000])
        return False
    logger.info("Build succeeded (rc=%d)", result.returncode)
    return True


def run_benchmark(output_dir: str) -> dict:
    """Run the full benchmark and return parsed results."""
    logger.info("Running benchmark...")
    os.makedirs(output_dir, exist_ok=True)
    result = subprocess.run([
        sys.executable, str(BENCHMARK_SCRIPT),
        "--payload", str(PAYLOAD),
        "--max-tokens", "4096",
        "--timeout", "300",
        "--output-dir", output_dir,
    ], capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        logger.error("Benchmark failed:\n%s", result.stderr[:2000])
    report_path = Path(output_dir) / "benchmark_report.json"
    if report_path.exists():
        data = json.loads(report_path.read_text())
        # Attach model outputs for analysis
        for model in data.get("results", {}):
            deobf_path = Path(output_dir) / f"{model}_deobf_output.py"
            if deobf_path.exists():
                data["results"][model]["deobfuscated"] = deobf_path.read_text()
            else:
                data["results"][model]["deobfuscated"] = ""
        logger.info("Benchmark complete:\n%s", json.dumps(
            {m: f"{r['score']['score']} {r['score']['label']}"
             for m, r in data.get("results", {}).items()}, indent=2))
        return data
    logger.error("No benchmark report found at %s", report_path)
    return {"results": {}, "_failed": True}


def check_regressions() -> bool:
    """Run existing tests to verify no regressions."""
    tests = list(ROOT.glob("test_*.py")) + list(ROOT.glob("tests/test_*.py"))
    if not tests:
        logger.info("No test files found, skipping regression check")
        return True
    # Run the 3 obfuscation test files specifically
    for test_file in ["test_mba_validator.py", "test_opaque_predicates.py", "test_dataflow_mba.py"]:
        tp = ROOT / test_file
        if tp.exists():
            result = subprocess.run([sys.executable, str(tp)], capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error("Regression in %s:\n%s", test_file, result.stderr[:1000])
                return False
            logger.info("  %s: PASS", test_file)
    return True


# ─── Main Loop ───────────────────────────────────────────────────────────────

def main():
    round_num = 0
    consecutive_proof = 0
    knobs = KnobState()

    # Load original payload for comparison
    original = PAYLOAD.read_text() if PAYLOAD.exists() else ""

    logger.info("=" * 60)
    logger.info("ADVERSARIAL IMPROVEMENT LOOP")
    logger.info("Target: %d consecutive rounds all-PROOF", CONSECUTIVE_TARGET)
    logger.info("=" * 60)

    while round_num < MAX_ROUNDS:
        round_num += 1
        logger.info("\n%s ROUND %d %s", "=" * 20, round_num, "=" * 20)
        logger.info("Knobs: %s", json.dumps(knobs.to_dict()))

        # Phase 0: Reset source files to clean state
        _reset_source_files()

        # Phase 1: Apply improvements to source
        if round_num > 1:
            apply_improvements(knobs)
        # For round 1, source files are already clean (just reset)

        # Phase 2: Check regressions
        if not check_regressions():
            logger.error("Regression detected, rolling back...")
            _reset_source_files()
            knobs = KnobState()
            continue

        # Phase 3: Rebuild payload
        if not rebuild_payload(knobs):
            logger.error("Build failed, rolling back...")
            _reset_source_files()
            knobs = KnobState()
            continue
        original = PAYLOAD.read_text()

        # Phase 4: Benchmark
        output_dir = f"adversarial_output/round_{round_num:03d}"
        benchmark = run_benchmark(output_dir)
        results = benchmark.get("results", {})

        # Check if benchmark actually ran
        if benchmark.get("_failed") or not results:
            logger.error("Benchmark did not produce results, retrying round...")
            round_num -= 1  # Don't count this round
            continue

        # Phase 5: Analyze results
        any_genuine = False
        all_signals = []
        for model, result in results.items():
            signals = analyze_model_output(model, result, original)
            all_signals.extend(signals)
            if is_genuine_deobfuscation(result, original):
                any_genuine = True
            score = result.get("score", {}).get("score", 0)
            label = result.get("score", {}).get("label", "?")
            logger.info("  %s: %d %s", model, score, label)

        # Phase 6: Check if all PROOF
        all_proof = all(
            result.get("score", {}).get("score", 0) >= PROOF_THRESHOLD
            for result in results.values()
        )

        if all_proof:
            consecutive_proof += 1
            logger.info("\n>>> ALL PROOF — round %d/%d <<<", consecutive_proof, CONSECUTIVE_TARGET)
            if consecutive_proof >= CONSECUTIVE_TARGET:
                logger.info("\n" + "=" * 60)
                logger.info("TARGET ACHIEVED — %d consecutive all-PROOF rounds!", CONSECUTIVE_TARGET)
                logger.info("=" * 60)
                break
        else:
            if consecutive_proof > 0:
                logger.info("Streak broken at %d", consecutive_proof)
            consecutive_proof = 0

        # Phase 7: Escalate knobs based on what AI succeeded at
        if any_genuine:
            knobs.escalate(all_signals)
            logger.info("Escalating knobs (genuine deobfuscation detected)")
        elif not all_proof:
            # Minimal escalation only when models still score below PROOF
            knobs.mba_depth = min(knobs.mba_depth + 1, 20)
            logger.info("Gentle escalation (some models below PROOF)")
        else:
            logger.info("All PROOF — no escalation needed")

    if round_num >= MAX_ROUNDS:
        logger.warning("Reached max rounds (%d) without achieving %d consecutive PROOF",
                       MAX_ROUNDS, CONSECUTIVE_TARGET)

    # Save final state
    final = {
        "rounds": round_num,
        "consecutive_proof": consecutive_proof,
        "target_achieved": consecutive_proof >= CONSECUTIVE_TARGET,
        "final_knobs": knobs.to_dict(),
    }
    (ROOT / "adversarial_state.json").write_text(json.dumps(final, indent=2))
    logger.info("Final state saved to adversarial_state.json")
    logger.info("Final knobs: %s", json.dumps(knobs.to_dict(), indent=2))


if __name__ == "__main__":
    main()
