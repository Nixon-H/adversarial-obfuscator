"""Find which import or phase kills the process on this platform.

An ACCESS_VIOLATION cannot be caught, so the only way to locate it is to print
and flush before each step: the last line in the log names the culprit.

Runs on any OS/Python; useful wherever the builder crashes natively.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def say(text):
    print(text, flush=True)


def try_import(name):
    say("import %s ..." % name)
    try:
        __import__(name)
    except Exception as exc:  # noqa: BLE001 - reporting is the point
        say("  -> raised %s: %s" % (type(exc).__name__, exc))
        return False
    say("  -> ok")
    return True


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    say("platform=%s python=%s" % (sys.platform, sys.version.split()[0]))
    say("executable=%s" % sys.executable)

    for name in ("hashlib", "zlib", "lzma", "json", "ast", "ctypes", "ssl", "secrets"):
        try_import(name)

    say("--- third-party")
    for name in ("cryptography", "cryptography.hazmat.primitives.ciphers",
                 "cryptography.hazmat.primitives.asymmetric.rsa"):
        try_import(name)

    say("--- project")
    sys.path.insert(0, ROOT)
    for name in ("obfuscator", "obfuscator.core.sources",
                 "obfuscator.core.transforms", "obfuscator.core.pipeline"):
        try_import(name)

    say("--- builder phases in a child process (a crash here is the AV)")
    launcher = (
        "import sys; sys.path.insert(0, %r); "
        "print('child: imported', flush=True); "
        "from obfuscator.core import sources as s; "
        "print('child: sources ok', flush=True); "
        "out, _ = s.apply_ast_mutation('def f(x):\\n    return x+1\\nprint(f(2))\\n', {'opt_level': 5}); "
        "compile(out, '<a>', 'exec'); "
        "print('child: mutation ok', len(out), flush=True)"
        % (ROOT,)
    )
    p = subprocess.run([sys.executable, "-c", launcher], cwd=ROOT,
                       capture_output=True, timeout=900)
    say("child rc=%d" % p.returncode)
    say("child stdout:\n" + p.stdout.decode("utf-8", "replace"))
    say("child stderr:\n" + p.stderr.decode("utf-8", "replace")[-2000:])
    if p.returncode != 0:
        say("CHILD CRASHED -- the last line above names the step")
    return 0


if __name__ == "__main__":
    sys.exit(main())
