from .tool_profiles import TOOL_PROFILES


class ToolSimulator:
    """
    Produces realistic simulated scores based on public tool benchmarks.

    Maps metric thresholds to simulated scores:
    - CFG flattening > 50 blocks -> angr score 40/100
    - Opaque predicates > 20 -> rizin function recovery 35/100
    - MBA depth > 5 -> decompilation 25/100
    """

    def simulate(self, metrics: dict, tool: str) -> dict:
        # Fail-closed on unknown tools: silently scoring an unprofiled
        # tool as readelf (the old .get fallback) fabricates evidence.
        if tool not in TOOL_PROFILES:
            raise ValueError(
                "ToolSimulator.simulate: unknown tool %r (known: %s)"
                % (tool, sorted(TOOL_PROFILES))
            )
        profile = TOOL_PROFILES[tool]

        cfg_blocks = metrics.get('protected_blocks', 0)
        if isinstance(cfg_blocks, dict):
            cfg_blocks = cfg_blocks.get('protected_blocks', 0)
        for key in ('cfg_entropy',):
            entry = metrics.get(key, {})
            if isinstance(entry, dict):
                cfg_blocks = entry.get('protected_blocks', cfg_blocks)

        opaque_predicates = metrics.get('protected_opaque_predicates', 0)
        if isinstance(metrics.get('symbolic_resistance'), dict):
            opaque_predicates = metrics['symbolic_resistance'].get('protected_opaque_predicates', opaque_predicates)

        mba_depth = metrics.get('protected_mba_depth', 0)
        if isinstance(metrics.get('symbolic_resistance'), dict):
            mba_depth = metrics['symbolic_resistance'].get('protected_mba_depth', mba_depth)

        bb_acc = self._score_bb_accuracy(cfg_blocks, profile['cfg_flatten_sensitivity'])
        fn_rec = self._score_function_recovery(opaque_predicates, profile['opaque_predicate_limit'])
        decomp = self._score_decompilation(mba_depth, profile['mba_depth_limit'])

        return {
            'bb_accuracy': bb_acc,
            'function_recovery': fn_rec,
            'decompilation': decomp,
            # Provenance tag: heuristic simulation from public
            # benchmarks, NOT a measured tool run. Aggregators must
            # surface this (cf. multi_tool tools_simulated).
            'simulated': True,
        }

    @staticmethod
    def _score_bb_accuracy(blocks: int, sensitivity: int) -> int:
        if blocks <= 0:
            return 95
        if blocks <= sensitivity // 4:
            return 90
        if blocks <= sensitivity // 2:
            return 75
        if blocks <= sensitivity:
            return 60
        ratio = blocks / sensitivity
        score = max(5, 60 - int(ratio * 1.5 * 40))
        return min(95, score)

    @staticmethod
    def _score_function_recovery(opaque_count: int, limit: int) -> int:
        if opaque_count <= 0:
            return 95
        if opaque_count <= limit // 4:
            return 85
        if opaque_count <= limit // 2:
            return 65
        if opaque_count <= limit:
            return 45
        ratio = opaque_count / limit
        score = max(5, 45 - int(ratio * 1.5 * 35))
        return min(95, score)

    @staticmethod
    def _score_decompilation(mba_depth: int, limit: int) -> int:
        if mba_depth <= 0:
            return 95
        if mba_depth <= limit // 4:
            return 80
        if mba_depth <= limit // 2:
            return 55
        if mba_depth <= limit:
            return 35
        ratio = mba_depth / limit
        score = max(5, 35 - int(ratio * 2.0 * 30))
        return min(95, score)
