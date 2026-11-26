"""
port_entangle.py

Purpose:
CPU port entanglement pass. Embeds timing checks into LLVM IR that measure
RDTSC deltas and correlate them with the target CPU's execution port
configuration (ALU, branch, load, store ports). Detected timing anomalies
trigger key corruption as an anti-debug / anti-emulation measure.

Architectural Role:
Anti-debug IR transformation pass. Injects prologue/epilogue code into
each function that reads the timestamp counter, measures elapsed cycles,
and compares against expected ranges for the target CPU microarchitecture.

Security Relevance:
- Detects emulation: emulators typically have different execution port
  configurations than real hardware, producing different RDTSC deltas.
- Detects debugger presence: single-stepping dramatically increases
  RDTSC deltas between successive measurements.
- On anomaly detection, calls __corrupt_key() which invalidates
  decryption keys, causing immediate runtime failure.
- The threshold and port configuration are baked into the IR at compile
  time, making them invisible in the source.
- Provides two modes:
  * hard_exit: crash immediately on timing anomaly.
  * soft (default): XOR-based corruption with threshold, harder to
    detect by the attacker.

Threat model: Debugger attachment, emulation, dynamic analysis,
timing manipulation.

Dependencies: None (standard library only: re, hashlib).
"""

import hashlib
import re
from typing import Optional

#: Capture the definition prefix and the function name so every function can
#: be patched with identifiers unique to it.
_FUNC_PATTERN = re.compile(
    r'(define\s+\S+\s+@(\w+)\s*\([^)]*\)\s*{)', re.MULTILINE)


def _func_suffix(name: str) -> str:
    """Stable short suffix for per-function LLVM local names."""
    return hashlib.blake2b(name.encode(), digest_size=4).hexdigest()


def _packed_seed(port_cfg: dict) -> int:
    total = sum(port_cfg[k] for k in
                ('alu_ports', 'branch_ports', 'load_ports', 'store_ports'))
    return int(f"{total:02x}{port_cfg['alu_ports']:02x}"
               f"{port_cfg['branch_ports']:02x}{port_cfg['load_ports']:02x}", 16)


def _anomaly_threshold(port_cfg: dict) -> int:
    """Generous upper bound in cycles for a function with no debugger."""
    return (sum(port_cfg.values()) + 8) * 10000


CPU_PORT_MAP = {
    'raptor_lake': {'alu_ports': 4, 'branch_ports': 1, 'load_ports': 2, 'store_ports': 1},
    'alder_lake': {'alu_ports': 4, 'branch_ports': 1, 'load_ports': 2, 'store_ports': 1},
    'zen4': {'alu_ports': 4, 'branch_ports': 1, 'load_ports': 3, 'store_ports': 2},
    'zen3': {'alu_ports': 4, 'branch_ports': 1, 'load_ports': 2, 'store_ports': 2},
    'auto': {'alu_ports': 3, 'branch_ports': 1, 'load_ports': 2, 'store_ports': 1},
}


def _function_body_span(text: str, body_start: int) -> tuple[int, int]:
    """Return (start, end) of a function body, where end is its closing brace."""
    depth = 1
    i = body_start
    while i < len(text):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return body_start, i
        i += 1
    return body_start, len(text)


def _first_block_label_end(text: str, body_start: int) -> int:
    """Offset just past the first basic-block label in a function body.

    Inserting the prologue directly after ``{`` puts instructions in an
    implicit entry block that then has no terminator, which llc rejects.
    """
    start, end = _function_body_span(text, body_start)
    m = re.search(r'^[A-Za-z_.][\w.$]*:\s*$', text[start:end], re.MULTILINE)
    if m is None:
        return body_start
    return start + m.end()


_LLVM_RETURN_TYPE = (
    r"(?:i\d+|half|bfloat|float|double|fp128|x86_fp80|ppc_fp128|ptr|"
    r"<[^>]+>|\[[^\]]+\]|\{[^}]*\}|%[A-Za-z0-9_.$]+)")
_RETURN_VALUE_RE = re.compile(
    rf"^\s*ret\s+({_LLVM_RETURN_TYPE})\s+(.+?)\s*$")
_RETURN_VOID_RE = re.compile(r"^\s*ret\s+void\s*$")
_BLOCK_LABEL_RE = re.compile(r"^[A-Za-z_.][A-Za-z0-9_.$]*:$")


def _parse_return(line: str) -> Optional[tuple[str, str]]:
    """Return ``(type, value)`` for a modeled LLVM return, else ``None``."""
    if _RETURN_VOID_RE.match(line):
        return "void", ""
    match = _RETURN_VALUE_RE.match(line)
    if not match:
        return None
    return match.group(1), match.group(2)


