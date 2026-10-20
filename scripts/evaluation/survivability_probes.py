import ast
import os
import re
from typing import Set

_CANONICAL_OPCODES: Set[str] = {
    'OP_NOP', 'OP_ADD', 'OP_SUB', 'OP_MUL', 'OP_DIV', 'OP_MOD',
    'OP_AND', 'OP_OR', 'OP_XOR', 'OP_NOT', 'OP_SHL', 'OP_SHR',
    'OP_LOAD', 'OP_STORE', 'OP_JMP', 'OP_BZ', 'OP_BNZ', 'OP_CALL',
    'OP_RET', 'OP_PUSH', 'OP_POP', 'OP_MOV', 'OP_CMP',
    'OP_HALT', 'OP_IN', 'OP_OUT',
}


def probe_watermark(artifact) -> float:
    """
    Try to extract watermark. Returns 1.0 if intact, 0.0 if removed.
    For Python source, checks if watermark comments or string patterns survive.
    For binary artifacts, checks byte-level markers.
    """
    if isinstance(artifact, str) and os.path.isfile(artifact):
        try:
            with open(artifact, 'rb') as f:
                data = f.read()
        except (IOError, OSError):
            # Fail-closed: an unreadable artifact is not an intact
            # watermark (was a neutral 0.5).
            return 0.0

        if data[:4] == b'\x7fELF':
            matches = len(re.findall(rb'[Nn][Ii][Xx][Oo][Nn]_[Ww][Mm]', data))
            return min(1.0, matches / 3.0)

        try:
            text = data.decode('utf-8', errors='replace')
        except UnicodeDecodeError:
            return 0.5

        watermark_patterns = [
            r'#\s*watermark',
            r'#\s*WM:',
            r'__watermark__',
            r'"_nx_wm_',
            r"'nx_wm_",
            r'watermark\s*=\s*["\']',
        ]
        found = sum(1 for p in watermark_patterns if re.search(p, text, re.IGNORECASE))
        if found >= 3:
            return 1.0
        if found >= 1:
            return 0.6
        return 0.2

    if isinstance(artifact, str):
        text = artifact
    else:
        text = str(artifact)

    watermark_patterns = [
        r'#\s*watermark',
        r'#\s*WM:',
        r'__watermark__',
        r'"_nx_wm_',
        r"'nx_wm_",
        r'watermark\s*=\s*["\']',
    ]
    found = sum(1 for p in watermark_patterns if re.search(p, text, re.IGNORECASE))
    if found >= 3:
        return 1.0
    if found >= 1:
        return 0.6
    return 0.2


def probe_vm_opcodes(artifact) -> float:
    """
    Measure VM opcode deviation from canonical opcode table.
    Higher score = more custom/non-standard opcodes = better obfuscation.
    Returns 1.0 if all opcodes are custom (non-canonical), 0.0 if all are standard.
    """
    text = artifact
    if isinstance(artifact, str) and os.path.isfile(artifact):
        try:
            with open(artifact, 'r') as f:
                text = f.read()
        except (IOError, OSError):
            pass
    elif not isinstance(artifact, str):
        text = str(artifact)

    found_opcodes = set(re.findall(r'OP_([A-Z0-9_]+)', text))
    if not found_opcodes:
        # Fail-closed: no measurable opcodes is not evidence of
        # deviation (was a neutral 0.5).
        return 0.0

    full_names = {'OP_' + name for name in found_opcodes}
    custom = full_names - _CANONICAL_OPCODES
    total = len(full_names)
    deviation = len(custom) / total if total > 0 else 0.0
    return max(0.0, min(1.0, deviation))


def probe_cfg(artifact) -> float:
    """
    Measure CFG reconstruction resistance by comparing original CFG
    to CFG extracted from a deobfuscated/normalized version.
    Returns 1.0 if CFG is completely different (high resistance),
    0.0 if identical (no resistance).
    """
    orig_blocks = _extract_cfg_blocks(artifact)

    normalized = _normalize_source(artifact)
    recon_blocks = _reconstruct_cfg(normalized)

    if not orig_blocks:
        # Fail-closed: nothing measurable proves nothing (was 0.5).
        return 0.0

    if not recon_blocks:
        return 1.0

    intersection = orig_blocks & recon_blocks
    union = orig_blocks | recon_blocks
    if not union:
        return 1.0
    similarity = len(intersection) / len(union)
    return 1.0 - similarity


