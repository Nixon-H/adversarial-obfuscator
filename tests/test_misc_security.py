"""Regression tests for the miscellaneous adversarial-audit shard."""

import importlib.util
import sys
import types
from pathlib import Path

import adversarial_loop


ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ai_obfuscator = _load_module("misc_ai_obfuscator", ROOT / "ai-obfuscator.py")
inventory_generator = _load_module(
    "misc_inventory_generator",
    ROOT / "audit" / "2026-11-25-full" / "generate_current_inventory.py",
)
cli_surface_verifier = _load_module(
    "misc_cli_surface_verifier",
    ROOT / "audit" / "2026-11-25-full" / "verify_cli_surface.py",
)


def test_inventory_python_symbols_include_except_handler_nested_defs():
    source = """\
try:
    import httpx
except ImportError:
    class _MissingHttpx:
        def __getattr__(self, name):
            raise RuntimeError(name)
"""
    probe_path = ROOT / "synthetic_inventory_probe.py"
    symbols, _flags, _imports = inventory_generator.python_symbols(probe_path, source)
    qualified = {entry["qualified"] for entry in symbols}
    assert qualified == {"_MissingHttpx", "_MissingHttpx.__getattr__"}


def test_inventory_native_symbols_exclude_control_flow_keywords():
    source = """\
__attribute__((visibility("default"))) int real_function(int x) {
    if (x) {
        return x;
    }
    while (x) {
        x--;
    }
#if defined(USE_EXTRA)
    {
        x++;
    }
#endif
}
"""
    symbols = inventory_generator.native_symbols(ROOT / "native_probe.c", source)
    assert [entry["name"] for entry in symbols] == ["real_function"]


def test_cli_subcommand_discovery_ignores_option_choice_groups():
    help_text = """\
usage: probe [-h] [--mode {fast,slow}] {run,build} ...

positional arguments:
  {run,build}

options:
  -h, --help          show this help message and exit
  --mode {fast,slow}
"""
    assert cli_surface_verifier.discover_subcommands("", help_text) == ["run", "build"]


