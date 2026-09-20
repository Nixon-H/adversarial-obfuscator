import re
from typing import Any

NIXON_TYPE_MAP = {
    "i1": "i1",
    "i8": "i8",
    "i16": "i16",
    "i32": "i32",
    "i64": "i64",
    "ptr": "ptr",
    "void": "void",
    "double": "double",
    "float": "float",
}

BINARY_OPS = {
    "add", "sub", "mul", "udiv", "sdiv", "urem", "srem",
    "and", "or", "xor", "shl", "lshr", "ashr",
}

ICMP_PREDICATES = {
    "eq": "eq", "ne": "ne",
    "ugt": "ugt", "uge": "uge", "ult": "ult", "ule": "ule",
    "sgt": "sgt", "sge": "sge", "slt": "slt", "sle": "sle",
}

CONVERSION_OPS = {"zext", "sext", "trunc", "ptrtoint", "inttoptr", "bitcast",
                  "fptoui", "uitofp", "sitofp", "fptosi", "fpext", "fptrunc"}

NIXON_TYPE_PATTERN = r'(?:i[1-9]\d*|ptr|void|double|float)'


def _parse_type(s: str) -> str:
    s = s.strip().rstrip(",").strip()
    if s.startswith("["):
        m = re.match(r'\[(\d+)\s+x\s+(' + NIXON_TYPE_PATTERN + r')\]', s)
        if m:
            return f"[{m.group(1)} x {_parse_type(m.group(2))}]"
    if s.startswith("struct("):
        inner = s[7:].rstrip(")").strip()
        parts = []
        depth = 0
        curr = ""
        for ch in inner:
            if ch == "(":
                depth += 1
                curr += ch
            elif ch == ")":
                depth -= 1
                curr += ch
            elif ch == "," and depth == 0:
                parts.append(curr.strip())
                curr = ""
            else:
                curr += ch
        if curr.strip():
            parts.append(curr.strip())
        parsed = ", ".join(_parse_type(p) for p in parts)
        return f"{{{parsed}}}"
    if s.endswith("*"):
        return "ptr"
    if s in NIXON_TYPE_MAP:
        return NIXON_TYPE_MAP[s]
    return s


def _value_ref(s: str) -> str:
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return s
    known = {"true", "false", "null", "zeroinitializer", "undef", "poison"}
    if s in known:
        return s
    return s


