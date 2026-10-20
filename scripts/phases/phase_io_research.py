"""
phase_io_research.py

Purpose:
Approximate indistinguishability obfuscation (iO) research for critical IR
fragments.  Converts compatible functions to branching programs and applies
matrix-based indistinguishability obfuscation.

WARNING:
This is a RESEARCH implementation.  All security metrics are MEASURED only —
no theoretical security guarantees are provided.

Architectural Role:
Experimental research phase — applies iO techniques and measures their
effectiveness.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, time, ..common, scripts.io_research, irgen.compile

Security Relevance:
Indistinguishability obfuscation is a theoretical gold standard;
this research implementation measures how close we can get in practice.
"""

from __future__ import annotations

import json
import os
import time

from ..common import log, BUILD_DIR


def phase_io_research(args, ir_module=None):
    """Run approximate indistinguishability obfuscation research on IR fragments.

    Args:
        args: argparse namespace with .io_research and .io_research_functions
        ir_module: IrModule from compile_py_to_ir, or None (load from payload)

    Returns:
        dict with manifest info, or None on failure.
    """
    log("IO_RESEARCH", "Approximate indistinguishability obfuscation research enabled")

    if ir_module is None:
        try:
            from irgen.compile import compile_py_to_ir
            payload = getattr(args, 'payload', None)
            if payload and os.path.exists(payload):
                with open(payload) as f:
                    source = f.read()
                ir_module = compile_py_to_ir(source)
            else:
                log("IO_RESEARCH", "No IR module available, skipping")
                return None
        except Exception as e:
            log("IO_RESEARCH", f"Failed to load IR module: {e}")
            return None

    from scripts.io_research import IndistinguishabilityObfuscator, is_io_compatible

    target_funcs_str = getattr(args, 'io_research_functions', None)
    target_funcs = None
    if target_funcs_str:
        target_funcs = set(f.strip() for f in target_funcs_str.split(',') if f.strip())

    obfuscator = IndistinguishabilityObfuscator()

    manifest = {
        'enabled': True,
        'functions': {},
        'summary': {
            'total_functions': len(ir_module.functions),
            'compatible': 0,
            'obfuscated': 0,
            'verified': 0,
            'failed': 0,
            'total_obfuscation_ms': 0.0,
        },
    }

    for func in ir_module.functions:
        func_name = func.name

        if target_funcs is not None and func_name not in target_funcs:
            manifest['functions'][func_name] = {'status': 'skipped_not_targeted'}
            continue

        if func_name.startswith('__'):
            manifest['functions'][func_name] = {'status': 'skipped_internal'}
            continue

        compatible, reason = is_io_compatible(func)
        if not compatible:
            manifest['functions'][func_name] = {
                'status': 'incompatible',
                'reason': reason,
            }
            continue

        manifest['summary']['compatible'] += 1

        try:
            t_start = time.time()
            result = obfuscator.obfuscate_fragment(func)
            elapsed_ms = (time.time() - t_start) * 1000.0

            if 'error' in result:
                manifest['functions'][func_name] = {
                    'status': 'error',
                    'error': result['error'],
                }
                manifest['summary']['failed'] += 1
                continue

            eq = result.get('equivalence', {})
            metrics = result.get('metrics', {})
            timing = result.get('timing_s', {})
            bp = result.get('bp')
            num_matrices = len(bp.matrices) if bp else 0

            manifest['functions'][func_name] = {
                'status': 'obfuscated',
                'equivalent': eq.get('equivalent', False),
                'equivalence_score': eq.get('score', 0.0),
                'indistinguishability_score': metrics.get('indistinguishability_score', 0.0),
                'entropy': metrics.get('entropy', 0.0),
                'program_distance': metrics.get('program_distance', 0.0),
                'num_matrices': num_matrices,
                'timing_s': timing,
                'note': 'MEASURED indistinguishability only — no theoretical security guarantees',
            }

            manifest['summary']['obfuscated'] += 1
            if eq.get('equivalent', False):
                manifest['summary']['verified'] += 1
            else:
                manifest['summary']['failed'] += 1
            manifest['summary']['total_obfuscation_ms'] += elapsed_ms

        except Exception as e:
            log("IO_RESEARCH", f"Failed to obfuscate function {func_name}: {e}")
            manifest['functions'][func_name] = {
                'status': 'error',
                'error': str(e),
            }
            manifest['summary']['failed'] += 1

    log("IO_RESEARCH",
        f"compatible={manifest['summary']['compatible']} "
        f"obfuscated={manifest['summary']['obfuscated']} "
        f"verified={manifest['summary']['verified']} "
        f"failed={manifest['summary']['failed']}")

    log("IO_RESEARCH",
        "IO RESEARCH: Measured indistinguishability only - "
        "no theoretical security guarantees")

    manifest_path = os.path.join(BUILD_DIR, 'io_research_manifest.json')
    try:
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)
        log("IO_RESEARCH", f"Manifest written to {manifest_path}")
    except Exception as e:
        log("IO_RESEARCH", f"Failed to write manifest: {e}")

    return manifest
