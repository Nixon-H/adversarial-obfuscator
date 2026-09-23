import sys,os,zipfile,base64,io,tokenize,py_compile,shutil,tempfile,random,hashlib,lzma,struct,time,json,argparse,uuid,re,inspect,platform,subprocess,marshal,hmac,secrets,ctypes,importlib.util,atexit,warnings,zlib,codecs,string,builtins,math,dis,multiprocessing,types,traceback,gc,ast,socket,threading,concurrent.futures,logging;from io import StringIO;from datetime import datetime; _nixon_ハッシュ해시 = hashlib
sys.setrecursionlimit(10000)
sys.stderr.flush()
warnings.filterwarnings("ignore")
_console = sys.stdout
if os.environ.get('NIXON_LOG_REDIRECT', '1') == '1':
    try:
        _log_fd = open("build.log", "w", encoding='utf-8')
        _console_fd = os.dup(1)
        os.dup2(_log_fd.fileno(), 1)
        os.dup2(_log_fd.fileno(), 2)
        _console = open(_console_fd, "w", encoding='utf-8')
    except Exception as _e:
        import sys as _sys
        print(f"[utils] Failed to redirect log: {_e}", file=_sys.__stderr__)
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
        UI.fail(f"Python 3.8+ recommended")
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
    safe_fallbacks = ['_var', '_val', '_x', '_y', '_z']
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
    return f"_nixon_{suffix}"
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
if os.environ.get('NIXON_LOG_REDIRECT', '1') == '1':
    _print_banner()
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
STRING_SESSION_KEY = secrets.token_bytes(32)
def _next_h_impl(current, step):
    return int.from_bytes(hashlib.sha256(str(current).encode() + str(step).encode()).digest()[:8], 'little')
globals()[FUNC_NEXT_H] = _next_h_impl
next_h = _next_h_impl
NEXT_H_SOURCE = None
class ConfigManager:
    CONFIG_FILE=os.path.join(os.path.expanduser("~"),".nixon_builder_config.json")
    def __init__(self):self.config=self._load()
    def _load(self):
        if not os.path.exists(self.CONFIG_FILE):return {}
        try:
            with open(self.CONFIG_FILE,"r")as f:return json.load(f)
        except Exception:return {}
    def save(self):
        with open(self.CONFIG_FILE,"w")as f:json.dump(self.config,f,indent=4)
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
        return f"https://{domain}"
    def _get_username(self):
        try:
            import requests
            r=requests.get(f"{self.base_url}/user",headers=self.headers,proxies=self.proxies,verify=False)
            r.raise_for_status()
            return r.json()['login']
        except Exception as e:
            print(f" [!] GitHub Auth Failed: {e}")
            sys.exit(1)
    def create_disposable_repo(self):
        print(f"\n [*] [Cloud] Ensuring private repo exists: {self.repo_name}...")
        import requests
        data={"name":self.repo_name,"private":True,"auto_init":True}
        r=requests.post(f"{self.base_url}/user/repos",headers=self.headers,json=data,proxies=self.proxies,verify=False)
        if r.status_code==201 or r.status_code==422:                           
            return True
        print(f" [!] Repo creation failed: {r.text}")
        return False
    def upload_file(self,local_path,remote_name):
        import requests
        with open(local_path,"rb")as f:content=base64.b64encode(f.read()).decode()
        url=f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/{remote_name}"
        data={"message":f"Upload {remote_name}","content":content}
        requests.put(url,headers=self.headers,json=data,proxies=self.proxies,verify=False)
    def create_workflow(self, payload_filename):
        script_content = f"""
from setuptools import setup, Extension
from Cython.Build import cythonize
import os
files = ['{payload_filename}']
extensions = [Extension("payload", files)]
setup(
    name='payload',
    ext_modules=cythonize(extensions, language_level=3, compiler_directives={{'always_allow_keywords': True}}),
    script_args=['build_ext', '--inplace']
)
"""
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
                    get_r = requests.get(url, headers=self.headers, proxies=self.proxies, verify=False, timeout=30)
                    sha = None
                    if get_r.status_code == 200:
                         sha = get_r.json().get("sha")
                    data = {"message": "Update workflow", "content": base64.b64encode(workflow_yaml.encode()).decode()}
                    if sha: data["sha"] = sha      
                    put_r = requests.put(url, headers=self.headers, json=data, proxies=self.proxies, verify=False, timeout=60)
                    if put_r.status_code in [200, 201]:
                        t.success("Workflow Updated")
                        return
                    else:
                        time.sleep(2)
                except Exception as e:
                    time.sleep(2)
            t.fail("Workflow Update Failed")
            raise Exception("Failed to update workflow")
    def trigger_and_wait(self):
        print(" [*] [Cloud] Triggering Build Matrix (Win/Lin/Android)...")
        import requests
        prev_run_id = None
        try:
            r=requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs",headers=self.headers,proxies=self.proxies,verify=False,timeout=20)
            runs=r.json()
            if runs.get('total_count',0)>0:
                prev_run_id=runs['workflow_runs'][0]['id']
        except Exception: pass
        url=f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/workflows/build.yml/dispatches"
        requests.post(url,headers=self.headers,json={"ref":"main"},proxies=self.proxies,verify=False)
        print(" [*] Waiting for runners (this takes 3-5 mins)...")
        run_id=None
        for _ in range(30):
            time.sleep(10)
            r=requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs",headers=self.headers,proxies=self.proxies,verify=False)
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
        while True:
            try:
                r = requests.get(jobs_url, headers=self.headers, proxies=self.proxies, verify=False)
                jobs_data = r.json()
                jobs = jobs_data.get("jobs", [])
                states = {"Wind": "Q", "Linux": "Q", "macOS": "Q", "Android": "Q"}
                any_failed = False
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
                        return datetime.datetime.fromisoformat(t).timestamp()
                    except Exception: return 0.0
                    s_time = parse_ts(job.get('started_at'))
                    c_time = parse_ts(job.get('completed_at'))
                    job_start_times[short_code] = s_time
                    job_end_times[short_code] = c_time
                    if status == "completed":
                        if conclusion == "success": states[short_code] = "✓"
                        elif conclusion == "skipped": states[short_code] = "-"
                        else: states[short_code] = "✗"; any_failed = True
                    elif status == "in_progress":
                        states[short_code] = "IP"
                    else:
                        states[short_code] = "Q"
                r_wf = requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}", headers=self.headers, proxies=self.proxies, verify=False)
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
            except Exception as e:
                time.sleep(5)
    def download_artifacts(self,run_id,output_dir):
        print(f" [*] [Cloud] Downloading binaries to {output_dir}...")
        import requests
        os.makedirs(output_dir,exist_ok=True)
        r=requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}/artifacts",headers=self.headers,proxies=self.proxies,verify=False)
        artifacts=r.json().get('artifacts',[])
        for art in artifacts:
            name=art['name']
            down_url=art['archive_download_url']
            zip_resp=requests.get(down_url,headers=self.headers,stream=True,proxies=self.proxies,verify=False)
            zip_path=os.path.join(output_dir,f"{name}.zip")
            with open(zip_path,"wb")as f:f.write(zip_resp.content)
            with zipfile.ZipFile(zip_path,'r')as z:z.extractall(output_dir)
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
        requests.delete(url, headers=self.headers, proxies=self.proxies, verify=False)
        UI.dot_item("Cleanup", "Repository Nuked", "SCORCHED")
