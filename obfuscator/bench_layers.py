"""Bench-driven adversarial layer selection.

The benchmark is an oracle: it measures, per protection layer, how much of the
payload an AI analyst recovers.  This module turns those measurements into a
build recommendation.

It answers one question: **given the campaign results, which layer set buys
the most analyst resistance per byte of artefact?**

The metric is deliberately not "which layer sounds strongest".  It is:

    resistance = 1 - recall        (how much the analyst FAILED to recover)
    cost       = surface_chars     (how much artefact the layer adds)
    value      = resistance / max(cost, 1)

A layer that adds 2 MB and stops nothing scores ~0.  A layer that adds 40 KB
and halves recall scores high.  That is the ranking this module produces.

Honesty rules baked in:

* A layer measured on **one** model is weak evidence; the report says how
  many cells back each number and refuses to rank a layer with none.
* ``cracked`` is the primary signal (a binary outcome); ``recall`` refines it.
* Layers with no measurement are reported as **unmeasured**, never assumed
  good or bad.
* The recommendation is advisory: it names layers to keep and to drop, and
  the caller decides.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Iterable, Optional

#: Layers this project can actually enable/disable at build time.  A campaign
#: arm that is not in this set is reported but cannot be recommended (there is
#: nothing to turn on).
KNOWN_LAYERS = (
    "cfg", "opaque", "bogus_exc", "mba", "strings", "unicode",
    "anti_rea", "decoy", "lowering", "data", "function_intent",
    "speculation", "full_source", "packed", "lex", "raw",
)


@dataclass
class LayerScore:
    """One layer's measured value."""

    layer: str
    cells: int = 0
    cracked_rate: float = 0.0
    mean_recall: float = 0.0
    mean_surface_chars: float = 0.0
    models: tuple = ()

    @property
    def resistance(self) -> float:
        """Fraction of the payload the analyst failed to recover."""
        return max(0.0, min(1.0, 1.0 - self.mean_recall))

    @property
    def value(self) -> float:
        """Resistance bought per KB of artefact surface."""
        kb = max(self.mean_surface_chars / 1024.0, 0.001)
        return self.resistance / kb

    @property
    def measured(self) -> bool:
        return self.cells > 0

    def as_dict(self) -> dict:
        return {
            "layer": self.layer,
            "cells": self.cells,
            "cracked_rate": round(self.cracked_rate, 3),
            "mean_recall": round(self.mean_recall, 3),
            "resistance": round(self.resistance, 3),
            "mean_surface_kb": round(self.mean_surface_chars / 1024.0, 1),
            "value": round(self.value, 4),
            "models": list(self.models),
            "measured": self.measured,
        }


@dataclass
class Recommendation:
    """The advisory output."""

    keep: list = field(default_factory=list)
    drop: list = field(default_factory=list)
    unmeasured: list = field(default_factory=list)
    scores: list = field(default_factory=list)
    cells_used: int = 0
    models: tuple = ()

    def as_dict(self) -> dict:
        return {
            "keep": self.keep,
            "drop": self.drop,
            "unmeasured": self.unmeasured,
            "scores": [s.as_dict() for s in self.scores],
            "cells_used": self.cells_used,
            "models": list(self.models),
        }

    def summary(self) -> str:
        lines = ["Bench-driven layer selection (%d cells, %d model(s))"
                 % (self.cells_used, len(self.models))]
        if self.keep:
            lines.append("  KEEP (best resistance per KB):")
            for name in self.keep:
                sc = next((s for s in self.scores if s.layer == name), None)
                if sc:
                    lines.append("    %-16s value=%.4f  resistance=%.2f  +%.0fKB"
                                 % (name, sc.value, sc.resistance,
                                    sc.mean_surface_chars / 1024.0))
        if self.drop:
            lines.append("  DROP (measured, bought little):")
            for name in self.drop:
                sc = next((s for s in self.scores if s.layer == name), None)
                if sc:
                    lines.append("    %-16s value=%.4f  resistance=%.2f  +%.0fKB"
                                 % (name, sc.value, sc.resistance,
                                    sc.mean_surface_chars / 1024.0))
        if self.unmeasured:
            lines.append("  UNMEASURED (no campaign data -- not ranked):")
            lines.append("    " + ", ".join(self.unmeasured))
        return "\n".join(lines)


