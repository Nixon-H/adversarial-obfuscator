"""
__init__.py

Purpose:
Package initializer for the research artifact generator. Exports
functions for generating diagrams (Mermaid), tables (Markdown/HTML),
reports (Markdown/HTML), and reproducibility bundles (tar.gz/zip).

Architectural Role:
Post-pipeline output generator. Consumes coverage maps, metrics,
benchmark data, and knowledge graphs to produce human-readable
artifacts for documentation and verification purposes.

Execution Context:
Called at the end of the build pipeline when all protections and
measurements are complete. Outputs go to build/artifacts/.

Dependencies:
- diagram_generator (generate_architecture_diagram, etc.)
- table_generator (generate_benchmark_table, etc.)
- report_generator (generate_verification_report, etc.)
- bundler (ReproducibilityBundle)
- builder (ArtifactBuilder)

Security Relevance:
Artifacts document the security posture of each build. The
reproducibility bundle enables independent verification that the
claimed protections were actually applied.

Maintenance Notes:
- Adding a new artifact type requires: (1) a new generator function,
  (2) an export here, (3) registration in ArtifactBuilder's
  generate_all() method.
"""

from .diagram_generator import (
    generate_architecture_diagram,
    generate_protection_flowchart,
    generate_attack_surface_diagram,
    generate_comparison_chart,
)
from .table_generator import (
    generate_benchmark_table,
    generate_comparison_table,
    generate_threat_model_table,
    generate_coverage_table,
)
from .report_generator import (
    generate_verification_report,
    generate_regression_report,
    generate_security_summary,
    generate_executive_summary,
)
from .bundler import ReproducibilityBundle
from .builder import ArtifactBuilder

__all__ = [
    "generate_architecture_diagram",
    "generate_protection_flowchart",
    "generate_attack_surface_diagram",
    "generate_comparison_chart",
    "generate_benchmark_table",
    "generate_comparison_table",
    "generate_threat_model_table",
    "generate_coverage_table",
    "generate_verification_report",
    "generate_regression_report",
    "generate_security_summary",
    "generate_executive_summary",
    "ReproducibilityBundle",
    "ArtifactBuilder",
]
