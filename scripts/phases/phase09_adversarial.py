"""
phase09_adversarial.py

Purpose:
Adversarial self-improvement loop and adversarial injection.  The
adversarial loop uses a DeobfuscationAgent to score the obfuscated IR
and evolves the compiler config if the deobfuscation score is below
threshold.  Adversarial injection adds dead-code and prompt-injection
payloads into the obfuscated source.

Architectural Role:
Runs after baseline obfuscation.  The loop improves obfuscation quality
iteratively; the injection phase poisons the final payload.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, time, ..common, scripts.deobfuscation_agent,
scripts.compiler_mutation, obfuscator.adversarial

Security Relevance:
Raises the effective obfuscation strength by adversarial training
and poisons the payload against LLM-based deobfuscation.
"""

import json
import os
import time

from ..common import log, atomic_write, BUILD_DIR, DEFAULT_CONFIG


def phase_adversarial_loop(ir_path, opts):
    """
    Run the adversarial self-improvement loop.

    Scores the obfuscated IR, evolves the compiler config if the
    deobfuscation threshold is not met, and saves evolution history.

    Args:
        ir_path: path to the .ir file to analyze
        opts: argparse.Namespace with deobfuscation_threshold, evolution_iterations
    """
    log("ADVERSARIAL", "Running adversarial self-improvement loop...")

    try:
        from scripts.deobfuscation_agent import DeobfuscationAgent
        from scripts.compiler_mutation import CompilerMutationEngine
    except ImportError:
        log("SKIP", "deobfuscation_agent or compiler_mutation not importable")
        return

    threshold = opts.deobfuscation_threshold
    evolution_iterations = opts.evolution_iterations

    ad_config = {}
    if os.path.exists(DEFAULT_CONFIG):
        with open(DEFAULT_CONFIG, "r") as f:
            default = json.load(f)
        ad_config = default.get("shadow_compiler", {}).get("adversarial_loop", {})
        if not ad_config.get("enabled", False) and not opts.adversarial_loop:
            log("SKIP", "Adversarial loop not enabled")
            return

    agent = DeobfuscationAgent(ad_config)
    report = agent.analyze_obfuscated_ir(ir_path)
    feedback = agent.generate_feedback(report)

    score = report.deobfuscation_score
    log("ADVERSARIAL", f"Deobfuscation score: {score:.2f} (threshold: {threshold})")

    if score < threshold:
        log("ADVERSARIAL", f"Score below threshold — evolving compiler config ({evolution_iterations} iterations)")

        comp_cfg = {}
        if os.path.exists(DEFAULT_CONFIG):
            with open(DEFAULT_CONFIG, "r") as f:
                comp_cfg = json.load(f).get("shadow_compiler", {})

        engine = CompilerMutationEngine(comp_cfg)
        evolved_config = comp_cfg

        for i in range(evolution_iterations):
            evolved_config = engine.evolve(evolved_config, feedback)
            log("ADVERSARIAL", f"  Evolution step {i+1}: weaknesses={feedback['weaknesses']}")

        history_path = ad_config.get("history_file", os.path.join(BUILD_DIR, "evolution_history.json"))
        os.makedirs(os.path.dirname(history_path) if os.path.dirname(history_path) else ".", exist_ok=True)

        history = []
        if os.path.exists(history_path):
            try:
                with open(history_path, "r") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        history.append({
            "timestamp": time.time(),
            "iteration": len(history),
            "score": score,
            "threshold": threshold,
            "feedback": feedback,
            "config_snapshot": evolved_config,
        })

        atomic_write(history_path, json.dumps(history, indent=2))

        log("ADVERSARIAL", f"Evolution history saved to {history_path}")
    else:
        log("ADVERSARIAL", "Score above threshold — no mutation needed")

    log("ADVERSARIAL", "Adversarial loop complete")


def phase_adversarial_injection(payload, output, opts):
    """
    Inject adversarial dead code and prompt-injection patterns into the payload.

    Args:
        payload: path to input .py file
        output: path for the modified output
        opts: argparse.Namespace with adversarial_level and phase2 config
    """
    log("ADVERSARIAL_INJ", "Running adversarial injection (dead code + prompt injection)...")

    phase2_cfg = vars(opts).get("_phase2_cfg", {})

    enabled = (phase2_cfg.get("enabled", False) and phase2_cfg.get("features", {}).get("adversarial", False)) or getattr(opts, "adversarial_injection", False)
    if not enabled:
        log("SKIP", "Adversarial injection not enabled (enable via --phase2 or --adversarial-injection)")
        return

    try:
        from obfuscator.adversarial import inject_adversarial_code
    except ImportError:
        log("SKIP", "obfuscator.adversarial not importable, skipping")
        return

    with open(payload, "r") as f:
        source = f.read()

    level = getattr(opts, "adversarial_level", 3)
    seed = hash(payload + str(opts)) & 0xFFFFFFFF

    modified = inject_adversarial_code(source, {
        "seed": seed,
        "level": level,
        "dead_code_types": ["all"],
        "prompt_injection": True,
    })

    atomic_write(output, modified)

    size = os.path.getsize(output)
    log("ADVERSARIAL_INJ", f"Done: {size/1024:.1f}KB (injected into obfuscated payload)")
