"""Catalogue every ladder flag and decide how to exercise it in isolation.

Reads scripts/build.py's argparse by AST (importing it would run the builder) and
emits JSON: one entry per flag with the argv that isolates it, or a reason it
cannot be isolated in CI.

The point is coverage that can be counted. "Some flags are tested" is not a
number; 274 flags, each with a verdict, is.
"""
import ast
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, "scripts", "build.py")

# Flags that cannot run in a sandbox: they need the network, credentials, a GPU,
# an external service, or they re-invoke the builder recursively. Kept explicit
# and few -- the default is "isolate it".
# Flags the harness itself owns: it must pass --payload, --output and the
# --skip-* switches to get a build at all, so isolating them would test a
# conflict of our own making rather than the product.
HARNESS_OWNED = {
    "--payload", "--output", "--opt-level", "--force-output",
    "--skip-irgen", "--skip-llvmgen", "--skip-encrypt", "--skip-relay",
    "--skip-extras", "--skip-debug", "--help", "--version",
}

NEEDS_EXTERNAL = {
    "--net-url": "needs a deployed server", "--bind": "needs a real bind host",
    "--webhook": "needs a receiver", "--tls-ca-bundle": "needs a CA bundle file",
    "--lock-hwid": "binds to this machine's hardware id",
    "--benchmark-model": "needs a model", "--adversarial-bench": "needs a benchmark model",
    "--attack-corpus": "needs a corpus", "--attack-store": "needs an external store",
    "--llm-api-key": "needs a credential", "--gh-token": "needs a credential",
    "--cf-token": "needs a credential", "--cf-account": "needs a credential",
    "--resume": "needs a previous run", "--watch": "never exits",
    # External tooling this harness does not install or drive.
    "--cross": "needs a cross-compilation toolchain",
    "--self-audit": "needs the external audit tooling",
    "--multi-tool": "needs several external analysis tools",
    "--independent-audit": "needs an external auditor",
    "--trust-boundary": "needs a declared boundary configuration",
    "--sgx": "needs SGX hardware",
    "--tee": "needs a trusted execution environment",
}


def _literal(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def collect():
    tree = ast.parse(open(BUILD, encoding="utf-8").read())
    flags = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument"):
            continue
        names = [a.value for a in node.args
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if not names:
            continue
        kw = {k.arg: k.value for k in node.keywords}
        action = _literal(kw["action"]) if "action" in kw else None
        value_type = getattr(kw.get("type"), "id", None)
        choices = _literal(kw["choices"]) if "choices" in kw else None
        nargs = _literal(kw["nargs"]) if "nargs" in kw else None
        for name in names:
            if not name.startswith("--"):
                continue
            flags[name] = {"action": action, "type": value_type,
                           "choices": list(choices) if isinstance(choices, (list, tuple)) else None,
                           "nargs": nargs}
    return flags


def sample_value(name, meta):
    """A value that is safe to pass, or None if none can be guessed."""
    if meta["choices"]:
        return str(meta["choices"][0])
    t = meta["type"]
    if t in ("int",):
        return "2"
    if t in ("float",):
        return "1.5"
    low = name.lower()
    if "dir" in low or "path" in low or "output" in low:
        return None          # needs a real path; caller supplies one
    return "2"


def probe(flag):
    """Ask argparse itself whether this flag needs a value.

    The AST heuristic misread several flags (--driver-check was classified as
    taking a value and the build then failed with "unrecognized arguments: 2").
    The parser is built inside main() so it cannot be imported; running it with a
    bogus payload reaches argument parsing first and exits in milliseconds.
    """
    import subprocess
    try:
        r = subprocess.run(
            [sys.executable, BUILD, "--payload", "/nonexistent/probe.py", flag],
            capture_output=True, timeout=30)
    except Exception:
        return None
    err = (r.stderr or b"").decode("utf-8", "replace")
    if "expected one argument" in err:
        return "value"
    if "invalid choice" in err:
        return "value"
    return "boolean"


def catalogue():
    entries = []
    for name, meta in sorted(collect().items()):
        bool_flag = meta["action"] in ("store_true", "store_false", "count")
        if name in HARNESS_OWNED:
            entries.append({"flag": name, "kind": "excluded",
                            "why": "owned by the harness (payload/output/skip switches)"})
            continue
        if name in NEEDS_EXTERNAL:
            entries.append({"flag": name, "kind": "excluded", "why": NEEDS_EXTERNAL[name]})
            continue
        if bool_flag:
            # Confirm with the real parser: a wrong guess here shows up as a
            # build failure that looks like a product bug.
            verdict = probe(name)
            if verdict == "value":
                value = sample_value(name, meta)
                if value is None:
                    entries.append({"flag": name, "kind": "excluded",
                                    "why": "needs a filesystem path"})
                    continue
                entries.append({"flag": name, "kind": "value", "argv": [name, value]})
                continue
            entries.append({"flag": name, "kind": "boolean", "argv": [name]})
            continue
        if meta["nargs"] in ("*", "+"):
            entries.append({"flag": name, "kind": "excluded", "why": "variadic; no safe sample"})
            continue
        value = sample_value(name, meta)
        if value is None:
            entries.append({"flag": name, "kind": "excluded", "why": "needs a filesystem path"})
            continue
        entries.append({"flag": name, "kind": "boolean" if False else "value",
                        "argv": [name, value]})
    return entries


def main():
    entries = catalogue()
    if "--json" in sys.argv:
        print(json.dumps(entries, indent=1))
        return 0
    kinds = {}
    for e in entries:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print("flags catalogued:", len(entries))
    for k, v in sorted(kinds.items()):
        print("  %-10s %d" % (k, v))
    for e in entries[:3]:
        print("  example:", e["flag"], e.get("argv", e.get("why")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
