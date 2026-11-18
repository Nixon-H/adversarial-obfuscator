import sys, os, zipfile, base64, io, shutil, tempfile, random, hashlib, lzma, struct, time, json, argparse, uuid, re, platform, subprocess, hmac, secrets, ctypes, importlib.util, warnings, string, multiprocessing, socket, threading, concurrent.futures  # noqa: F401 (this line binds a name used by an embedded template)
# Do NOT raise the recursion limit at import.
#
# This line used to be `sys.setrecursionlimit(10000)`, set as a side effect of
# importing a library. On Windows a thread's native stack is 1 MB (Linux and
# macOS give 8 MB), so a limit that the interpreter accepts on those platforms
# overflows the real stack there -- and a native stack overflow is an
# ACCESS_VIOLATION (0xC0000005) that kills the process before Python can raise
# RecursionError or print anything. That is exactly the crash observed on
# windows-latest / CPython 3.14 importing obfuscator.core, at a point where no
# Python-level work was happening.
#
# Code that genuinely needs deeper recursion should raise the limit around the
# operation that needs it, not for every importer of this module.
sys.stderr.flush()
warnings.filterwarnings("ignore")

#: Recursion depth the transform needs. Kept here, applied only around the work
#: that needs it -- never as an import side effect (see the comment above):
#: on Windows the native stack is 1 MB, so a global high limit turns deep
#: recursion into an ACCESS_VIOLATION that no except clause can catch.
DEEP_RECURSION_LIMIT = 10000


class deep_recursion:
    """Raise the recursion limit for the duration of a deep operation."""

    def __init__(self, limit=DEEP_RECURSION_LIMIT):
        self.limit = limit
        self.previous = None

    def __enter__(self):
        self.previous = sys.getrecursionlimit()
        if self.limit > self.previous:
            sys.setrecursionlimit(self.limit)
        return self

    def __exit__(self, *exc_info):
        try:
            sys.setrecursionlimit(self.previous)
        except Exception:
            pass
        return False


_console = sys.stdout

#: Default file for the build log when logging is redirected.
DEFAULT_LOG_FILE = "build.log"

#: True when the environment asked for the console-to-file redirect.
#: The redirect itself is NOT performed at import time: importing a
#: module must not create or truncate a file in the current working
#: directory.  Entry points call :func:`enable_log_redirect` explicitly.
_LOG_REDIRECT_REQUESTED = os.environ.get('NIXON_LOG_REDIRECT', '1') == '1'

def enable_log_redirect(path=None):
    """Send stdout/stderr to a log file, and return the log path.

    This is the explicit replacement for the import-time side effect
    that used to open ``./build.log`` (mode ``"w"``) as soon as
    ``obfuscator.core.utils`` was imported.  That truncated any
    ``build.log`` in the current working directory — including a file
    that had nothing to do with this project — and it did so merely
    because something imported the module.

    Call it from an entry point that wants a log file.  Returns the log
    path, or ``None`` when the redirect was not requested
    (``NIXON_LOG_REDIRECT=0``) or could not be set up.
    """
    global _console, _log_fd
    if not _LOG_REDIRECT_REQUESTED:
        return None
    target = os.path.abspath(path or DEFAULT_LOG_FILE)
    try:
        _log_fd = open(target, "w", encoding='utf-8')
        try:
            os.chmod(target, 0o600)
        except Exception:
            pass
        _console_fd = os.dup(1)
        os.dup2(_log_fd.fileno(), 1)
        os.dup2(_log_fd.fileno(), 2)
        _console = open(_console_fd, "w", encoding='utf-8')
    except Exception as _e:
        import sys as _sys
        print(f"[utils] Failed to redirect log: {_e}", file=_sys.__stderr__)
        return None
    try:
        _print_banner()
    except Exception:
        pass
    return target
class UI:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    BLUE = "\033[34m"; CYAN = "\033[36m"; GREEN = "\033[32m"
    YELLOW = "\033[33m"; RED = "\033[31m"; MAGENTA = "\033[35m"
    current_task = None
    @staticmethod
    def _out(*args, **kwargs):
        try:
            end = kwargs.get("end", "\n")
            msg = " ".join(map(str, args))
            _console.write(msg + end)
            _console.flush()
        except Exception as _e:
            import sys as _sys
            _sys.stderr.write(f"[UI._out] {_e}\n")
    @staticmethod
    def _get_width():
        try: return shutil.get_terminal_size().columns
        except Exception as _e:
            import sys as _sys
            _sys.stderr.write(f"[UI._get_width] {_e}\n")
            return 80
    @staticmethod
    def _fit(msg, max_len):
        if len(msg) <= max_len: return msg
        if max_len < 3: return "..."[:max_len]
        return msg[:max_len-3] + "..."
    @staticmethod
    def update_status(msg):
        width = UI._get_width()
        if msg.strip().startswith("Start:"):
            # Truncate to avoid wrap artifact but maximize space
            clean_msg = msg[:width-1]
        else:
            max_len = max(10, width - 5)
            clean_msg = UI._fit(msg, max_len)
        if UI.current_task:
            UI.current_task.update(value=f"{UI.current_task.original_value} ({clean_msg})")
        else:
            try:
                _console.write(f"\r\033[K {UI.BLUE}│{UI.RESET}   {UI.DIM}↳ {clean_msg}{UI.RESET}")
                _console.flush()
            except Exception: pass
    @staticmethod
    def prompt(msg):
        try:
            _console.write(f"\n {UI.YELLOW} [?] {msg}{UI.RESET}")
            _console.flush()
            val = sys.stdin.readline()
            return val.strip() if val else ""
        except Exception: return ""
    @staticmethod
    def banner():
        logo = [
            r"┌──────────────────────────────────────────────────────────────┐",
            r"│  ███╗   ██╗██╗██╗  ██╗ ██████╗ ███╗   ██╗   ██████╗██████╗   │",
            r"│  ████╗  ██║██║╚██╗██╔╝██╔═══██╗████╗  ██║  ██╔════╝██╔══██╗  │",
            r"│  ██╔██╗ ██║██║ ╚███╔╝ ██║   ██║██╔██╗ ██║  ██║     ██████╔╝  │",
            r"│  ██║╚██╗██║██║ ██╔██╗ ██║   ██║██║╚██╗██║  ██║     ██╔══██╗  │",
            r"│  ██║ ╚████║██║██╔╝ ██╗╚██████╔╝██║ ╚████║  ╚██████╗██║  ██║  │",
            r"│  ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═════╝╚═╝  ╚═╝  │",
            r"│                                                              │",
            r"│  [ v2.0 ]  >> ADVANCED PYTHON OBFUSCATION SYSTEM <<          │",
            r"│  ──────────────────────────────────────────────────────────  │",
            r"│  Target  : Universal Multi-Arch (Win/Lin/Mac/Android)        │",
            r"│  Profile : Maximum Protection (Phased VM + Cloud Auth)       │",
            r"└──────────────────────────────────────────────────────────────┘"
        ]
        print(f"{UI.CYAN}{UI.BOLD}")
        for line in logo:
            print(line)
        print(f"{UI.RESET}")
    @staticmethod
    def section(title):
        UI._out(f"\n {UI.BLUE}╭── [ {UI.BOLD}{title}{UI.RESET}{UI.BLUE} ]{UI.RESET}")
        UI._out(f" {UI.BLUE}│{UI.RESET}")
    @staticmethod
    def item(key, value, status=None):
        status_str = ""
        if status == "OK" or status == "ACTIVE" or status == "PASS": status_str = f"[{UI.GREEN}✓{UI.RESET}]"
        elif status == "FAIL": status_str = f"[{UI.RED}✗{UI.RESET}]"
        elif status: status_str = f"[{UI.CYAN}{status}{UI.RESET}]"
        key_padded = f"{key:<18}"
        UI._out(f" {UI.BLUE}├──{UI.RESET} {key_padded}: {UI.BOLD}{value}{UI.RESET} {status_str}")
    @staticmethod
    def check_tools(tools_dict):
        UI._out(f" {UI.BLUE}└──{UI.RESET} Dependencies      : ", end="")
        for tool, available in tools_dict.items():
            mark = f"{UI.GREEN}[✓]{UI.RESET}" if available else f"{UI.RED}[✗]{UI.RESET}"
            try: _console.write(f"{tool.upper()} {mark}  "); _console.flush()
            except Exception: pass
        UI._out("")
    @staticmethod
    def dot_item(key, value, status="OK"):
        status_str = ""
        if status in ["OK", "SUCCESS", "PASS", "SCORCHED"]: status_str = f"[{UI.GREEN}✓{UI.RESET}]"
        elif status in ["FAIL", "ERROR"]: status_str = f"[{UI.RED}✗{UI.RESET}]"
        else: status_str = f"[{UI.CYAN}{status}{UI.RESET}]"
        term_width = UI._get_width()
        overhead = 9 
        status_clean = re.sub(r'\033\[[0-9;]*m', '', status_str)
        key_width = 18
        available_for_content = max(10, term_width - len(status_clean) - overhead - 2)
        val_width = available_for_content - key_width
        key_str = UI._fit(str(key), key_width)
        val_str = UI._fit(str(value), val_width)
        val_clean = re.sub(r'\033\[[0-9;]*m', '', val_str)
        overhead_real = 9
        used_width = overhead_real + key_width + len(val_clean) + len(status_clean)
        dots_needed = max(2, term_width - used_width)
        dots = " " * dots_needed
        key_padded = f"{key_str:<{key_width}}"
        UI._out(f" {UI.BLUE}├──{UI.RESET} {key_padded}: {UI.BOLD}{val_str}{UI.RESET} {UI.DIM}{dots}{UI.RESET} {status_str}")
    @staticmethod
    def print_table(headers, rows):
        col_widths = [len(h) + 2 for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths): col_widths[i] = max(col_widths[i], len(str(cell)) + 2)
        UI._out(f" {UI.BLUE}┌" + "┬".join(["─" * w for w in col_widths]) + f"┐{UI.RESET}")
        header_str = "│".join([f" {h.ljust(w-1)}" for h, w in zip(headers, col_widths)])
        UI._out(f" {UI.BLUE}│{UI.RESET}" + header_str + f"{UI.BLUE}│{UI.RESET}")
        UI._out(f" {UI.BLUE}├" + "┼".join(["─" * w for w in col_widths]) + f"┤{UI.RESET}")
        for row in rows:
            row_str = ""
            for i, cell in enumerate(row):
                if i >= len(col_widths): continue
                color = UI.RESET
                if "PASS" in str(cell) or "Match" in str(cell): color = UI.GREEN
                elif "FAIL" in str(cell) or "Mismatch" in str(cell): color = UI.RED
                content = str(cell).ljust(col_widths[i]-1)
                row_str += f" {color}{content}{UI.RESET}{UI.BLUE}│{UI.RESET}"
            UI._out(f" {UI.BLUE}│{UI.RESET}" + row_str)
        UI._out(f" {UI.BLUE}└" + "┴".join(["─" * w for w in col_widths]) + f"┘{UI.RESET}")
    @staticmethod
    def fail(msg):
        UI._out(f" {UI.BLUE}│{UI.RESET}   {UI.RED}↳ [ERROR] {msg}{UI.RESET}")
    @staticmethod
    def warn(msg):
        UI._out(f" {UI.BLUE}│{UI.RESET}   {UI.YELLOW}↳ [WARN] {msg}{UI.RESET}")
    class Task:
        def __init__(self, key, value, init_status="PENDING", prefix="├──"):
            self.key = key
            self.value = value
            self.original_value = value
            self.status = init_status
            self.prefix = prefix
            self.start_time = time.time()
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._tick)
            self._thread.daemon = True
            self._thread.start()
            self._print()
        def _print(self, end=""):
            clear_line = "\033[K"
            connector_color = UI.BLUE
            status_str = ""
            if self.status == "PENDING":
                connector_color = UI.YELLOW
                status_str = f"[{UI.YELLOW}⚡{UI.RESET}]"
            elif self.status in ["OK", "ACTIVE", "PASS", "SUCCESS"]: 
                connector_color = UI.GREEN
                status_str = f"[{UI.GREEN}✓{UI.RESET}]"
            elif self.status in ["FAIL", "ERROR", "FAILED"]: 
                connector_color = UI.RED
                status_str = f"[{UI.RED}✗{UI.RESET}]"
            elif self.status: 
                status_str = f"[{UI.CYAN}{self.status}{UI.RESET}]"
            else:
                status_str = f"[{UI.YELLOW}..{UI.RESET}]"
            term_width = UI._get_width()
            status_clean = re.sub(r'\033\[[0-9;]*m', '', status_str)
            overhead = 10 
            available_for_content = max(10, term_width - len(status_clean) - overhead - 2)
            key_width = 18 
            val_width = available_for_content - key_width
            key_str = UI._fit(self.key, key_width)
            current_duration = time.time() - self.start_time
            if self.status == "PENDING" and not self._stop_event.is_set():
                 val_str = f"{UI._fit(str(self.value), val_width)} ({current_duration:.1f}s)"
            else:
                 val_str = UI._fit(str(self.value), val_width)
            val_clean = re.sub(r'\033\[[0-9;]*m', '', val_str)
            status_clean = re.sub(r'\033\[[0-9;]*m', '', status_str)
            
            prefix_clean = re.sub(r'\033\[[0-9;]*m', '', self.prefix)
            overhead = 6 + len(prefix_clean)
            
            used_width = overhead + key_width + len(val_clean) + len(status_clean)
            dots_needed = max(2, term_width - used_width)
            dots = " " * dots_needed
            key_padded = f"{key_str:<{key_width}}"
            msg = f"\r{clear_line} {connector_color}{self.prefix}{UI.RESET} {key_padded}: {UI.BOLD}{val_str}{UI.RESET} {UI.DIM}{dots}{UI.RESET} {status_str}"
            UI._out(msg, end=end)
        def _tick(self):
            while self._stop_event and not self._stop_event.is_set():
                self._print()
                time.sleep(0.1)
        def update(self, value=None, status=None):
            if value: self.value = value
            if status: self.status = status
        def success(self, value=None):
            self._stop()
            duration = time.time() - self.start_time
            if value: self.value = f"{value} ({duration:.2f}s)"
            elif self.original_value: self.value = f"{self.original_value} ({duration:.2f}s)"
            else: self.value = f"{self.value} ({duration:.2f}s)"
            self.status = "SUCCESS"
            self._print(end="\n")
        def fail(self, msg=None):
            self._stop()
            duration = time.time() - self.start_time
            if msg: self.value = f"{self.value} ({msg}) ({duration:.2f}s)"
            else: self.value = f"{self.value} ({duration:.2f}s)"
            self.status = "FAIL"
            self._print(end="\n")
        def _stop(self):
            if self._stop_event: self._stop_event.set()
            if self._thread: self._thread.join(timeout=2.0)
            self._stop_event = None
            self._thread = None
        def __enter__(self): 
            UI.current_task = self
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            self._stop()
            UI.current_task = None
            if exc_type: self.fail(str(exc_val))
            elif self.status == "PENDING": self.success()
    @staticmethod
    def fatal(msg):
        UI._out(f"\n {UI.RED}[FATAL ERROR] {msg}{UI.RESET}")
        sys.exit(1)
