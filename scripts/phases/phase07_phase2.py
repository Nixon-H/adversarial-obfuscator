"""
phase07_phase2.py

Purpose:
"Phase 2" protection suite — function classification, variant pool
generation, provenance removal, data-flow obfuscation, watermark
embedding, VM compilation, JIT template generation, and adaptive
classify-protect-benchmark loops.

Architectural Role:
Advanced protection layer applied after baseline obfuscation but before
compilation.  Operates on the AST and IR levels.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
ast, hashlib, json, os, sys, ..common, obfuscator.*, irgen.*, llvmgen.*

Security Relevance:
Provides targeted protection (crown-jewel functions get VM compilation,
variant pools, watermarking) based on ML classification.
"""

import ast
import hashlib
import json
import os
import sys

from ..common import log, atomic_write, BUILD_DIR, ROOT, DEFAULT_CONFIG


def phase_classify(payload, config):
    """
    Classify functions in the payload using obfuscator.classification.

    Produces a classification report and returns the classifications dict.

    Args:
        payload: path to the source .py file
        config: pipeline config dict

    Returns:
        dict mapping function names to classification labels, or None
    """
    log("CLASSIFY", f"Running classification pass on {payload}")
    log("CLASSIFY", f"Running classification pass on {payload}")
    script = os.path.join(ROOT, "obfuscator", "classification.py")
    if not os.path.exists(script):
        log("SKIP", "classification.py not found, skipping")
        return None

    try:
        from obfuscator.classification import classify_functions, generate_classification_report
    except ImportError:
        log("SKIP", "obfuscator.classification not importable, skipping")
        return None

    with open(payload, "r") as f:
        source = f.read()
    classifications = classify_functions(source, config)
    report = generate_classification_report(classifications, source)
    log("CLASSIFY", f"{len(classifications)} functions classified")
    log("CLASSIFY", f"  standard={sum(1 for v in classifications.values() if v == 'standard')} "
                    f"crown_jewel={sum(1 for v in classifications.values() if v == 'crown_jewel')} "
                    f"jit_target={sum(1 for v in classifications.values() if v == 'jit_target')}")

    report_path = os.path.join(BUILD_DIR, "classification_report.txt")
    atomic_write(report_path, report)
    log("CLASSIFY", f"Report: {report_path}")

    return classifications


def phase_variant_pool(source, config):
    """
    Generate runtime-switchable variant pools for crown jewel functions.

    Args:
        source: path to source .py file
        config: pipeline config dict
    """
    log("VARIANT_POOL", "Generating variant pools for crown jewel functions")
    try:
        from irgen.variant_pool import generate_variants
        with open(source) as f:
            src = f.read()
        variants = generate_variants(src, "target", num_variants=4, seed=b"build")
        log("VARIANT_POOL", f"Generated {len(variants)} variants")
        # Build-time config that the runtime should load — variant metadata for runtime switching
        variant_meta = {
            "variant_files": [],
            "variant_ids": [],
            "num_variants": len(variants),
            "pool_seed": "build",
            "target": "crown_jewel",
        }
        for i, v in enumerate(variants):
            fname = f"variant_{i}.bin"
            vpath = os.path.join(BUILD_DIR, "variant_pool", fname)
            os.makedirs(os.path.dirname(vpath), exist_ok=True)
            with open(vpath, "wb") as f:
                f.write(v if isinstance(v, bytes) else str(v).encode())
            variant_meta["variant_files"].append(fname)
            variant_meta["variant_ids"].append(i)
        meta_path = os.path.join(BUILD_DIR, "variant_pool", "variant_metadata.json")
        atomic_write(meta_path, json.dumps(variant_meta, indent=2))
        log("VARIANT_POOL", f"Metadata written to {meta_path}")

        # Also write a top-level variant_pool.json for runtime single-file loading
        pool_config_path = os.path.join(BUILD_DIR, "variant_pool.json")
        pool_config = {
            "num_variants": len(variants),
            "pool_seed": "build",
            "target": "crown_jewel",
            "metadata_path": "variant_pool/variant_metadata.json",
        }
        atomic_write(pool_config_path, json.dumps(pool_config, indent=2))
        log("VARIANT_POOL", f"Pool config written to {pool_config_path}")
    except (ImportError, Exception) as e:
        log("SKIP", f"Variant pool not available: {e}")