def _load_cells(paths: Iterable[str]) -> list:
    cells = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        for cell in doc.get("cells", []) or []:
            if isinstance(cell, dict) and cell.get("arm"):
                cells.append(cell)
    return cells


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def score_layers(cells: Iterable[dict]) -> list:
    """Aggregate campaign cells into one LayerScore per arm."""
    by_layer: dict = {}
    for cell in cells:
        arm = str(cell.get("arm")).strip()
        if not arm:
            continue
        entry = by_layer.setdefault(arm, {
            "cracked": [], "recall": [], "surface": [], "models": set(),
        })
        cracked = cell.get("cracked")
        if isinstance(cracked, bool):
            entry["cracked"].append(1.0 if cracked else 0.0)
        elif isinstance(cracked, str):
            entry["cracked"].append(1.0 if cracked.lower() == "true" else 0.0)
        entry["recall"].append(_as_float(cell.get("recall"), 0.0))
        entry["surface"].append(_as_float(cell.get("surface_chars"), 0.0))
        model = cell.get("model")
        if model:
            entry["models"].add(str(model))

    scores = []
    for layer, data in by_layer.items():
        n = len(data["recall"])
        if n == 0:
            continue
        scores.append(LayerScore(
            layer=layer,
            cells=n,
            cracked_rate=sum(data["cracked"]) / max(len(data["cracked"]), 1),
            mean_recall=sum(data["recall"]) / n,
            mean_surface_chars=sum(data["surface"]) / n,
            models=tuple(sorted(data["models"])),
        ))
    scores.sort(key=lambda s: s.value, reverse=True)
    return scores


def recommend(paths: Iterable[str], *,
              drop_threshold: float = 0.02) -> Recommendation:
    """Rank the measured layers and split them into keep/drop.

    ``drop_threshold`` is the value below which a measured layer is
    recommended for removal: it bought less than 0.02 resistance per KB,
    which in practice means it stopped nothing an analyst noticed.
    """
    paths = list(paths)
    cells = _load_cells(paths)
    scores = score_layers(cells)
    measured = [s for s in scores if s.measured]
    unmeasured = sorted(set(KNOWN_LAYERS) - {s.layer for s in measured})

    keep = [s.layer for s in measured
            if s.value >= drop_threshold and s.layer in KNOWN_LAYERS]
    drop = [s.layer for s in measured
            if s.value < drop_threshold and s.layer in KNOWN_LAYERS]
    return Recommendation(
        keep=keep, drop=drop, unmeasured=unmeasured,
        scores=scores, cells_used=len(cells),
        models=tuple(sorted({s.models[0] for s in measured if s.models})),
    )


def campaign_files(root: str = "docs/research") -> list:
    """Every campaign JSON under ``root`` (recursively)."""
    found = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(".json") and (
                    "bench" in dirpath or "bench" in name
                    or name.startswith(("qwen-", "deepseek-", "kern-",
                                        "opencode-", "results"))):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def main(argv: Optional[list] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python3 -m obfuscator.bench_layers",
        description="Rank protection layers by measured analyst resistance "
                    "per KB, from the campaign JSONs.")
    parser.add_argument("--root", default="docs/research",
                        help="campaign root (default: docs/research)")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of the text summary")
    parser.add_argument("--drop-threshold", type=float, default=0.02,
                        help="value below which a layer is recommended for "
                             "removal (default 0.02)")
    opts = parser.parse_args(argv)

    rec = recommend(campaign_files(opts.root),
                    drop_threshold=opts.drop_threshold)
    if opts.json:
        print(json.dumps(rec.as_dict(), indent=2))
    else:
        print(rec.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