def _route_function_returns(
    body: str,
    prologue: str,
    epilogue: str,
    *,
    suffix: str,
    result_prefix: str,
    return_slot: Optional[str],
    checked_label: str,
) -> Optional[str]:
    """Route every return through one checked epilogue.

    Non-void values are stored by per-return trampolines and loaded by the
    common epilogue.  This preserves early-return values without referring to
    a value that does not dominate the shared block.
    """
    lines = body.splitlines()
    returns: dict[int, tuple[str, str]] = {}
    return_type: Optional[str] = None
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("ret"):
            continue
        parsed = _parse_return(line)
        if parsed is None:
            return None
        if return_type is None:
            return_type = parsed[0]
        elif parsed[0] != return_type:
            return None
        returns[index] = parsed
    if not returns or return_type is None:
        return None
    if return_type != "void" and not return_slot:
        return None

    rebuilt: list[str] = []
    for index, line in enumerate(lines):
        parsed = returns.get(index)
        if parsed is None:
            rebuilt.append(line)
            continue
        _type, value = parsed
        # Keep the original return block's label; an extra consecutive label
        # would create an empty basic block, which LLVM rejects.
        if return_type != "void":
            rebuilt.append(
                f"  store {return_type} {value}, ptr {return_slot}, align 8")
        rebuilt.append(f"  br label %{checked_label}")

    label_index = next(
        (index for index, line in enumerate(rebuilt)
         if _BLOCK_LABEL_RE.match(line.strip())), None)
    if label_index is None:
        return None
    prologue_lines = prologue.strip().splitlines()
    if return_type != "void":
        prologue_lines.insert(
            0, f"  {return_slot} = alloca {return_type}, align 8")
    rebuilt[label_index + 1:label_index + 1] = prologue_lines

    final_return = ""
    if return_type != "void":
        result = f"%{result_prefix}_retval_{suffix}"
        final_return = (
            f"  {result} = load {return_type}, ptr {return_slot}, align 8\n"
            f"  ret {return_type} {result}")
    rebuilt.append(f"{checked_label}:")
    rebuilt.extend(epilogue.strip().splitlines())
    if final_return:
        rebuilt.extend(final_return.splitlines())
    else:
        rebuilt.append("  ret void")
    return "\n".join(rebuilt) + "\n"


def _insert_before_terminator(text: str, body_start: int, snippet: str) -> str:
    """Insert ``snippet`` just before the function's final terminator.

    Appending the epilogue at end-of-file put instructions outside any
    function, and appending it before the closing brace put them after the
    existing ``ret``. Both are invalid IR. The epilogue's last block falls
    through into the original terminator instead.
    """
    start, end = _function_body_span(text, body_start)
    body = text[start:end]
    last_ret = None
    for m in re.finditer(r'^\s*ret\s+[^\n]*$', body, re.MULTILINE):
        last_ret = m
    if last_ret is None:
        return text[:end] + snippet + text[end:]
    cut = start + last_ret.start()
    return text[:cut] + snippet + text[cut:]


