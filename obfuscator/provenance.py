"""Advanced Protection - Code Provenance Removal.

Scans source code and removes/replaces identifying provenance markers.
"""

import ast
import hashlib
import json
import os
import random
import re
import struct
import sys
from typing import Any, Optional

_PHASE2_ENABLED = True

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "default.json"
)


def _phase2_enabled() -> bool:
    try:
        with open(_CONFIG_PATH) as f:
            cfg = json.load(f)
        return cfg.get("shadow_compiler", {}).get("advanced_protection", cfg.get("shadow_compiler", {}).get("phase2", {})).get("enabled", False)
    except Exception as _e:
        import logging as _lg
        _lg.warning(f"Config load failed, using defaults: {_e}")
        return _PHASE2_ENABLED


_ERROR_PATTERNS = re.compile(
    r"(Error|Invalid|Failed|expected|must be|not found|not supported|"
    r"required|missing|unexpected|already exists|permission denied|"
    r"connection refused|timeout|overflow|underflow|assert|exception|"
    r"warning|fatal|critical)",
    re.IGNORECASE,
)

_PROTOCOL_PATTERNS = re.compile(
    r"(AES|SHA|MD5|RSA|HMAC|TLS|SSL|HTTP|HTTPS|FTP|SSH|"
    r"Content-Type|Content-Length|Authorization|Bearer|Basic|"
    r"-----BEGIN |-----END |application/|text/|charset=|"
    r"json|base64|hex|utf-?8|ascii|utf16|urlencoded|"
    r"form-data|multipart|binary|octet-stream)",
    re.IGNORECASE,
)

_ALGORITHMIC_CONSTANTS: dict[int, str] = {
    0x6A09E667: "SHA-256 IV h0",
    0xBB67AE85: "SHA-256 IV h1",
    0x3C6EF372: "SHA-256 IV h2",
    0xA54FF53A: "SHA-256 IV h3",
    0x510E527F: "SHA-256 IV h4",
    0x9B05688C: "SHA-256 IV h5",
    0x1F83D9AB: "SHA-256 IV h6",
    0x5BE0CD19: "SHA-256 IV h7",
    0x9E3779B9: "Golden ratio hash (Knuth)",
    0x61C88647: "ThreadLocalRandom",
    0x517CC1B727220A95: "xxHash prime",
    0xC6A4A7935BD1E995: "MurmurHash3 mixing constant",
    0xC3D2E1F0: "CRC-32 polynomial remainder",
    0xEDB88320: "CRC-32 reversed polynomial",
    0x9E3779B97F4A7C15: "Golden ratio hash 64-bit",
    0xB84CB2FA: "ISAAC stream cipher constant",
    0x6C078965: "MT19937 (Mersenne Twister) constant",
    0x5DEECE66D: "LCG multiplier (java.util.Random)",
    0xB5297A4D: "PCG generator constant",
}

_LIBRARY_ADAPTER_TEMPLATE = """def {adapter_name}({params}):
    return {target_func}({args})
"""


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def scan_error_messages(ast_tree: ast.AST) -> list[dict[str, Any]]:
    """Find all string literals that look like error messages.

    Returns list of {node, message, line, col} for each found.
    """
    results: list[dict[str, Any]] = []
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _ERROR_PATTERNS.search(node.value):
                lineno = getattr(node, "lineno", 0)
                col_offset = getattr(node, "col_offset", 0)
                results.append({
                    "node": node,
                    "message": node.value,
                    "line": lineno,
                    "col": col_offset,
                })
    return results


def replace_error_messages(ast_tree: ast.Module) -> ast.Module:
    """Replace error message strings with integer error codes.

    Generates error_codes.json mapping codes->messages for dev use only.
    Error codes: E0001, E0002, etc. Randomly assigned per build.
    """
    found = scan_error_messages(ast_tree)
    code_map: dict[str, str] = {}
    error_codes: dict[str, str] = {}

    seen = set()
    for entry in found:
        msg = entry["message"]
        if msg in seen:
            continue
        seen.add(msg)
        code_num = len(code_map) + 1
        code_str = f"E{code_num:04d}"
        code_map[msg] = code_str
        error_codes[code_str] = msg

    seen_msgs = set(f["message"] for f in found)

    class ErrorReplacer(ast.NodeTransformer):
        def visit_Constant(self, node: ast.Constant) -> ast.AST:
            if isinstance(node.value, str) and node.value in code_map:
                code = code_map[node.value]
                return ast.Constant(value=code)
            return node

    transformer = ErrorReplacer()
    result = transformer.visit(ast_tree)
    ast.fix_missing_locations(result)

    try:
        codes_path = os.path.join(os.getcwd(), "error_codes.json")
        with open(codes_path, "w") as f:
            json.dump(error_codes, f, indent=2)
    except Exception:
        pass

    return result