def probe_fragments(artifact) -> float:
    """
    Check if fragment boundaries are detectable.
    1.0 - detection_rate.
    Returns 1.0 if fragments are perfectly hidden (undetectable).
    """
    detected = _detect_fragment_boundaries(artifact)
    total_expected = _count_expected_fragments(artifact)

    if total_expected == 0:
        # Fail-closed: with nothing expected there is nothing hidden —
        # a vacuous 1.0 ("perfectly hidden") certified empty inputs.
        return 0.0

    detection_rate = min(1.0, detected / total_expected)
    return 1.0 - detection_rate


def _extract_vm_opcodes(artifact) -> str:
    if isinstance(artifact, str) and os.path.isfile(artifact):
        try:
            with open(artifact, 'rb') as f:
                data = f.read()
            text = data.decode('utf-8', errors='replace')
        except (IOError, OSError):
            text = artifact
    else:
        text = str(artifact) if not isinstance(artifact, str) else artifact

    opcodes = re.findall(r'OP_([A-Z0-9_]+)', text)
    if not opcodes:
        opcodes = re.findall(r'opcode[_\s]*[:=]\s*(\d+)', text)
    return ''.join(opcodes[:100])


def _simulate_deobfuscation(artifact) -> str:
    text = artifact
    if isinstance(artifact, str) and os.path.isfile(artifact):
        try:
            with open(artifact, 'r') as f:
                text = f.read()
        except (IOError, OSError):
            return artifact
    text = re.sub(r'OP_[A-Z0-9_]+\s*=\s*\d+', '', text)
    text = re.sub(r'vm_execute.*', '', text)
    text = re.sub(r'dispatch_table.*', '', text)
    return text


def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _normalize_source(source_text: str) -> str:
    """
    Normalize source to simulate decompiler output:
    - Strip dead code blocks (if __debug__:, if 0:)
    - Normalize obfuscated variable names (_0x... -> v_N)
    - Remove opaque predicates (constant if-conditions)
    """
    lines = source_text.split('\n')
    filtered = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith('if __debug__:') or stripped == 'if 0:':
            base_indent = len(line) - len(line.lstrip())
            i += 1
            while i < len(lines):
                if lines[i].strip() == '':
                    i += 1
                    continue
                curr_indent = len(lines[i]) - len(lines[i].lstrip())
                if curr_indent <= base_indent and lines[i].strip():
                    break
                i += 1
            continue
        filtered.append(line)
        i += 1
    text = '\n'.join(filtered)

    counter = [0]

    def _replace_obfuscated(m):
        counter[0] += 1
        return f'v_{counter[0]}'
    text = re.sub(r'_0x[a-f0-9]+', _replace_obfuscated, text)

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text

    class _Normalizer(ast.NodeTransformer):
        def visit_If(self, node):
            if isinstance(node.test, ast.Constant):
                if node.test.value:
                    body = [self.visit(stmt) for stmt in node.body]
                    orelse = [self.visit(stmt) for stmt in node.orelse]
                    return body + orelse
                else:
                    return [self.visit(stmt) for stmt in node.orelse]
            if isinstance(node.test, ast.Name) and node.test.id == '__debug__':
                return [self.visit(stmt) for stmt in node.orelse]
            self.generic_visit(node)
            return node

    transformer = _Normalizer()
    tree = transformer.visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _extract_cfg_blocks(artifact) -> set:
    text = artifact
    if isinstance(artifact, str) and os.path.isfile(artifact):
        try:
            with open(artifact, 'r') as f:
                text = f.read()
        except (IOError, OSError):
            return set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()

    blocks = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            blocks.add(('func', node.name, node.lineno))
        elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
            blocks.add(('ctrl', type(node).__name__, node.lineno))
    return blocks


def _reconstruct_cfg(artifact) -> set:
    return _extract_cfg_blocks(artifact)


def _detect_fragment_boundaries(artifact) -> int:
    text = artifact
    if isinstance(artifact, str) and os.path.isfile(artifact):
        try:
            with open(artifact, 'r') as f:
                text = f.read()
        except (IOError, OSError):
            return 0
    patterns = [
        r'frag_\d+',
        r'fragment_\d+',
        r'\.fragment',
        r'end_fragment',
        r'begin_fragment',
        r'FRAGMENT_BOUNDARY',
    ]
    count = 0
    for p in patterns:
        count += len(re.findall(p, text))
    return count


def _count_expected_fragments(artifact) -> int:
    text = artifact
    if isinstance(artifact, str) and os.path.isfile(artifact):
        try:
            with open(artifact, 'r') as f:
                text = f.read()
        except (IOError, OSError):
            return 0
    frag_starts = len(re.findall(r'frag_(?:start|begin|0)', text))
    func_count = text.count('def ') + text.count('function ')
    return max(frag_starts, func_count // 3)
