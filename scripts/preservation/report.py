from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class StageResult:
    stage_name: str
    passed: bool
    input_hash: str
    output_hash: str
    counterexample: Optional[dict] = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PreservationReport:
    stages: List[StageResult] = field(default_factory=list)
    all_passed: bool = False
    total_duration_ms: float = 0.0

    def to_json(self) -> str:
        return json.dumps({
            "all_passed": self.all_passed,
            "total_duration_ms": self.total_duration_ms,
            "stages": [s.to_dict() for s in self.stages],
        }, indent=2)

    def print_summary(self):
        print(f"Preservation Report:")
        print(f"  All passed: {self.all_passed}")
        print(f"  Total time: {self.total_duration_ms:.2f} ms")
        print(f"  Stages:")
        for s in self.stages:
            status = "PASS" if s.passed else "FAIL"
            print(f"    [{status}] {s.stage_name} ({s.duration_ms:.1f}ms)")
            if s.counterexample:
                print(f"      Counterexample: {s.counterexample}")
