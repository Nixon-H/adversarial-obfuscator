import os
import shutil
import subprocess
import sys


class BinaryNinjaSimulator:
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

        il = self._score_component(cfg_blocks, 80, 1.3)
        ac = self._score_component(opaque_preds, 25, 1.8)
        hlil = self._score_component(mba_depth, 6, 2.5)

        return {
            'il_translation': il,
            'analysis_completeness': ac,
            'hlil_quality': hlil,
        }

    def _score_component(self, value: int, threshold: int, slope: float) -> int:
        if value <= 0:
            return 95
        if value <= threshold // 4:
            return 85
        if value <= threshold // 2:
            return 60
        if value <= threshold:
            return 35
        ratio = value / threshold
        score = max(0, 35 - int(ratio * slope * 25))
        return min(100, score)


class BinaryNinjaBenchmark:
    def __init__(self):
        self.simulator = BinaryNinjaSimulator()
        self._bn_available = (
            shutil.which('binaryninja') is not None
            or shutil.which('bnheadless') is not None
            or shutil.which('binaryninja-headless') is not None
        )

    def run(self, artifact_path: str) -> dict:
        complexity = self._extract_complexity(artifact_path)
        if self._bn_available:
            try:
                return self._run_bn_real(artifact_path)
            except Exception:
                pass
        scores = self.simulator.simulate(complexity)
        scores['tool'] = 'simulator'
        return scores

    def _run_bn_real(self, path: str) -> dict:
        bn_bin = 'binaryninja'
        for candidate in ('binaryninja', 'bnheadless', 'binaryninja-headless'):
            if shutil.which(candidate):
                bn_bin = candidate
                break
        try:
            result = subprocess.run(
                [bn_bin, '-execute', '-script', 'analysis_report.py', path],
                capture_output=True, text=True, timeout=120,
            )
            output = result.stdout + result.stderr
            il_count = output.count('IL') + output.count('il')
            analysis_count = output.count('analysis') + output.count('Analysis')
            hlil_count = output.count('HLIL') + output.count('hlil')
            return {
                'il_translation': min(100, 40 + il_count * 3),
                'analysis_completeness': min(100, 50 + analysis_count * 2),
                'hlil_quality': min(100, 30 + hlil_count * 5),
                'tool': 'binaryninja',
            }
        except subprocess.TimeoutExpired:
            return {'il_translation': 0, 'analysis_completeness': 0, 'hlil_quality': 0, 'tool': 'binaryninja', 'error': 'timeout'}
        except FileNotFoundError:
            return {'il_translation': 0, 'analysis_completeness': 0, 'hlil_quality': 0, 'tool': 'binaryninja', 'error': 'binaryninja not found'}
        except Exception as e:
            return {'il_translation': 0, 'analysis_completeness': 0, 'hlil_quality': 0, 'tool': 'binaryninja', 'error': str(e)}

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


def run_bninja_benchmark(artifact_path: str, verbose: bool = False) -> dict:
    benchmark = BinaryNinjaBenchmark()
    if verbose:
        print(f"BinaryNinjaBenchmark: analyzing {artifact_path}...", file=sys.stderr)
    try:
        result = benchmark.run(artifact_path)
        if verbose:
            print(f"BinaryNinjaBenchmark complete", file=sys.stderr)
        return result
    except Exception as e:
        if verbose:
            print(f"BinaryNinjaBenchmark error: {e}", file=sys.stderr)
        return {"error": str(e), "tool": "simulator"}


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <artifact_path> [--verbose]", file=sys.stderr)
        sys.exit(1)
    verbose = "--verbose" in sys.argv
    artifact_path = sys.argv[1]
    result = run_bninja_benchmark(artifact_path, verbose)
    print(json.dumps(result, indent=2))