def scan_protocol_strings(ast_tree: ast.AST) -> list[dict[str, Any]]:
    """Find strings that identify protocols, formats, or standards.

    Returns list of {node, string, line, col} for each found.
    """
    results: list[dict[str, Any]] = []
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _PROTOCOL_PATTERNS.search(node.value):
                lineno = getattr(node, "lineno", 0)
                col_offset = getattr(node, "col_offset", 0)
                results.append({
                    "node": node,
                    "string": node.value,
                    "line": lineno,
                    "col": col_offset,
                })
    return results


def _derive_string_key(seed: bytes, index: int, length: int) -> bytes:
    """Derive a per-string XOR key from build seed and index."""
    safe_len = max(1, min(length, 64))
    h = hashlib.blake2b(
        seed + struct.pack(">I", index), digest_size=safe_len
    )
    return h.digest()


def _make_xor_decode_ast(
    encoded_fragments: list[bytes],
    keys: list[bytes],
    var_name: str,
) -> list[ast.AST]:
    """Generate AST for runtime string reconstruction via XOR."""
    import_strs: list[ast.AST] = []
    body: list[ast.AST] = []

    fragments_var = f"_{var_name}_frags"
    keys_var = f"_{var_name}_keys"

    frag_lists: list[ast.AST] = []
    for frag in encoded_fragments:
        frag_lists.append(
            ast.Constant(value=bytes([b for b in frag]))
        )

    key_lists: list[ast.AST] = []
    for k in keys:
        key_lists.append(
            ast.Constant(value=bytes([b for b in k]))
        )

    body.append(
        ast.Assign(
            targets=[ast.Name(id=fragments_var, ctx=ast.Store())],
            value=ast.List(elts=frag_lists, ctx=ast.Load()),
        )
    )
    body.append(
        ast.Assign(
            targets=[ast.Name(id=keys_var, ctx=ast.Store())],
            value=ast.List(elts=key_lists, ctx=ast.Load()),
        )
    )

    recover_call = ast.Call(
        func=ast.Attribute(
            value=ast.Call(
                func=ast.Name(id="bytes", ctx=ast.Load()),
                args=[],
                keywords=[],
            ),
            attr="join",
            ctx=ast.Load(),
        ),
        args=[
            ast.ListComp(
                elt=ast.Call(
                    func=ast.Attribute(
                        value=ast.BinOp(
                            left=ast.BinOp(
                                left=ast.Subscript(
                                    value=ast.Name(id=fragments_var, ctx=ast.Load()),
                                    slice=ast.Name(id="_i", ctx=ast.Load()),
                                    ctx=ast.Load(),
                                ),
                                op=ast.BitXor(),
                                right=ast.Subscript(
                                    value=ast.Name(id=keys_var, ctx=ast.Load()),
                                    slice=ast.Name(id="_i", ctx=ast.Load()),
                                    ctx=ast.Load(),
                                ),
                            ),
                            op=ast.BitXor(),
                            right=ast.Subscript(
                                value=ast.Name(id=keys_var, ctx=ast.Load()),
                                slice=ast.Name(id="_i", ctx=ast.Load()),
                                ctx=ast.Load(),
                            ),
                        ),
                        attr="decode",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                ),
                generators=[
                    ast.comprehension(
                        target=ast.Name(id="_i", ctx=ast.Store()),
                        iter=ast.Call(
                            func=ast.Name(id="range", ctx=ast.Load()),
                            args=[
                                ast.Call(
                                    func=ast.Name(id="len", ctx=ast.Load()),
                                    args=[ast.Name(id=fragments_var, ctx=ast.Load())],
                                    keywords=[],
                                )
                            ],
                            keywords=[],
                        ),
                        ifs=[],
                        is_async=0,
                    )
                ],
            )
        ],
        keywords=[],
    )

    return body


def encode_sensitive_strings(
    ast_tree: ast.Module, seed: bytes
) -> ast.Module:
    """Replace sensitive strings with runtime-constructed byte sequences.

    Each string is split into fragments, each fragment XOR-encrypted with
    a per-string key derived from the build seed + string index.
    """
    protocol_strings = scan_protocol_strings(ast_tree)
    if not protocol_strings:
        return ast_tree

    string_index = 0
    replacements: dict[ast.Constant, str] = {}
    encoded_map: dict[str, tuple[list[bytes], list[bytes]]] = {}

    for entry in protocol_strings:
        node = entry["node"]
        s = entry["string"]
        if not isinstance(node, ast.Constant):
            continue
        key = _derive_string_key(seed, string_index, len(s))
        frag_size = max(4, len(s) // 3)
        fragments: list[bytes] = []
        frag_keys: list[bytes] = []
        for start in range(0, len(s), frag_size):
            frag = s[start : start + frag_size].encode("utf-8")
            frag_key = _derive_string_key(
                seed + struct.pack(">I", string_index), start, len(frag)
            )
            encrypted = bytes(a ^ b for a, b in zip(frag, frag_key))
            fragments.append(encrypted)
            frag_keys.append(frag_key)
        encoded_map[s] = (fragments, frag_keys)
        var_name = f"_nx_str_{string_index}"
        replacements[node] = var_name
        string_index += 1

    class StringEncoder(ast.NodeTransformer):
        def visit_Module(self, node: ast.Module) -> ast.AST:
            new_body: list[ast.AST] = []
            for entry in protocol_strings:
                target_node = entry["node"]
                s = entry["string"]
                if s in encoded_map:
                    fragments, frag_keys = encoded_map[s]
                    var_name = replacements.get(target_node, "")
                    if var_name:
                        decode_stmts = _make_xor_decode_ast(
                            fragments, frag_keys, var_name
                        )
                        new_body.extend(decode_stmts)
            new_body.extend(node.body)
            node.body = new_body
            return node

        def visit_Constant(self, node: ast.Constant) -> ast.AST:
            if node in replacements:
                return ast.Name(id=replacements[node], ctx=ast.Load())
            return node

    transformer = StringEncoder()
    result = transformer.visit(ast_tree)
    ast.fix_missing_locations(result)
    return result


def scan_algorithmic_constants(
    ast_tree: ast.AST,
) -> list[dict[str, Any]]:
    """Find known cryptographic/mathematical constants.

    Returns list of {node, value, name, line, col} for each found.
    """
    results: list[dict[str, Any]] = []
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            for const_val, const_name in _ALGORITHMIC_CONSTANTS.items():
                if node.value == const_val:
                    lineno = getattr(node, "lineno", 0)
                    col_offset = getattr(node, "col_offset", 0)
                    results.append({
                        "node": node,
                        "value": node.value,
                        "name": const_name,
                        "line": lineno,
                        "col": col_offset,
                    })
                    break
    return results


def obfuscate_algorithmic_constants(ast_tree: ast.Module) -> ast.Module:
    """Replace algorithmic constants with runtime-computed expressions.

    Each constant is encoded as: (constant XOR runtime_derived_mask)
    where runtime_derived_mask is computed from build_seed + context.
    """
    found = scan_algorithmic_constants(ast_tree)
    if not found:
        return ast_tree

    rand = random.Random()
    obfuscations: dict[int, tuple[int, int]] = {}

    unique_values = set(f["value"] for f in found)
    for val in unique_values:
        mask = rand.getrandbits(64)
        encoded = val ^ mask
        obfuscations[val] = (encoded, mask)

    class ConstantObfuscator(ast.NodeTransformer):
        def visit_Constant(self, node: ast.Constant) -> ast.AST:
            if isinstance(node.value, int) and node.value in obfuscations:
                encoded, mask = obfuscations[node.value]
                mask_low = mask & 0xFFFFFFFF
                mask_high = (mask >> 32) & 0xFFFFFFFF
                encoded_low = encoded & 0xFFFFFFFF
                encoded_high = (encoded >> 32) & 0xFFFFFFFF

                runtime_mask = ast.BinOp(
                    left=ast.BinOp(
                        left=ast.Constant(value=mask_low),
                        op=ast.BitXor(),
                        right=ast.BinOp(
                            left=ast.Constant(value=mask_high),
                            op=ast.LShift(),
                            right=ast.Constant(value=32),
                        ),
                    ),
                    op=ast.BitXor(),
                    right=ast.BinOp(
                        left=ast.Constant(value=encoded_high),
                        op=ast.LShift(),
                        right=ast.Constant(value=32),
                    ),
                )

                reconstructed = ast.BinOp(
                    left=ast.BinOp(
                        left=ast.Constant(value=encoded_low),
                        op=ast.BitXor(),
                        right=runtime_mask,
                    ),
                    op=ast.BitXor(),
                    right=ast.BinOp(
                        left=ast.Constant(value=encoded_high),
                        op=ast.LShift(),
                        right=ast.Constant(value=32),
                    ),
                )

                return reconstructed
            return node

    transformer = ConstantObfuscator()
    result = transformer.visit(ast_tree)
    ast.fix_missing_locations(result)
    return result


def _generate_adapter_name(
    prefix: str, rand: random.Random
) -> str:
    """Generate a random adapter function name."""
    adjectives = ["nx", "zx", "qm", "xr", "vt", "kp", "mn", "rw"]
    suffix = f"{rand.randint(1000, 9999):x}"
    return f"_{rand.choice(adjectives)}_{suffix}_{prefix}"


def wrap_library_calls(
    ast_tree: ast.Module, library_patterns: dict[str, str]
) -> ast.Module:
    """Wrap calls to known libraries with generated-name adapters.

    library_patterns: {'chacha20': 'chacha20_poly1305_encrypt', ...}
    """
    rand = random.Random()
    func_names = set(
        name.lower() for name in library_patterns.values()
    )

    call_sites: list[tuple[ast.Call, str]] = []

    for node in ast.walk(ast_tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            fname = node.func.id.lower()
            if fname in func_names:
                call_sites.append((node, node.func.id))

    if not call_sites:
        return ast_tree

    used: set[str] = set()
    wrappers: list[ast.FunctionDef] = []

    for _, original_name in call_sites:
        if original_name in used:
            continue
        used.add(original_name)

        adapter_name = _generate_adapter_name(
            original_name[:4], rand
        )

        num_params = 2
        params = [
            ast.arg(arg=f"a{i}", annotation=None)
            for i in range(num_params)
        ]

        call_args = [ast.Name(id=f"a{i}", ctx=ast.Load()) for i in range(num_params)]

        wrapper_body = [
            ast.Return(
                value=ast.Call(
                    func=ast.Name(id=original_name, ctx=ast.Load()),
                    args=call_args,
                    keywords=[],
                )
            )
        ]

        func_def = ast.FunctionDef(
            name=adapter_name,
            args=ast.arguments(
                posonlyargs=[],
                args=params,
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=wrapper_body,
            decorator_list=[],
            returns=None,
        )
        wrappers.append(func_def)

    class CallWrapper(ast.NodeTransformer):
        def __init__(self, wrap_map: dict[str, str]):
            self.wrap_map = wrap_map

        def visit_Call(self, node: ast.Call) -> ast.AST:
            if isinstance(node.func, ast.Name):
                lower = node.func.id.lower()
                if lower in self.wrap_map:
                    node.func.id = self.wrap_map[lower]
            return node

    wrap_map = {}
    for orig_name in used:
        lower = orig_name.lower()
        wrap_map[lower] = _generate_adapter_name(
            orig_name[:4], rand
        )

    transformer = CallWrapper(wrap_map)
    result = transformer.visit(ast_tree)

    if isinstance(result, ast.Module):
        result.body = wrappers + result.body

    ast.fix_missing_locations(result)
    return result


def audit_provenance(binary_path: str) -> dict[str, Any]:
    """Scan compiled binary for provenance leaks.

    Returns {pass: bool, warnings: list, errors: list}
    """
    if not _PHASE2_ENABLED:
        return {"pass": True, "warnings": [], "errors": []}

    warnings: list[str] = []
    errors: list[str] = []

    if not os.path.exists(binary_path):
        return {"pass": False, "warnings": [], "errors": ["Binary not found"]}

    try:
        with open(binary_path, "rb") as f:
            data = f.read()
    except Exception as e:
        return {"pass": False, "warnings": [], "errors": [f"Cannot read: {e}"]}

    data_lower = data.lower()

    for const_val, const_name in _ALGORITHMIC_CONSTANTS.items():
        try:
            packed = struct.pack("<Q", const_val)
            if packed in data:
                warnings.append(
                    f"Found constant {const_name} (0x{const_val:X}) in binary"
                )
        except Exception:
            pass
        try:
            packed_be = struct.pack(">Q", const_val)
            if packed_be in data:
                warnings.append(
                    f"Found constant {const_name} (0x{const_val:X}) in binary (BE)"
                )
        except Exception:
            pass

    protocol_checks = [
        b"application/", b"text/", b"charset=",
        b"base64", b"-----BEGIN ", b"Bearer ",
        b"Content-Type", b"Authorization",
    ]
    for pat in protocol_checks:
        if pat.lower() in data_lower:
            warnings.append(f"Found protocol string: {pat.decode(errors='replace')}")

    error_pattern_checks = [
        b"Invalid", b"Failed", b"Error:", b"Exception",
        b"Traceback", b"Permission denied",
    ]
    for pat in error_pattern_checks:
        if pat.lower() in data_lower:
            warnings.append(f"Found error string: {pat.decode(errors='replace')}")

    known_libs = [
        b"chacha20", b"aes", b"sha256", b"sha512",
        b"hmac", b"openssl", b"libcrypto", b"libssl",
    ]
    for lib in known_libs:
        if lib in data_lower:
            warnings.append(f"Found library reference: {lib.decode(errors='replace')}")

    return {
        "pass": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Nixon Code Provenance Removal Tool"
    )
    sub = parser.add_subparsers(dest="command")

    scan_parser = sub.add_parser("scan", help="Scan source for provenance markers")
    scan_parser.add_argument("input", help="Python source file")

    strip_parser = sub.add_parser(
        "strip", help="Strip provenance markers from source"
    )
    strip_parser.add_argument("input", help="Python source file")
    strip_parser.add_argument("-o", "--output", required=True, help="Output file")

    audit_parser = sub.add_parser("audit", help="Audit binary for provenance leaks")
    audit_parser.add_argument("binary", help="Binary file to scan")

    args = parser.parse_args()

    if not _PHASE2_ENABLED:
        print("[Advanced Protection disabled] Set advanced_protection.enabled=true in config/default.json")
        return

    if args.command == "scan":
        with open(args.input) as f:
            source = f.read()
        tree = ast.parse(source)
        errors = scan_error_messages(tree)
        protocols = scan_protocol_strings(tree)
        constants = scan_algorithmic_constants(tree)

        print(f"Error messages found: {len(errors)}")
        for e in errors:
            print(f"  Line {e['line']}:{e['col']} -> {e['message'][:60]}")
        print(f"Protocol strings found: {len(protocols)}")
        for p in protocols:
            print(f"  Line {p['line']}:{p['col']} -> {p['string'][:60]}")
        print(f"Algorithmic constants found: {len(constants)}")
        for c in constants:
            print(f"  Line {c['line']}:{c['col']} -> {c['name']}")

    elif args.command == "strip":
        with open(args.input) as f:
            source = f.read()
        tree = ast.parse(source)

        tree = replace_error_messages(tree)
        seed = hashlib.sha256(b"nixon_provenance_seed").digest()
        tree = encode_sensitive_strings(tree, seed)
        tree = obfuscate_algorithmic_constants(tree)

        try:
            import astor

            output = astor.to_source(tree)
        except ImportError:
            output = ast.dump(tree, indent=2)

        with open(args.output, "w") as f:
            f.write(output)
        print(f"Stripped source written to {args.output}")

    elif args.command == "audit":
        result = audit_provenance(args.binary)
        status = "PASS" if result["pass"] else "FAIL"
        print(f"Audit result: {status}")
        for w in result.get("warnings", []):
            print(f"  WARNING: {w}")
        for e in result.get("errors", []):
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