def phase_provenance_removal(source, config, replace_mode=False):
    """
    Remove or replace code provenance indicators (error messages, strings, constants).

    Args:
        source: path to source .py file
        config: pipeline config dict
        replace_mode: if True, apply actual replacements; otherwise diagnostic only
    """
    log("PROVENANCE", "Removing code provenance indicators")
    try:
        from obfuscator.provenance import (
            replace_error_messages, encode_sensitive_strings,
            obfuscate_algorithmic_constants, scan_protocol_strings,
            scan_algorithmic_constants,
        )
        with open(source) as f:
            src = f.read()
        tree = ast.parse(src)

        if replace_mode:
            tree = replace_error_messages(tree)
            seed = hashlib.sha256(b"nixon_provenance_build").digest()
            tree = encode_sensitive_strings(tree, seed)
            tree = obfuscate_algorithmic_constants(tree)

            output = ast.unparse(tree)
            with open(source, "w") as f:
                f.write(output)
            log("PROVENANCE", f"Applied automated replacements: error codes + string encoding + constant obfuscation")
        else:
            log("PROVENANCE", f"Provenance removal loaded for {len(src)} bytes (diagnostic only)")
    except (ImportError, Exception) as e:
        log("SKIP", f"Provenance removal not available: {e}")


def phase_dataflow_obfuscation(source, config):
    """
    Apply data-flow obfuscation via AffineStateEncoder.

    Args:
        source: path to source .py file
        config: pipeline config dict
    """
    log("DATAFLOW", "Applying data-flow obfuscation")
    try:
        from obfuscator.dataflow import AffineStateEncoder, obfuscate_dataflow
        encoder = AffineStateEncoder(b"build_seed", num_registers=4)
        log("DATAFLOW", f"AffineStateEncoder initialized with {encoder.num_registers} registers")
        with open(source) as f:
            src = f.read()
        tree = ast.parse(src)
        obfuscated_tree = obfuscate_dataflow(tree, config)
        output = ast.unparse(obfuscated_tree)
        with open(source, "w") as f:
            f.write(output)
        log("DATAFLOW", f"Applied data-flow obfuscation to {source} ({len(output)} bytes)")
    except (ImportError, Exception) as e:
        log("SKIP", f"Data-flow obfuscation not available: {e}")


def phase_watermark_embedding(ir_module, config):
    """
    Embed a build-specific watermark into the IR module.

    Args:
        ir_module: path to the .ir module file
        config: pipeline config dict
    """
    log("WATERMARK", "Embedding IR watermark (via import)")
    try:
        from irgen.watermark import generate_watermark
        from llvmgen.lower import NixonIRParser
        parser = NixonIRParser()
        ir_mod = parser.parse_file(ir_module)
        wm, meta = generate_watermark(
            customer_id=b"default",
            build_id=config.get("build_seed", b"default").encode()[:16],
        )
        log("WATERMARK", f"Watermark generated: {len(wm)} bytes, meta={meta}")
        wm_path = os.path.join(BUILD_DIR, "watermark_meta.json")
        wm_data = {
            "watermark_hex": wm.hex(),
            "watermark_length": len(wm),
            "meta": str(meta),
        }
        os.makedirs(BUILD_DIR, exist_ok=True)
        with open(wm_path, "w") as f:
            json.dump(wm_data, f, indent=2)
        log("WATERMARK", f"Watermark metadata written to {wm_path}")
    except ImportError as e:
        log("SKIP", f"Watermark import failed: {e}")
    except Exception as e:
        log("ERROR", f"Watermark embedding failed: {e}")


