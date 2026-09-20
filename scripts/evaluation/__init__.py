from .cost_model import ReverseEngineeringCostModel, CostBreakdown
from .calibration_data import CALIBRATION_SOURCES
from .multi_tool import MultiToolEvaluator, MultiToolResistance
from .tool_simulator import ToolSimulator
from .tool_profiles import TOOL_PROFILES
from .survivability import SurvivabilityIndex, SurvivabilityResult
from .survivability_probes import (
    probe_watermark,
    probe_vm_opcodes,
    probe_cfg,
    probe_fragments,
)
from .angr_bench import AngrBenchmark, AngrSimulator
from .ghidra_bench import GhidraBenchmark, GhidraSimulator
from .bninja_bench import BinaryNinjaBenchmark, BinaryNinjaSimulator
from .difficulty_curves import DifficultyCurveAnalyzer
from .economic_model import EconomicAttackModel
from .summary_report import EvaluationSummary
from .runtime_overhead import measure_execution_time, measure_runtime_overhead
from .binary_size import measure_binary_size, measure_size_overhead
from .unified_report import (
    generate_evaluation_report,
    collect_cfg_entropy,
    collect_cyclomatic_complexity,
    collect_symbolic_resistance,
    collect_decompiler_resistance,
    collect_ai_resistance,
    collect_watermark_survivability,
    collect_protection_survivability,
    collect_runtime_overhead,
    collect_binary_size_overhead,
)

__all__ = [
    "ReverseEngineeringCostModel",
    "CostBreakdown",
    "CALIBRATION_SOURCES",
    "MultiToolEvaluator",
    "MultiToolResistance",
    "ToolSimulator",
    "TOOL_PROFILES",
    "SurvivabilityIndex",
    "SurvivabilityResult",
    "probe_watermark",
    "probe_vm_opcodes",
    "probe_cfg",
    "probe_fragments",
    "AngrBenchmark",
    "AngrSimulator",
    "GhidraBenchmark",
    "GhidraSimulator",
    "BinaryNinjaBenchmark",
    "BinaryNinjaSimulator",
    "DifficultyCurveAnalyzer",
    "EconomicAttackModel",
    "EvaluationSummary",
    "measure_execution_time",
    "measure_runtime_overhead",
    "measure_binary_size",
    "measure_size_overhead",
    "generate_evaluation_report",
    "collect_cfg_entropy",
    "collect_cyclomatic_complexity",
    "collect_symbolic_resistance",
    "collect_decompiler_resistance",
    "collect_ai_resistance",
    "collect_watermark_survivability",
    "collect_protection_survivability",
    "collect_runtime_overhead",
    "collect_binary_size_overhead",
]