class GitHubNuitkaFarm:
    def __init__(self, token, is_public=False, use_tor=False, tor_proxy=None):
        self.is_public = is_public
        self.token = token
        self.tor_proxy = resolve_tor_proxy(tor_proxy) if use_tor else None
        self.proxies = tor_proxies(tor_proxy) if use_tor else None
        self.headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        self.base_url = "https://api.github.com"
        self.repo_name = "nixon-build-farm-nuitka" 
        self.username = self._get_username()
    def _get_username(self):
        try:
            import requests
            r = requests.get(f"{self.base_url}/user", headers=self.headers, proxies=self.proxies, verify=False)
            return r.json()['login']
        except Exception: return "unknown"
    def create_disposable_repo(self):
        try:
            import requests
            with UI.Task("Repo Access", f"Repo {self.repo_name}") as t:
                data = {"name": self.repo_name, "private": not self.is_public, "auto_init": True}
                r = requests.post(f"{self.base_url}/user/repos", headers=self.headers, json=data, proxies=self.proxies, verify=False)
                if r.status_code in [201, 422]:
                    t.success(f"{self.repo_name} Verified")
                    return True
                else:
                    t.fail(f"Failed: {r.status_code}")
                    return False
        except Exception as e:
            if 't' in locals(): t.fail(str(e))
            return False
    def upload_file(self, local_path, remote_name):
        import requests
        import time
        import base64
        with UI.Task("Code Staging", f"{remote_name} uploaded to build farm") as t:
            try:
                with open(local_path, "rb") as f: 
                    content = base64.b64encode(f.read()).decode()
                url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/{remote_name}"
                for attempt in range(3):
                    try:
                        sha = None
                        try:
                            get_r = requests.get(url, headers=self.headers, proxies=self.proxies, verify=False, timeout=30)
                            if get_r.status_code == 200:
                                sha = get_r.json().get("sha")
                        except Exception: pass
                        data = {"message": f"Upload {remote_name}", "content": content}
                        if sha: data["sha"] = sha
                        r = requests.put(url, headers=self.headers, json=data, proxies=self.proxies, verify=False, timeout=300)
                        if r.status_code in [200, 201]:
                            t.success()
                            return True
                        elif r.status_code == 409:
                            time.sleep(1)
                            continue
                        else:
                            time.sleep(2 * (attempt + 1))
                    except Exception as e:
                        time.sleep(2 * (attempt + 1))
                t.fail(f"Failed to upload {remote_name}")
                return False
            except Exception as e:
                t.fail(f"Error: {str(e)}")
                return False
    def delete_file(self, filename):
        import requests
        url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/{filename}"
        get_r = requests.get(url, headers=self.headers, proxies=self.proxies, verify=False)
        if get_r.status_code == 200:
            sha = get_r.json().get("sha")
            data = {"message": "Cleanup payload", "sha": sha}
            requests.delete(url, headers=self.headers, json=data, proxies=self.proxies, verify=False)
            UI.item("Cleanup", f"Wiped {filename}", "SECURE")
    def nuke(self):
        import requests
        url = f"{self.base_url}/repos/{self.username}/{self.repo_name}"
        try:
            r = requests.delete(url, headers=self.headers, proxies=self.proxies, verify=False)
            if r.status_code == 204:
                UI.dot_item("Cleanup", f"Repo Deleted", "SCORCHED")
            elif r.status_code == 403:
                UI.dot_item("Cleanup", f"Permission Denied (Check 'delete_repo' scope)", "FAIL")
            elif r.status_code == 404:
                UI.dot_item("Cleanup", f"Repo already gone", "OK")
            else:
                UI.dot_item("Cleanup", f"Failed ({r.status_code})", "FAIL")
        except Exception as e:
            UI.dot_item("Cleanup", f"Error: {e}", "FAIL")
    def create_workflow(self, payload_filename="payload.py", exclude_android=False, pip_command=None, extra_nuitka_flags="", python_version=None):
        import re
        import sys
        if python_version is None:
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        if not re.match(r'^[a-zA-Z0-9_.-]+\.py$', payload_filename):
            UI.fail(f"Invalid payload filename: {payload_filename}")
            payload_filename = "payload.py"
        safe_filename = payload_filename.replace('"', '').replace("'", "").replace(";", "").replace("|", "")
        install_cmd = pip_command if pip_command else "pip install nuitka zstandard ordered-set requests websockets"
        base_nuitka_flags = "--enable-plugin=upx --include-package=runpy --include-package=importlib --include-package=ctypes --include-package=encodings --include-package=asyncio --include-module=uuid,json,ssl,socket,base64,lzma,struct,hashlib,hmac,secrets,datetime,threading,multiprocessing,subprocess,platform,argparse,urllib.request,shutil,tempfile,random,warnings,contextlib,weakref,signal,bisect,email,http,requests,websockets,websockets.exceptions,websockets.legacy,websockets.legacy.client"
        full_nuitka_flags = f"{base_nuitka_flags} {extra_nuitka_flags}"
        full_nuitka_flags = f"{base_nuitka_flags} {extra_nuitka_flags}"
        matrix_entries = """          - os: windows-latest
            suffix: .exe
            output_name: payload.exe
            final_name: payload.windows.exe
          - os: ubuntu-22.04
            suffix: .bin
            output_name: payload.bin
            final_name: payload.linux.bin
          - os: macos-latest
            suffix: .bin
            output_name: payload.bin
            final_name: payload.macos.bin"""
        android_matrix = """
          - os: ubuntu-22.04
            suffix: .bin
            final_name: payload.android.bin"""
        android_steps = f"""
        - name: Setup QEMU for Android
          if: matrix.final_name == 'payload.android.bin'
          uses: docker/setup-qemu-action@v3
          with:
            platforms: arm64
        - name: Build Android
          if: matrix.final_name == 'payload.android.bin'
          run: |
              docker run --rm --platform linux/arm64 -v "${{{{ github.workspace }}}}":/src python:3.11-slim-bullseye \\
              /bin/bash -c "apt-get update && apt-get install -y gcc build-essential patchelf ccache \\
              && {install_cmd} \\
              && cd /src \\
              && python -m nuitka --standalone --onefile --remove-output --assume-yes-for-downloads {full_nuitka_flags} --output-filename=payload.bin {safe_filename} \\
              && mv payload.bin payload.android.bin"
"""
        if not exclude_android:
            matrix_entries += android_matrix
            android_build_steps = android_steps
            linux_condition = "if: matrix.os != 'windows-latest' && matrix.final_name != 'payload.android.bin'"
            setup_python_condition = "if: matrix.final_name != 'payload.android.bin'"
            nuitka_condition = "if: matrix.final_name != 'payload.android.bin'"
        else:
            android_build_steps = ""
            linux_condition = "if: matrix.os != 'windows-latest'"
            setup_python_condition = ""
            nuitka_condition = ""
        packer_script = r'''
import sys, os, zipfile, io, base64, tempfile, shutil, subprocess, platform
def get_platform_key():
    s = platform.system().lower()
    if "windows" in s: return "windows"
    if "darwin" in s: return "macos"
    if "linux" in s:
        if os.path.exists("/system/build.prop") or os.path.exists("/data/data/com.termux"):
            return "android"
        return "linux"
    return "unknown"
def pack():
    print("[*] Starting Universal Pack...")
    mapping = {
        "payload.windows.exe": "windows",
        "payload.linux.bin": "linux",
        "payload.macos.bin": "macos",
        "payload.android.bin": "android"
    }
    final_zip = io.BytesIO()
    with zipfile.ZipFile(final_zip, "w", zipfile.ZIP_LZMA) as z:
        for root, _, files in os.walk("."):
            for f in files:
                if f in mapping:
                    print(f" [+] Adding {f} as {mapping[f]}...")
                    z.write(f, mapping[f])
    payload_encoded = base64.b85encode(final_zip.getvalue()).decode()
    loader_code = f"""# -*- coding: utf-8 -*-
import sys, os, base64, zipfile, io, tempfile, subprocess, platform, shutil
import time
PAYLOAD = "{payload_encoded}"
def run():
    print("Please wait up to 30 seconds for execution...")
    s = platform.system().lower()
    target = "linux"
    if "windows" in s: target = "windows"
    elif "darwin" in s: target = "macos"
    elif "linux" in s:
        if os.path.exists("/system/build.prop"): target = "android"
    try:
        raw = base64.b85decode(PAYLOAD)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if target not in z.namelist():
                return
            mem_path = "/dev/shm" if os.path.exists("/dev/shm") else tempfile.gettempdir()
            ext = ".exe" if target == "windows" else ".bin"
            fd, path = tempfile.mkstemp(suffix=ext, dir=mem_path)
            os.close(fd)
            with open(path, "wb") as f:
                f.write(z.read(target))
            os.chmod(path, 0o777)
            try:
                subprocess.call([path] + sys.argv[1:])
            finally:
                if os.path.exists(path):
                    try: os.remove(path)
                    except Exception: pass
    except Exception: pass
if __name__ == "__main__":
    run()
"""
    with open("Universal_Loader.py", "w") as f:
        f.write(loader_code)
    print("[+] Universal_Loader.py generated (Base85 Optimized).")
if __name__ == "__main__":
    pack()
'''
        indented_packer_script = "\n".join(["          " + line for line in packer_script.strip().split('\n')])
        workflow_yaml = f"""name: Nixon Nuitka Build
on:
  workflow_dispatch:
jobs:
  build-farm:
    strategy:
      fail-fast: false
      matrix:
        include:
{matrix_entries}
    runs-on: ${{{{ matrix.os }}}}
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          ref: main
          fetch-depth: 0
      - name: Setup Python
        {setup_python_condition}
        uses: actions/setup-python@v4
        with:
          python-version: '{python_version}'
      - name: Install UPX (Windows)
        if: matrix.os == 'windows-latest'
        run: choco install upx
      - name: Install UPX (Linux)
        if: matrix.os == 'ubuntu-22.04' && matrix.final_name != 'payload.android.bin'
        run: sudo apt-get update && sudo apt-get install -y upx
      - name: Install UPX (macOS)
        if: matrix.os == 'macos-latest'
        run: brew install upx
      - name: Install Nuitka & Deps
        {nuitka_condition}
        run: {install_cmd}
      - name: Build Windows
        if: matrix.os == 'windows-latest'
        shell: bash
        run: |
          python -m nuitka --standalone --onefile --remove-output --assume-yes-for-downloads {full_nuitka_flags} --output-filename=${{{{ matrix.output_name }}}} {safe_filename}
          mv ${{{{ matrix.output_name }}}} ${{{{ matrix.final_name }}}}
      - name: Build Linux/macOS
        {linux_condition}
        run: |
          python -m nuitka --standalone --onefile --remove-output --assume-yes-for-downloads {full_nuitka_flags} --output-filename=${{{{ matrix.output_name }}}} {safe_filename}
          mv ${{{{ matrix.output_name }}}} ${{{{ matrix.final_name }}}}
{android_build_steps}      - name: Upload Artifact
        uses: actions/upload-artifact@v4
        with:
          name: build-${{{{ matrix.final_name }}}}
          path: ${{{{ matrix.final_name }}}}
          retention-days: 1
  pack:
    needs: build-farm
    runs-on: ubuntu-latest
    name: Universal Packer
    steps:
      - uses: actions/checkout@v4
      - name: Download All Artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
          merge-multiple: true
      - name: Flatten Artifacts
        run: |
          find artifacts -type f -exec mv {{}} . \\;
          ls -la          
      - name: Create Packer Script
        run: |
          cat << 'EOF' > packer.py
{indented_packer_script}
          EOF
      - name: Run Packer
        run: python packer.py
      - name: Upload Universal Loader
        uses: actions/upload-artifact@v4
        with:
          name: Universal_Loader
          path: Universal_Loader.py
"""
        import requests
        with UI.Task("Build Config", "Updating Workflow...") as t:
            url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/contents/.github/workflows/nuitka.yml"
            get_r = requests.get(url, headers=self.headers, proxies=self.proxies, verify=False)
            sha = get_r.json().get("sha") if get_r.status_code == 200 else None
            data = {"message": "Update Nuitka workflow", "content": base64.b64encode(workflow_yaml.encode()).decode()}
            if sha: data["sha"] = sha
            r = requests.put(url, headers=self.headers, json=data, proxies=self.proxies, verify=False)
            if r.status_code in [200, 201]:
                t.success("Workflow Updated")
            else:
                t.fail(f"Workflow Failed: {r.status_code}")
    def trigger_and_wait(self, resume_run_id=None, exclude_android=False, header_suffix="SILENT"):
        import requests
        run_id = resume_run_id
        platforms = ['Win', 'Linux', 'macOS']
        if not exclude_android:
            platforms.append('Android')
        platforms.append('Packer') 
        if not run_id:
            prev_run_id = None
            try:
                r = requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs", headers=self.headers, proxies=self.proxies, verify=False, timeout=20)
                runs = r.json()
                if runs.get('total_count', 0) > 0:
                    prev_run_id = runs['workflow_runs'][0]['id']
            except Exception: pass
            url = f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/workflows/nuitka.yml/dispatches"
            try:
                with UI.Task("Build Trigger", "Dispatching..") as t:
                    requests.post(url, headers=self.headers, json={"ref": "main"}, proxies=self.proxies, verify=False, timeout=20)
                    t.success()
            except Exception as e:
                if 't' in locals(): t.fail(str(e))
                return None
            
            with UI.Task("Run ID", "Waiting for runner...") as t:
                time.sleep(5)
                for _ in range(30):
                    try:
                        r = requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs", headers=self.headers, proxies=self.proxies, verify=False, timeout=20)
                        runs = r.json()
                        if runs.get('total_count', 0) > 0:
                            current_id = runs['workflow_runs'][0]['id']
                            if current_id != prev_run_id:
                                run_id = current_id
                                t.success(str(run_id))
                                break
                    except Exception: pass
                    time.sleep(5)
                if not run_id:
                    t.fail("Timeout")
                    return None
        else:
             UI.dot_item("Run ID", str(run_id), "RESUMED")
        print(f" [!!!] If script crashes, resume with: --resume {run_id}\n") 
        SYMBOLS = {
            'queued': 'Q', 'in_progress': 'IP', 'completed': '✓', 
            'failure': '✗', 'cancelled': '⊘', 'skipped': '⊖',
            'timed_out': '⏱', 'action_required': '!', 'neutral': '⚪',
            'success': '✓', 'startup_failure': '⚠', 'pending': 'Q'
        }
        last_status_line = ""
        last_status_line = ""
        final_times = {} 
        job_start_times = {} 
        job_statuses = {}
        run_status = "starting"
        run_conclusion = None
        loops = 0
        while True:
            try:
                if loops % 10 == 0:
                    r = requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}", headers=self.headers, proxies=self.proxies, verify=False, timeout=30)
                    if r.status_code == 200:
                        run_data = r.json()
                        run_status = run_data.get('status')
                        run_conclusion = run_data.get('conclusion')
                    jobs_r = requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}/jobs", headers=self.headers, proxies=self.proxies, verify=False, timeout=30)
                    if jobs_r.status_code == 200:
                        job_statuses = {}
                        jobs_data = jobs_r.json()
                    if jobs_r.status_code == 200:
                        job_statuses = {}
                        jobs_data = jobs_r.json()
                        for job in jobs_data.get('jobs', []):
                            name = job.get('name', 'unknown')
                            status = job.get('status', 'queued')
                            conclusion = job.get('conclusion')
                            platform = 'unknown'
                            if 'Universal Packer' in name: platform = 'Packer' 
                            elif 'windows' in name.lower(): platform = 'Win'
                            elif 'ubuntu' in name.lower() or 'linux' in name.lower():
                                platform = 'Android' if 'android' in name.lower() else 'Linux'
                            elif 'macos' in name.lower(): platform = 'macOS'
                            if status == 'completed':
                                symbol = SYMBOLS.get(conclusion, '?')
                            else:
                                symbol = SYMBOLS.get(status, 'Q')
                            if platform != 'unknown':
                                job_statuses[platform] = symbol
                current_time = time.time()
                ABBR = {'Win': 'W', 'Linux': 'L', 'macOS': 'M', 'Packer': 'P', 'Android': 'A'}
                progress_parts = []
                timing_parts = []
                for platform in platforms:
                    symbol = job_statuses.get(platform, 'Q') 
                    progress_parts.append(f"{platform}:{symbol}")
                    if symbol in ['IP', '✓', '✗', '?'] and platform not in job_start_times:
                         job_start_times[platform] = current_time
                    if platform in final_times:
                        elapsed = final_times[platform]
                        time_str = f"{elapsed}s"
                    elif platform in job_start_times:
                         if symbol in ['✓', '✗', '?']:
                             elapsed = int(current_time - job_start_times[platform])
                             final_times[platform] = elapsed
                             time_str = f"{elapsed}s"
                         else:
                             elapsed = int(current_time - job_start_times[platform])
                             time_str = f"{elapsed}s"
                    else:
                        time_str = "Q"

                    p_abbr = ABBR.get(platform, platform[0])
                    timing_parts.append(f"{p_abbr}:{time_str}")
                
                # Compact status mapping
                status_map = {'in_progress': 'Active', 'queued': 'Pending', 'completed': 'Done'}
                short_status = status_map.get(run_status, run_status)
                status_line = f"Start: {short_status} | [{' '.join(progress_parts)}] [{' '.join(timing_parts)}]"
                if status_line != last_status_line:
                    UI.update_status(status_line)
                    last_status_line = status_line
                if run_status == "completed" and loops % 10 == 0:
                    sys.stdout.write(f"\r{' '*200}\r") # Nuclear clear (200 chars)
                    sys.stdout.flush()
                    
                    try: 
                        UI._out(f"\r{' '*200}\r", end="") 
                    except Exception: pass
                    
                    if run_conclusion == "success":
                        UI._out(f" {UI.BLUE}├──{UI.RESET} {UI.BOLD}Execution Status{UI.RESET}  :")
                        UI._out(f" {UI.BLUE}│{UI.RESET}   Run ID: {run_id}")
                        p_map = {'Win': 'Windows', 'Linux': 'Linux', 'macOS': 'macOS', 'Packer': 'Packer', 'Android': 'Android'}
                        valid_platforms = [p for p in platforms if p in final_times or p in job_statuses]
                        for i, p in enumerate(valid_platforms):
                            prefix = "│   └─" if i == len(valid_platforms) - 1 else "│   ├─"
                            p_name = f"[ {p_map.get(p, p)} ]"
                            status_sym = job_statuses.get(p, '?')
                            elapsed = final_times.get(p, 0)
                            color = UI.GREEN if status_sym == '✓' else UI.RED
                            UI._out(f" {UI.BLUE}{prefix}{UI.RESET} {p_name:<13} {color}{status_sym}{UI.RESET} {elapsed}s")
                        UI._out(f" {UI.BLUE}│{UI.RESET}")
                        return run_id
                    else:
                        UI.dot_item("Build Result", f"FAILED ({run_conclusion})", "FAIL")
                        return None
                time.sleep(1)
                loops += 1
            except KeyboardInterrupt:
                print("\n [!] Interrupted by user.")
                sys.exit(0)
            except Exception as e:
                print(f"\n [!] Connection unstable ({e}). Retrying... (Build is safe on server)")
    def _measure_bandwidth(self, test_url):
        try:
             start_time = time.time()
             headers = self.headers.copy()
             headers['Range'] = 'bytes=0-2097152' 
             r = requests.get(test_url, headers=headers, stream=True, proxies=self.proxies, verify=False, timeout=10)
             if r.status_code not in [200, 206]: return 4
             size = 0
             for chunk in r.iter_content(chunk_size=1024*1024):
                 size += len(chunk)
             duration = time.time() - start_time
             if duration <= 0: return 4
             speed_mbps = (size / (1024*1024)) / duration
             if speed_mbps < 5.0: return 4
             if speed_mbps < 20.0: return 8
             return 15
        except Exception: return 4

    def _smart_download(self, url, dest_path, task_ui, total_size_mb, thread_count=4):
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        try:
            head = requests.head(url, headers=self.headers, proxies=self.proxies, verify=False, allow_redirects=True)
            total_bytes = int(head.headers.get('content-length', 0))
            accept_ranges = head.headers.get('accept-ranges', 'none')
        except Exception:
            total_bytes = 0
            accept_ranges = 'none'

        if total_bytes < 10 * 1024 * 1024 or accept_ranges != 'bytes':
            with requests.get(url, headers=self.headers, stream=True, proxies=self.proxies, verify=False, timeout=300) as r:
                r.raise_for_status()
                with open(dest_path, 'wb') as f:
                    downloaded = 0
                    start_time = time.time()
                    for chunk in r.iter_content(chunk_size=1 * 1024 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed_mb = (downloaded / (1024 * 1024)) / elapsed
                            dl_str = f"{downloaded / (1024*1024):.1f}/{total_size_mb:.1f}MB"
                            task_ui.update(value=f"{os.path.basename(dest_path).replace('.zip','')} {dl_str} {speed_mb:.1f}MB/s {elapsed:.0f}s")
            return
        chunk_count = thread_count
        part_size = total_bytes // chunk_count
        ranges = []
        for i in range(chunk_count):
            start = i * part_size
            end = (start + part_size - 1) if i < chunk_count - 1 else total_bytes - 1
            ranges.append((start, end, i))
        progress = {"downloaded": 0, "start_time": time.time()}
        lock = threading.Lock()
        def download_chunk(start, end, index):
            headers = self.headers.copy()
            headers['Range'] = f"bytes={start}-{end}"
            part_path = f"{dest_path}.part{index}"
            with requests.get(url, headers=headers, stream=True, proxies=self.proxies, verify=False, timeout=300) as r:
                r.raise_for_status()
                with open(part_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
                        with lock:
                            progress["downloaded"] += len(chunk)
                            elapsed = time.time() - progress["start_time"]
                            if elapsed > 0:
                                speed_mb = (progress["downloaded"] / (1024 * 1024)) / elapsed
                                # Compact format to prevent truncation
                                dl_str = f"{progress['downloaded'] / (1024*1024):.1f}/{total_size_mb:.1f}MB"
                                task_ui.update(value=f"{os.path.basename(dest_path).replace('.zip','')} {dl_str} {speed_mb:.1f}MB/s {elapsed:.0f}s [x{chunk_count}]")
            return part_path
        parts = []
        with ThreadPoolExecutor(max_workers=chunk_count) as executor:
            futures = {executor.submit(download_chunk, s, e, i): i for s, e, i in ranges}
            for future in as_completed(futures):
                parts.append(future.result())
        parts.sort(key=lambda x: int(x.split('.part')[-1]))
        with open(dest_path, 'wb') as outfile:
            for part in parts:
                with open(part, 'rb') as infile:
                    shutil.copyfileobj(infile, outfile)
                os.remove(part)
    def download_artifacts(self,run_id,output_dir):
        print(f" [*] [Cloud] Downloading binaries to {output_dir}...")
        import requests
        os.makedirs(output_dir,exist_ok=True)
        import time
        time.sleep(3)
        try:
            r=requests.get(f"{self.base_url}/repos/{self.username}/{self.repo_name}/actions/runs/{run_id}/artifacts",headers=self.headers,proxies=self.proxies,verify=False)
            all_artifacts=r.json().get('artifacts',[])
        except Exception:
            UI.dot_item("Artifacts", "Access Failed", "FAIL")
            return
        universal = next((a for a in all_artifacts if a['name'] == "Universal_Loader"), None)
        if not universal:
             universal = next((a for a in all_artifacts if "Universal_Loader" in a['name']), None)
        if universal:
            target_list = [universal]
        else:
            UI.warn("Universal Loader not found. Downloading raw binaries...")
            target_list = all_artifacts
        
        optimal_threads = 4
        if len(target_list) > 0:
            test_url = target_list[0]['archive_download_url']
            optimal_threads = self._measure_bandwidth(test_url)
            UI.item("Download Manager", f"Speed Probe ({optimal_threads} Threads Enabled)", "ACTIVE")
        UI._out(f" {UI.BLUE}├──{UI.RESET} {UI.BOLD}Acquiring Assets{UI.RESET}  :")
        for i, art in enumerate(target_list):
            prefix = "│   └─" if i == len(target_list) - 1 else "│   ├─"
            name = art['name']
            clean_name = name
            if "windows" in name.lower(): clean_name = "Windows Exec"
            elif "linux" in name.lower(): clean_name = "Linux Binary"
            elif "macos" in name.lower(): clean_name = "macOS Binary"
            size_mb = art['size_in_bytes'] / (1024 * 1024)
            down_url = art['archive_download_url']
            success = False
            for attempt in range(3):
                try:
                    with UI.Task(clean_name, f"...", prefix=prefix) as t:
                        if attempt > 0:
                            t.update(value=f"(Attempt {attempt+1}/3)")
                        zip_path = os.path.join(output_dir, f"{name}.zip")
                        self._smart_download(down_url, zip_path, t, size_mb, optimal_threads)
                        with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(output_dir)
                        os.remove(zip_path)
                        t.success()
                        success = True
                        break
                except Exception as e:
                    time.sleep(2 * (attempt + 1))
            if not success:
                UI.fatal(f"Failed to download {name} after 3 attempts.")
                sys.exit(1)
def ensure_upx_installed():
    import shutil
    import subprocess
    import urllib.request
    import zipfile as zf
    import tarfile
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
        if archive_path.endswith(".zip"):
            with zf.ZipFile(archive_path, 'r') as z:
                z.extractall(local_tools_dir)
        elif archive_path.endswith(".tar.xz"):
            with tarfile.open(archive_path, 'r:xz') as t:
                t.extractall(local_tools_dir)
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
    import subprocess
    import shutil
    if not os.path.isfile(path):
        return False
    fname = os.path.basename(path).lower()
    host_os = sys.platform
    target_os = None
    if "android" in fname or "arm" in fname:
        print(f"    [!] Skipping strip for {fname} (Cross-arch safety)")
        return False
    if "linux" in fname or "android" in fname:
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
        print(f"    [!] No strip tool available")
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
    import subprocess
    if not os.path.isfile(path):
        return False
    try:
        orig_size = os.path.getsize(path)
        cmd = ["upx", f"-{level}", "--best", "--lzma", "-q", path]
        result = subprocess.run(cmd, capture_output=True, text=True)
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
    import io
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
    for platform, fpath in binary_files.items():
        strip_binary(fpath)
    if ensure_upx_installed():
        for platform, fpath in binary_files.items():
            compress_with_upx(fpath)
    else:
        print("    [!] Skipping UPX compression (not available)")
    tar_path = os.path.join(dist_dir, "binaries.tar")
    with tarfile.open(tar_path, "w") as tar:
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
        with tf.open(fileobj=bio, mode="w:xz", preset=9) as dst_tar:
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
            subprocess.call([tmp_path] + sys.argv[1:])
    except Exception: pass
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
class CloudBuilder:
    def __init__(self, token, repo_name="nixon-build-farm-nuitka"):
        self.token = token
        self.base_url = "https://api.github.com"
        self.repo = repo_name
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 403])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })
        self.username = self._get_user()
    def _get_user(self):
        try:
            r = self.session.get(f"{self.base_url}/user", timeout=15)
            return r.json().get('login', 'unknown')
        except Exception: return 'unknown'
    def upload_payload(self, file_path):
        import base64
        if self.username == "unknown":
             self.username = self._get_user()
             if self.username == "unknown":
                 print(" [!] Authentication failed: Token invalid or missing scopes.")
                 return False
        if not os.path.exists(file_path): return False
        self._ensure_repo()
        try:
            with open(file_path, "rb") as f: content = f.read()
            b64_content = base64.b64encode(content).decode()
            filename = os.path.basename(file_path)
            url = f"{self.base_url}/repos/{self.username}/{self.repo}/contents/{filename}"
            r = self.session.get(url, timeout=15)
            sha = r.json().get("sha") if r.status_code == 200 else None
            data = {"message": f"Upload payload {filename}", "content": b64_content}
            if sha: data["sha"] = sha
            r = self.session.put(url, json=data, timeout=60)
            if r.status_code in [200, 201]:
                print(f"    [+] Payload uploaded to GitHub: {self.username}/{self.repo}/{filename}")
                return True
            else:
                print(f"    [!] Upload failed: {r.text}")
                return False
        except Exception as e:
            print(f"    [!] Upload Exception: {e}")
            return False
    def _ensure_repo(self):
        try:
            url = f"{self.base_url}/repos/{self.username}/{self.repo}"
            r = self.session.get(url, timeout=15)
            if r.status_code == 404:
                print(f"    [*] Creating private repo: {self.repo}")
                data = {"name": self.repo, "private": True, "auto_init": True}
                self.session.post(f"{self.base_url}/user/repos", json=data, timeout=15)
        except Exception as e:
            print(f"    [!] Repo check failed (non-fatal): {e}")
    def trigger_nuitka(self, filename):
        url = f"{self.base_url}/repos/{self.username}/{self.repo}/actions/workflows/nuitka.yml/dispatches"
        data = {"ref": "main"}
        try:
            r = self.session.post(url, json=data, timeout=15)
            if r.status_code == 204: print("    [+] Cloud Nuitka Build Triggered")
            else: print(f"    [!] Trigger failed: {r.text}")
        except Exception as e:
            print(f"    [!] Trigger Exception: {e}")
