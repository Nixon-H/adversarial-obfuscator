from dataclasses import dataclass
from typing import List, Optional

from .survivability_probes import (
    probe_watermark,
    probe_vm_opcodes,
    probe_cfg,
    probe_fragments,
)


@dataclass
class SurvivabilityResult:
    watermark_survival: Optional[float]
    vm_opcode_recovery: Optional[float]
    cfg_reconstruction: Optional[float]
    fragment_isolation: Optional[float]
    combined_index: float
    active_layers: List[str]

    def __post_init__(self):
        self.combined_index = round(self.combined_index, 4)


class SurvivabilityIndex:
    """
    Measures how well each protection layer survives simulated analysis.
    """

    WEIGHTS = {
        'watermark': 0.20,
        'vm_opcode': 0.30,
        'cfg': 0.30,
        'fragment': 0.20,
    }

    def measure(self, protected_artifact, config: dict = None) -> SurvivabilityResult:
        if config is None:
            config = {}

        active_layers = []
        layer_flags = config.get('layers', config)

        if layer_flags.get('watermark', True):
            active_layers.append('watermark')
        if layer_flags.get('vm_opcode', True):
            active_layers.append('vm_opcode')
        if layer_flags.get('cfg', True):
            active_layers.append('cfg')
        if layer_flags.get('fragment', True):
            active_layers.append('fragment')

        watermark_survival = None
        vm_opcode_recovery = None
        cfg_reconstruction = None
        fragment_isolation = None

        if 'watermark' in active_layers:
            watermark_survival = self.measure_watermark_survival(protected_artifact)
        if 'vm_opcode' in active_layers:
            vm_opcode_recovery = self.measure_vm_opcode_recovery(protected_artifact)
        if 'cfg' in active_layers:
            cfg_reconstruction = self.measure_cfg_reconstruction(protected_artifact)
        if 'fragment' in active_layers:
            fragment_isolation = self.measure_fragment_isolation(protected_artifact)

        combined_index = self._compute_combined(
            watermark_survival, vm_opcode_recovery,
            cfg_reconstruction, fragment_isolation, active_layers,
        )

        return SurvivabilityResult(
            watermark_survival=watermark_survival,
            vm_opcode_recovery=vm_opcode_recovery,
            cfg_reconstruction=cfg_reconstruction,
            fragment_isolation=fragment_isolation,
            combined_index=combined_index,
            active_layers=active_layers,
        )

    def measure_watermark_survival(self, artifact) -> float:
        return probe_watermark(artifact)

    def measure_vm_opcode_recovery(self, artifact) -> float:
        return probe_vm_opcodes(artifact)

    def measure_cfg_reconstruction(self, artifact) -> float:
        return probe_cfg(artifact)

    def measure_fragment_isolation(self, artifact) -> float:
        return probe_fragments(artifact)

    def _compute_combined(
        self,
        wm: Optional[float],
        vm: Optional[float],
        cfg: Optional[float],
        frag: Optional[float],
        active_layers: List[str],
    ) -> float:
        values = []
        total_weight = 0.0

        if 'watermark' in active_layers and wm is not None:
            values.append(wm * self.WEIGHTS['watermark'])
            total_weight += self.WEIGHTS['watermark']

        if 'vm_opcode' in active_layers and vm is not None:
            values.append(vm * self.WEIGHTS['vm_opcode'])
            total_weight += self.WEIGHTS['vm_opcode']

        if 'cfg' in active_layers and cfg is not None:
            values.append(cfg * self.WEIGHTS['cfg'])
            total_weight += self.WEIGHTS['cfg']

        if 'fragment' in active_layers and frag is not None:
            values.append(frag * self.WEIGHTS['fragment'])
            total_weight += self.WEIGHTS['fragment']

        if not values or total_weight == 0:
            return 0.0

        return sum(values) / total_weight