def check_dependencies():
    import shutil
    UI.banner()
    UI.section("SYSTEM CHECK")
    results = {"python_ok": False, "tools": {}}
    py_ver = sys.version_info
    ver_str = f"{py_ver.major}.{py_ver.minor}.{py_ver.micro} ({sys.platform})"
    if py_ver.major >= 3 and py_ver.minor >= 8:
        results["python_ok"] = True
        UI.item("Python Version", ver_str, "OK")
    else:
        UI.item("Python Version", ver_str, "FAIL")
        UI.fail("Python 3.8+ recommended")
    tools_to_check = ["strip", "llvm-strip", "upx", "docker", "nuitka"]
    for tool in tools_to_check:
        results["tools"][tool] = shutil.which(tool) is not None
    UI.check_tools(results["tools"])
    if not results["tools"]["llvm-strip"] and not results["tools"]["strip"]:
        UI.fail("No strip tool found. Binary size will be larger.")
    if not results["tools"]["upx"]:
        UI.fail("UPX not found. Compression disabled.")
    return results

def fast_xor_bytes(data, key):
    key = bytes(key)
    k_len = len(key)
    return bytes([b ^ key[i % k_len] for i, b in enumerate(data)])

def get_random_var_name(prefix="NX"):
    babel_ranges = [
        (0x0100, 0x017F), 
        (0x0180, 0x024F), 
        (0x0250, 0x02AF), 
        (0x0370, 0x03FF), 
        (0x0400, 0x04FF), 
        (0x0530, 0x058F), 
        (0x05D0, 0x05EA), 
        (0x0600, 0x06FF), 
        (0x0900, 0x097F), 
        (0x0980, 0x09FF), 
        (0x0E00, 0x0E7F), 
        (0x10A0, 0x10FF), 
        (0x13A0, 0x13F4), 
        (0x16A0, 0x16EA), 
        (0x3040, 0x309F), 
        (0x4E00, 0x9FFF), 
    ]
    suffix = ""
    for _ in range(random.randint(5, 10)):
        found = False
        for _ in range(20):
            r_start, r_end = random.choice(babel_ranges)
            char_code = random.randint(r_start, r_end)
            char = chr(char_code)
            if ("_" + char).isidentifier() and char.isprintable():
                suffix += char
                found = True
                break
        if not found:
            suffix += random.choice(['A', 'B', 'C', 'X', 'Y', 'Z'])
    name = f"_nixon_{suffix}"
    # NFKC invariance is not cosmetic: Python normalises identifiers at
    # compile time, so `def <name>` binds the NFKC-normalised key while a
    # runtime `globals().get("<raw name>")` looks up the raw string.  A
    # non-invariant name (17% of the old draw: combining sequences such as
    # Bengali ঁ or Devanagari ़) made the kill ladder's server alert look
    # up a key that does not exist -- the webhook silently missed every
    # strict-kill in those builds, and the snippet test flaked the same
    # way.  Redraw until raw == normalised.
    import unicodedata as _unicodedata
    for _ in range(50):
        if _unicodedata.normalize("NFKC", name) == name:
            return name
        suffix = ""
        for _ in range(random.randint(5, 10)):
            found = False
            for _ in range(20):
                r_start, r_end = random.choice(babel_ranges)
                char = chr(random.randint(r_start, r_end))
                if ("_" + char).isidentifier() and char.isprintable():
                    suffix += char
                    found = True
                    break
            if not found:
                suffix += random.choice(['A', 'B', 'C', 'X', 'Y', 'Z'])
        name = f"_nixon_{suffix}"
    # The ASCII fallback is always invariant.
    return "_nixon_" + "".join(random.choices('ABCDEFGHJKMNPQRSTUVWXYZ', k=8))
