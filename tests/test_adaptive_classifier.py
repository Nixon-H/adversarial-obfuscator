import ast
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.classification import FunctionClassifier, StrategySelector, STRATEGY_MAP


# ---------------------------------------------------------------------------
# Test functions as source snippets for each category
# ---------------------------------------------------------------------------

CRYPTO_SRC = """
import hashlib

def aes_encrypt(data, key):
    sbox = [0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, 0x30]
    state = [b ^ k for b, k in zip(data, key)]
    for _ in range(10):
        for i in range(16):
            state[i] = sbox[(state[i] >> 4) * 16 + (state[i] & 0x0f)]
        # shift rows
        state[1], state[5], state[9], state[13] = state[5], state[9], state[13], state[1]
        # mix columns
        for i in range(4):
            a = state[4*i:4*(i+1)]
            state[4*i] = gmul(a[0], 2) ^ gmul(a[1], 3) ^ a[2] ^ a[3]
        # add round key
        for i in range(16):
            state[i] ^= key[i % len(key)]
    return bytes(state)

def gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xff
        if hi:
            a ^= 0x1b
        b >>= 1
    return p

def decrypt_aes(data):
    return aes_encrypt(data, b'\\x00' * 16)

def compute_sha256(data):
    return hashlib.sha256(data).hexdigest()
"""

LICENSE_SRC = """
from datetime import datetime

def verify_license(key):
    valid_keys = ['ABCD-1234-EFGH-5678', 'WXYZ-9012-IJKL-3456']
    if key in valid_keys:
        return True
    return False

def check_auth(token):
    if token == 'super-secret-token-2024':
        return True
    return False

def validate_user(username, password):
    if username == 'admin' and password == 'password123':
        return True
    if datetime.now().year > 2025:
        return password == 'new_password'
    return False
"""

KEY_DERIVE_SRC = """
import hashlib
import os

def derive_key(password, salt, iterations=100000):
    key = password.encode('utf-8')
    for i in range(iterations):
        key = hashlib.sha256(key + salt + str(i).encode()).digest()
    return key

def pbkdf2_derive(password, salt):
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return dk

def generate_key_material(seed):
    return hashlib.sha256(seed).digest() + os.urandom(16)
"""

SIMPLE_SRC = """
def add(a, b):
    return a + b

def greet(name):
    return f'Hello, {name}!'

def is_even(n):
    return n % 2 == 0

def square(x):
    return x * x

def identity(x):
    return x
"""

SENSITIVE_SRC = """
import math
import statistics
import sys

def complex_algorithm(data, weights, bias):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            if weights[i] != 0:
                temp = data[i] * weights[i] + bias
                if temp > 100:
                    temp = math.log(temp)
                elif temp > 50:
                    temp = math.sqrt(temp)
                else:
                    temp = temp * 1.5
                for j in range(len(weights)):
                    if j % 2 == 0:
                        temp += math.sin(data[j])
                    else:
                        temp -= math.cos(data[j])
                result.append(temp)
            else:
                result.append(0)
        elif data[i] == 0:
            result.append(bias)
        else:
            try:
                temp = -data[i] * weights[i] + bias
                result.append(temp)
            except Exception:
                result.append(None)
    mean_val = statistics.mean(result) if result else 0
    std_val = statistics.stdev(result) if len(result) > 1 else 0
    return {'result': result, 'mean': mean_val, 'std': std_val}

def analyze_statistics(values):
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)
    median = sorted(values)[n // 2]
    return {'mean': mean, 'median': median, 'std': std, 'variance': variance}
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _classify(source: str) -> dict:
    classifier = FunctionClassifier()
    tree = ast.parse(source)
    classifier._collect_imports(tree)
    results = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            results[node.name] = classifier.classify(node)
    return results


class TestFunctionClassifier:
    """
    TestFunctionClassifier
    
    Positive test cases for functionclassifier.
    """
    def test_crypto_classification(self):
        results = _classify(CRYPTO_SRC)
        assert results.get('aes_encrypt') == 'crypto', f"Expected crypto, got {results.get('aes_encrypt')}"
        assert results.get('decrypt_aes') == 'crypto', f"Expected crypto, got {results.get('decrypt_aes')}"
        assert results.get('compute_sha256') == 'crypto', f"Expected crypto, got {results.get('compute_sha256')}"

    def test_license_classification(self):
        results = _classify(LICENSE_SRC)
        assert results.get('verify_license') == 'license_check', f"Expected license_check, got {results.get('verify_license')}"
        assert results.get('check_auth') == 'license_check', f"Expected license_check, got {results.get('check_auth')}"
        assert results.get('validate_user') == 'license_check', f"Expected license_check, got {results.get('validate_user')}"

    def test_key_derivation_classification(self):
        results = _classify(KEY_DERIVE_SRC)
        assert results.get('derive_key') == 'key_derivation', f"Expected key_derivation, got {results.get('derive_key')}"
        assert results.get('pbkdf2_derive') == 'key_derivation', f"Expected key_derivation, got {results.get('pbkdf2_derive')}"

    def test_simple_helper_classification(self):
        helpers = {
            'add': 'def add(a, b):\n    return a + b\n',
            'greet': 'def greet(name):\n    return "Hello, " + name\n',
            'is_even': 'def is_even(n):\n    return n % 2 == 0\n',
            'square': 'def square(x):\n    return x * x\n',
            'identity': 'def identity(x):\n    return x\n',
        }
        for fn_name, src in helpers.items():
            tree = ast.parse(src)
            classifier = FunctionClassifier()
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    cls = classifier.classify(node)
                    assert cls == 'simple_helper', f"{fn_name}: Expected simple_helper, got {cls}"

    def test_sensitive_algo_classification(self):
        results = _classify(SENSITIVE_SRC)
        assert results.get('complex_algorithm') == 'sensitive_algo', f"Expected sensitive_algo, got {results.get('complex_algorithm')}"
        assert results.get('analyze_statistics') == 'sensitive_algo', f"Expected sensitive_algo, got {results.get('analyze_statistics')}"

    def test_classify_from_source(self):
        classifier = FunctionClassifier()
        results = classifier.classify_from_source(CRYPTO_SRC)
        assert 'aes_encrypt' in results
        assert results['aes_encrypt'] == 'crypto'

    def test_all_categories_present(self):
        assert set(FunctionClassifier.CATEGORIES) == {
            'simple_helper', 'crypto', 'license_check', 'key_derivation', 'sensitive_algo'
        }

    def test_empty_function(self):
        src = "def empty():\n    pass\n"
        tree = ast.parse(src)
        classifier = FunctionClassifier()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                cls = classifier.classify(node)
                assert cls == 'simple_helper', f"Expected simple_helper, got {cls}"

    def test_mixed_characteristics(self):
        src = """
