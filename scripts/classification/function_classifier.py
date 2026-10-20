"""
function_classifier.py

Purpose:
Analyzes Python source code via AST to classify each function into a
protection category: simple_helper, crypto, license_check,
key_derivation, or sensitive_algo.

TWIN: scripts/classify_features.py (feature-level claim validation) —
that script classifies the 129 RESEARCH features; this module classifies
CODE to drive pass selection (see strategy_selector.py). Do not merge.

Architectural Role:
First stage of the function-classification pipeline. The output feeds
StrategySelector, which maps each category to a set of obfuscation
passes. The classifier inspects imports, function names, AST patterns,
cyclomatic complexity, nesting depth, and use of crypto/date APIs.

Security Relevance:
Dictates which protection stack each function receives. A crypto
function misclassified as simple_helper may skip VM compilation,
leaving it exposed. Conversely, classifying a helper as crypto wastes
overhead. The heuristics are tuned to be conservative (favor
over-classification) for security-sensitive patterns.
"""

import ast
import re
from typing import Dict, Set


class FunctionClassifier:
    """
    Analyzes Python source code via AST to classify each function into a
    protection category: simple_helper, crypto, license_check,
    key_derivation, or sensitive_algo.

    Uses a combination of import inspection, name-based regex matching,
    AST pattern detection, cyclomatic complexity, and nesting depth to
    determine the appropriate category. The classification drives
    StrategySelector which maps each category to a protection pass list.

    Heuristics are conservative: when in doubt between two categories,
    the classifier picks the stronger protection level to avoid
    under-protecting sensitive code.
    """

    CATEGORIES = ['simple_helper', 'crypto', 'license_check', 'key_derivation', 'sensitive_algo']

    CRYPTO_NAMES = re.compile(
        r'(aes|encrypt|decrypt|cipher|hash|sha|md5|hmac|rsa|dsa|ecc|elliptic'
        r'|signature|sign|digest|bcrypt|argon)', re.I
    )
    LICENSE_NAMES = re.compile(r'(license|verify|validate|check|auth|register)', re.I)
    KEY_DERIVE_NAMES = re.compile(r'(key|derive|pbkdf|scrypt|argon|kdf)', re.I)

    CRYPTO_IMPORTS = frozenset({
        'hashlib', 'cryptography', 'Crypto', 'Crypto.Cipher', 'Crypto.Hash',
        'Crypto.Protocol', 'Crypto.PublicKey', 'Crypto.Util',
        'nacl', 'pynacl', 'ecdsa', 'pycryptodome',
    })

    def __init__(self):
        """
        Initialize the classifier with empty import state.

        Imports are collected once per classify_from_source() call
        and cached in _module_imports for reuse across function
        classifications within the same source file.
        """
        self._module_imports: Set[str] = set()
        self._module_imports_aliases: Dict[str, str] = {}

    def classify(self, func_def: ast.FunctionDef) -> str:
        """
        Classify a single function definition node.

        Returns one of: 'key_derivation', 'crypto', 'license_check',
        'sensitive_algo', 'simple_helper'. The checks are ordered by
        specificity so that a function matching multiple patterns gets
        the most protection.
        """
        if self._is_key_derivation(func_def):
            return 'key_derivation'
        if self._is_crypto(func_def):
            return 'crypto'
        if self._is_license_check(func_def):
            return 'license_check'
        if self._is_sensitive_algo(func_def):
            return 'sensitive_algo'
        return 'simple_helper'

    def classify_from_source(self, source: str) -> Dict[str, str]:
        """
        Classify all functions in a Python source string.

        Parses the source into an AST, collects all imports, then
        classifies each FunctionDef node. Returns a dict mapping
        function name to category label.
        Handles SyntaxError gracefully by returning an empty dict.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {}
        self._collect_imports(tree)
        results: Dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                results[node.name] = self.classify(node)
        return results

    def _collect_imports(self, tree: ast.AST) -> None:
        """
        Walk the AST to collect all Import and ImportFrom statements.

        Populates _module_imports with fully-qualified module names
        and _module_imports_aliases with any 'as' aliases so that
        usage like 'import Crypto.Cipher.AES as aes' is tracked.
        """
        self._module_imports.clear()
        self._module_imports_aliases.clear()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._module_imports.add(alias.name)
                    if alias.asname:
                        self._module_imports_aliases[alias.asname] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                self._module_imports.add(module)
                for alias in node.names:
                    full = f'{module}.{alias.name}' if module else alias.name
                    self._module_imports.add(full)
                    if alias.asname:
                        self._module_imports_aliases[alias.asname] = full

    def _uses_crypto_import(self) -> bool:
        """
        Check whether any collected import matches a known crypto library.

        Matches against CRYPTO_IMPORTS (hashlib, cryptography, Crypto.*,
        nacl, pynacl, ecdsa, pycryptodome). Returns True if any import
        is a prefix or exact match.
        """
        for imp in self._module_imports:
            for prefix in self.CRYPTO_IMPORTS:
                if imp == prefix or imp.startswith(prefix + '.') or imp.startswith(prefix + ' '):
                    return True
        return False

    def _is_crypto(self, func_def: ast.FunctionDef) -> bool:
        """
        Heuristic for cryptographic function detection.

        Signals: name matches CRYPTO_NAMES regex, function body calls
        encrypt/decrypt/cipher/hash/digest/sign/verify methods, uses
        XOR/S-box symbols, or performs wide-bitwise operations on
        large constants (common in crypto primitives).
        """
        name = func_def.name.lower()
        if self.CRYPTO_NAMES.search(name):
            return True
        if self._uses_crypto_import():
            for node in ast.walk(func_def):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        attr = node.func.attr.lower()
                        if any(kw in attr for kw in ('encrypt', 'decrypt', 'cipher', 'hash',
                                                      'digest', 'sign', 'verify')):
                            return True
                if isinstance(node, ast.Name):
                    if node.id.lower() in ('xor', 'sbox', 's_box', 'sub_bytes'):
                        return True
        for node in ast.walk(func_def):
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitXor, ast.BitAnd, ast.BitOr)):
                if isinstance(node.right, ast.Constant) and isinstance(node.right.value, int):
                    if node.right.value > 0xFFFFFF:
                        return True
                    if node.right.value.bit_length() >= 32:
                        return True
        return False

    def _is_license_check(self, func_def: ast.FunctionDef) -> bool:
        """
        Heuristic for license/validation function detection.

        Signals: function name matches LICENSE_NAMES (license, verify,
        validate, check, auth, register). Body contains boolean returns,
        hardcoded comparisons, date comparisons, or calls to verify/validate.
        """
        name = func_def.name.lower()
        if not self.LICENSE_NAMES.search(name):
            return False

        returns_bool = False
        has_hardcoded_compare = False
        has_date_compare = False

        for node in ast.walk(func_def):
            if isinstance(node, ast.Return):
                if isinstance(node.value, (ast.Constant, ast.Name)):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
                        returns_bool = True
                    else:
                        returns_bool = True
            if isinstance(node, ast.Compare):
                if isinstance(node.left, ast.Constant) or any(isinstance(c, ast.Constant) for c in node.comparators):
                    has_hardcoded_compare = True
                for op in node.ops:
                    if isinstance(op, (ast.In, ast.NotIn)):
                        has_hardcoded_compare = True
                for c in node.comparators:
                    if _is_date_like(c):
                        has_date_compare = True
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attr = node.func.attr.lower()
                    if 'date' in attr or 'time' in attr or 'datetime' in attr or 'timestamp' in attr:
                        has_date_compare = True
                    if attr in ('verify', 'validate'):
                        has_hardcoded_compare = True

        return returns_bool or has_hardcoded_compare or has_date_compare

    def _is_key_derivation(self, func_def: ast.FunctionDef) -> bool:
        """
        Heuristic for key derivation function detection.

        Signals: function name matches KEY_DERIVE_NAMES (key, derive,
        pbkdf, scrypt, argon, kdf). Body contains hash-loop patterns,
        byte generation (urandom, token_bytes, randbytes), or wide
        integer bitwise ops characteristic of key schedule algorithms.
        """
        name = func_def.name.lower()
        if not self.KEY_DERIVE_NAMES.search(name):
            for node in ast.walk(func_def):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        attr = node.func.attr.lower()
                        if any(kw in attr for kw in ('pbkdf', 'derive', 'kdf', 'scrypt', 'argon')):
                            return True
            return False

        has_hash_loop = False
        generates_bytes = False

        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attr = node.func.attr.lower()
                    if any(kw in attr for kw in ('digest', 'update', 'pbkdf', 'derive', 'kdf', 'scrypt', 'argon')):
                        has_hash_loop = True
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('bytes', 'bytearray', 'urandom', 'token_bytes', 'randbytes'):
                        generates_bytes = True
                elif isinstance(node.func, ast.Attribute):
                    if 'bytes' in node.func.attr.lower() or 'random' in node.func.attr.lower():
                        generates_bytes = True
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.LShift | ast.RShift | ast.BitXor | ast.BitAnd | ast.BitOr):
                if isinstance(node.left, ast.Constant) and isinstance(node.left.value, int) and node.left.value.bit_length() > 128:
                    has_hash_loop = True

        for node in ast.walk(func_def):
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute):
                            if child.func.attr.lower() in ('digest', 'update', 'hash'):
                                has_hash_loop = True

        return has_hash_loop or generates_bytes

    def _is_sensitive_algo(self, func_def: ast.FunctionDef) -> bool:
        """
        Heuristic for sensitive/important algorithm detection.

        Signals: cyclomatic complexity >= 6, >= 2 imported modules,
        nesting depth >= 4, uses math/stat/numpy/scipy/torch/tf functions,
        >= 2 comprehensions, body >= 15 statements, or loops with
        many assignments (stateful algorithms).
        """
        complexity = _cyclomatic_complexity(func_def)
        if complexity >= 6:
            return True
        import_count = 0
        for node in ast.walk(func_def):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_count += 1
        if import_count >= 2:
            return True
        nest_depth = _max_nesting_depth(func_def)
        if nest_depth >= 4:
            return True

        math_stat_names = {
            'sqrt', 'log', 'exp', 'sin', 'cos', 'tan', 'pow', 'floor', 'ceil',
            'mean', 'median', 'std', 'variance', 'stdev', 'corrcoef', 'linregress',
            'sum', 'average', 'dot', 'matmul', 'transpose',
        }
        for node in ast.walk(func_def):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attr = node.func.attr.lower()
                    if attr in math_stat_names:
                        return True
                    if isinstance(node.func.value, ast.Name):
                        name = node.func.value.id.lower()
                        if name in ('math', 'statistics', 'numpy', 'np', 'scipy', 'torch', 'tf', 'jax'):
                            return True
                elif isinstance(node.func, ast.Name):
                    if node.func.id.lower() in math_stat_names:
                        return True

        comprehension_count = 0
        for node in ast.walk(func_def):
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                comprehension_count += 1
        if comprehension_count >= 2:
            return True

        body_size = len(func_def.body)
        if body_size >= 15:
            return True
        loop_state_count = 0
        for node in ast.walk(func_def):
            if isinstance(node, (ast.For, ast.While)):
                assigns = [c for c in ast.walk(node) if isinstance(c, ast.Assign)]
                if len(assigns) > 3:
                    loop_state_count += 1
        if loop_state_count >= 2:
            return True
        return False

    def _check_license(self, func_def: ast.FunctionDef) -> None:
        """
        Reserved for future license-check analysis.

        Currently a no-op placeholder. Intended to run deeper
        analysis on functions classified as license_check.
        """
        pass


def _cyclomatic_complexity(func_def: ast.FunctionDef) -> int:
    """
    Compute McCabe-style cyclomatic complexity for a function.

    Counts branching constructs (if, while, for, except, with, try,
    assert), boolean operators (each additional operand adds 1), and
    ternary expressions (ifexp).
    Used by _is_sensitive_algo to flag complex functions.
    """
    complexity = 1
    for node in ast.walk(func_def):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                              ast.With, ast.Try, ast.Assert)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
        elif isinstance(node, ast.IfExp):
            complexity += 1
    return complexity


def _max_nesting_depth(func_def: ast.FunctionDef) -> int:
    """
    Compute the maximum nesting depth of control-flow constructs.

    Tracks if/for/while/try/with/except-handler nesting via recursive
    walk. AsyncFor and AsyncWith are also counted.
    Deep nesting is a signal of algorithmic complexity.
    """
    max_depth = 0
    def _walk(node, depth):
        nonlocal max_depth
        max_depth = max(max_depth, depth)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With,
                                   ast.ExceptHandler, ast.AsyncFor, ast.AsyncWith)):
                _walk(child, depth + 1)
            else:
                _walk(child, depth)
    _walk(func_def, 0)
    return max_depth


def _is_date_like(node: ast.AST) -> bool:
    """
    Check whether an AST node represents a date-like value.

    Matches calls to date-related attributes/functions and string
    constants matching common date patterns (YYYY-MM-DD, MM/DD/YYYY).
    Used by _is_license_check for expiration date comparisons.
    """
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and 'date' in node.func.attr.lower():
            return True
        if isinstance(node.func, ast.Name) and 'date' in node.func.id.lower():
            return True
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            date_pattern = re.compile(r'\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}')
            return bool(date_pattern.search(node.value))
    return False