FUNC_NEXT_H = get_random_var_name("NEXT_H")
FUNC_REM_ENT = get_random_var_name("REM_ENT")
FUNC_SEC_WIPE = get_random_var_name("SEC_WIPE")
FUNC_PROT_EXEC = get_random_var_name("PROT_EXEC")
FUNC_GC_SHIELD = get_random_var_name("GC_SHIELD")
FUNC_GC_RESTORE = get_random_var_name("GC_RESTOR")
FUNC_HIDE_OBJ = get_random_var_name("HIDE_OBJ")
FUNC_FAKE_ENC = get_random_var_name("FAKE_ENC")
FUNC_FAKE_DEC = get_random_var_name("FAKE_DEC")
FUNC_DECOY_XFORM = get_random_var_name("DECOY_T")
FUNC_PIPE_WRAP = get_random_var_name("PIPE_WRAP")
FUNC_STACK_XOR = get_random_var_name("STACK_XOR")
FUNC_STATE_INIT = get_random_var_name("ST_INIT")
FUNC_STATE_STG0 = get_random_var_name("ST_STG0")
FUNC_STATE_REC = get_random_var_name("ST_REC")
FUNC_STATE_ON1 = get_random_var_name("ST_ON1")
FUNC_STATE_ZIP1 = get_random_var_name("ST_ZIP1")
FUNC_STATE_ON2 = get_random_var_name("ST_ON2")
FUNC_STATE_DEC1 = get_random_var_name("ST_DEC1")
FUNC_STATE_VM = get_random_var_name("ST_VM")
FUNC_STATE_PAD = get_random_var_name("ST_PAD")
FUNC_STATE_LOAD = get_random_var_name("ST_LOAD")
FUNC_STATE_EXEC = get_random_var_name("ST_EXEC")
def _print_banner():
    try:
        cols = shutil.get_terminal_size().columns
    except Exception:
        cols = 80
    if cols >= 82:
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ███╗   ██╗██╗██╗  ██╗ ██████╗ ███╗   ██╗     ██████╗██████╗ ██╗   ██╗     ║
║    ████╗  ██║██║╚██╗██╔╝██╔═══██╗████╗  ██║    ██╔════╝██╔══██╗╚██╗ ██╔╝     ║
║    ██╔██╗ ██║██║ ╚███╔╝ ██║   ██║██╔██╗ ██║    ██║     ██████╔╝ ╚████╔╝      ║
║    ██║╚██╗██║██║ ██╔██╗ ██║   ██║██║╚██╗██║    ██║     ██╔══██╗  ╚██╔╝       ║
║    ██║ ╚████║██║██╔╝ ██╗╚██████╔╝██║ ╚████║    ╚██████╗██║  ██║   ██║        ║
║    ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝     ╚═════╝╚═╝  ╚═╝   ╚═╝        ║
║                                                                              ║
║                 ░▒▓█  ADVANCED PYTHON OBFUSCATOR  █▓▒░                       ║
║                 ════════════════════════════════════════                     ║
║             >> LAYER ENCRYPTION  >> VM PROTECTION  >> ANTI-DEBUG             ║
║             >> CODE MUTATION     >> AST TRANSFORM  >> SECURE PACK            ║
║                                                                              ║
║           [====================================================]             ║
║                        PROTECTION LEVEL: MAXIMUM                             ║
║           [====================================================]             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    else:
        banner = """
┌───────────────────────────────────┐
│ ░█▄░█ █ ▀▄▀ █▀█ █▄░█  █▀▀ █▀█ █▄█ │
│ ░█░▀█ █ █░█ █▄█ █░▀█  █▄▄ █▀▄ ░█░ │
├───────────────────────────────────┤
│    ADVANCED PYTHON OBFUSCATOR     │
├───────────────────────────────────┤
│  ▸ LAYER ENCRYPTION               │
│  ▸ VM PROTECTION                  │
│  ▸ ANTI-DEBUG                     │
│  ▸ CODE MUTATION                  │
│  ▸ AST TRANSFORM                  │
│  ▸ SECURE PACK                    │
├───────────────────────────────────┤
│     PROTECTION: ████████ MAX      │
└───────────────────────────────────┘
"""
    print(banner)
def _probe_numpy():
    """Is numpy importable *and* working?

    This used to be a bare `import numpy` at module scope. On Windows with
    CPython 3.14 numpy crashes the interpreter natively (ACCESS_VIOLATION,
    0xC0000005) while importing `numpy._core.printoptions`, and a native crash
    is not an ImportError, so the `except ImportError` guard did not run and
    merely importing `obfuscator.core` killed the process.

    The probe is a capability test, not a requirement: numpy is not used by this
    module. So it runs here, catches everything an import can raise, and callers
    that would have used numpy simply take their fallback path.
    """
    import subprocess as _sp
    try:
        # In a SUBPROCESS: on Windows + CPython 3.14 numpy dies with an
        # ACCESS_VIOLATION while importing, and no except clause can catch a
        # native crash -- it takes the interpreter with it. A child process can
        # die without harming the builder.
        r = _sp.run([sys.executable, "-c", "import numpy"],
                    stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, timeout=60)
        return r.returncode == 0
    except Exception:
        return False


#: Kept as a module attribute for compatibility with callers that read it.
#: Probed lazily rather than at import: see _probe_numpy.
HAS_NUMPY = _probe_numpy()
STRING_SESSION_KEY = secrets.token_bytes(32)
def _next_h_impl(current, step):
    return int.from_bytes(hashlib.sha256(str(current).encode() + str(step).encode()).digest()[:8], 'little')