class NixonIRParser:
    def __init__(self, text: str):
        self.text = text
        self.lines = []
        self.pos = 0
        self.string_literals: dict[str, str] = {}
        self._string_counter = 0

    def _remove_comments(self, line: str) -> str:
        idx = line.find(";")
        if idx >= 0:
            line = line[:idx]
        return line.strip()

    def _next_line(self) -> str | None:
        while self.pos < len(self.lines):
            line = self.lines[self.pos]
            self.pos += 1
            stripped = self._remove_comments(line)
            if stripped:
                return stripped
        return None

    def _peek_line(self) -> str | None:
        saved = self.pos
        result = self._next_line()
        self.pos = saved
        return result

    def parse(self) -> dict:
        self.lines = self.text.split("\n")
        self.pos = 0
        module = {"name": "nixon_module", "globals": [], "functions": [], "declares": []}

        first = self._next_line()
        if first is None:
            return module
        m = re.match(r'module\s*@?(\S+)', first)
        if not m:
            raise SyntaxError(f"Expected 'module <name>' but got: {first}")
        module["name"] = m.group(1)

        # Module body ends at end of input (no module-level braces in this IR format)
        while self.pos < len(self.lines):
            line = self._next_line()
            if line is None:
                break
            if line == "" or line == "}":
                continue
            if line.startswith("global"):
                self._parse_global(line, module)
            elif line.startswith("declare"):
                self._parse_declare(line, module)
            elif line.startswith("func"):
                self._parse_function(line, module)
            elif line.startswith("@") or line.startswith("  @"):
                # continuation lines within a function — skip, handled by _parse_function
                continue
            else:
                raise SyntaxError(f"Unexpected top-level statement: {line}")

        return module

    def _parse_global(self, line: str, module: dict):
        m = re.match(r'global\s+(\S+)\s+(@\S+)\s*=\s*(.*)', line)
        if not m:
            raise SyntaxError(f"Invalid global: {line}")
        gtype = _parse_type(m.group(1))
        gname = m.group(2)
        gval = m.group(3).strip().rstrip(";")
        module["globals"].append({"name": gname, "type": gtype, "init": gval})

    def _parse_declare(self, line: str, module: dict):
        m = re.match(r'declare\s+(\S+)\s+(@\S+)\s*(?:\((.*)\))?', line)
        if not m:
            raise SyntaxError(f"Invalid declare: {line}")
        ret_type = _parse_type(m.group(1))
        name = m.group(2)
        params_str = m.group(3).strip() if m.group(3) else ""
        params = []
        if params_str:
            for p in params_str.split(","):
                p = p.strip()
                if p:
                    pt = _parse_type(p.split()[-1] if " " in p else p)
                    params.append(pt)
        module["declares"].append({"name": name, "return_type": ret_type, "params": params})

    def _parse_function(self, line: str, module: dict):
        m = re.match(r'func\s+(@\S+)\s*\((.*)\)(?:\s*->\s*(\S+))?\s*\{', line)
        if not m:
            raise SyntaxError(f"Invalid function: {line}")
        name = m.group(1)
        params_str = m.group(2).strip()
        ret_type = _parse_type(m.group(3)) if m.group(3) else "void"
        params = []
        if params_str:
            for p in params_str.split(","):
                p = p.strip()
                if p:
                    # IR format: %name: type
                    pm = re.match(r'(%\S+)\s*:\s*(\S+)', p)
                    if pm:
                        params.append({"type": _parse_type(pm.group(2)), "name": pm.group(1)})
                    else:
                        parts = p.split()
                        if len(parts) == 2:
                            params.append({"type": _parse_type(parts[0]), "name": parts[1]})
                        elif len(parts) == 1:
                            params.append({"type": _parse_type(parts[0]), "name": ""})
                        else:
                            raise SyntaxError(f"Invalid param: {p}")

        func = {"name": name, "return_type": ret_type, "params": params, "blocks": []}
        var_types: dict[str, str] = {}
        for p in params:
            pname = p.get("name", "")
            if pname:
                var_types[pname] = p["type"]
        while True:
            line = self._next_line()
            if line is None:
                raise SyntaxError(f"Unterminated function {name}")
            if line == "}":
                module["functions"].append(func)
                return
            block = self._parse_block(line, var_types)
            if block:
                func["blocks"].append(block)

    def _parse_block(self, first_line: str, var_types: dict | None = None) -> dict | None:
        m = re.match(r'^([a-zA-Z_$][a-zA-Z0-9_.$]*):\s*(.*)', first_line)
        if not m:
            return None
        label = m.group(1)
        rest = m.group(2).strip()
        if var_types is None:
            var_types = {}
        block = {"label": label, "instructions": []}
        if rest:
            instr = self._parse_instruction(rest, var_types)
            if instr:
                block["instructions"].append(instr)
        while True:
            peek = self._peek_line()
            if peek is None or peek == "}":
                break
            if re.match(r'^[a-zA-Z_$][a-zA-Z0-9_.$]*:', peek):
                break
            line = self._next_line()
            if line is None:
                break
            stripped = self._remove_comments(line)
            if not stripped:
                continue
            instr = self._parse_instruction(stripped, var_types)
            if instr:
                block["instructions"].append(instr)
        return block

    def _resolve_call_arg(self, arg: str, var_types: dict) -> str:
        arg = arg.strip()
        if arg.startswith("%") or arg.startswith("@"):
            t = var_types.get(arg)
            if t:
                return f"{t} {arg}"
            return f"i32 {arg}"
        if arg.startswith('"') and arg.endswith('"'):
            s = arg[1:-1]
            if s not in self.string_literals:
                name = f"@.str.{self._string_counter}"
                self._string_counter += 1
                self.string_literals[s] = name
            return f"ptr {self.string_literals[s]}"
        if arg in ("true", "false"):
            return f"i1 {arg}"
        if arg in ("null", "zeroinitializer", "undef", "poison"):
            return f"ptr {arg}"
        if re.match(r'^-?\d+$', arg):
            return f"i32 {arg}"
        if re.match(r'^-?\d+\.\d*$', arg) or re.match(r'^-?\d*\.\d+$', arg):
            return f"double {arg}"
        return f"i32 {arg}"

    def _parse_instruction(self, line: str, var_types: dict | None = None) -> dict | None:
        if var_types is None:
            var_types = {}
        if not line:
            return None
        result = None
        eq_idx = line.find(" = ")
        if eq_idx >= 0:
            possible = line[:eq_idx].strip()
            if possible.startswith("%") or possible.startswith("@"):
                result = possible
                line = line[eq_idx + 3:].strip()
        parts = line.split()
        if not parts:
            return None
        opcode = parts[0]

        if opcode == "ret":
            if len(parts) == 1 or parts[1] == "void":
                return {"result": result, "opcode": "ret", "void": True}
            vtype = _parse_type(parts[1])
            val = parts[2] if len(parts) > 2 else ""
            return {"result": result, "opcode": "ret", "void": False, "type": vtype, "value": val}

        if opcode == "br":
            if len(parts) == 2:
                return {"result": result, "opcode": "br", "uncond": parts[1].lstrip("%")}
            if len(parts) >= 5:
                condtype = parts[1]
                condval = parts[2].rstrip(",")
                true_label = parts[4].lstrip("%").rstrip(",")
                false_label = parts[6].lstrip("%").rstrip(",") if len(parts) > 6 else None
                return {"result": result, "opcode": "br",
                        "cond_type": condtype, "cond": condval,
                        "true_label": true_label, "false_label": false_label}

        if opcode in BINARY_OPS:
            vtype = _parse_type(parts[1])
            lhs = parts[2].rstrip(",")
            rhs = parts[3].rstrip(",") if len(parts) > 3 else ""
            if result:
                var_types[result] = vtype
            return {"result": result, "opcode": opcode, "type": vtype,
                    "operands": [lhs, rhs]}

        if opcode == "eq":
            vtype = _parse_type(parts[1])
            lhs = parts[2].rstrip(",")
            rhs = parts[3].rstrip(",") if len(parts) > 3 else ""
            if result:
                var_types[result] = "i1"
            return {"result": result, "opcode": "icmp", "predicate": "eq",
                    "type": vtype, "operands": [lhs, rhs]}

        if opcode == "mod":
            vtype = _parse_type(parts[1])
            lhs = parts[2].rstrip(",")
            rhs = parts[3].rstrip(",") if len(parts) > 3 else ""
            if result:
                var_types[result] = vtype
            return {"result": result, "opcode": "srem", "type": vtype,
                    "operands": [lhs, rhs]}

        if opcode == "icmp":
            pred = parts[1]
            if pred not in ICMP_PREDICATES:
                raise SyntaxError(f"Unknown icmp pred: {pred}")
            vtype = _parse_type(parts[2])
            lhs = parts[3].rstrip(",")
            rhs = parts[4] if len(parts) > 4 else ""
            if result:
                var_types[result] = "i1"
            return {"result": result, "opcode": "icmp", "predicate": ICMP_PREDICATES[pred],
                    "type": vtype, "operands": [lhs, rhs]}

        if opcode == "alloca":
            vtype = _parse_type(parts[1])
            align = None
            for i, p in enumerate(parts):
                if p == "align" and i + 1 < len(parts):
                    align = int(parts[i + 1])
            if result:
                var_types[result] = "ptr"
            return {"result": result, "opcode": "alloca", "type": vtype, "align": align}

        if opcode == "load":
            vtype = _parse_type(parts[1])
            ptr_val = parts[3].rstrip(",") if len(parts) > 3 else ""
            align = None
            for i, p in enumerate(parts):
                if p == "align" and i + 1 < len(parts):
                    align = int(parts[i + 1])
            if result:
                var_types[result] = vtype
            return {"result": result, "opcode": "load", "type": vtype,
                    "ptr": ptr_val, "align": align}

        if opcode == "store":
            vtype = _parse_type(parts[1])
            val = parts[2].rstrip(",")
            ptr_val = parts[4] if len(parts) > 4 else ""
            align = None
            for i, p in enumerate(parts):
                if p == "align" and i + 1 < len(parts):
                    align = int(parts[i + 1])
            return {"result": result, "opcode": "store", "type": vtype,
                    "value": val, "ptr": ptr_val, "align": align}

        if opcode == "call":
            m = re.match(r'call\s+(\S+)\s+(@\S+)\s*\((.*)\)', line)
            if m:
                ret_type = _parse_type(m.group(1))
                callee = m.group(2)
                args_str = m.group(3).strip()
                args = []
                if args_str:
                    for a in args_str.split(","):
                        a = a.strip()
                        if a:
                            args.append(self._resolve_call_arg(a, var_types))
                if result and ret_type != "void":
                    var_types[result] = ret_type
                return {"result": result, "opcode": "call", "return_type": ret_type,
                        "callee": callee, "args": args}
            return {"result": result, "opcode": "call", "raw": line}

        if opcode == "phi":
            vtype = _parse_type(parts[1])
            incoming = []
            for m in re.finditer(r'\[\s*(\S+)\s*,\s*%(\S+)\s*\]', line):
                incoming.append({"value": m.group(1), "label": m.group(2)})
            if result:
                var_types[result] = vtype
            return {"result": result, "opcode": "phi", "type": vtype, "incoming": incoming}

        if opcode == "select":
            cond = parts[1]
            vtype = _parse_type(parts[2])
            tval = parts[3].rstrip(",")
            fval = parts[4].rstrip(",") if len(parts) > 4 else ""
            if result:
                var_types[result] = vtype
            return {"result": result, "opcode": "select", "type": vtype,
                    "cond": cond, "true_val": tval, "false_val": fval}

        if opcode in CONVERSION_OPS:
            src_type = _parse_type(parts[1])
            val = parts[2].rstrip(",")
            idx = 3
            while idx < len(parts) and parts[idx] == "to":
                idx += 1
            dst_type = _parse_type(parts[idx]) if idx < len(parts) else "i32"
            if result:
                var_types[result] = dst_type
            return {"result": result, "opcode": opcode, "src_type": src_type,
                    "value": val, "dst_type": dst_type}

        if opcode == "getelementptr":
            vtype = _parse_type(parts[1])
            ptr_val = parts[3].rstrip(",")
            remaining = parts[4:]
            indices = []
            i = 0
            while i < len(remaining):
                if remaining[i] in ("i32", "i64", "i8", "i16", "i1") and i + 1 < len(remaining):
                    indices.append(f"{remaining[i]} {remaining[i + 1].rstrip(',')}")
                    i += 2
                else:
                    indices.append(remaining[i].rstrip(","))
                    i += 1
            if result:
                var_types[result] = "ptr"
            return {"result": result, "opcode": "getelementptr", "type": vtype,
                    "ptr": ptr_val, "indices": indices}

        if opcode == "jmp":
            target = parts[-1].lstrip("%")
            return {"result": result, "opcode": "br", "uncond": target}

        if opcode == "switch":
            vtype = _parse_type(parts[1])
            val = parts[2].rstrip(",")
            default_label = parts[4].lstrip("%")
            cases = []
            for m in re.finditer(r'(\S+)\s*,\s*label\s+%(\S+)', line):
                cases.append({"value": m.group(1), "label": m.group(2)})
            return {"result": result, "opcode": "switch", "type": vtype,
                    "value": val, "default": default_label, "cases": cases}

        if opcode == "unreachable":
            return {"result": result, "opcode": "unreachable"}

        return {"result": result, "opcode": opcode, "raw": line}