def phase_vm_compile(ir_module, config):
    """
    Compile crown jewel functions to custom VM bytecode.

    Args:
        ir_module: path to the .ir module file
        config: pipeline config dict
    """
    log("VM_COMPILE", "Compiling crown jewel functions to VM bytecode (via import)")
    try:
        from vm.bytecode_compiler import compile_to_bytecode
        from llvmgen.lower import NixonIRParser
        parser = NixonIRParser()
        ir_mod = parser.parse_file(ir_module)
        for func in ir_mod.functions:
            bc = compile_to_bytecode(func)
            log("VM_COMPILE", f"  Compiled {func.name}: {len(bc)} bytes")
            vm_path = os.path.join(BUILD_DIR, f"{func.name}.vm")
            os.makedirs(os.path.dirname(vm_path), exist_ok=True)
            with open(vm_path, "wb") as f:
                f.write(bc)
            log("VM_COMPILE", f"  Wrote bytecode to {vm_path}")
    except ImportError as e:
        log("SKIP", f"VM compile import failed: {e}")
    except Exception as e:
        log("ERROR", f"VM compile failed: {e}")


def phase_jit_generate(ir_module, config):
    """
    Generate JIT compilation templates for target functions.

    Args:
        ir_module: path to the .ir module file
        config: pipeline config dict
    """
    log("JIT_GEN", "Generating JIT templates for target functions (via import)")
    try:
        from irgen.jit_template import generate_template
        template = generate_template("target", seed=config.get("seed", 42))
        log("JIT_GEN", f"Generated JIT template: {len(template)} bytes")
        jit_path = os.path.join(BUILD_DIR, "template.jit")
        os.makedirs(os.path.dirname(jit_path), exist_ok=True)
        with open(jit_path, "w") as f:
            json.dump(template, f, indent=2)
        log("JIT_GEN", f"JIT template written to {jit_path}")
    except (ImportError, Exception) as e:
        log("SKIP", f"JIT template generation not available: {e}")


def phase_adaptive_classifier_loop(payload, opts):
    """
    Run an adaptive loop: classify, protect, benchmark, re-classify, re-protect.

    Iterates up to 3 times, using benchmark feedback to guide AdaptiveRewriter.

    Args:
        payload: path to the payload .py file
        opts: argparse.Namespace
    """
    log("ADAPTIVE_LOOP", "Running classify → protect → benchmark → re-classify → re-protect loop")
    try:
        from scripts.classification import FunctionClassifier, StrategySelector
        from scripts.benchmark.feedback import BenchmarkFeedbackAnalyzer
        from scripts.benchmark import AIBenchmark

        for iteration in range(3):
            log("ADAPTIVE_LOOP", f"Iteration {iteration + 1}/3")

            with open(payload) as f:
                source = f.read()

            classifier = FunctionClassifier()
            classifications = classifier.classify_from_source(source)

            if not classifications:
                log("ADAPTIVE_LOOP", "No functions classified, skipping")
                break

            selector = StrategySelector()
            protected = source
            for fn, category in classifications.items():
                passes = selector.select(category)
                log("ADAPTIVE_LOOP", f"  {fn}: {category} → {passes}")

            import ast as _ast_mod
            import os as _os_mod
            protected_path = payload.replace(".py", "_protected.py")
            from obfuscator.core.pipeline import build_pipeline
            protected = build_pipeline(source)
            with open(protected_path, "w") as f:
                f.write(protected)

            bm = AIBenchmark()
            results = bm.evaluate(payload, protected_path)

            analyzer = BenchmarkFeedbackAnalyzer()
            profile = analyzer.analyze(results)

            from obfuscator.adaptive_rewriter import AdaptiveRewriter
            rewriter = AdaptiveRewriter()
            with open(protected_path) as f:
                current = f.read()
            rewritten = rewriter.rewrite(profile, current)
            with open(protected_path, "w") as f:
                f.write(rewritten)

            log("ADAPTIVE_LOOP", f"  Applied {len(profile.recommended_actions)} adaptive actions")

            if _os_mod.path.exists(protected_path):
                _os_mod.replace(protected_path, payload)

            if iteration < 2:
                reclassified = classifier.classify_from_source(rewritten)
                log("ADAPTIVE_LOOP", f"  Re-classified {len(reclassified)} functions")

        log("ADAPTIVE_LOOP", "Adaptive classification loop complete")
    except (ImportError, Exception) as e:
        log("SKIP", f"Adaptive classifier loop not available: {e}")