globals()[FUNC_NEXT_H] = _next_h_impl
next_h = _next_h_impl
# Loader-embedded definition of the FUNC_NEXT_H chaining hash. The
# loader template calls {FUNC_NEXT_H}(h, step) ~15 times but never
# defined it (this slot was None, emitting a literal "None" line).
# Brace-free so apply_vars/.format pass it through untouched.
NEXT_H_SOURCE = (
    "def " + FUNC_NEXT_H + "(current, step):\n"
    "    import hashlib as _nx_hh\n"
    "    return int.from_bytes(_nx_hh.sha256(str(current).encode() + str(step).encode()).digest()[:8], 'little')\n"
)
class ConfigManager:
    CONFIG_FILE=os.path.join(os.path.expanduser("~"),".nixon_builder_config.json")
    def __init__(self):self.config=self._load()
    def _load(self):
        if not os.path.exists(self.CONFIG_FILE):return {}
        try:
            with open(self.CONFIG_FILE,"r", encoding='utf-8')as f:return json.load(f)
        except Exception:return {}
    def save(self):
        # Owner-only. This file holds GitHub and Cloudflare tokens, and the wizard
        # tells the user they are "stored securely" -- 0644, the default, is not
        # that. Written then chmod'd so the window where it is world-readable does
        # not exist.
        _fd = os.open(self.CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(_fd, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            raise
        try:
            os.chmod(self.CONFIG_FILE, 0o600)   # in case the file already existed
        except OSError:
            pass
        print(f" [+] Configuration saved to {self.CONFIG_FILE}")
    def get(self,key,default=None):return self.config.get(key,default)
    def set(self,key,value):self.config[key]=value
    def run_wizard(self):
        print("\n[*] FIRST-TIME SETUP WIZARD")
        print("    This information will be stored securely in config.json")
        if not self.get("github_token"):
            UI._out("\n[?] GitHub Personal Access Token (Repo Scope)")
            UI._out("    Generate here: https://github.com/settings/tokens")
            token=UI.prompt("Token: ")
            if token:self.set("github_token",token)
        if not self.get("cf_token"):
            UI._out("\n[?] Cloudflare API Token (Workers/KV Scope)")
            token=UI.prompt("Token: ")
            if token:self.set("cf_token",token)
        if not self.get("cf_account"):
            UI._out("\n[?] Cloudflare Account ID")
            acc=UI.prompt("Account ID: ")
            if acc:self.set("cf_account",acc)
        self.save()
        print("\n[*] Setup Complete. You can now run builds automatically.")
#: Default Tor SOCKS proxy (``host:port``).  Overridable per-process via
#: the ``NIXON_TOR_PROXY`` env var (e.g. ``"127.0.0.1:9150"`` for Tor
#: Browser's default port).  Read at farm ``__init__`` time so tests can
#: monkeypatch ``os.environ`` without a reload.
DEFAULT_TOR_PROXY = "127.0.0.1:9050"


def resolve_tor_proxy(explicit=None):
    # type: (object) -> str
    """Return the Tor proxy endpoint as ``"host:port"``.

    Precedence: explicit ``tor_proxy`` argument > ``NIXON_TOR_PROXY``
    env var > :data:`DEFAULT_TOR_PROXY`.  Malformed values fall back to
    the default (never raise — proxy misconfig must not fail a build;
    ``requests`` will surface connectivity errors instead).
    """
    raw = explicit or os.environ.get("NIXON_TOR_PROXY") or DEFAULT_TOR_PROXY
    try:
        host, _, port = str(raw).strip().partition(":")
        port_i = int(port)
        if not host or not (1 <= port_i <= 65535):
            raise ValueError("bad tor proxy %r" % (raw,))
        return "%s:%d" % (host, port_i)
    except Exception:
        return DEFAULT_TOR_PROXY


def tor_proxies(explicit=None):
    # type: (object) -> dict
    """``requests``-style proxies dict for the resolved Tor endpoint."""
    ep = resolve_tor_proxy(explicit)
    url = "socks5h://%s" % (ep,)
    return {"http": url, "https": url}


def _github_retry_after(response, default=2.0):
    """Seconds to wait before retrying, honouring the rate-limit headers.

    GitHub signals a rate limit with ``Retry-After`` (seconds, or an
    HTTP-date) and/or ``X-RateLimit-Reset`` (a unix timestamp).  The old
    code ignored both and used a fixed sleep, so a 429 was retried far
    too early and the request was rate-limited again.

    Never raises: a missing or malformed header falls back to *default*.
    """
    if response is None:
        return default
    headers = getattr(response, "headers", None) or {}
    try:
        raw = headers.get("Retry-After") or headers.get("retry-after")
        if raw is not None:
            value = float(str(raw).strip())
            if value >= 0:
                return min(value, _GITHUB_MAX_BACKOFF)
    except (TypeError, ValueError):
        pass
    try:
        reset = headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")
        if reset is not None:
            import time as _time
            when = float(str(reset).strip())
            delta = when - _time.time()
            if delta > 0:
                return min(delta, _GITHUB_MAX_BACKOFF)
    except (TypeError, ValueError, OverflowError, OSError):
        pass
    return default


#: Per-request timeout for GitHub API calls that had none.
_GITHUB_REQUEST_TIMEOUT = 30

#: Upper bound on any single backoff wait.
_GITHUB_MAX_BACKOFF = 60.0

#: Overall deadline for waiting on a cloud build to finish.  Without it
#: a run that never completes left the CLI polling forever.
_GITHUB_WAIT_DEADLINE = 1800


def _github_backoff(attempt, response=None, base=2.0):
    """Sleep for the right amount before a retry.

    Honours ``Retry-After`` when the server sent one, otherwise uses
    capped exponential backoff.
    """
    import time as _time
    delay = _github_retry_after(response, default=base * (2 ** attempt))
    delay = min(max(delay, 0.0), _GITHUB_MAX_BACKOFF)
    if delay > 0:
        _time.sleep(delay)
    return delay


def _confined_member_path(base_dir, member_name):
    """The resolved destination of an archive member, or raise.

    A member named ``../x`` (or one behind a symlink) would otherwise
    write outside the extraction directory (ZipSlip / tar traversal).
    The check is on the RESOLVED destination, so neither a ``..``
    component nor a symlinked member can escape.

    Every archive this project extracts goes through here, so the
    build-farm paths and the tool-download path share one check rather
    than each growing its own.  The implementation lives in
    ``obfuscator/core/archive_safety.py`` so that the build scripts
    can use it without importing this module (which has import-time
    side effects).
    """
    from obfuscator.core.archive_safety import confined_member_path
    return confined_member_path(base_dir, member_name)


def _extract_zip_confined(zip_path, output_dir):
    """Extract *zip_path* into *output_dir*, refusing to escape it."""
    from obfuscator.core.archive_safety import extract_zip_confined
    return extract_zip_confined(zip_path, output_dir)


def _extract_tar_confined(tar_path, output_dir, mode="r:*"):
    """Extract *tar_path* into *output_dir*, refusing to escape it."""
    from obfuscator.core.archive_safety import extract_tar_confined
    return extract_tar_confined(tar_path, output_dir, mode)


def _artifact_sign_key(explicit_hex=None):
    """Resolve the farm artifact HMAC key (bytes) or ``None``.

    Precedence: explicit hex string > ``NIXON_ARTIFACT_KEY_HEX`` >
    ``NIXON_SIGN_KEY`` (see ``scripts/artifact_sign.resolve_key``,
    ADR-0005). Never raises: unconfigured/malformed means
    opportunistic-unsigned operation with an auditable log line.
    """
    try:
        if explicit_hex:
            _k = bytes.fromhex(str(explicit_hex).strip())
            if _k:
                return _k
    except (ValueError, TypeError, AttributeError):
        pass
    try:
        from scripts.artifact_sign import resolve_key as _resolve_artifact_key
        return _resolve_artifact_key()
    except Exception:
        return None


def _verify_download_zip(zip_path, artifact_name, sign_key):
    """Verify-before-extract gate for one downloaded farm zip.

    Returns True when extraction is allowed.  Raises ``ValueError`` when
    it is not: a signature mismatch, unreadable sidecars, or signature
    sidecars present with no key configured.  The no-sidecar cases are
    an auditable downgrade (a farm that holds no key stages unsigned
    binaries) and return True.

    The farm identity is pinned when one is configured: a sidecar
    minted by a *different* farm is a mismatch, not a pass.  That closes
    the "no per-farm identity" limit ADR-0005 recorded.

    An Ed25519 public key is enough to enforce the gate: the verifier
    holds no secret, so it cannot mint a sidecar it would later accept.
    """
    import logging as _logging
    _log = _logging.getLogger("scripts.artifact_sign")
    try:
        from scripts import artifact_sign as _as
        _names = _as.zip_sidecar_names(zip_path)
    except Exception as _e:
        raise ValueError(
            "could not read signature sidecars for %r: %s (refusing extract)"
            % (artifact_name, _e))
    _expected = {}
    _farm = os.environ.get("NIXON_FARM_ID", "").strip()
    if _farm:
        _expected["farm"] = _farm
    _pinned = _as.resolve_ed25519_public_keys()
    if sign_key is not None or _pinned:
        if _names:
            try:
                _n = _as.verify_zip_sidecars(zip_path, sign_key, _expected or None)
            except Exception as _e:
                try:
                    os.remove(zip_path)
                except OSError:
                    pass
                raise ValueError(
                    "artifact signature mismatch for %r: %s (refusing extract)"
                    % (artifact_name, _e))
            print("    [+] Signatures verified (%d) for: %s" % (_n, artifact_name))
            return True
        _log.info("ARTIFACT-AUTH: no signature sidecars for %r "
                  "(the farm holds no signing key).", artifact_name)
        return True
    if _names:
        _log.warning("ARTIFACT-AUTH: %d signature sidecar(s) present for %r "
                     "but no signing key configured (NIXON_ARTIFACT_KEY_HEX / "
                     "NIXON_SIGN_KEY / %s) — REFUSING extraction: an "
                     "unverified artifact with signature sidecars must not "
                     "be trusted. Set a key to enforce.", len(_names),
                     artifact_name, _as.ED25519_PUBLIC_KEY_ENV)
        print("    [!] ARTIFACT-AUTH: signatures present for %s but no key "
              "configured — extraction REFUSED (see log)." % artifact_name)
        raise ValueError(
            "artifact %r carries signature sidecars but no verification key "
            "is configured (refusing extract)" % (artifact_name,))
    _log.warning("ARTIFACT-AUTH: no signing key configured "
                 "(NIXON_ARTIFACT_KEY_HEX / NIXON_SIGN_KEY) and no "
                 "signatures present for %r — proceeding without "
                 "verification (auditable downgrade).", artifact_name)
    return True
#: Modules the farm driver imports at module scope. The runner only receives the
#: files uploaded to the farm repo, so EVERY name here must be uploaded before
#: the workflow is dispatched. This list exists because that coupling has
#: already failed silently once: the driver imported ``c_transform`` but the
#: legacy ``build-farm`` CLI path uploaded only the payload, so the runner died
#: on ``ImportError`` and the whole C-transform layer was skipped on those
#: builds. ``native_harden`` (added for §3 header verification) would have
#: failed the same way. ``farm_driver_dependencies`` resolves each one to a path
#: so the upload sites cannot forget.
FARM_DRIVER_MODULES = ("c_transform", "native_harden")


def _repo_root():
    """Repository root, from this file's location (``obfuscator/core/utils.py``)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))


def farm_driver_dependencies():
    """``[(remote_name, local_path), ...]`` the driver needs on the runner.

    Returned even when a file is missing so the caller can report which one,
    rather than silently uploading a smaller set (a partial upload is exactly
    the failure mode this function exists to prevent). Use
    :func:`missing_farm_dependencies` to check before dispatching.
    """
    root = _repo_root()
    found = []
    for name in FARM_DRIVER_MODULES:
        candidates = (os.path.join(root, "scripts", name + ".py"),
                      os.path.join(root, "obfuscator", name + ".py"))
        # Prefer the first candidate that EXISTS; fall back to the first
        # candidate only when none does, so the "missing" report names a path
        # the operator should have created rather than an artefact of ordering.
        chosen = next((p for p in candidates if os.path.exists(p)), candidates[0])
        found.append((name + ".py", chosen))
    return found


def missing_farm_dependencies():
    """Local paths the driver imports that do not exist (empty when complete)."""
    return [path for _remote, path in farm_driver_dependencies()
            if not os.path.exists(path)]


def render_farm_driver(payload_filename="payload.py"):
    """Return the driver text the farm workflow embeds, for inspection.

    `create_workflow` builds this as an f-string inside a method, which makes
    it awkward to read from a test (and `eval` on generated source is the wrong
    tool). This renders the same template through the class, so a test can
    compile it and assert the attestation fields are present before a real farm
    run -- the f-string context has already produced two syntax bugs, where
    literal braces were read as format specifiers.
    """
    farm = object.__new__(GitHubBuildFarm)
    farm.token = ""
    farm.tor_proxy = None
    farm.proxies = None
    farm.headers = {}
    farm.base_url = "https://api.github.com"
    farm.repo_name = "inspect"
    farm.username = "inspect"
    # create_workflow uploads as a side effect; the renderer only needs the
    # text, so swallow the network failure and read what it produced.
    try:
        farm.create_workflow(payload_filename)
    except Exception:
        pass
    return getattr(farm, "_nx_last_driver", "")


class GitHubBuildFarm:
    def __init__(self,token, use_tor=False, tor_proxy=None):
        self.token=token
        self.tor_proxy = resolve_tor_proxy(tor_proxy) if use_tor else None
        self.proxies=tor_proxies(tor_proxy) if use_tor else None
        self.headers={"Authorization":f"token {token}","Accept":"application/vnd.github.v3+json"}
        self.base_url="https://api.github.com"
        if use_tor:self.base_url=self._resolve_doh("api.github.com")
        self.repo_name="nixon-build-farm-native"
        self.username=self._get_username()
    def _resolve_doh(self,domain):
        try:
            url=f"https://8.8.8.8/resolve?name={domain}&type=A"
            import requests
            r=requests.get(url,timeout=10,proxies=self.proxies)
            data=r.json()
            if "Answer" in data:
                ip=data["Answer"][0]["data"]
                print(f" [*] [DoH] Resolved {domain} -> {ip}")
                self.headers["Host"]=domain
                return f"https://{ip}"
        except Exception as e:print(f" [!] DoH Resolution Failed: {e}")
        # Fallback: the plain hostname instead of a DoH-resolved address.
        # The TRAFFIC still goes through the configured proxy -- every
        # request carries self.proxies -- so the Tor transport is not
        # dropped; what is lost is the DoH resolution path itself.  Say
        # so, because "DoH failed" and "the request left over the direct
        # connection" are very different statements.
        if self.proxies:
            print(f" [!] DoH resolution failed: using {domain} directly "
                  f"(traffic still goes through the configured proxy)")
        else:
            print(f" [!] DoH resolution failed: using {domain} directly, "
                  f"with NO proxy -- this request will NOT go through Tor")
        return f"https://{domain}"
    def _get_username(self):
        # Resilient, like the removed Nuitka farm's version was: the username
        # only names the disposable build repo, so an auth failure here must
        # not sys.exit(1) before the actual farm calls have had their say --
        # the farm tests construct this class against a fully rate-limited
        # fake, and the real build fails loudly enough on its own.
        try:
            import requests
            r=requests.get(f"{self.base_url}/user",headers=self.headers,proxies=self.proxies,verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()['login']
        except Exception as e:
            print(f" [!] GitHub Auth Failed: {e}")
            return "unknown"
    def create_disposable_repo(self):
        print(f"\n [*] [Cloud] Ensuring private repo exists: {self.repo_name}...")
        import requests
        data={"name":self.repo_name,"private":True,"auto_init":True}
        r=requests.post(f"{self.base_url}/user/repos",headers=self.headers,json=data,proxies=self.proxies,verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
        if r.status_code==201 or r.status_code==422:                           
            return True
        print(f" [!] Repo creation failed: {r.text}")
        return False
    def delete_repo(self):
        """Delete the build repo. Returns True when it is gone (or absent).

        --public advertises "Nukes repo after build" and nothing implemented
        it: the flag was parsed and never read, so every cloud build left a
        repo holding the payload source behind.  That is a supply-chain
        finding, not a cosmetic one -- the source is the thing the protection
        exists to withhold, and the farm's copy survives after the artefact is
        downloaded.
        """
        import requests
        url = f"{self.base_url}/repos/{self.username}/{self.repo_name}"
        try:
            r = requests.delete(url, headers=self.headers,
                                proxies=self.proxies, verify=True,
                                timeout=_GITHUB_REQUEST_TIMEOUT)
        except Exception as exc:
            print(f" [!] Repo delete failed: {exc}")
            return False
        if r.status_code in (204, 404):
            print(f"    [+] Build repo deleted: {self.repo_name}")
            return True
        print(f" [!] Repo delete returned {r.status_code}: {r.text[:160]}")
        return False
    def upload_file(self,local_path,remote_name):
        import requests
        with open(local_path,"rb")as f:content=base64.b64encode(f.read()).decode()
        url=f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/{remote_name}"
        data={"message":f"Upload {remote_name}","content":content}
        # GitHub's contents API requires the CURRENT blob sha to UPDATE an
        # existing file; without it every re-upload returns
        # 422 "sha wasn't supplied".  The farm repo is auto_init=True and
        # reused across builds, so on the SECOND build every upload failed
        # and the farm silently degraded to bytecode (caught by the live
        # ABSOLUTE run, 2026-11-18).  Probe first; create (no sha) or update.
        try:
            _get = requests.get(url, headers=self.headers, proxies=self.proxies,
                                verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
            if getattr(_get, 'status_code', None) == 200:
                _sha = (_get.json() or {}).get('sha')
                if _sha:
                    data['sha'] = _sha
        except Exception:
            pass
        r=requests.put(url,headers=self.headers,json=data,proxies=self.proxies,verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
        # Rate-limit resilience: wait out the server's Retry-After and retry
        # once (ported from the removed Nuitka farm).
        if getattr(r, 'status_code', None) == 429:
            time.sleep(_github_retry_after(r))
            r=requests.put(url,headers=self.headers,json=data,proxies=self.proxies,verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
        try:
            r.raise_for_status()
        except Exception:
            print(f" [!] Upload failed: {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')}")
            return False
        # Artifact-authenticity (ADR-0005, opportunistic): operator-side
        # upload can access the env key, so attach a metadata-bound
        # <remote_name>.sig.json sidecar when configured. Best-effort —
        # never fails the upload. Absent key → logged + proceed unsigned.
        # An Ed25519 private key is preferred: a verifier holding only
        # the public key can check the artifact but cannot mint one.
        try:
            _skey = _artifact_sign_key()
            try:
                from scripts.artifact_sign import sign_artifact_auto as _sa, default_metadata as _dm
                import json as _json
                _sig = _sa(local_path, _skey, _dm(extra={"file": remote_name}))
                if _sig is None:
                    raise RuntimeError("no signing key")
                _scontent = base64.b64encode(_json.dumps(_sig, sort_keys=True).encode()).decode()
                _surl = f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/{remote_name}.sig.json"
                try:
                    _get = requests.get(_surl, headers=self.headers, proxies=self.proxies, verify=True, timeout=30)
                    _sdata = {"message": f"Upload {remote_name}.sig.json", "content": _scontent}
                    if _get.status_code == 200:
                        _sha = _get.json().get("sha")
                        if _sha: _sdata["sha"] = _sha
                    _sr = requests.put(_surl, headers=self.headers, json=_sdata, proxies=self.proxies, verify=True, timeout=60)
                    if _sr.status_code in [200, 201]:
                        print(f"    [+] Signature sidecar uploaded: {remote_name}.sig.json")
                    else:
                        print(f"    [!] Sidecar upload skipped ({_sr.status_code}, non-fatal)")
                except Exception as _se:
                    print(f"    [!] Sidecar upload skipped (non-fatal): {_se}")
            except Exception as _se:
                print(f"    [!] Sidecar signing skipped (non-fatal): {_se}")
        except Exception as _se:
            print(f"    [!] Sidecar step skipped (non-fatal): {_se}")
        return True
    def create_workflow(self, payload_filename):
        import re as _re
        import os as _os
        payload_filename = _os.path.basename(payload_filename or "")
        if not _re.match(r'^[a-zA-Z0-9_.-]+\.py$', payload_filename):
            payload_filename = "payload.py"
        # The driver applies the SAME C transform layer the local build does
        # (c_transform.py is uploaded beside payload.py by the caller): the
        # per-OS blobs must not be weaker than the local .so.  Seed derives
        # from the payload, so all three OS builds share one transform.
        # No braces in the driver: the workflow embeds it in an f-string
        # with doubled braces.
        script_content = f"""
import os, sys, hashlib, secrets
import platform as _platform
sys.path.insert(0, os.getcwd())
# 1. Cython: payload.py -> payload.c (transpile only)
from Cython.Build import cythonize
from setuptools import Extension
cythonize([Extension("payload", ["{payload_filename}"])], language_level=3)
# 2. The C transform layer, same as the local native build.
# SEED SEPARATION (review §5, 2026-11-18): this used to be
# sha256(payload bytes), which is REPRODUCIBLE -- fine for a rebuild of the
# same target, but it meant all three OS runners drew IDENTICAL transform
# choices, so one analysis of the linux blob predicted the windows and mac
# layouts. A reproducible seed and an anti-correlation seed are different
# requirements and are now derived separately:
#   * _repro_seed  -> logged, stable for the same payload (audit trail);
#   * _divers_seed -> the transform seed, salted with per-runner entropy so
#                      each platform gets its own polymorphic sequence.
# Matrix builds are separate machines, so os.urandom differs per runner and
# the three blobs no longer share a structure. Set NIXON_REPRODUCIBLE=1 to
# pin the old behaviour when bit-identical rebuilds are wanted.
import c_transform, os as _os
_payload_bytes = open("{payload_filename}", "rb").read()
_repro_seed = hashlib.sha256(_payload_bytes).digest()
print("repro seed:", _repro_seed.hex())
if _os.environ.get("NIXON_REPRODUCIBLE"):
    _divers_seed = _repro_seed
    print("C transform seed: REPRODUCIBLE (NIXON_REPRODUCIBLE=1)")
else:
    _divers_seed = hashlib.sha256(
        _repro_seed + _os.urandom(32) + _os.uname().machine.encode()
    ).digest()
    print("C transform seed: DIVERSIFIED", _divers_seed.hex()[:16])
_res = c_transform.transform_file("payload.c", _divers_seed)
print("C transform:", _res.transforms_applied)
# Strip the Cython metadata comment block before compiling. It is pure
# metadata (JSON inside a C comment) and MSVC rejected it as code --
# C2449 "found an open brace at file scope" on line 7 and C4138
# "comment terminator found outside of comment" on line 37. gcc and clang
# accept it; MSVC does not; nothing needs it to compile.
try:
    _txt = open("payload.c", encoding="utf-8", errors="replace").read()
    _a = _txt.find("/* BEGIN: Cython Metadata")
    _b = _txt.find("END: Cython Metadata */")
    if _a >= 0 and _b > _a:
        _end = _b + len("END: Cython Metadata */")
        with open("payload.c", "w", encoding="utf-8") as _mw:
            _mw.write(_txt[:_a] + _txt[_end:])
        print("stripped Cython metadata block (MSVC compatibility)")
except Exception as _strip_exc:
    print("metadata strip skipped:", _strip_exc)
# 3. Compile the TRANSFORMED C into the per-OS native blob.
# PLATFORM HARDENING (review §3). The review's own constraint is "don't blindly
# enable every flag -- verify the resulting binary with platform-native
# inspection tools". So the flags below are emitted AND the object they produce
# is parsed afterwards (step 5): a flag the toolchain ignored shows up as
# applied:false in the attestation instead of as a reassuring log line.
#
# windows: /DYNAMICBASE (ASLR), /NXCOMPAT (DEP), /GUARD:CF (CFG),
#          /CETCOMPAT (CET where supported), /HIGHENTROPYVA, /GS.
#          These are MSVC names and ONLY MSVC accepts them. Measured on
#          2026-11-19 with x86_64-w64-mingw32-gcc 14.2 (a real object, not a
#          guess):
#              gcc: error: unrecognized command-line option '-NXCOMPAT'
#          so an earlier "-" + MSVC-name list made the mingw build FAIL to
#          compile -- hardening that breaks the build is not hardening. mingw
#          therefore gets the --dynamicbase/--nxcompat/--high-entropy-va link
#          flags it does implement. It has no Control Flow Guard (GNU ld 2.44
#          has no such option; lld-link only), so CFG is reported as
#          `unavailable` for that toolchain instead of being demanded.
# macOS:   -fPIE -pie (MH_PIE), -fstack-protector-strong, and a version-min so
#          Hardened Runtime is available. Hardened Runtime and library
#          validation live in the CODE SIGNATURE, not the compiler flags, so
#          they are only present if the operator signs; the attestation reports
#          what the signature actually says.
import sys as _hsys
_extra_cc = []
_extra_ld = []
_toolchain = ""
if _hsys.platform.startswith("win"):
    # A genuine MSVC shell defines VSCMD_ARG_TGT_ARCH; MSYSTEM means mingw.
    _msvc = bool(_os.environ.get("MSYSTEM") is None
                 and _os.environ.get("VSCMD_ARG_TGT_ARCH") is not None)
    if _msvc:
        _toolchain = "msvc"
        _extra_cc = ["/" + f for f in ("DYNAMICBASE", "NXCOMPAT", "GUARD:CF",
                                       "CETCOMPAT", "HIGHENTROPYVA", "GS")]
        _extra_ld = ["/" + f for f in ("DYNAMICBASE", "NXCOMPAT", "GUARD:CF",
                                       "CETCOMPAT")]
    else:
        _toolchain = "gcc"
        _extra_cc = ["-fstack-protector-strong"]
        _extra_ld = ["-Wl,--dynamicbase", "-Wl,--high-entropy-va",
                     "-Wl,--nxcompat"]
elif _hsys.platform == "darwin":
    _toolchain = "clang"
    _extra_cc = ["-fPIE", "-fstack-protector-strong",
                 "-mmacosx-version-min=10.15"]
    _extra_ld = ["-pie", "-Wl,-dead_strip"]
else:
    _toolchain = "gcc"
    _extra_cc = ["-fPIE", "-fstack-protector-strong"]
    _extra_ld = ["-pie", "-Wl,-z,relro,-z,now", "-Wl,-z,noexecstack"]
from setuptools import setup
setup(
    name='payload',
    ext_modules=[Extension("payload", ["payload.c"],
                           extra_compile_args=_extra_cc,
                           extra_link_args=_extra_ld)],
    script_args=['build_ext', '--inplace']
)
# 4. RUNNER SELF-ATTESTATION (review item 7.9, farm-runner integrity).
# A compromised runner can bypass every protection implemented in the
# compiler, so the runner states what it used: OS/Python/Cython, the toolchain
# version strings, the hash of the payload it was GIVEN, the hash of the C it
# transformed, the transform seeds, and the hash of every blob it produced.
# The controller verifies this on download (obfuscator.runner_attest.verify)
# against the digest it recorded before upload.
#
# Built with json.dumps over collected values rather than a dict literal: this
# driver is embedded in an f-string, where literal braces are format specifiers
# and a nested dict silently corrupts the template.
def _tool_version(_argv):
    try:
        import subprocess as _sp
        _r = _sp.run(_argv, capture_output=True, text=True, timeout=30)
        _lines = (_r.stdout or "").strip().splitlines()
        return _lines[0][:200] if _lines else ""
    except Exception:
        return ""
try:
    import Cython as _Cy
    _cython_v = str(getattr(_Cy, "__version__", ""))
except Exception:
    _cython_v = ""
_artifact_pairs = list()
for _name in sorted(_os.listdir(".")):
    if _name.startswith("payload") and _name.endswith((".so", ".pyd", ".dylib")):
        _artifact_pairs.append((_name, hashlib.sha256(open(_name, "rb").read()).hexdigest()))
_runner_pairs = [
    ("os", _platform.system()),
    ("release", _platform.release()),
    ("machine", _platform.machine()),
    ("python", _sys.version.split()[0]),
    ("cython", _cython_v),
    ("cc", _tool_version(["cc", "--version"])),
    ("gcc", _tool_version(["gcc", "--version"])),
    ("clang", _tool_version(["clang", "--version"])),
]
_seed_pairs = [
    ("reproducible", _repro_seed.hex()),
    ("diversified", _divers_seed.hex()),
    ("mode", "reproducible" if _os.environ.get("NIXON_REPRODUCIBLE") else "diversified"),
]
# 5. PLATFORM HARDENING VERIFICATION (review §3: verify, don't assume).
# Parse the object we just produced and record what its header ACTUALLY says.
# A toolchain that silently ignored /DYNAMICBASE or -pie shows up as
# applied:false, which is the only honest way to report it.
# No dict literals here: this driver is embedded in an f-string, where literal
# braces are format specifiers. Three separate attempts to add this step failed
# on exactly that, so the values are built with tuples and a helper.
_hardening = None
_hard_verdict = None
try:
    import native_harden as _nh
    _blob = None
    for _n in sorted(_os.listdir(".")):
        if _n.startswith("payload") and _n.endswith((".so", ".pyd", ".dylib")):
            _blob = _n
            break
    if _blob:
        _raw = open(_blob, "rb").read()
        if _raw[:4] == bytes((0x7f, 0x45, 0x4c, 0x46)):      # ELF
            _rep = _nh.elf_note()
        elif _raw[:2] == bytes((0x4d, 0x5a)):                 # MZ
            _rep = _nh.verify_pe_bytes(_raw)
        elif _raw[:4] in (bytes((0xcf, 0xfa, 0xed, 0xfe)),
                          bytes((0xce, 0xfa, 0xed, 0xfe)),
                          bytes((0xca, 0xfe, 0xba, 0xbe))):   # Mach-O
            _rep = _nh.verify_macho_bytes(_raw)
        else:
            _rep = _nh.unknown_note()
        _hardening = _rep
        # The toolchain matters: GNU ld has no CFG, so demanding it from a
        # mingw build would fail every Windows build forever. check() records
        # that flag as `unavailable` instead, naming the gap rather than
        # hiding it.
        _hard_verdict = _nh.check(_rep, _sys.platform, _toolchain)
except Exception as _hx:
    _hardening = "error: " + str(_hx)[:200]
_top = [
    ("schema", "nx-runner-attestation/v1"),
    ("runner", dict(_runner_pairs)),
    ("toolchain", _toolchain),
    ("payload_sha256", hashlib.sha256(_payload_bytes).hexdigest()),
    ("c_sha256", hashlib.sha256(open("payload.c", "rb").read()).hexdigest()),
    ("seed", dict(_seed_pairs)),
    ("transforms", list(getattr(_res, "transforms_applied", []) or [])),
    ("artifacts", dict(_artifact_pairs)),
    ("hardening", _hardening),
    ("hardening_verdict", _hard_verdict),
]
import json as _j
with open("runner-attestation.json", "w", encoding="utf-8") as _af:
    _af.write(_j.dumps(dict(_top), indent=2, sort_keys=True))
print("runner attestation:", dict(_top)["payload_sha256"][:16],
      "blobs:", len(_artifact_pairs))
"""
        # Keep the rendered driver on the instance: create_workflow assembles
        # it as an f-string, and a test needs to compile exactly that text
        # without eval'ing generated source.
        self._nx_last_driver = script_content
        indented_script = "\n".join(["          " + line for line in script_content.strip().split('\n')])
        workflow_yaml = f"""name: Nixon Native Build
on:
  workflow_dispatch:
jobs:
  build-farm:
    runs-on: ${{{{ matrix.os }}}}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: windows-latest
            suffix: .pyd
            prep_cmd: choco install upx && pip install cython setuptools wheel
            build_cmd: python setup_remote.py
          - os: ubuntu-22.04
            suffix: .so
            prep_cmd: sudo apt-get update && sudo apt-get install -y upx && pip install cython setuptools
            build_cmd: python setup_remote.py
          - os: macos-latest
            suffix: .dylib
            prep_cmd: brew install upx && pip install cython setuptools
            build_cmd: python setup_remote.py
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Create Setup Script
        shell: bash
        run: |
          cat <<'EOF' > setup_remote.py
{indented_script}
          EOF
      - name: Install Dependencies
        run: ${{{{ matrix.prep_cmd }}}}
      - name: Compile Native Binary
        run: ${{{{ matrix.build_cmd }}}}
      - name: List Files (Debug)
        run: ls -R || dir
      - name: Rename Artifact (Standard)
        shell: bash
        run: |
          find . -maxdepth 1 -name "payload*" -type f ! -name "*.py" ! -name "setup_remote.py" ! -name "*.c" -print0 | xargs -0 -I {{}} mv {{}} payload${{{{ matrix.suffix }}}}
      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: blob-payload${{{{ matrix.suffix }}}}
          path: payload${{{{ matrix.suffix }}}}
          retention-days: 1
"""
        import requests
        url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/.github/workflows/build.yml"  
        with UI.Task("Build Config", "Updating Workflow...") as t:
            for attempt in range(3):
                try:
                    get_r = requests.get(url, headers=self.headers, proxies=self.proxies, verify=True, timeout=30)
                    sha = None
                    if get_r.status_code == 200:
                         sha = get_r.json().get("sha")
                    data = {"message": "Update workflow", "content": base64.b64encode(workflow_yaml.encode()).decode()}
                    if sha: data["sha"] = sha      
                    put_r = requests.put(url, headers=self.headers, json=data, proxies=self.proxies, verify=True, timeout=60)
                    if put_r.status_code in [200, 201]:
                        t.success("Workflow Updated")
                        return
                    else:
                        time.sleep(2)
                except Exception:
                    time.sleep(2)
            t.fail("Workflow Update Failed")
            raise Exception("Failed to update workflow")
    def trigger_and_wait(self):
        print(" [*] [Cloud] Triggering Build Matrix (Win/Lin/Android)...")
        import requests
        prev_run_id = None
        try:
            r=requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs",headers=self.headers,proxies=self.proxies,verify=True,timeout=20)
            runs=r.json()
            if runs.get('total_count',0)>0:
                prev_run_id=runs['workflow_runs'][0]['id']
        except Exception: pass
        url=f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/workflows/build.yml/dispatches"
        requests.post(url,headers=self.headers,json={"ref":"main"},proxies=self.proxies,verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
        print(" [*] Waiting for runners (this takes 3-5 mins)...")
        run_id=None
        for _ in range(30):
            time.sleep(10)
            r=requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs",headers=self.headers,proxies=self.proxies,verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
            runs=r.json()
            if runs.get('total_count',0)>0:
                current_id=runs['workflow_runs'][0]['id']
                if current_id != prev_run_id:
                    run_id=current_id
                    break
        if not run_id:
            print(" [!] Timeout waiting for workflow to start.")
            return None
        jobs_url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}/jobs"
        job_map = {
            "payload.windows.exe": "Wind",
            "payload.linux.bin": "Linux",
            "payload.macos.bin": "macOS",
            "payload.android.bin": "Android"
        }        
        time.sleep(5)
        job_start_times = {}
        job_end_times = {}
        # An overall deadline: the loop below only breaks when the
        # workflow reports "completed", so a run that never completes (or
        # a farm that stops answering) would poll forever.
        deadline = time.time() + _GITHUB_WAIT_DEADLINE
        while True:
            if time.time() >= deadline:
                print(" [!] Timed out waiting for the build farm. The build "
                      "may still be running on the server.")
                return None
            try:
                r = requests.get(jobs_url, headers=self.headers, proxies=self.proxies, verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
                jobs_data = r.json()
                jobs = jobs_data.get("jobs", [])
                states = {"Wind": "Q", "Linux": "Q", "macOS": "Q", "Android": "Q"}
                for job in jobs:
                    name = job['name']
                    short_code = None
                    for k, v in job_map.items():
                        if k in name: short_code = v; break
                    if not short_code: continue
                    status = job['status'] 
                    conclusion = job['conclusion']
                    def parse_ts(t):
                        if not t: return 0.0
                        try:
                            t = t.replace('Z', '+00:00')
                            from datetime import datetime
                            return datetime.datetime.fromisoformat(t).timestamp()
                        except Exception: return 0.0
                    s_time = parse_ts(job.get('started_at'))
                    c_time = parse_ts(job.get('completed_at'))
                    job_start_times[short_code] = s_time
                    job_end_times[short_code] = c_time
                    if status == "completed":
                        if conclusion == "success": states[short_code] = "✓"
                        elif conclusion == "skipped": states[short_code] = "-"
                    elif status == "in_progress":
                        states[short_code] = "IP"
                    else:
                        states[short_code] = "Q"
                r_wf = requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}", headers=self.headers, proxies=self.proxies, verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
                wf_data = r_wf.json()
                wf_status = wf_data.get('status')
                wf_conclusion = wf_data.get('conclusion')
                for _ in range(100):
                    ui_parts = []
                    now = time.time()                    
                    for p in ["Wind", "Linux", "macOS", "Android"]: 
                        s = states.get(p, "Q")
                        start = job_start_times.get(p, 0.0)
                        end = job_end_times.get(p, 0.0)
                        duration = 0.0
                        if s == "IP":
                             if start > 0: duration = now - start
                        elif s in ["✓", "✗", "-"]:
                             if end > start: duration = end - start
                        color = UI.RESET
                        if s == "IP": color = UI.YELLOW
                        elif s == "✓": color = UI.GREEN
                        elif s == "✗": color = UI.RED
                        ui_parts.append(f"[{p}:{color}{s}{UI.RESET} {duration:.2f}s]")
                    status_line = " ".join(ui_parts)
                    sys.stdout.write(f"\r\033[K    ↳ Status: {status_line}")
                    sys.stdout.flush()
                    if wf_status == "completed": break
                    time.sleep(0.1)
                if wf_status == "completed":
                    print("")
                    if wf_conclusion == "success":
                        print(" [+] Build SUCCESS!")
                        return run_id
                    else:
                        print(" [!] Build FAILED on GitHub side.")
                        return None
            except KeyboardInterrupt:
                raise
            except Exception:
                time.sleep(5)
    def download_artifacts(self,run_id,output_dir,sign_key_hex=None):
        print(f" [*] [Cloud] Downloading binaries to {output_dir}...")
        import requests
        os.makedirs(output_dir,exist_ok=True)
        # Integrity model (documented): artifacts come over authenticated
        # TLS (verify=True) from the repo's own Actions runs — the channel
        # is the integrity mechanism (GitHub's API provides no artifact
        # content hash to pin against). Below adds timeouts, HTTP-status
        # enforcement, and ZipSlip confinement on top of that channel.
        # ADR-0005 adds: verify-before-extract against any *.sig.json
        # sidecars inside the zips when a key is configured (explicit hex
        # or NIXON_ARTIFACT_KEY_HEX / NIXON_SIGN_KEY); mismatch raises
        # fail-closed before extract. No key → auditable warning + proceed.
        _sign_key = _artifact_sign_key(sign_key_hex)
        # Rate-limit resilience (ported from the removed Nuitka farm): a 429
        # on the artifact listing is waited out with the server's own
        # Retry-After and retried once, not treated as terminal.
        r=requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}/artifacts",headers=self.headers,proxies=self.proxies,verify=True,timeout=30)
        if getattr(r, 'status_code', None) == 429:
            time.sleep(_github_retry_after(r))
            r=requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}/artifacts",headers=self.headers,proxies=self.proxies,verify=True,timeout=30)
        r.raise_for_status()
        artifacts=r.json().get('artifacts',[])
        for art in artifacts:
            name=art['name']
            down_url=art['archive_download_url']
            zip_resp=requests.get(down_url,headers=self.headers,stream=True,proxies=self.proxies,verify=True,timeout=120)
            zip_resp.raise_for_status()
            zip_path=os.path.join(output_dir,f"{name}.zip")
            with open(zip_path,"wb")as f:f.write(zip_resp.content)
            if not _verify_download_zip(zip_path, name, _sign_key):
                raise ValueError(
                    "artifact verification refused for %r" % (name,))
            _extract_zip_confined(zip_path, output_dir)
            os.remove(zip_path)
            clean_name=name.replace("blob-","")
            if "android.so" in clean_name: clean_name = "android.so" 
            final_path=os.path.join(output_dir,clean_name)
            for root,dirs,files in os.walk(output_dir):
                for f in files:
                    if clean_name in f and os.path.join(root,f)!=final_path:shutil.move(os.path.join(root,f),final_path)
            print(f"    [+] Acquired: {clean_name}")
    def nuke(self):
        import requests
        url = f"{self.base_url}/repos/{self.username}/{self.repo_name}"
        requests.delete(url, headers=self.headers, proxies=self.proxies, verify=True, timeout=_GITHUB_REQUEST_TIMEOUT)
        UI.dot_item("Cleanup", "Repository Nuked", "SCORCHED")
def ensure_upx_installed():
    import shutil
    import urllib.request
    if shutil.which("upx"):
        return shutil.which("upx")
    print("    [*] UPX not found, attempting install...")
    try:
        if sys.platform.startswith("linux"):
            for cmd in [
                ["sudo", "apt-get", "install", "-y", "upx-ucl"],
                ["sudo", "dnf", "install", "-y", "upx"],
                ["sudo", "pacman", "-S", "--noconfirm", "upx"],
            ]:
                try:
                    subprocess.run(cmd, check=True, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
                    if shutil.which("upx"): return shutil.which("upx")
                except Exception: pass
        elif sys.platform == "darwin":
            try:
                subprocess.run(["brew", "install", "upx"], check=True, capture_output=True, timeout=120)
                if shutil.which("upx"): return shutil.which("upx")
            except Exception: pass
        elif sys.platform == "win32":
            try:
                subprocess.run(["choco", "install", "upx", "-y"], check=True, capture_output=True, timeout=120)
                if shutil.which("upx"): return True
            except Exception: pass
            try:
                subprocess.run(["winget", "install", "upx"], check=True, capture_output=True, timeout=120)
                if shutil.which("upx"): return True
            except Exception: pass
    except Exception as e:
        print(f"    [!] Package manager install failed: {e}")
    try:
        print("    [*] Attempting direct UPX binary download...")
        upx_version = "4.2.2"
        upx_urls = {
            "linux": f"https://github.com/upx/upx/releases/download/v{upx_version}/upx-{upx_version}-amd64_linux.tar.xz",
            "darwin": f"https://github.com/upx/upx/releases/download/v{upx_version}/upx-{upx_version}-amd64_macos.tar.xz",
            "win32": f"https://github.com/upx/upx/releases/download/v{upx_version}/upx-{upx_version}-win64.zip",
        }
        plat_key = "linux" if sys.platform.startswith("linux") else sys.platform
        if plat_key not in upx_urls:
            print(f"    [!] No UPX binary available for platform: {sys.platform}")
            return False
        url = upx_urls[plat_key]
        local_tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tools")
        os.makedirs(local_tools_dir, exist_ok=True)
        archive_path = os.path.join(local_tools_dir, os.path.basename(url))
        urllib.request.urlretrieve(url, archive_path)
        # The archive is about to become executable code on this machine (the
        # binary is chmod'd and prepended to PATH below). Nothing verified it:
        # a compromised release or CDN mirror meant code execution on the
        # builder. When NIXON_UPX_SHA256 is set the hash is enforced; when it
        # is not, the hash is printed so it can be pinned. The pin pattern is
        # the same one the JIT loader hooks use (RUNTIME_JIT_SO_SHA256).
        import hashlib as _hl
        with open(archive_path, "rb") as _af:
            _got = _hl.sha256(_af.read()).hexdigest()
        _want = os.environ.get("NIXON_UPX_SHA256", "").strip().lower()
        if _want and _got != _want:
            print(f"    [!] UPX archive sha256 {_got} != pinned {_want}; refusing it")
            try:
                os.remove(archive_path)
            except OSError:
                pass
            return False
        if not _want:
            # Download-and-exec without a pinned hash is exactly the
            # supply chain the pin exists to stop (audit round 2).
            print(f"    [!] UPX archive sha256 {_got} but no pin set; "
                  "refusing download (set NIXON_UPX_SHA256)")
            try:
                os.remove(archive_path)
            except OSError:
                pass
            return False
        if archive_path.endswith(".zip"):
            _extract_zip_confined(archive_path, local_tools_dir)
        elif archive_path.endswith(".tar.xz"):
            _extract_tar_confined(archive_path, local_tools_dir, "r:xz")
        for root, dirs, files in os.walk(local_tools_dir):
            for f in files:
                if f in ("upx", "upx.exe"):
                    upx_path = os.path.join(root, f)
                    if sys.platform != "win32":
                        os.chmod(upx_path, 0o755)
                    os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")
                    print(f"    [+] UPX downloaded and available at: {upx_path}")
                    return True
        print("    [!] UPX binary not found in download")
        return False
    except Exception as e:
        print(f"    [!] UPX download failed: {e}")
        return False
def strip_binary(path):
    import shutil
    if not os.path.isfile(path):
        return False
    fname = os.path.basename(path).lower()
    host_os = sys.platform
    target_os = None
    # Policy (explicit): Android/ARM artifacts are NEVER stripped —
    # host binutils would corrupt cross-arch binaries. This early
    # return also makes any "android" alternative below unreachable
    # by design (kept out deliberately, not a dead branch).
    if "android" in fname or "arm" in fname:
        print(f"    [!] Skipping strip for {fname} (Cross-arch safety)")
        return False
    if "linux" in fname:
        target_os = "linux"
    elif "macos" in fname or "darwin" in fname:
        target_os = "darwin"
    elif "windows" in fname or fname.endswith(".exe") or fname.endswith(".pyd"):
        target_os = "windows"
    else:
        if fname.endswith(".so"):
            target_os = "linux"
        elif fname.endswith(".dylib"):
            target_os = "darwin"
        elif fname.endswith(".dll") or fname.endswith(".exe"):
            target_os = "windows"
    if target_os is None:
        print(f"    [!] Cannot determine target OS for {fname}, skipping strip")
        return False
    can_strip = False
    strip_cmd = None
    if shutil.which("llvm-strip"):
        strip_cmd = ["llvm-strip", "--strip-all", path]
        can_strip = True
    elif shutil.which("strip"):
        if host_os.startswith("linux") and target_os == "linux":
            strip_cmd = ["strip", "--strip-all", path]
            can_strip = True
        elif host_os == "darwin" and target_os == "darwin":
            strip_cmd = ["strip", "-x", path]
            can_strip = True
        elif host_os == "win32" and target_os == "windows":
            strip_cmd = ["strip", "--strip-all", path]
            can_strip = True
        else:
            print(f"    [!] Cannot strip {target_os} binary on {host_os} host (install llvm-strip for cross-platform support)")
            return False
    else:
        print("    [!] No strip tool available")
        return False
    if not can_strip or not strip_cmd:
        return False
    try:
        subprocess.run(strip_cmd, check=True, capture_output=True, timeout=60)
        print(f"    [+] Stripped: {os.path.basename(path)}")
        return True
    except subprocess.TimeoutExpired:
        print(f"    [!] Strip timed out for {os.path.basename(path)}")
        return False
    except Exception as e:
        print(f"    [!] Strip failed for {os.path.basename(path)}: {e}")
        return False
def compress_with_upx(path, level=9):
    if not os.path.isfile(path):
        return False
    try:
        orig_size = os.path.getsize(path)
        cmd = ["upx", f"-{level}", "--best", "--lzma", "-q", path]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            new_size = os.path.getsize(path)
            ratio = (1 - new_size / orig_size) * 100 if orig_size > 0 else 0
            print(f"    [+] UPX: {os.path.basename(path)} ({orig_size//1024}KB -> {new_size//1024}KB, -{ratio:.1f}%)")
            return True
        else:
            print(f"    [!] UPX skip: {os.path.basename(path)} (may be unsupported)")
            return False
    except Exception as e:
        print(f"    [!] UPX error for {os.path.basename(path)}: {e}")
        return False
def optimize_and_pack_binaries(dist_dir):
    import tarfile
    binary_files = {}
    for fname in os.listdir(dist_dir):
        fpath = os.path.join(dist_dir, fname)
        if not os.path.isfile(fpath) or fname.endswith(".zip") or fname.endswith(".tar"):
            continue
        fname_lower = fname.lower()
        if "windows" in fname_lower:
            binary_files["windows"] = fpath
        elif "linux" in fname_lower and "android" not in fname_lower:
            binary_files["linux"] = fpath
        elif "macos" in fname_lower or "darwin" in fname_lower:
            binary_files["darwin"] = fpath
        elif "android" in fname_lower:
            binary_files["android"] = fpath
    if not binary_files:
        print("    [!] No binaries found to optimize")
        return None
    print(f"    [*] Found {len(binary_files)} binaries to optimize...")
    for _plat, fpath in binary_files.items():
        strip_binary(fpath)
    if ensure_upx_installed():
        for _plat, fpath in binary_files.items():
            compress_with_upx(fpath)
    else:
        print("    [!] Skipping UPX compression (not available)")
    tar_path = os.path.join(dist_dir, "binaries.tar")
    with tarfile.open(tar_path, "w", encoding='utf-8') as tar:
        for platform, fpath in binary_files.items():
            arcname = f"payload.{platform}" + (".exe" if platform == "windows" else ".bin")
            tar.add(fpath, arcname=arcname)
            print(f"    [+] Packed: {arcname}")
    print(f"    [+] Created TAR archive: {tar_path} ({os.path.getsize(tar_path)//1024}KB)")
    return tar_path
def generate_tar_loader_script(tar_path):
    import tarfile as tf
    import io as _io
    with open(tar_path, "rb") as f:
        tar_data = f.read()
    bio = _io.BytesIO()
    with tf.open(fileobj=_io.BytesIO(tar_data), mode="r") as src_tar:
        with tf.open(fileobj=bio, mode="w:xz", preset=9, encoding='utf-8') as dst_tar:
            for member in src_tar.getmembers():
                dst_tar.addfile(member, src_tar.extractfile(member))
    xz_payload = bio.getvalue()
    loader_stub = r'''# -*- coding: utf-8 -*-
import sys,os,tarfile,io,subprocess,platform,tempfile,shutil,stat
def run_payload():
    s = platform.system().lower()
    is_android = "android" in s or os.path.exists("/data/data/com.termux") or os.path.exists("/system/build.prop")
    target = ""
    if "windows" in s: target = "windows"
    elif "darwin" in s: target = "darwin"
    elif is_android: target = "android"
    elif "linux" in s: target = "linux"
    else: return
    try:
        me = sys.argv[0]
        if not os.path.exists(me): me = __file__
        with open(me, "rb") as f:
            content = f.read()
        sep = b"\n#_NX_PAYLOAD_START_#\n"
        idx = content.find(sep)
        if idx == -1: return
        archive_data = content[idx + len(sep):]
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:xz") as tar:
            try:
                member = tar.getmember(target)
            except KeyError:
                if target == "android":
                    try: member = tar.getmember("linux")
                    except Exception: return
                else: return
            ext = ".exe" if target == "windows" else ".bin"
            mem_path = "/dev/shm" if os.path.exists("/dev/shm") else tempfile.gettempdir()
            fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=mem_path)
            with os.fdopen(fd, "wb") as f_out:
                shutil.copyfileobj(tar.extractfile(member), f_out)
            if target != "windows":
                try:
                    st = os.stat(tmp_path)
                    os.chmod(tmp_path, st.st_mode | stat.S_IEXEC)
                except Exception: pass
            try:
                # Same as the universal loader: propagate the payload's status and
                # bound its runtime instead of swallowing both.
                _rc = subprocess.call([tmp_path] + sys.argv[1:], timeout=3600)
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            sys.exit(_rc)
    except SystemExit:
        raise
    except Exception as _e:
        sys.stderr.write("[loader] failed: %s\n" % (_e,))
        sys.exit(1)
if __name__=="__main__":
    run_payload()
'''
    return loader_stub, xz_payload
def generate_xz_loader_file(tar_path, output_path):
    loader_stub, xz_payload = generate_tar_loader_script(tar_path)
    final_content = loader_stub.encode('utf-8') + b"\n#_NX_PAYLOAD_START_#\n" + xz_payload
    with open(output_path, "wb") as f:
        f.write(final_content)
    return output_path
