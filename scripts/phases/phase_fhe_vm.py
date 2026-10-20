"""
phase_fhe_vm.py

Purpose:
Compiles crown-jewel IR functions into Fully Homomorphic Encryption (FHE)
circuits.  Compatible functions (≤10 arithmetic ops, single basic block,
no control flow/memory) are compiled to BGV scheme circuits, verified
for equivalence, and benchmarked for overhead.

Architectural Role:
Experimental compilation phase — replaces selected function bodies with
FHE circuits that operate on encrypted data.

Execution Context:
Called from build.py during pipeline execution.

Dependencies:
json, os, time, typing, ..common, scripts.fhe_vm (BGVScheme, FHEExecutor, etc.)

Security Relevance:
FHE circuits allow computation on encrypted data without decryption,
providing mathematical confidentiality for selected functions.
"""

from __future__ import annotations
import json
import os
import time  # noqa: F401 (this line binds a name used by an embedded template)

from ..common import log, BUILD_DIR


def phase_fhe_vm(args, ir_module=None):
    """Run FHE-VM compilation on the IR module.

    Args:
        args: argparse namespace with .fhe_vm and .fhe_vm_functions
        ir_module: IrModule from compile_py_to_ir, or None (will try to load)

    Returns:
        dict with manifest info, or None on failure.
    """
    log("FHE_VM", "FHE-VM compilation enabled")

    if ir_module is None:
        try:
            from irgen.compile import compile_py_to_ir
            payload = getattr(args, 'payload', None)
            if payload and os.path.exists(payload):
                with open(payload) as f:
                    source = f.read()
                ir_module = compile_py_to_ir(source)
            else:
                log("FHE_VM", "No IR module available, skipping")
                return None
        except Exception as e:
            log("FHE_VM", f"Failed to load IR module: {e}")
            return None

    from scripts.fhe_vm import BGVScheme, FHEExecutor, SSAToFHECircuit, is_fhe_compatible, verify_equivalence  # noqa: F401 (this line binds a name used by an embedded template)

    target_funcs_str = getattr(args, 'fhe_vm_functions', None)
    target_funcs = None
    if target_funcs_str:
        target_funcs = set(f.strip() for f in target_funcs_str.split(',') if f.strip())

    manifest = {
        'enabled': True,
        'functions': {},
        'summary': {
            'total_functions': len(ir_module.functions),
            'compatible': 0,
            'compiled': 0,
            'verified': 0,
            'failed': 0,
            'total_keygen_ms': 0.0,
            'total_encrypt_ms': 0.0,
            'total_evaluate_ms': 0.0,
            'total_decrypt_ms': 0.0,
        },
    }

    for func in ir_module.functions:
        func_name = func.name

        if target_funcs is not None and func_name not in target_funcs:
            continue

        if func_name.startswith('__'):
            manifest['functions'][func_name] = {'status': 'skipped_internal'}
            continue

        compatible, reason = is_fhe_compatible(func)
        if not compatible:
            manifest['functions'][func_name] = {
                'status': 'incompatible',
                'reason': reason,
            }
            continue

        manifest['summary']['compatible'] += 1

        try:
            adapter = SSAToFHECircuit()
            circuit = adapter.convert_function(func)

            if circuit.num_ops() == 0:
                manifest['functions'][func_name] = {
                    'status': 'skipped_no_ops',
                }
                continue

            eq_result = verify_equivalence(func, circuit)
            is_equivalent = eq_result.get('equivalent', False)

            executor = FHEExecutor()
            pipeline_result = executor.run_full_pipeline(circuit, [1, 2])

            overhead_ms = sum(executor.get_timings().values()) * 1000

            manifest['functions'][func_name] = {
                'status': 'compiled' if pipeline_result['success'] else 'evaluation_failed',
                'gates': circuit.gate_count(),
                'arithmetic_ops': circuit.num_ops(),
                'equivalent': is_equivalent,
                'overhead_ms': round(overhead_ms, 3),
                'circuit_str': str(circuit),
            }

            if pipeline_result['success']:
                manifest['summary']['compiled'] += 1
                if is_equivalent:
                    manifest['summary']['verified'] += 1
                timings = pipeline_result.get('timings', {})
                manifest['summary']['total_keygen_ms'] += timings.get('keygen', 0) * 1000
                manifest['summary']['total_encrypt_ms'] += timings.get('encrypt', 0) * 1000
                manifest['summary']['total_evaluate_ms'] += timings.get('evaluate', 0) * 1000
                manifest['summary']['total_decrypt_ms'] += timings.get('decrypt', 0) * 1000
            else:
                manifest['summary']['failed'] += 1

        except Exception as e:
            log("FHE_VM", f"Failed to compile function {func_name}: {e}")
            manifest['functions'][func_name] = {
                'status': 'error',
                'error': str(e),
            }
            manifest['summary']['failed'] += 1

    manifest_path = os.path.join(BUILD_DIR, 'fhe_vm_manifest.json')
    try:
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)
        log("FHE_VM", f"Manifest written to {manifest_path}")
    except Exception as e:
        log("FHE_VM", f"Failed to write manifest: {e}")

    log("FHE_VM",
        f"compatible={manifest['summary']['compatible']} "
        f"compiled={manifest['summary']['compiled']} "
        f"verified={manifest['summary']['verified']} "
        f"failed={manifest['summary']['failed']}")

    return manifest