def test_offline_fallback_dry_run_prints_without_writing(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "input.py"
    output_path = tmp_path / "output.py"
    input_path.write_text("λ = 1\n", encoding="utf-8")
    monkeypatch.setattr(ai_obfuscator, "TRANSFORMERS_AVAILABLE", False)
    monkeypatch.setattr(sys, "argv", [
        "ai-obfuscator.py", "-f", str(input_path),
        "-o", str(output_path), "--dry-run",
    ])

    ai_obfuscator.main()

    assert not output_path.exists()
    assert "var01 = 1" in capsys.readouterr().out


def test_source_encoding_cookie_is_honored_instead_of_dropping_bytes(
        tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "latin_input.py"
    input_path.write_bytes(
        '# -*- coding: cp1252 -*-\nresult = "é"\n'.encode("cp1252"))
    monkeypatch.setattr(ai_obfuscator, "TRANSFORMERS_AVAILABLE", False)
    monkeypatch.setattr(sys, "argv", [
        "ai-obfuscator.py", "-f", str(input_path), "--dry-run",
    ])

    ai_obfuscator.main()

    assert "é" in capsys.readouterr().out


def test_hub_model_loading_cannot_download_when_download_flag_is_false(monkeypatch):
    class TokenizerLoader:
        calls = []

        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            cls.calls.append((args, kwargs))
            return object()

    class ModelLoader:
        calls = []

        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            cls.calls.append((args, kwargs))
            return object()

    monkeypatch.setattr(ai_obfuscator, "TRANSFORMERS_AVAILABLE", True)
    monkeypatch.setattr(ai_obfuscator, "AutoTokenizer", TokenizerLoader, raising=False)
    monkeypatch.setattr(ai_obfuscator, "AutoModelForCausalLM", ModelLoader, raising=False)

    loaded = ai_obfuscator._load_llm(model_name="fake-model", download_if_missing=False)

    assert loaded is not None
    assert ModelLoader.calls[0][1]["local_files_only"] is True


class _FakeTensor:
    def __init__(self, values):
        self.values = list(values)
        self.shape = (1, len(self.values))

    def __getitem__(self, index):
        if isinstance(index, slice):
            return _FakeTensor(self.values[index])
        return self.values[index]


class _NoGrad:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_llm_generation_decodes_only_new_tokens_not_the_prompt(monkeypatch):
    decoded_ids = []

    class Tokenizer:
        eos_token_id = 0

        def __call__(self, prompt, return_tensors):
            assert return_tensors == "pt"
            return {"input_ids": _FakeTensor([1, 2, 3])}

        def decode(self, ids, skip_special_tokens):
            assert skip_special_tokens is True
            decoded_ids.extend(ids.values)
            return "print('deobfuscated')"

    class Model:
        def eval(self):
            return self

        def generate(self, *_args, **_kwargs):
            return [_FakeTensor([1, 2, 3, 4, 5])]

    fake_torch = types.SimpleNamespace(
        no_grad=lambda: _NoGrad(),
        cuda=types.SimpleNamespace(is_available=lambda: False),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    result = ai_obfuscator._generate_with_llm(Tokenizer(), Model(), "prompt")

    assert result == "print('deobfuscated')"
    assert decoded_ids == [4, 5]


def _execute_rewritten(source):
    rewritten = ai_obfuscator.deobfuscate_offline_ascii(source)
    namespace = {}
    exec(compile(rewritten, "<renamed>", "exec"), namespace)
    return rewritten, namespace["result"]


def test_unknown_method_decorator_does_not_turn_duck_receiver_into_class_instance():
    source = """\
import types
def as_static(fn):
    return staticmethod(fn)
class 类:
    属性 = 1
    @as_static
    def 方法(self):
        return self.属性
外部 = types.SimpleNamespace()
setattr(外部, "属性", 9)
result = 类().方法(外部)
"""
    _rewritten, result = _execute_rewritten(source)
    assert result == 9


def test_unbound_class_method_call_with_duck_receiver_preserves_attribute():
    source = """\
import types
class 类:
    属性 = 1
    def 方法(self):
        return self.属性
外部 = types.SimpleNamespace()
setattr(外部, "属性", 9)
result = 类.方法(外部)
"""
    _rewritten, result = _execute_rewritten(source)
    assert result == 9


def test_constant_getattr_name_tracks_renamed_internal_attribute():
    source = """\
class 类:
    属性 = 5
对象 = 类()
result = getattr(对象, "属性")
"""
    rewritten, result = _execute_rewritten(source)
    assert result == 5
    assert "getattr" in rewritten


def test_super_keyword_call_resolves_after_the_overriding_subclass():
    source = """\
class 基类:
    def 方法(self, 参数):
        return 参数 + 1
class 子类(基类):
    def 方法(self, 其他):
        return super().方法(参数=其他)
result = 子类().方法(4)
"""
    _rewritten, result = _execute_rewritten(source)
    assert result == 5


def test_dataflow_mba_knobs_patch_the_rng_call_sites_that_exist(
        tmp_path, monkeypatch):
    transforms = tmp_path / "transforms.py"
    dataflow = tmp_path / "dataflow.py"
    decoy_apis = tmp_path / "decoy_apis.py"
    attention_poison = tmp_path / "attention_poison.py"
    reasoning_traps = tmp_path / "reasoning_traps.py"
    for path in (transforms, decoy_apis, attention_poison, reasoning_traps):
        path.write_text("", encoding="utf-8")
    dataflow.write_text("""\
depth=rng.randint(1, 2)
rng.randint(1000, 9999999)
rng.randint(1, 9999999)
rng.randint(100, 9999999)
rng.randint(2, min(9999, 99999))
def __init__(self, seed: bytes, num_registers: int = 16):
""", encoding="utf-8")

    monkeypatch.setattr(adversarial_loop, "TRANSFORMS", transforms)
    monkeypatch.setattr(adversarial_loop, "DATAFLOW", dataflow)
    monkeypatch.setattr(adversarial_loop, "DECOY_APIS", decoy_apis)
    monkeypatch.setattr(adversarial_loop, "ATTN_POISON", attention_poison)
    monkeypatch.setattr(adversarial_loop, "REASON_TRAPS", reasoning_traps)
    monkeypatch.setattr(adversarial_loop, "SOURCE_FILES", [
        transforms, dataflow, decoy_apis, attention_poison, reasoning_traps,
    ])
    monkeypatch.setattr(adversarial_loop, "BACKUP_DIR", tmp_path / "backups")

    knobs = adversarial_loop.KnobState()
    knobs.mba_dataflow_depth = 6
    knobs.mba_dataflow_K_max = 123456789
    adversarial_loop.apply_improvements(knobs)

    patched = dataflow.read_text(encoding="utf-8")
    assert "depth=rng.randint(3, 6)" in patched
    assert "rng.randint(1000, 123456789)" in patched
    assert "rng.randint(1, 123456789)" in patched
    assert "rng.randint(100, 123456789)" in patched
    assert "rng.randint(2, min(9999, 1234567))" in patched
