"""Structural-signature attack (Experiment v2.0, T_CFG_hash).

Level: Python BYTECODE CFG. Source is compiled with builtin compile()
(never executed); basic blocks split at jump targets/sources; node
labels are opname-only tuples (names/consts/args normalized away, so
renaming is invisible by construction). Cython/binaries are never
involved: no C-boilerplate mass confound (v1.0 Ghidra lesson).

Profile per function: out-degree multiset + edge multiset
((src_block, dst_block)) + block multiset + cyclomatic count.
Primary S: multiset-Jaccard over OUT-DEGREES (pure topology:
content-free, so rep/MBA tuple-rewrites that only change intra-block
opcodes cannot move it; flattening/junk that add blocks and branches
do). Secondary: content edge-Jaccard. Tertiary: block-hash Jaccard.

Gate history (disclosed): the first primary (content-labeled edges)
failed the H2->H2 gate at 0.767 -- rep tuple-rewrites change block
contents, which relabels edges even when topology is identical. The
gate worked as designed (rejected a confounded instrument before any
cross-arm number was measured); primary switched to topology-only,
re-gated, then cross-arm measured.

Alignment across builds: (argcount, occurrence-index) among module-level
functions, excluding the _demo entry point (name-stable: entry contract).
Module order is preserved by the pipeline (reorder repair); alignment
coverage is reported per cell, unaligned functions omitted.

S(B_j | P_i): mean edge-Jaccard over aligned pairs. Symmetric in (i,j)
by construction (documented, not hidden); directionality lives in the
arm-pair cells (H2->H0 vs H0->H0), not in the measure.
"""
import dis
from collections import Counter

_UNCOND_JUMPS = {
    "JUMP_FORWARD", "JUMP_ABSOLUTE", "JUMP_BACKWARD",
    "JUMP_BACKWARD_NO_INTERRUPT", "RETURN_VALUE", "RETURN_CONST",
    "RAISE_VARARGS", "RERAISE", "RETURN_GENERATOR",
}
_HAS_TARGET = set(dis.hasjabs) | set(dis.hasjrel)


def _code_objects(source):
    """Module-level function code objects in definition order.

    Returns list of (key, code) with key = (argcount, occurrence-index
    among same-argcount functions), entry point (_demo shape: called
    under `if __name__`) excluded by name `_demo` or by trailing
    position? _demo keeps its name (entry contract) in all builds.
    """
    top = compile(source, "<nxk>", "exec")
    out = []
    counts = {}
    for const in top.co_consts:
        if not hasattr(const, "co_name"):
            continue
        if const.co_name == "_demo" or const.co_name.startswith("<"):
            continue
        key = (const.co_argcount, counts.get(const.co_argcount, 0))
        counts[const.co_argcount] = counts.get(const.co_argcount, 0) + 1
        out.append((key, const))
    return out


def _blocks(code):
    """Split instructions into basic blocks. Returns (blocks, edges).

    blocks: list of opname tuples. edges: list of (src_idx, dst_idx).
    """
    insns = list(dis.get_instructions(code))
    if not insns:
        return [], []
    off2idx = {ins.offset: n for n, ins in enumerate(insns)}
    leaders = {0}
    for n, ins in enumerate(insns):
        if ins.opcode in _HAS_TARGET and ins.argval in off2idx:
            leaders.add(off2idx[ins.argval])
            if n + 1 < len(insns):
                leaders.add(n + 1)
    bounds = sorted(leaders)
    starts = {b: i for i, b in enumerate(bounds)}
    blocks, bens = [], []
    for i, b in enumerate(bounds):
        e = bounds[i + 1] if i + 1 < len(bounds) else len(insns)
        blocks.append(tuple(ins.opname for ins in insns[b:e]))
        bens.append((insns[b].offset, insns[e - 1]))
    edges = []
    for i, (start_off, last) in enumerate(bens):
        nxt = bounds[i + 1] if i + 1 < len(bounds) else None
        if last.opcode in _HAS_TARGET and last.argval in off2idx:
            tgt = starts[off2idx[last.argval]]
            if last.opname in _UNCOND_JUMPS:
                edges.append((i, tgt))
            else:
                edges.append((i, tgt))
                if nxt is not None:
                    edges.append((i, i + 1))
        elif last.opname in _UNCOND_JUMPS:
            pass  # return/raise: no outgoing edge
        elif nxt is not None:
            edges.append((i, i + 1))
    return blocks, edges


def _jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 1.0


def profile(source):
    """Extract per-function CFG profiles.

    Returns {"ok": True, "functions": {key: {...}}} or not-ok.
    """
    try:
        items = _code_objects(source)
    except SyntaxError as e:
        return {"ok": False, "reason": "uncompilable: %s" % e}
    funcs = {}
    for key, code in items:
        try:
            blocks, edges = _blocks(code)
        except Exception as e:
            return {"ok": False, "reason": "cfg-split: %s" % e}
        ekeys = [((blocks[s], blocks[d])) for s, d in edges]
        outdeg = Counter()
        for i in range(len(blocks)):
            outdeg[sum(1 for (a, b) in edges if a == i)] += 1
        funcs[key] = {
            "edges": Counter(ekeys),
            "blocks": Counter(blocks),
            "outdeg": outdeg,
            "n_blocks": len(blocks),
            "n_insns": sum(len(b) for b in blocks),
        }
    if not funcs:
        return {"ok": False, "reason": "no-functions"}
    return {"ok": True, "functions": funcs}


def pair_score(f_i, f_j):
    """(topo_Jaccard, edge_Jaccard, block_Jaccard) between profiles."""
    return (_jaccard(f_i["outdeg"], f_j["outdeg"]),
            _jaccard(f_i["edges"], f_j["edges"]),
            _jaccard(f_i["blocks"], f_j["blocks"]))


def decode_score(target_source, ext_i):
    """S(B_j | P_i): mean edge-Jaccard over aligned functions.

    Returns (S_edge, S_block, n_aligned, n_total) or
    (None, None, 0, n) when nothing aligns (caller excludes).
    """
    ext_j = profile(target_source)
    if not ext_j["ok"]:
        return None, None, None, 0, 0
    n_total = len(ext_j["functions"])
    st, se, sb, n = 0.0, 0.0, 0.0, 0
    for key, fj in ext_j["functions"].items():
        fi = ext_i["functions"].get(key)
        if fi is None:
            continue
        t, e, b = pair_score(fi, fj)
        st += t
        se += e
        sb += b
        n += 1
    if n == 0:
        return None, None, None, 0, n_total
    return st / n, se / n, sb / n, n, n_total


def self_score(source):
    """S(B_j | P_j): always 1.0 for deterministic compile (sanity).

    The informative gate for this arm is same-arm cross-seed
    (H2->H2) >= 0.80, measured in the experiment, not here.
    """
    ext = profile(source)
    if not ext["ok"]:
        return None, None, None, 0, 0, ext["reason"]
    s = decode_score(source, ext)
    return s[0], s[1], s[2], s[3], s[4], "ok"
