import os
import shutil
import subprocess
import sys


class GhidraSimulator:
    def simulate(self, complexity_metrics: dict) -> dict:
        cfg_blocks = complexity_metrics.get('protected_blocks', 0)
        if isinstance(cfg_blocks, dict):
            cfg_blocks = cfg_blocks.get('protected_blocks', 0)
        mba_depth = complexity_metrics.get('protected_mba_depth', 0)
        if isinstance(complexity_metrics.get('symbolic_resistance'), dict):
            mba_depth = complexity_metrics['symbolic_resistance'].get('protected_mba_depth', mba_depth)
            cfg_blocks = complexity_metrics['symbolic_resistance'].get('protected_blocks', cfg_blocks)
        opaque_preds = complexity_metrics.get('protected_opaque_predicates', 0)
        if isinstance(complexity_metrics.get('symbolic_resistance'), dict):
            opaque_preds = complexity_metrics['symbolic_resistance'].get('protected_opaque_predicates', opaque_preds)

        dq = self._score_component(opaque_preds, 30, 1.2)
        fr = self._score_component(cfg_blocks, 100, 1.0)
        tr = self._score_component(mba_depth, 8, 2.0)

        return {
            'decompilation_quality': dq,
            'function_recovery': fr,
            'type_recovery': tr,
        }

    def _score_component(self, value: int, threshold: int, slope: float) -> int:
        if value <= 0:
            return 95
        if value <= threshold // 4:
            return 80
        if value <= threshold // 2:
            return 55
        if value <= threshold:
            return 30
        ratio = value / threshold
        score = max(0, 30 - int(ratio * slope * 25))
        return min(100, score)


class GhidraBenchmark:
    def __init__(self):
        self.simulator = GhidraSimulator()
        self._ghidra_available = (
            shutil.which('ghidraHeadless') is not None
            or shutil.which('ghidra_script') is not None
            or shutil.which('analyzeHeadless') is not None
        )

    def run(self, artifact_path: str) -> dict:
        complexity = self._extract_complexity(artifact_path)
        if self._ghidra_available:
            try:
                return self._run_ghidra_real(artifact_path)
            except Exception:
                pass
        scores = self.simulator.simulate(complexity)
        scores['tool'] = 'simulator'
        return scores

    def _run_ghidra_real(self, path: str) -> dict:
        ghidra_bin = 'analyzeHeadless'
        for candidate in ('ghidraHeadless', 'analyzeHeadless', 'ghidra_script'):
            if shutil.which(candidate):
                ghidra_bin = candidate
                break
        try:
            result = subprocess.run(
                [ghidra_bin, os.path.dirname(path) or '.', 'TempProject',
                 '-import', path, '-postScript', 'Decompile.java'],
                capture_output=True, text=True, timeout=120,
            )
            output = result.stdout + result.stderr
            func_count = output.count('function') + output.count('FUNCTION')
            decomp_ok = output.count('Decompilation') + output.count('decompiled')
            type_hits = output.count('type') + output.count('Type')
            return {
                'decompilation_quality': min(100, 50 + decomp_ok * 5),
                'function_recovery': min(100, 40 + func_count * 2),
                'type_recovery': min(100, 30 + type_hits * 3),
                'tool': 'ghidra',
            }
        except subprocess.TimeoutExpired:
            return {'decompilation_quality': 0, 'function_recovery': 0, 'type_recovery': 0, 'tool': 'ghidra', 'error': 'timeout'}
        except FileNotFoundError:
            return {'decompilation_quality': 0, 'function_recovery': 0, 'type_recovery': 0, 'tool': 'ghidra', 'error': 'ghidra not found'}
        except Exception as e:
            return {'decompilation_quality': 0, 'function_recovery': 0, 'type_recovery': 0, 'tool': 'ghidra', 'error': str(e)}

    @staticmethod
    def _extract_complexity(path: str) -> dict:
        metrics = {}
        if path and os.path.isfile(path):
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                metrics['file_size'] = len(data)
            except (IOError, OSError) as e:
                metrics['error'] = str(e)
        return metrics


def run_ghidra_benchmark(artifact_path: str, verbose: bool = False) -> dict:
    benchmark = GhidraBenchmark()
    if verbose:
        print(f"GhidraBenchmark: analyzing {artifact_path}...", file=sys.stderr)
    try:
        result = benchmark.run(artifact_path)
        if verbose:
            print("GhidraBenchmark complete", file=sys.stderr)
        return result
    except Exception as e:
        if verbose:
            print(f"GhidraBenchmark error: {e}", file=sys.stderr)
        return {"error": str(e), "tool": "simulator"}


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <artifact_path> [--verbose]", file=sys.stderr)
        sys.exit(1)
    verbose = "--verbose" in sys.argv
    artifact_path = sys.argv[1]
    result = run_ghidra_benchmark(artifact_path, verbose)
    print(json.dumps(result, indent=2))