def _llvm_id(name: str) -> str:
    """Quote an LLVM identifier if it contains non-identifier characters."""
    if not name:
        return name
    prefix = ""
    rest = name
    if name[0] in ("@", "%"):
        prefix = name[0]
        rest = name[1:]
    # Bare identifier: [-a-zA-Z$._][-a-zA-Z$._0-9]*
    if re.match(r'^[a-zA-Z$._][a-zA-Z$._0-9]*$', rest):
        return name
    return f'{prefix}"{rest}"'


def _emit_instruction(instr: dict) -> str:
    opcode = instr["opcode"]
    result_prefix = "  "
    if instr.get("result"):
        result_prefix = f"  {instr['result']} = "

    if opcode == "ret":
        if instr.get("void"):
            return "  ret void"
        return f"  ret {instr['type']} {_value_ref(instr['value'])}"

    if opcode == "br":
        if "uncond" in instr:
            return f"  br label %{instr['uncond']}"
        cond = _value_ref(instr["cond"])
        ct = instr.get("cond_type", "i1")
        return f"  br {ct} {cond}, label %{instr['true_label']}, label %{instr['false_label']}"

    if opcode == "unreachable":
        return "  unreachable"

    if opcode in BINARY_OPS:
        lhs = _value_ref(instr["operands"][0])
        rhs = _value_ref(instr["operands"][1])
        t = instr["type"]
        return f"{result_prefix}{opcode} {t} {lhs}, {rhs}"

    if opcode == "icmp":
        lhs = _value_ref(instr["operands"][0])
        rhs = _value_ref(instr["operands"][1])
        t = instr["type"]
        return f"{result_prefix}icmp {instr['predicate']} {t} {lhs}, {rhs}"

    if opcode == "alloca":
        align = f", align {instr['align']}" if instr.get("align") else ""
        return f"{result_prefix}alloca {instr['type']}{align}"

    if opcode == "load":
        ptr = _value_ref(instr["ptr"])
        align = f", align {instr['align']}" if instr.get("align") else ""
        return f"{result_prefix}load {instr['type']}, ptr {ptr}{align}"

    if opcode == "store":
        val = _value_ref(instr["value"])
        ptr = _value_ref(instr["ptr"])
        align = f", align {instr['align']}" if instr.get("align") else ""
        return f"  store {instr['type']} {val}, ptr {ptr}{align}"

    if opcode == "call":
        args = ", ".join(instr.get("args", []))
        callee = instr["callee"]
        ret_type = instr.get("return_type", "void")
        return f"{result_prefix}call {ret_type} {_llvm_id(callee)}({args})"

    if opcode == "phi":
        incoming = ", ".join(
            f"[{_value_ref(inc['value'])}, %{inc['label']}]"
            for inc in instr.get("incoming", [])
        )
        return f"{result_prefix}phi {instr['type']} {incoming}"

    if opcode == "select":
        cond = _value_ref(instr["cond"])
        tval = _value_ref(instr["true_val"])
        fval = _value_ref(instr["false_val"])
        t = instr["type"]
        return f"{result_prefix}select {t} {cond}, {t} {tval}, {t} {fval}"

    if opcode in CONVERSION_OPS:
        val = _value_ref(instr["value"])
        return f"{result_prefix}{opcode} {instr['src_type']} {val} to {instr['dst_type']}"

    if opcode == "getelementptr":
        ptr = _value_ref(instr["ptr"])
        indices = " ".join(instr.get("indices", []))
        return f"{result_prefix}getelementptr {instr['type']}, ptr {ptr}, {indices}"

    if opcode == "switch":
        val = _value_ref(instr["value"])
        result = [f"  switch {instr['type']} {val}, label %{instr['default']} ["]
        for c in instr.get("cases", []):
            result.append(f"    {c['value']}, label %{c['label']}")
        result.append("  ]")
        return "\n".join(result)

    if "raw" in instr:
        return f"  ; {instr['raw']}"

    return f"  ; unrecognized: {opcode}"


