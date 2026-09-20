import ast
import math


class ProvenanceMetrics:
    def measure_confusion(self, tree: ast.AST) -> dict:
        if not isinstance(tree, ast.Module):
            return {}

        all_funcs = [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        all_imports = [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.Import, ast.ImportFrom))
        ]
        all_calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]

        decoy_funcs = [
            f
            for f in all_funcs
            if f.name.startswith("_nx_decoy_")
            or f.name.startswith("_nx_fake_")
            or f.name.startswith("_nx_proto_")
        ]

        fake_api_funcs = [
            f for f in all_funcs if "_nx_fake_api_" in f.name
        ]

        protocol_parser_funcs = [
            f for f in all_funcs if "_nx_proto_" in f.name
        ]

        decoy_calls = [
            c for c in all_calls if (
                isinstance(c.func, ast.Name)
                and c.func.id.startswith("_nx_decoy_")
            )
        ]

        fake_call_edges = set()
        for c in decoy_calls:
            if isinstance(c.func, ast.Name):
                caller_func = self._find_enclosing_func(tree, c)
                if caller_func:
                    fake_call_edges.add((caller_func, c.func.id))

        misleading_imports = [
            i for i in all_imports if self._is_misleading_import(i)
        ]

        total_funcs = len(all_funcs)
        decoy_count = len(decoy_funcs)

        return {
            "fake_call_graph_complexity": len(decoy_calls),
            "fake_call_graph_edges": len(fake_call_edges),
            "fake_api_count": len(fake_api_funcs),
            "decoy_function_count": decoy_count,
            "decoy_function_pct": round(
                (decoy_count / total_funcs * 100) if total_funcs else 0, 1
            ),
            "protocol_parser_count": len(protocol_parser_funcs),
            "misleading_import_count": len(misleading_imports),
            "total_import_count": len(all_imports),
            "total_function_count": total_funcs,
            "misleading_import_ratio": round(
                (len(misleading_imports) / len(all_imports) * 100) if all_imports else 0, 1
            ),
        }

    def _find_enclosing_func(self, tree: ast.AST, node: ast.AST) -> str | None:
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(n):
                    if child is node:
                        return n.name
        return None

    def _is_misleading_import(self, node: ast.AST) -> bool:
        misleading_names = [
            "cryptography", "socket", "ssl", "requests",
            "http", "serial", "usb", "bluetooth", "nacl",
        ]
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(m in alias.name for m in misleading_names):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and any(m in node.module for m in misleading_names):
                return True
        return False

    def measure_storyline_confusion(self, tree: ast.AST) -> dict:
        if not isinstance(tree, ast.Module):
            return {}
        all_funcs = [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        narrative_funcs = [f for f in all_funcs if any(
            isinstance(d, ast.Expr) and isinstance(d.value, ast.Constant)
            and isinstance(d.value.value, str) and "NARRATIVE:" in d.value.value
            for d in f.body
        )]
        narrative_counts: dict[str, int] = {}
        for f in narrative_funcs:
            for d in f.body:
                if isinstance(d, ast.Expr) and isinstance(d.value, ast.Constant):
                    txt = d.value.value
                    if "NARRATIVE:" in txt:
                        tag = txt.split("NARRATIVE:")[1].strip()
                        narrative_counts[tag] = narrative_counts.get(tag, 0) + 1
        total = sum(narrative_counts.values())
        entropy = 0.0
        if total > 0:
            for count in narrative_counts.values():
                p = count / total
                entropy -= p * math.log2(p)
        return {
            "distinct_narratives": len(narrative_counts),
            "narrative_function_count": total,
            "narrative_entropy": round(entropy, 4),
        }