import hashlib
def mixed_func(data):
    if data == 'hardcoded':
        return hashlib.sha256(data.encode()).hexdigest()
    return data
"""
        results = _classify(src)
        cls = results.get('mixed_func', '')
        assert cls == 'crypto', f"Expected crypto (uses hashlib + hash), got {cls}"


class TestStrategySelector:
    """
    TestStrategySelector
    
    Positive test cases for strategyselector.
    """
    def test_select_simple_helper(self):
        sel = StrategySelector()
        passes = sel.select('simple_helper')
        assert passes == ['ast_obfuscate']

    def test_select_crypto(self):
        sel = StrategySelector()
        passes = sel.select('crypto')
        assert passes == ['ast_obfuscate', 'vm_compile']

    def test_select_license_check(self):
        sel = StrategySelector()
        passes = sel.select('license_check')
        assert passes == ['ast_obfuscate', 'jit_compile']

    def test_select_key_derivation(self):
        sel = StrategySelector()
        passes = sel.select('key_derivation')
        assert passes == ['ast_obfuscate', 'rop_compile']

    def test_select_sensitive_algo(self):
        sel = StrategySelector()
        passes = sel.select('sensitive_algo')
        assert passes == ['ast_obfuscate', 'oram_compile']

    def test_select_unknown_defaults_to_simple(self):
        sel = StrategySelector()
        passes = sel.select('unknown_category')
        assert passes == ['ast_obfuscate']

    def test_get_config(self):
        sel = StrategySelector()
        config = sel.get_config('crypto')
        assert 'ast_obfuscate' in config
        assert 'vm_compile' in config
        assert config['vm_compile']['full_vm_wrapping'] is True

    def test_get_description(self):
        sel = StrategySelector()
        assert 'Light AST' in sel.get_description('simple_helper')
        assert 'VM' in sel.get_description('crypto')
        assert 'JIT' in sel.get_description('license_check')
        assert 'ROP' in sel.get_description('key_derivation')
        assert 'ORAM' in sel.get_description('sensitive_algo')

    def test_strategy_map_structure(self):
        for cat, entry in STRATEGY_MAP.items():
            assert 'passes' in entry
            assert 'config' in entry
            assert 'description' in entry
            assert len(entry['passes']) >= 1
            assert 'ast_obfuscate' in entry['passes']

    def test_edge_case_empty_function_strategy(self):
        """Empty function should still get a valid strategy."""
        src = "def empty():\n    pass\n"
        tree = ast.parse(src)
        classifier = FunctionClassifier()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                cls = classifier.classify(node)
                assert cls == 'simple_helper'
                sel = StrategySelector()
                passes = sel.select(cls)
                assert passes == ['ast_obfuscate']
