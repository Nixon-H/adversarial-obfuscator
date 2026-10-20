"""
reachability/analyzer.py — Reachability Analysis engine (F169)

Purpose:
    For each feature in the feature map, traces CLI flags through build.py AST,
    resolves import chains via importlib, discovers runtime files and test
    files, and produces a FeatureReachability status (REACHABLE / PARTIAL /
    UNREACHABLE).

Architectural Role:
    Core analysis engine called by reachability/__init__.py. Consumed by the
    Self-Audit Agent (F180) and the Reality Score (F167) to detect wiring gaps.

Security Relevance:
    Identifies features that exist in documentation but are unreachable from
    the pipeline, preventing blind spots in the protection surface.
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from scripts.reachability.feature_map import ALL_FEATURES


class ReachabilityStatus(Enum):
    """Enumeration of reachability states for a feature."""
    REACHABLE = "REACHABLE"
    PARTIALLY_REACHABLE = "PARTIALLY_REACHABLE"
    UNREACHABLE = "UNREACHABLE"


@dataclass
class FeatureReachability:
    """Per-feature reachability analysis result.

    Attributes:
        feature_name: Name of the feature from the feature map.
        status: REACHABLE, PARTIALLY_REACHABLE, or UNREACHABLE.
        cli_flag_found: Whether the CLI flag was found in build.py.
        cli_flag_path: Line references where the CLI flag appears.
        phase_found: Whether the phase function was found in build.py.
        phase_path: File:line where the phase call appears.
        import_chain: Module-resolution chain from importlib.
        implementation_found: Whether the implementation module was resolved.
        implementation_path: Resolved filesystem path of the implementation.
        runtime_paths: Discovered runtime source files for this feature.
        test_files: Discovered test files for this feature.
        missing_links: Human-readable descriptions of what is missing.
    """

    feature_name: str
    status: ReachabilityStatus
    cli_flag_found: bool
    cli_flag_path: List[str] = field(default_factory=list)
    phase_found: bool = False
    phase_path: Optional[str] = None
    import_chain: List[str] = field(default_factory=list)
    implementation_found: bool = False
    implementation_path: Optional[str] = None
    runtime_paths: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    missing_links: List[str] = field(default_factory=list)


@dataclass
class ReachabilityReport:
    """Aggregate report over all features in the feature map.

    Attributes:
        features: Mapping from feature name to FeatureReachability.
        reachable_count / partially_reachable_count / unreachable_count: Counts.
        total_features: Total number of features analysed.
        timestamp: ISO-8601 generation timestamp.
    """

    features: Dict[str, FeatureReachability]
    reachable_count: int
    partially_reachable_count: int
    unreachable_count: int
    total_features: int
    timestamp: str

    def to_dict(self) -> dict:
        """Serialize the report to a plain dict suitable for JSON export."""
        return {
            "timestamp": self.timestamp,
            "total_features": self.total_features,
            "reachable_count": self.reachable_count,
            "partially_reachable_count": self.partially_reachable_count,
            "unreachable_count": self.unreachable_count,
            "features": {
                name: {
                    "feature_name": fr.feature_name,
                    "status": fr.status.value,
                    "cli_flag_found": fr.cli_flag_found,
                    "cli_flag_path": fr.cli_flag_path,
                    "phase_found": fr.phase_found,
                    "phase_path": fr.phase_path,
                    "import_chain": fr.import_chain,
                    "implementation_found": fr.implementation_found,
                    "implementation_path": fr.implementation_path,
                    "runtime_paths": fr.runtime_paths,
                    "test_files": fr.test_files,
                    "missing_links": fr.missing_links,
                }
                for name, fr in self.features.items()
            },
        }


class ReachabilityAnalyzer:
    """AST-based reachability analyser for protection features.

    Parses build.py to trace CLI flags and phase calls, resolves module
    imports via importlib, and searches runtime/ and tests/ directories
    for supporting files.
    """

    def __init__(self, build_py_path: Optional[str] = None):
        if build_py_path is None:
            build_py_path = os.path.join(_ROOT, "scripts", "build.py")
        self.build_py_path = build_py_path
        self._build_source: Optional[str] = None
        self._build_tree: Optional[ast.Module] = None
        self._runtime_dir: str = os.path.join(_ROOT, "runtime", "src")
        self._tests_dir: str = os.path.join(_ROOT, "tests")

    def _ensure_build_parsed(self):
        """Ensure build.py has been read and parsed into an AST (lazy-load)."""
        if self._build_source is not None:
            return
        with open(self.build_py_path, encoding="utf-8") as f:
            self._build_source = f.read()
        self._build_tree = ast.parse(self._build_source)

    def trace_cli_flag(self, flag: str) -> List[str]:
        """Search the build.py AST for argparse registrations of the given CLI flag.

        Returns a list of "build.py:<lineno>" strings for each match.
        """
        self._ensure_build_parsed()
        if not flag:
            return []
        paths = []
        flag_clean = flag.lstrip("-").replace("-", "_")
        for node in ast.walk(self._build_tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "add_argument":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if arg.value == flag:
                                paths.append(f"build.py:{node.lineno}")
                    for kw in node.keywords:
                        if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                            if kw.value.value == flag_clean:
                                paths.append(f"build.py:{node.lineno}")
        return paths

    def trace_phase(self, phase_name: str) -> Optional[str]:
        """Search the build.py AST for calls referencing the given phase name.

        Returns "build.py:<lineno>" if found, None otherwise.
        """
        self._ensure_build_parsed()
        if not phase_name:
            return None
        for node in ast.walk(self._build_tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == phase_name:
                    return f"build.py:{node.lineno}"
                if isinstance(func, ast.Attribute) and func.attr == phase_name:
                    return f"build.py:{node.lineno}"
        return None

    def trace_import_chain(self, module_name: str) -> List[str]:
        """Resolve the import chain for a dotted module name using importlib + AST.

        BFS-walks transitive imports and returns human-readable resolution
        strings like "module -> /path/to/file.py".
        """
        if not module_name:
            return []
        chain = []
        seen = set()
        queue = [module_name]
        while queue:
            name = queue.pop(0)
            if name in seen:
                continue
            seen.add(name)
            top = name.split(".")[0]
            origin = None
            spec = None
            try:
                spec = importlib.util.find_spec(top)
            except Exception:
                pass
            if spec is not None:
                origin = spec.origin
                if origin is None:
                    origin_str = "(built-in)"
                else:
                    origin_str = origin
                is_file = origin is not None and os.path.isfile(origin)
                chain.append(f"{name} -> {origin_str}")
                if is_file:
                    try:
                        with open(origin, encoding="utf-8") as f:
                            src = f.read()
                        tree = ast.parse(src)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    qname = alias.name
                                    if qname not in seen:
                                        queue.append(qname.split(".")[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    base = node.module.split(".")[0]
                                    if base not in seen:
                                        queue.append(base)
                    except Exception:
                        pass
            else:
                chain.append(f"{name} -> NOT FOUND")
        return chain

    def trace_runtime_path(self, feature_name: str) -> List[str]:
        """Find runtime source files (.rs) related to the given feature name.

        Checks the explicit runtime_file entry in ALL_FEATURES first,
        then falls back to a name-similarity search.
        """
        paths = []
        if not os.path.isdir(self._runtime_dir):
            return paths
        feature_info = ALL_FEATURES.get(feature_name, {})
        runtime_file = feature_info.get("runtime_file")
        if runtime_file:
            rpath = os.path.join(self._runtime_dir, runtime_file)
            if os.path.exists(rpath):
                paths.append(rpath)
        else:
            feature_slug = feature_name.replace("_", "")
            for fname in os.listdir(self._runtime_dir):
                if fname.endswith(".rs"):
                    base = fname.replace(".rs", "").replace("_", "").replace("-", "")
                    if feature_slug in base or base in feature_slug:
                        paths.append(os.path.join(self._runtime_dir, fname))
        return paths

    def find_test_files(self, feature_name: str) -> List[str]:
        """Find test files (.py) related to the given feature name.

        Checks the explicit test_file entry in ALL_FEATURES first,
        then falls back to a name-similarity search against test_*.py.
        """
        test_files = []
        feature_info = ALL_FEATURES.get(feature_name, {})
        explicit_test = feature_info.get("test_file")
        if explicit_test:
            tpath = os.path.join(self._tests_dir, explicit_test)
            if os.path.exists(tpath):
                test_files.append(tpath)
            return test_files
        feature_slug = feature_name.replace("_", "").lower()
        if os.path.isdir(self._tests_dir):
            for fname in os.listdir(self._tests_dir):
                if fname.endswith(".py") and fname.startswith("test_"):
                    base = fname.replace("test_", "").replace(".py", "").replace("_", "").lower()
                    if feature_slug in base or base in feature_slug:
                        test_files.append(os.path.join(self._tests_dir, fname))
        return test_files

    def analyze_feature(
        self,
        feature_name: str,
        cli_flag: Optional[str] = None,
        phase_name: Optional[str] = None,
        implementation_module: Optional[str] = None,
    ) -> FeatureReachability:
        """Analyse reachability for a single feature across all dimensions.

        Traces CLI flag, phase call, import chain, runtime paths, and test
        files. Sets status to REACHABLE / PARTIALLY_REACHABLE / UNREACHABLE
        based on which links are present.
        """
        feature_info = ALL_FEATURES.get(feature_name, {})
        if cli_flag is None:
            cli_flag = feature_info.get("cli_flag")
        if phase_name is None:
            phase_name = feature_info.get("phase_name")
        if implementation_module is None:
            implementation_module = feature_info.get("impl_module")

        cli_flag_found = False
        cli_flag_paths: List[str] = []
        if cli_flag:
            cli_flag_paths = self.trace_cli_flag(cli_flag)
            cli_flag_found = len(cli_flag_paths) > 0

        phase_found = False
        phase_path: Optional[str] = None
        if phase_name:
            phase_path = self.trace_phase(phase_name)
            phase_found = phase_path is not None

        import_chain: List[str] = []
        implementation_found = False
        implementation_path: Optional[str] = None
        if implementation_module:
            import_chain = self.trace_import_chain(implementation_module)
            found_entries = [c for c in import_chain if "NOT FOUND" not in c and "ERROR" not in c]
            implementation_found = len(found_entries) > 0
            for c in found_entries:
                if "-> " in c:
                    p = c.split("-> ", 1)[1]
                    if p and p != "NOT FOUND" and p != "(namespace)" and p != "(built-in)":
                        if os.path.exists(p):
                            implementation_path = p
                            break
                    else:
                        implementation_path = p
                        break

        runtime_paths = self.trace_runtime_path(feature_name)
        test_files = self.find_test_files(feature_name)

        missing_links: List[str] = []
        if cli_flag and not cli_flag_found:
            missing_links.append(f"cli_flag '{cli_flag}' not found in build.py")
        if phase_name and not phase_found:
            missing_links.append(f"phase '{phase_name}' not found in build.py")
        if implementation_module and not implementation_found:
            missing_links.append(f"implementation module '{implementation_module}' not importable")
        if feature_info.get("runtime_file") and not runtime_paths:
            missing_links.append(f"runtime file '{feature_info['runtime_file']}' not found")
        if feature_info.get("test_file") and not test_files:
            missing_links.append(f"test file '{feature_info['test_file']}' not found")

        has_cli = cli_flag is None or cli_flag_found
        has_phase = phase_name is None or phase_found
        has_impl = implementation_module is None or implementation_found
        has_runtime = (feature_info.get("runtime_file") is None) or len(runtime_paths) > 0
        has_tests = (feature_info.get("test_file") is None) or len(test_files) > 0
        all_found = has_cli and has_phase and has_impl and has_runtime and has_tests
        any_missing = not has_cli or not has_phase or not has_impl or not has_runtime or not has_tests

        if not cli_flag and not phase_name and not implementation_module:
            all_found = False

        if all_found:
            status = ReachabilityStatus.REACHABLE
        elif any_missing:
            status = ReachabilityStatus.PARTIALLY_REACHABLE
        else:
            status = ReachabilityStatus.UNREACHABLE

        if len(missing_links) >= 3:
            status = ReachabilityStatus.UNREACHABLE

        if not cli_flag and not phase_name and not implementation_module and not feature_info.get("runtime_file"):
            status = ReachabilityStatus.UNREACHABLE

        return FeatureReachability(
            feature_name=feature_name,
            status=status,
            cli_flag_found=cli_flag_found,
            cli_flag_path=cli_flag_paths,
            phase_found=phase_found,
            phase_path=phase_path,
            import_chain=import_chain,
            implementation_found=implementation_found,
            implementation_path=implementation_path,
            runtime_paths=runtime_paths,
            test_files=test_files,
            missing_links=missing_links,
        )

    def analyze_all_features(self) -> Dict[str, FeatureReachability]:
        """Analyse reachability for every feature in the feature map."""
        results: Dict[str, FeatureReachability] = {}
        for feature_name in ALL_FEATURES:
            results[feature_name] = self.analyze_feature(feature_name)
        return results

    def generate_report(self) -> ReachabilityReport:
        """Run analysis on all features and return a ReachabilityReport with counts."""
        features = self.analyze_all_features()
        reachable = sum(1 for f in features.values() if f.status == ReachabilityStatus.REACHABLE)
        partially = sum(1 for f in features.values() if f.status == ReachabilityStatus.PARTIALLY_REACHABLE)
        unreachable = sum(1 for f in features.values() if f.status == ReachabilityStatus.UNREACHABLE)
        timestamp = datetime.now(timezone.utc).isoformat()
        return ReachabilityReport(
            features=features,
            reachable_count=reachable,
            partially_reachable_count=partially,
            unreachable_count=unreachable,
            total_features=len(features),
            timestamp=timestamp,
        )