class PortEntanglementPass:
    """
    CPU port entanglement pass for anti-debug / anti-emulation.

    Injects RDTSC-based timing checks keyed to the target CPU's
    execution port configuration. Timing deltas are XOR'd with
    the port configuration as an opaque comparison.

    Design rationale: RDTSC is used instead of CLOCK_MONOTONIC
    because (a) it measures actual CPU cycles, not wall time,
    (b) it is accessible from user space on x86_64, and (c) it
    has low overhead.
    """

    def __init__(self, target_cpu: str = 'raptor_lake'):
        """
        Initialize with a target CPU model.

        Falls back to 'auto' configuration if the CPU is not
        in CPU_PORT_MAP.
        """
        target = target_cpu.lower()
        if target not in CPU_PORT_MAP:
            target = 'auto'
        self.target_cpu = target
        self.port_config = CPU_PORT_MAP[target]

    def apply_to_ir(self, ir_text: str) -> str:
        """Inject timing checks into every function in the module.

        Each function gets its own local-value suffix so the checks do not
        collide, and the two runtime helpers are declared once at module
        scope. The old pass patched only the first function and emitted calls
        to undeclared intrinsics.
        """
        result = ir_text
        if 'declare i64 @__rdtsc()' not in result:
            result = ('declare i64 @__rdtsc()\n'
                      'declare void @__corrupt_key()\n' + result)

        # Work backwards so earlier match offsets stay valid as text grows.
        for match in reversed(list(_FUNC_PATTERN.finditer(result))):
            suffix = _func_suffix(match.group(2))
            start, end = _function_body_span(result, match.end())
            routed = _route_function_returns(
                result[start:end],
                self.generate_timing_prologue(suffix),
                self.generate_timing_epilogue(suffix),
                suffix=suffix,
                result_prefix="port_entangle",
                return_slot=f"%port_entangle_ret_{suffix}",
                checked_label=f"port_entangle_check_{suffix}",
            )
            if routed is not None:
                result = result[:start] + routed + result[end:]
        return result

    def generate_timing_prologue(self, suffix: str = "") -> str:
        """
        Generate LLVM IR for the timing check prologue.

        Stores the total port count and individual port counts
        packed into a single i64 as the "seed" for the timing
        comparison. Reads RDTSC into t0.

        Security note: The port configuration is embedded as
        a constant in the IR but will be visible in the binary.
        It is XOR'd with the timing delta to make the comparison
        opaque to static analysis.
        """
        port_cfg = self.port_config
        # LLVM IR has no hex integer literals; the packed port counts have to
        # be emitted in decimal.
        packed_seed = _packed_seed(port_cfg)
        ir = f"""
; Port Entanglement Timing Prologue
; Target: {self.target_cpu}
; Port config: alu={port_cfg['alu_ports']} branch={port_cfg['branch_ports']} load={port_cfg['load_ports']} store={port_cfg['store_ports']}
%port_entangle_seed_{suffix} = alloca i64, align 8
store i64 {packed_seed}, ptr %port_entangle_seed_{suffix}
%port_entangle_t0_{suffix} = call i64 @__rdtsc()
"""
        return ir

    def generate_timing_epilogue(self, suffix: str = "") -> str:
        """
        Generate LLVM IR for the timing check epilogue.

        Reads RDTSC into t1 and compares the delta against an upper bound.
        Only an anomalously slow run (single-stepping or emulation) corrupts
        the key. The old check compared delta XOR seed against a magic number
        that normal runs almost never equal, so it corrupted on every call.

        The threshold is stored XOR'd with the port seed and recovered at
        runtime, keeping the comparison value out of the obvious constant.
        """
        port_cfg = self.port_config
        threshold = _anomaly_threshold(port_cfg)
        obfuscated_threshold = threshold ^ _packed_seed(port_cfg)
        ir = f"""
; Port Entanglement Timing Epilogue
%port_entangle_t1_{suffix} = call i64 @__rdtsc()
%port_entangle_delta_{suffix} = sub i64 %port_entangle_t1_{suffix}, %port_entangle_t0_{suffix}
%port_entangle_seed_val_{suffix} = load i64, ptr %port_entangle_seed_{suffix}
%port_entangle_threshold_{suffix} = xor i64 {obfuscated_threshold}, %port_entangle_seed_val_{suffix}
%port_entangle_key_corrupt_{suffix} = icmp uge i64 %port_entangle_delta_{suffix}, %port_entangle_threshold_{suffix}
br i1 %port_entangle_key_corrupt_{suffix}, label %port_entangle_corrupt_{suffix}, label %port_entangle_clean_{suffix}
port_entangle_corrupt_{suffix}:
  call void @__corrupt_key()
  br label %port_entangle_clean_{suffix}
port_entangle_clean_{suffix}:
"""
        return ir

    def embed_timing_check(self, ir_text: str, config: dict) -> str:
        """
        Embed an alternative timing check with configurable parameters.

        This is a second variant of the timing check that uses a
        threshold-based comparison rather than port-based matching.
        Configurable parameters:
        - timing_threshold: minimum expected cycle count.
        - timing_hard_exit: if True, routes through an exit block; otherwise
          routes through a soft corruption block. Both call __corrupt_key().

        The anomaly is a run that is *faster* than the configured floor
        (typical when instrumentation is stubbed out). The old soft mode
        tested delta XOR threshold != 0, which is true for nearly every
        delta and corrupted the key on every call.
        """
        threshold = config.get('timing_threshold', 0)
        if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 0:
            raise ValueError("timing_threshold must be a non-negative integer")
        hard_exit = bool(config.get('timing_hard_exit', False))

        result = ir_text
        if not result.strip():
            return result

        rdtsc_decl = """declare i64 @__rdtsc()
declare void @__corrupt_key()
"""
        if 'declare i64 @__rdtsc()' not in result:
            result = rdtsc_decl + '\n' + result

        for match in reversed(list(_FUNC_PATTERN.finditer(result))):
            suffix = _func_suffix(match.group(2))
            prologue = f"""
; Port entangle timing check prologue
%pe_seed_{suffix} = alloca i64, align 8
store i64 {threshold}, ptr %pe_seed_{suffix}
%pe_t0_{suffix} = call i64 @__rdtsc()
"""
            epilogue = f"""
; Port entangle timing check epilogue
%pe_t1_{suffix} = call i64 @__rdtsc()
%pe_delta_{suffix} = sub i64 %pe_t1_{suffix}, %pe_t0_{suffix}
%pe_threshold_val_{suffix} = load i64, ptr %pe_seed_{suffix}
%pe_too_fast_{suffix} = icmp ult i64 %pe_delta_{suffix}, %pe_threshold_val_{suffix}
""" + (f"""br i1 %pe_too_fast_{suffix}, label %pe_exit_{suffix}, label %pe_checked_{suffix}
pe_exit_{suffix}:
  call void @__corrupt_key()
  br label %pe_checked_{suffix}
pe_checked_{suffix}:
""" if hard_exit else f"""br i1 %pe_too_fast_{suffix}, label %pe_slow_{suffix}, label %pe_checked_{suffix}
pe_slow_{suffix}:
  call void @__corrupt_key()
  br label %pe_checked_{suffix}
pe_checked_{suffix}:
""")
            start, end = _function_body_span(result, match.end())
            routed = _route_function_returns(
                result[start:end], prologue, epilogue,
                suffix=suffix,
                result_prefix="pe",
                return_slot=f"%pe_ret_{suffix}",
                checked_label=f"pe_check_{suffix}",
            )
            if routed is not None:
                result = result[:start] + routed + result[end:]
        return result
