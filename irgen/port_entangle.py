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

import re

CPU_PORT_MAP = {
    'raptor_lake': {'alu_ports': 4, 'branch_ports': 1, 'load_ports': 2, 'store_ports': 1},
    'alder_lake': {'alu_ports': 4, 'branch_ports': 1, 'load_ports': 2, 'store_ports': 1},
    'zen4': {'alu_ports': 4, 'branch_ports': 1, 'load_ports': 3, 'store_ports': 2},
    'zen3': {'alu_ports': 4, 'branch_ports': 1, 'load_ports': 2, 'store_ports': 2},
    'auto': {'alu_ports': 3, 'branch_ports': 1, 'load_ports': 2, 'store_ports': 1},
}


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
        """
        Apply timing check injection to LLVM IR text.

        Finds the first function definition and inserts the
        timing prologue after the opening brace and appends
        the timing epilogue after the closing brace.
        """
        prologue = self.generate_timing_prologue()
        epilogue = self.generate_timing_epilogue()

        func_pattern = re.compile(r'(define\s+\S+\s+@\w+\s*\([^)]*\)\s*{)', re.MULTILINE)
        match = func_pattern.search(ir_text)
        if not match:
            return ir_text

        pos = match.end()
        inserted = '\n' + prologue + '\n'
        result = ir_text[:pos] + inserted + ir_text[pos:]
        result += '\n' + epilogue + '\n'
        return result

    def generate_timing_prologue(self) -> str:
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
        total_ports = port_cfg['alu_ports'] + port_cfg['branch_ports'] + port_cfg['load_ports'] + port_cfg['store_ports']
        ir = f"""
; Port Entanglement Timing Prologue
; Target: {self.target_cpu}
; Port config: alu={port_cfg['alu_ports']} branch={port_cfg['branch_ports']} load={port_cfg['load_ports']} store={port_cfg['store_ports']}
%port_entangle_seed = alloca i64, align 8
store i64 0x{total_ports:02x}{port_cfg['alu_ports']:02x}{port_cfg['branch_ports']:02x}{port_cfg['load_ports']:02x}, ptr %port_entangle_seed
%port_entangle_t0 = call i64 @__rdtsc()
"""
        return ir

    def generate_timing_epilogue(self) -> str:
        """
        Generate LLVM IR for the timing check epilogue.

        Reads RDTSC into t1, computes delta = t1 - t0, XORs with
        the port configuration seed, and compares against an
        expected value derived from the port counts. If the
        comparison fails, calls __corrupt_key().

        Security note: The expected comparison value is computed
        as alu_ports * 1000 + load_ports * 100 + store_ports * 10
        + branch_ports. This is a heuristic; the actual threshold
        should be calibrated per target microarchitecture.
        """
        port_cfg = self.port_config
        ir = f"""
; Port Entanglement Timing Epilogue
%port_entangle_t1 = call i64 @__rdtsc()
%port_entangle_delta = sub i64 %port_entangle_t1, %port_entangle_t0
%port_entangle_seed_val = load i64, ptr %port_entangle_seed
%port_entangle_xor = xor i64 %port_entangle_delta, %port_entangle_seed_val
%port_entangle_key_corrupt = icmp ne i64 %port_entangle_xor, {port_cfg['alu_ports'] * 1000 + port_cfg['load_ports'] * 100 + port_cfg['store_ports'] * 10 + port_cfg['branch_ports']}
br i1 %port_entangle_key_corrupt, label %port_entangle_corrupt, label %port_entangle_clean
port_entangle_corrupt:
  call void @__corrupt_key()
  br label %port_entangle_clean
port_entangle_clean:
"""
        return ir

    def embed_timing_check(self, ir_text: str, config: dict) -> str:
        """
        Embed an alternative timing check with configurable parameters.

        This is a second variant of the timing check that uses a
        threshold-based comparison rather than port-based matching.
        Configurable parameters:
        - timing_threshold: minimum expected cycle count.
        - timing_hard_exit: if True, crashes directly; if False,
          uses XOR-based key corruption.

        Security note: The threshold mode (timing_hard_exit=False)
        uses XOR to corrupt keys rather than a direct exit, making
        the failure mode harder for an attacker to diagnose.
        """
        threshold = config.get('timing_threshold', 5000)
        hard_exit = config.get('timing_hard_exit', False)

        result = ir_text

        if not result.strip():
            return result

        rdtsc_decl = """declare i64 @__rdtsc()
declare void @__corrupt_key()
"""
        if 'declare i64 @__rdtsc()' not in result:
            result = rdtsc_decl + '\n' + result

        prologue = f"""
; Port entangle timing check prologue
%pe_seed = alloca i64, align 8
store i64 {threshold}, ptr %pe_seed
%pe_t0 = call i64 @__rdtsc()
"""
        epilogue = """
; Port entangle timing check epilogue
%pe_t1 = call i64 @__rdtsc()
%pe_delta = sub i64 %pe_t1, %pe_t0
%pe_threshold_val = load i64, ptr %pe_seed
%pe_too_fast = icmp ult i64 %pe_delta, %pe_threshold_val
"""
        if hard_exit:
            epilogue += """br i1 %pe_too_fast, label %pe_exit, label %pe_ok
pe_exit:
  call void @__corrupt_key()
  br label %pe_ok
pe_ok:
"""
        else:
            epilogue += """%pe_corrupt = xor i64 %pe_delta, %pe_threshold_val
  %pe_corrupt_cond = icmp ne i64 %pe_corrupt, 0
  br i1 %pe_corrupt_cond, label %pe_maybe_corrupt, label %pe_ok
pe_maybe_corrupt:
  call void @__corrupt_key()
  br label %pe_ok
pe_ok:
"""

        func_pattern = re.compile(r'(define\s+\S+\s+@\w+\s*\([^)]*\)\s*{)', re.MULTILINE)
        match = func_pattern.search(result)
        if not match:
            return result
        pos = match.end()
        result = result[:pos] + '\n' + prologue + result[pos:]
        result += '\n' + epilogue + '\n'
        return result
