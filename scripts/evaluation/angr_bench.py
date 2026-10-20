import os
import sys

try:
    import angr
    HAS_ANGR = True
except ImportError:
    HAS_ANGR = False


class AngrSimulator:
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

        bb = self._score_component(cfg_blocks, 50, 1.5)
        pe = self._score_component(opaque_preds, 20, 2.0)
        cfg = self._score_component(mba_depth, 5, 3.0)

        return {
            'bb_recovery': bb,
            'path_exploration': pe,
            'cfg_accuracy': cfg,
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

    def composite_score(self, scores: dict) -> float:
        return round(
            scores['bb_recovery'] * 0.35
            + scores['path_exploration'] * 0.35
            + scores['cfg_accuracy'] * 0.30,
            2,
        )


class AngrBenchmark:
    def __init__(self):
        self.simulator = AngrSimulator()
        self._angr_available = HAS_ANGR

    def run(self, artifact_path: str) -> dict:
        complexity = self._extract_complexity(artifact_path)
        if self._angr_available:
            try:
                return self._run_angr_real(artifact_path)
            except Exception:
                pass
        scores = self.simulator.simulate(complexity)
        scores['angr_resistance_score'] = self.simulator.composite_score(scores)
        scores['tool'] = 'simulator'
        return scores

    def _run_angr_real(self, path: str) -> dict:
        proj = angr.Project(path, auto_load_libs=False)
        cfg = proj.analyses.CFGFast()
        blocks_resolved = len(cfg.model.nodes())
        total_blocks = max(blocks_resolved, 1)
        try:
            state = proj.factory.entry_state()
            simgr = proj.factory.simulation_manager(state)
            simgr.explore(find=None, avoid=None, num_find=5)
            paths_explored = len(simgr.active) + len(simgr.deadended)
        except Exception:
            paths_explored = 0
        timeouts = 0
        bb_recovery = min(100, int(blocks_resolved / max(total_blocks, 1) * 100))
        path_exploration = min(100, int(paths_explored / max(total_blocks // 10, 1) * 100))
        cfg_accuracy = min(100, int(bb_recovery * 0.9 + path_exploration * 0.1))
        composite = round(bb_recovery * 0.35 + path_exploration * 0.35 + cfg_accuracy * 0.30, 2)
        return {
            'bb_recovery': bb_recovery,
            'path_exploration': path_exploration,
            'cfg_accuracy': cfg_accuracy,
            'angr_resistance_score': composite,
            'blocks_resolved': blocks_resolved,
            'paths_explored': paths_explored,
            'timeouts': timeouts,
            'tool': 'angr',
        }

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


def run_angr_benchmark(artifact_path: str, verbose: bool = False) -> dict:
    """Standalone CLI entry point for angr benchmarking."""
    benchmark = AngrBenchmark()
    if verbose:
        print(f"AngrBenchmark: analyzing {artifact_path}...", file=sys.stderr)
    try:
        result = benchmark.run(artifact_path)
        if verbose:
            print(f"AngrBenchmark: score={result.get('angr_resistance_score', 'N/A')}", file=sys.stderr)
        return result
    except Exception as e:
        if verbose:
            print(f"AngrBenchmark error: {e}", file=sys.stderr)
        return {"error": str(e), "tool": "simulator", "angr_resistance_score": 0}


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <artifact_path> [--verbose]", file=sys.stderr)
        sys.exit(1)
    verbose = "--verbose" in sys.argv
    artifact_path = sys.argv[1]
    result = run_angr_benchmark(artifact_path, verbose)
    print(json.dumps(result, indent=2))
