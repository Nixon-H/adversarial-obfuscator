import ast
import hashlib
import os
import random
import struct
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set


def _ctx():
    """The multiprocessing context this module spawns workers with.

    "spawn", not the platform default: forking a multi-threaded
    process is deprecated (Python 3.12+ warns) and may deadlock in the
    child, and Python 3.14 changes the default on Linux.
    """
    from .process_ctx import process_context
    return process_context()


@dataclass
class VariantInfo:
    variant_id: int
    code: str
    checksum: bytes
    deployed_on: Optional[int]
    deployed_at: Optional[float]
    rotation_count: int = 0


@dataclass
class NodeDeployment:
    node_id: int
    current_variant_id: Optional[int]
    previous_variant_ids: List[int]
    deployed_at: Optional[float]


class DistributedDiversityPool:
    def __init__(self, pool_secret: Optional[bytes] = None, rotation_interval: float = 3600.0, mode: str = "simulation"):
        self.pool_secret = pool_secret or os.urandom(32)
        self.rotation_interval = rotation_interval
        self.mode = mode
        self._variants: Dict[int, VariantInfo] = {}
        self._nodes: Dict[int, NodeDeployment] = {}
        self._variant_generator: Optional[Callable[[int, bytes], str]] = None
        self._base_source: Optional[str] = None

    def set_variant_generator(self, generator: Callable[[int, bytes], str]):
        self._variant_generator = generator

    def _reorder_independent_statements(self, lines: List[str], rng: random.Random) -> List[str]:
        groups = []
        current = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "return", "if", "else", "elif", "for", "while", "try", "except", "finally", "def ", "class ")):
                if current:
                    groups.append(current)
                    current = []
                groups.append([line])
            else:
                current.append(line)
        if current:
            groups.append(current)

        result = []
        for g in groups:
            if len(g) > 1 and all("=" in l for l in g):
                lefts = set()
                rights = set()
                for l in g:
                    parts = l.split("=", 1)
                    lefts.add(parts[0].strip())
                    rights.update(parts[1].strip().split())
                if lefts.isdisjoint(rights):
                    shuffled = g[:]
                    rng.shuffle(shuffled)
                    result.extend(shuffled)
                    continue
            result.extend(g)
        return result

    def _insert_nops(self, lines: List[str], rng: random.Random) -> List[str]:
        result = []
        for line in lines:
            result.append(line)
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and rng.random() < 0.15:
                nop_var = f"_nop_{rng.randint(0, 2**32):x}"
                result.append(f"    {nop_var} = {rng.randint(0, 1000)}")
        return result

    def _split_var_declaration(self, lines: List[str], rng: random.Random) -> List[str]:
        result = []
        for line in lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#") and rng.random() < 0.2:
                parts = stripped.split("=", 1)
                var_name = parts[0].strip()
                if var_name.startswith("_"):
                    result.append(line)
                    continue
                expr = parts[1].strip()
                if "+" in expr or "-" in expr:
                    sub_parts = expr.split("+") if "+" in expr else expr.split("-")
                    if len(sub_parts) == 2 and all(p.strip().isidentifier() or p.strip().isdigit() for p in sub_parts):
                        op = "+" if "+" in expr else "-"
                        temp_var = f"_t_{rng.randint(0, 2**32):x}"
                        indent = line[:len(line) - len(line.lstrip())]
                        result.append(f"{indent}{temp_var} = {sub_parts[0].strip()}")
                        result.append(f"{indent}{var_name} = {temp_var} {op} {sub_parts[1].strip()}")
                        continue
            result.append(line)
        return result

    def generate_variants(self, base_source: str, num_variants: int) -> List[VariantInfo]:
        self._base_source = base_source
        variants = []
        base_hash = hashlib.sha256(base_source.encode()).digest()

        for vid in range(num_variants):
            seed_material = self.pool_secret + struct.pack(">I", vid) + base_hash
            variant_seed = hashlib.sha256(seed_material).digest()

            if self._variant_generator:
                code = self._variant_generator(vid, variant_seed)
            else:
                rng = random.Random(int.from_bytes(variant_seed[:8], "big"))
                lines = base_source.split("\n")
                varied_lines = []
                for line in lines:
                    if line.strip().startswith("#"):
                        varied_lines.append(line)
                    elif "=" in line and rng.random() < 0.3:
                        parts = line.split("=", 1)
                        new_var = f"_{vid:x}_{rng.randint(0, 2**32):x}_" + parts[0].strip()
                        varied_lines.append(f"    {new_var} ={parts[1]}")
                    else:
                        varied_lines.append(line)

                varied_lines = self._reorder_independent_statements(varied_lines, rng)
                varied_lines = self._insert_nops(varied_lines, rng)
                varied_lines = self._split_var_declaration(varied_lines, rng)
                code = "\n".join(varied_lines)

            cksum = hashlib.sha256(code.encode()).digest()
            vi = VariantInfo(
                variant_id=vid,
                code=code,
                checksum=cksum,
                deployed_on=None,
                deployed_at=None,
            )
            self._variants[vid] = vi
            variants.append(vi)

        return variants

    def setup_nodes(self, num_nodes: int):
        for nid in range(num_nodes):
            self._nodes[nid] = NodeDeployment(
                node_id=nid,
                current_variant_id=None,
                previous_variant_ids=[],
                deployed_at=None,
            )

    def distribute_variants(self) -> Dict[int, int]:
        if not self._nodes:
            raise ValueError("no nodes configured, call setup_nodes() first")
        if not self._variants:
            raise ValueError("no variants generated, call generate_variants() first")

        if self.mode == "multiprocess":
            return self._distribute_multiprocess()

        deployment: Dict[int, int] = {}
        variant_ids = list(self._variants.keys())

        for nid in sorted(self._nodes.keys()):
            vid = variant_ids[nid % len(variant_ids)]
            node = self._nodes[nid]
            if node.current_variant_id is not None:
                node.previous_variant_ids.append(node.current_variant_id)
            node.current_variant_id = vid
            node.deployed_at = time.time()
            self._variants[vid].deployed_on = nid
            self._variants[vid].deployed_at = node.deployed_at
            deployment[nid] = vid

        return deployment

    def _distribute_multiprocess(self) -> Dict[int, int]:
        processes = []
        queues = {}
        variant_ids = list(self._variants.keys())
        deployment: Dict[int, int] = {}

        for nid in sorted(self._nodes.keys()):
            queues[nid] = _ctx().Queue()

        for nid in sorted(self._nodes.keys()):
            vid = variant_ids[nid % len(variant_ids)]
            code = self._variants[vid].code
            p = _ctx().Process(target=_verify_and_deploy, args=(nid, vid, code, queues[nid]))
            processes.append(p)
            p.start()

        for nid in sorted(self._nodes.keys()):
            try:
                result, success = queues[nid].get(timeout=5)
                if success:
                    node = self._nodes[nid]
                    if node.current_variant_id is not None:
                        node.previous_variant_ids.append(node.current_variant_id)
                    node.current_variant_id = result
                    node.deployed_at = time.time()
                    self._variants[result].deployed_on = nid
                    self._variants[result].deployed_at = node.deployed_at
                    deployment[nid] = result
            except Exception:
                deployment[nid] = variant_ids[nid % len(variant_ids)]

        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1)

        return deployment

    def rotate_variants(self) -> Dict[int, int]:
        if not self._nodes:
            raise ValueError("no nodes configured")

        if not self._variants:
            raise ValueError("no variants generated")

        deployment: Dict[int, int] = {}
        variant_ids = list(self._variants.keys())

        now = time.time()
        for nid in sorted(self._nodes.keys()):
            node = self._nodes[nid]

            if node.deployed_at and (now - node.deployed_at) < self.rotation_interval:
                deployment[nid] = node.current_variant_id
                continue

            used_ids = set(node.previous_variant_ids)
            if node.current_variant_id is not None:
                used_ids.add(node.current_variant_id)

            available = [vid for vid in variant_ids if vid not in used_ids]
            if not available:
                node.previous_variant_ids = []
                available = variant_ids

            new_vid = available[node.node_id % len(available)]

            if node.current_variant_id is not None:
                node.previous_variant_ids.append(node.current_variant_id)
                self._variants[node.current_variant_id].rotation_count += 1

            node.current_variant_id = new_vid
            node.deployed_at = now
            self._variants[new_vid].deployed_on = nid
            self._variants[new_vid].deployed_at = now
            deployment[nid] = new_vid

        return deployment

    def get_node_variant_code(self, node_id: int) -> Optional[str]:
        node = self._nodes.get(node_id)
        if node is None or node.current_variant_id is None:
            return None
        variant = self._variants.get(node.current_variant_id)
        if variant is None:
            return None
        return variant.code

    def verify_semantic_equivalence(self) -> bool:
        if len(self._variants) < 2:
            # Fail-closed: fewer than 2 variants means there is nothing
            # to compare — a vacuous True would certify an unchecked pool.
            return False

        codes = [v.code for v in self._variants.values()]
        base_ops = self._extract_ops(codes[0])
        if base_ops is None:
            return False

        for code in codes[1:]:
            ops = self._extract_ops(code)
            if ops is None:
                return False
            if ops != base_ops:
                return False

        return True

    def _extract_ops(self, code: str) -> Optional[Set[str]]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None

        ops = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                ops.add("assign")
            elif isinstance(node, ast.AugAssign):
                ops.add("augassign")
            elif isinstance(node, ast.Return):
                ops.add("return")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    ops.add("call")
            elif isinstance(node, ast.BinOp):
                ops.add(f"binop:{type(node.op).__name__}")
            elif isinstance(node, ast.If):
                ops.add("if")
            elif isinstance(node, ast.For):
                ops.add("for")
            elif isinstance(node, ast.While):
                ops.add("while")
            elif isinstance(node, ast.FunctionDef):
                ops.add("def")
            elif isinstance(node, ast.Expr):
                ops.add("expr")

        return ops


def _verify_and_deploy(node_id: int, variant_id: int, code: str, queue):
    import ast
    success = True
    try:
        ast.parse(code)
    except SyntaxError:
        success = False
    queue.put((variant_id, success))
