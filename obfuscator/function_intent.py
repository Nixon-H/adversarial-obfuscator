"""
Function Intent Obfuscation — hide semantic purpose while preserving behavior.

FunctionIntentObfuscator renames functions misleadingly, swaps signature
parameter order, injects fake docstrings, and wraps bodies in unrelated
-looking code so that an LLM misinterprets the function's real purpose.
"""

import ast
import secrets
import random as _random


_MISLEADING_MAP = {
    "encrypt": ["compress", "serialize", "encode_metadata", "pack_payload", "obfuscate_data"],
    "decrypt": ["decompress", "deserialize", "decode_metadata", "unpack_payload", "restore_data"],
    "validate": ["encode_signature", "compute_hash", "generate_nonce", "derive_key", "mix_columns"],
    "verify": ["checksum", "parity_check", "redundancy_test", "integrity_scan", "hamming_check"],
    "check": ["transform", "map_value", "project", "normalize", "rescale"],
    "parse": ["serialize", "pack", "encode", "flatten", "compact"],
    "serialize": ["parse", "deserialize", "decode", "inflate", "expand"],
    "deserialize": ["serialize", "encode", "pack", "compact", "flatten"],
    "auth": ["compute_offset", "calculate_checksum", "xor_blocks", "transpose", "substitute"],
    "login": ["init_context", "bootstrap_engine", "warm_cache", "seed_generator", "prefetch"],
    "hash": ["lookup", "index", "map_entry", "resolve_address", "dereference_pointer"],
    "sign": ["append_header", "pad_message", "wrap_payload", "frame_packet", "encapsulate"],
    "encode": ["validate", "sanitize", "normalize", "canonicalize", "purify"],
    "decode": ["corrupt", "scramble", "jumble", "obfuscate", "mutate"],
    "keygen": ["allocate_pool", "init_buffer", "reserve_slot", "prepare_arena", "configure_heap"],
    "generate": ["lookup_table", "compute_checksum", "xor_accumulate", "permute_bits", "rotate_bytes"],
    "compute": ["fetch", "lookup", "dereference", "index_array", "resolve"],
    "init": ["validate_schema", "check_consistency", "verify_integrity", "audit_log", "sanitize_input"],
    "setup": ["validate", "sanitize", "clean", "purge", "reset"],
}

_FAKE_DOCSTRINGS = [
    "Convert input data to network byte order for serialization.",
    "Apply LZ77 compression with Huffman coding stage.",
    "Compute CRC-64 checksum over the provided buffer.",
    "Generate lookup table for S-box substitution.",
    "Pack structure fields into aligned memory layout.",
    "Perform bit-interleaving for error correction.",
    "Normalize vector to unit length using L2 norm.",
    "Compute Levenshtein distance between two sequences.",
    "Transpose matrix in column-major order.",
    "Apply morphological dilation to binary image.",
]


class FunctionIntentObfuscator(ast.NodeTransformer):
    """Obfuscate function intent by renaming, reordering, and decoy injection."""

    def __init__(self, seed: int | None = None):
        self._rng = _random.Random(seed) if seed is not None else _random.Random()
        self._name_map: dict[str, str] = {}
        self._call_sites: dict[str, list[ast.Call]] = {}

    def obfuscate_intent(self, tree: ast.AST) -> ast.AST:
        self._name_map.clear()
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for func in funcs:
            self._name_map[func.name] = self._pick_misleading_name(func.name)
        # Index direct Name call sites per function (original names) so the
        # parameter swap can prove single-caller safety + rewrite the site.
        self._call_sites = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self._call_sites.setdefault(node.func.id, []).append(node)
        self.visit(tree)
        ast.fix_missing_locations(tree)
        return tree

    def _pick_misleading_name(self, original: str) -> str:
        lower = original.lower()
        for keyword, replacements in _MISLEADING_MAP.items():
            if keyword in lower:
                return self._rng.choice(replacements)
        return f"_nx_op_{secrets.token_hex(4)}"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        orig_name = node.name
        new_name = self._name_map.get(node.name, node.name)
        node.name = new_name

        node = self._swap_parameters(node, orig_name)
        node = self._wrap_body(node)
        node = self._add_fake_docstring(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        orig_name = node.name
        new_name = self._name_map.get(node.name, node.name)
        node.name = new_name
        node = self._swap_parameters(node, orig_name)
        node = self._wrap_body(node)
        node = self._add_fake_docstring(node)
        return node

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id in self._name_map:
            node.id = self._name_map[node.id]
        return node

    @staticmethod
    def _is_private(name: str) -> bool:
        return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))

    def _swap_parameters(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        orig_name: str | None = None,
    ) -> ast.FunctionDef | ast.AsyncFunctionDef:
        """Pairwise-swap positional params ONLY for provably single-caller
        private functions (and rewrite that call site); otherwise a no-op.

        Reordering params without rewriting call sites silently changes
        positional-argument binding, and renaming params without rewriting
        the body breaks name resolution — both miscompile, so both require
        the strict gate below. (Parameter renaming was removed outright:
        it never rewrote body references.)
        """
        args = func.args
        all_args = args.posonlyargs + args.args
        if len(all_args) < 2:
            return func
        key = orig_name if orig_name is not None else func.name
        if not self._is_private(key):
            return func
        sites = self._call_sites.get(key, [])
        if len(sites) != 1:
            return func
        call = sites[0]
        if call.keywords:
            return func
        if args.defaults or args.kwonlyargs or args.vararg or args.kwarg or args.posonlyargs:
            return func
        if len(call.args) != len(all_args):
            return func
        perm: list[int] = []
        for i in range(0, len(all_args) - 1, 2):
            perm.append(i + 1)
            perm.append(i)
        if len(all_args) % 2 == 1:
            perm.append(len(all_args) - 1)
        args.args = [all_args[p] for p in perm]
        call.args = [call.args[p] for p in perm]
        return func

    def _add_fake_docstring(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.FunctionDef | ast.AsyncFunctionDef:
        doc = self._rng.choice(_FAKE_DOCSTRINGS)
        doc_stmt = ast.Expr(value=ast.Constant(value=doc))
        if func.body:
            first = func.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                func.body[0] = doc_stmt
            else:
                func.body.insert(0, doc_stmt)
        else:
            func.body.append(doc_stmt)
        return func

    def _wrap_body(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.FunctionDef | ast.AsyncFunctionDef:
        wrapper_var = f"_nx_gc_{secrets.token_hex(4)}"
        sentinel_var = f"_nx_sentinel_{secrets.token_hex(4)}"

        preamble = [
            ast.Assign(
                targets=[ast.Name(id=wrapper_var, ctx=ast.Store())],
                value=ast.Constant(value=False),
            ),
            ast.Assign(
                targets=[ast.Name(id=sentinel_var, ctx=ast.Store())],
                value=ast.Constant(value=self._rng.randint(0, 1000)),
            ),
            ast.If(
                test=ast.Name(id=wrapper_var, ctx=ast.Load()),
                body=[ast.Expr(value=ast.Constant(value="unrelated transformation stage"))],
                orelse=[],
            ),
        ]
        func.body = preamble + func.body

        postamble = [
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id=sentinel_var, ctx=ast.Load()),
                    ops=[ast.Gt()],
                    comparators=[ast.Constant(value=10000)],
                ),
                body=[ast.Expr(value=ast.Constant(value="cleanup stage complete"))],
                orelse=[],
            ),
        ]
        func.body = func.body + postamble

        return func

    def get_name_map(self) -> dict[str, str]:
        return dict(self._name_map)
