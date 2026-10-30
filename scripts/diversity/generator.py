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
    # The seed and the pass set must be independent.  Using variant_id in
    # the seed made them inseparable: selecting pass set i also changed the
    # seed, so an arm's transform effect could not be distinguished from a
    # seed effect.  `seed_id` defaults to 0 (seed depends on master_seed
    # only); callers that want N seeds per pass set set it explicitly.
    seed_id = config.get("seed_id", 0)
    seed = int.from_bytes(
        hashlib.sha256(f"{seed_id}:{master_seed}".encode()).digest()[:8], "little"
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

    # `explicit` lets a caller isolate these two transforms instead of
    # having them applied in every arm.
    explicit = bool(config.get("explicit_options", False))
    options = {
        "cfg_flatten": "cfg_flatten" in passes,
        "opaque_predicates": "opaque_pred" in passes,
        "bogus_exceptions": "bogus_exceptions" in passes,
        "mba_subs": "mba" in passes,
        "fragment_strings": "string_encode" in passes,
        "unicode_ids": "unicode" in passes,
        "symbol_rename": "rename" in passes,
        # Was hard-coded True, which put it in every arm including the
        # negative control.  Now gated on the pass token, with an explicit
        # opt-out so existing configs keep their behaviour only when they
        # ask for it.
        "strip_meta": ("strip_meta" in passes) if explicit else True,
        "split_vars": "split_vars" in passes,
        "unfold_constants": ("unfold_constants" in passes) if explicit else True,
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
    return _repair_empty_bodies(result)


def _repair_empty_bodies(code: str) -> str:
    """Give any emptied class or function body a `pass`.

    Several passes strip statements (annotations, docstrings, metadata) and each
    can leave a block empty, which is not valid Python. A dataclass whose fields
    are bare annotations hit this: the class became `class X:` followed by the
    next def, and the artefact did not compile. The annotation case is handled
    where it happens (the fields are load-bearing), but a docstring-only class
    empties later and needs this pass.

    This is the cheap guard the corpus work argued for: compile what you emit.
    """
    import ast as _ast

    try:
        tree = _ast.parse(code)
    except SyntaxError:
        return code
    changed = False
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.ClassDef, _ast.FunctionDef, _ast.AsyncFunctionDef,
                             _ast.With, _ast.For, _ast.While, _ast.If, _ast.Try)):
            body = getattr(node, "body", None)
            if body is not None and not body:
                node.body = [_ast.Pass()]
                changed = True
    if not changed:
        return code
    return _ast.unparse(tree)


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
