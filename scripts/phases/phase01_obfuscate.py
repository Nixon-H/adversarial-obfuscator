"""
phase01_obfuscate.py

Purpose:
First pipeline phase — obfuscates the Python payload using the obfuscator
core pipeline (direct import) or falls back to a subprocess invocation.
Applies optional passes: CFG flattening, opaque predicates, MBA
substitutions, string fragmentation, attention poisoning, decoy APIs,
LLM-resilient transforms (context collapse, honey functions), speculation
obfuscation, and data-oriented obfuscation.

Architectural Role:
Invoked first, before compilation.  Depends on the obfuscator package
being installed.  Produces the obfuscated .py file consumed by later phases.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
os, sys, obfuscator.core.pipeline, scripts.data_obfuscation, ast

Security Relevance:
Provides the primary code obfuscation layer — the baseline protection
that all subsequent phases reinforce.
"""

import os
import sys


def _get_build():
    """
    Lazy-import the shared build utilities from the parent package.

    Returns:
        tuple of (log, run, OBFUSCATOR)
    """
    from ..common import log, run, OBFUSCATOR
    return log, run, OBFUSCATOR


def phase_obfuscate(payload, output, opts):
    """
    Obfuscate a Python source file using the configured obfuscator pipeline.

    Attempts an in-process import of obfuscator.core.pipeline; on failure
    falls back to a CLI subprocess.  After the primary pass, applies
    optional LLM-resilient, speculation, and data-oriented transforms.

    Args:
        payload: path to the input .py source file
        output: path for the obfuscated output .py file
        opts: argparse.Namespace with obfuscation flags

    Security Relevance:
        Baseline code obfuscation — must run before any subsequent
        protection can be applied.
    """
    log, run, OBFUSCATOR = _get_build()
    log("OBFUSCATE", f"{payload} → {output}")

    try:
        from obfuscator.core.pipeline import build_pipeline
    except ImportError:
        log("ERROR", "Cannot import obfuscator pipeline — falling back to subprocess")
        cmd = [sys.executable, OBFUSCATOR, "obfuscate", payload, "-o", output]
        if opts.cfg_flatten: cmd.append("--cfg-flatten")
        if opts.opaque_predicates: cmd.append("--opaque-predicates")
        if opts.bogus_exceptions: cmd.append("--bogus-exceptions")
        if opts.mba_subs: cmd.append("--mba-subs")
        if opts.fragment_strings: cmd.append("--fragment-strings")
        if opts.unicode_ids: cmd.append("--unicode-ids")
        if getattr(opts, 'attention_poison', 0) > 0:
            cmd.append(f"--attention-poison={opts.attention_poison}")
        if getattr(opts, 'decoy_apis', False):
            cmd.append("--decoy-apis")
            cmd.append(f"--decoy-api-count={getattr(opts, 'decoy_api_count', 5)}")
        result = run(cmd)
    else:
        with open(payload, encoding="utf-8") as f:
            source = f.read()
        mba_opt = getattr(opts, '_mba_validator', None)
        extra_opts = {}
        if getattr(opts, 'attention_poison', 0) > 0:
            extra_opts['attention_poison'] = True
            extra_opts['attention_poison_fan_out'] = opts.attention_poison
        if getattr(opts, 'decoy_apis', False):
            extra_opts['decoy_apis'] = True
            extra_opts['decoy_api_count'] = getattr(opts, 'decoy_api_count', 5)
        if getattr(opts, 'adaptive_adversarial', False):
            extra_opts['adaptive_rewrite'] = True
        result = build_pipeline(source, mba_validator=mba_opt, extra_options=extra_opts)

        # LLM-Resilient passes
        if getattr(opts, "llm_resilient", False) or getattr(opts, "honey_functions", 0):
            import ast
            from obfuscator.llm_resilient import (
                ContextCollapseObfuscator,
                HoneyFunctionInjector,
            )
            tree = ast.parse(result)
            if getattr(opts, "llm_resilient", False):
                depth = getattr(opts, "llm_resilient_depth", 15)
                dead_vars = getattr(opts, "llm_resilient_vars", 50)
                log("LLM-RESILIENT", f"Applying ContextCollapseObfuscator (depth={depth}, vars={dead_vars})")
                obf = ContextCollapseObfuscator(depth=depth, dead_vars=dead_vars)
                tree = obf.obfuscate(tree)
            honey_count = getattr(opts, "honey_functions", 0)
            if honey_count:
                log("HONEY", f"Injecting {honey_count} honey functions")
                injector = HoneyFunctionInjector(count=honey_count)
                tree = injector.inject(tree)
            result = ast.unparse(tree)

        # Item 123: Speculation obfuscation (post-pipeline AST pass)
        if getattr(opts, "speculation_obfuscation", False):
            import ast as _ast_spec
            from obfuscator.speculation_obfuscation import obfuscate_with_speculation
            log("SPECULATION", "Applying AST-level speculation obfuscation...")
            result = obfuscate_with_speculation(result, seed=getattr(opts, 'randomization_seed', None) or 0xCAFEBABE)

        # Data-oriented obfuscation
        if getattr(opts, "data_obfuscation", False):
            import ast
            from scripts.data_obfuscation.data_protector import DataProtector
            level = getattr(opts, "data_obf_level", 3)
            log("DATA-OBF", f"Applying data-oriented obfuscation (level={level})")
            tree = ast.parse(result)
            protector = DataProtector(level=level)
            tree = protector.protect(tree)
            result = ast.unparse(tree)

        # V10 semantic lowering (opt-in via --lowering CSV): rewrite covered
        # call sites to _nxk_* kernel calls + prepend the shim import.
        # Runs AFTER the main pipeline so lowering sees final call shapes.
        if getattr(opts, "lowering", ""):
            import ast as _ast_low
            try:
                from obfuscator.lowering import (
                    emit_shim_import as _low_import,
                    lower_source as _low_src,
                    resolve_families as _low_resolve,
                )
                _low_active = _low_resolve(getattr(opts, "lowering", ""))
                if _low_active:
                    _low_body, _low_n = _low_src(result, _low_active)
                    _low_imp = _low_import(_low_active)
                    if _low_n:
                        result = (_low_imp + _low_body) if _low_imp else _low_body
                        log("LOWERING", f"Semantic lowering: {len(_low_active)} families, {_low_n} call sites")
            except Exception as _le:
                log("LOWERING", f"lowering skipped (non-fatal): {_le}")

        with open(output, "w", encoding="utf-8") as f:
            f.write(result)

    if not os.path.exists(output):
        log("ERROR", "Obfuscation produced no output — check obfuscator/core.py")
        sys.exit(1)
    size = os.path.getsize(output)
    log("OBFUSCATE", f"Done: {size/1024:.1f}KB (was {os.path.getsize(payload)/1024:.1f}KB)")
