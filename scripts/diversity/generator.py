import ast
import hashlib
import os
import random
import secrets
import sys
from typing import List

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)


def derive_subseed(master: int, label: str) -> int:
    h = hashlib.sha256(f"{master}:{label}".encode()).digest()
    return int.from_bytes(h[:8], "little")


def generate_variant(source: str, variant_id: int, config: dict) -> str:
    master_seed = config.get("master_seed", 0)
    seed = int.from_bytes(
        hashlib.sha256(f"{variant_id}:{master_seed}".encode()).digest()[:8], "little"
    )
    ast_seed = derive_subseed(seed, "ast")
    mba_seed = derive_subseed(seed, "mba")
    cfg_seed = derive_subseed(seed, "cfg")
    derive_subseed(seed, 'vm')
    derive_subseed(seed, 'opaque')
    derive_subseed(seed, 'string')

    pass_sets = config.get("pass_sets", None)
    if pass_sets is not None:
        passes = pass_sets[variant_id % len(pass_sets)]
    elif variant_id % 3 == 0:
        passes = ["rename", "dead_code", "mba", "cfg_flatten", "vm"]
    elif variant_id % 3 == 1:
        passes = ["rename", "dead_code", "opaque_pred", "string_encode", "vm"]
    else:
        passes = [
            "rename",
            "mba",
            "cfg_flatten",
            "opaque_pred",
            "string_encode",
            "vm",
        ]

    options = {
        "cfg_flatten": "cfg_flatten" in passes,
        "opaque_predicates": "opaque_pred" in passes,
        "bogus_exceptions": "bogus_exceptions" in passes,
        "mba_subs": "mba" in passes,
        "fragment_strings": "string_encode" in passes,
        "unicode_ids": "unicode" in passes,
        "symbol_rename": "rename" in passes,
        "strip_meta": True,
        "split_vars": "split_vars" in passes,
        "unfold_constants": True,
        "enhanced_junk": "dead_code" in passes,
        "dynamic_code": False,
        "code_checksums": False,
        "obf_calls": True,
        "exception_flow": "exception_flow" in passes,
    }

    from obfuscator.core.pipeline import ObfuscationTransformer

    combined_seed = ast_seed ^ mba_seed ^ cfg_seed
    # Experiment arms (transfer H0-H5) inject extra options here
    # (rep/vm families, isolation flags). Absent by default: zero
    # behavior change for all existing callers.
    for _k, _v in dict(config.get("extra_options", {}) or {}).items():
        options[_k] = _v
    # Seed the new families deterministically per variant unless the
    # experiment pins them explicitly.
    options.setdefault("rep_seed", combined_seed)
    options.setdefault("vm_seed", combined_seed ^ 0x9E3779B9)
    transformer = ObfuscationTransformer(seed=combined_seed)

    rng = random.Random(combined_seed)
    _patch_secrets_for_variant(rng)
    try:
        result = transformer.transform(source, options=options)
    finally:
        _unpatch_secrets_for_variant()
    return result


_SAVED_SECRETS = {}


def _patch_secrets_for_variant(rng):
    global _SAVED_SECRETS
    _SAVED_SECRETS["randbelow"] = secrets.randbelow
    _SAVED_SECRETS["token_bytes"] = secrets.token_bytes
    _SAVED_SECRETS["choice"] = secrets.choice
    secrets.randbelow = lambda n: rng.randint(0, n - 1)
    secrets.token_bytes = lambda n=None: bytes(
        [rng.randint(0, 255) for _ in range(n or 16)]
    )
    secrets.choice = lambda s: s[rng.randint(0, len(s) - 1)]


def _unpatch_secrets_for_variant():
    global _SAVED_SECRETS
    if "randbelow" in _SAVED_SECRETS:
        secrets.randbelow = _SAVED_SECRETS["randbelow"]
        secrets.token_bytes = _SAVED_SECRETS["token_bytes"]
        secrets.choice = _SAVED_SECRETS["choice"]
        _SAVED_SECRETS.clear()


class DiversityGenerator:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._master_seed = secrets.randbits(64)

    def generate(
        self, source_path: str, n: int, output_dir: str, start: int = 0
    ) -> List[str]:
        """Generate ``n`` variants starting at variant index ``start``.

        ``start`` matters: the pass set is chosen as
        ``pass_sets[variant_id % len(pass_sets)]``, so a caller that wants
        build ``i`` to use pass set ``i`` must pass ``start=i``.  The
        transfer runner used to call ``generate(path, 1, dir)``, which
        always produced variant 0 -- every build in a supposedly
        heterogeneous arm used the first pass set.
        """
        os.makedirs(output_dir, exist_ok=True)
        with open(source_path, encoding="utf-8") as f:
            source = f.read()

        config = dict(self.config)
        config.setdefault("master_seed", self._master_seed)

        variant_paths = []
        for i in range(start, start + n):
            variant_code = generate_variant(source, i, config)
            valid, error = _validate_syntax(variant_code)
            if not valid:
                variant_code = generate_variant(source, i + n, config)
                valid, error = _validate_syntax(variant_code)
                if not valid:
                    raise RuntimeError(
                        f"Variant {i}: syntax error after retry: {error}"
                    )
            variant_path = os.path.join(output_dir, f"variant_{i:04d}.py")
            with open(variant_path, "w", encoding="utf-8") as f:
                f.write(variant_code)
            variant_paths.append(variant_path)

        return variant_paths

    def rank_variants_by_scores(self, variants: list[str], scores: list[float]) -> list[str]:
        paired = sorted(zip(variants, scores), key=lambda x: x[1], reverse=True)
        return [p[0] for p in paired]

    def evolve_pass_set(self, base_passes: list[str], seed: int) -> list[str]:
        rng = random.Random(seed)
        passes = list(base_passes)
        if rng.random() < 0.3:
            extra = rng.choice(["bogus_exceptions", "split_vars", "exception_flow"])
            passes.append(extra)
        if rng.random() < 0.2 and len(passes) > 2:
            passes.remove(rng.choice(passes))
        return passes

    @property
    def master_seed(self):
        return self._master_seed


def _validate_syntax(code: str):
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)