def lower_ir_to_llvm(ir_text: str, module_name: str = "nixon_module") -> str:
    parser = NixonIRParser(ir_text)
    module = parser.parse()

    target_triple = "x86_64-pc-linux-gnu"
    data_layout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"

    lines = []
    lines.append(f"; ModuleID = '{module_name}'")
    lines.append(f"target triple = \"{target_triple}\"")
    lines.append(f"target datalayout = \"{data_layout}\"")
    lines.append("")

    for s, name in parser.string_literals.items():
        escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\0A")
        raw = s.encode("utf-8")
        length = len(raw) + 1
        lines.append(f'{name} = private unnamed_addr constant [{length} x i8] c"{escaped}\\00"')
    if parser.string_literals:
        lines.append("")

    for g in module.get("globals", []):
        init = g.get("init", "zeroinitializer")
        lines.append(f"@{g['name'].lstrip('@')} = global {g['type']} {init}")
    if module.get("globals"):
        lines.append("")

    defined_funcs = {f["name"] for f in module.get("functions", [])}
    declared_funcs = {d["name"] for d in module.get("declares", [])}
    called_funcs: dict[str, str] = {}
    for func in module.get("functions", []):
        for block in func.get("blocks", []):
            for instr in block.get("instructions", []):
                if instr["opcode"] == "call" and "callee" in instr:
                    callee = instr["callee"]
                    if callee not in called_funcs:
                        called_funcs[callee] = instr.get("return_type", "void")

    for callee, ret_type in called_funcs.items():
        if callee not in defined_funcs and callee not in declared_funcs:
            module.setdefault("declares", []).append(
                {"name": callee, "return_type": ret_type, "params": []}
            )

    for d in module.get("declares", []):
        params = ", ".join(d.get("params", []))
        lines.append(f"declare {d['return_type']} {_llvm_id(d['name'])}({params})")
    if module.get("declares"):
        lines.append("")

    for func in module.get("functions", []):
        params = []
        for p in func.get("params", []):
            ptype = p["type"]
            pname = p.get("name", "")
            if pname:
                params.append(f"{ptype} {pname}")
            else:
                params.append(ptype)
        params_str = ", ".join(params)
        lines.append(f"define {func['return_type']} {_llvm_id(func['name'])}({params_str}) {{")
        for block in func.get("blocks", []):
            lines.append(f"{block['label']}:")
            for instr in block.get("instructions", []):
                try:
                    lines.append(_emit_instruction(instr))
                except Exception as e:
                    lines.append(f"  ; ERROR: {e}")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)
