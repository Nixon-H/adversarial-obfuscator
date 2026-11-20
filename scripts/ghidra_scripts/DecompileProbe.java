// Ghidra headless post-script: decompile a named function and report what is
// recoverable. Used to answer "can a binary-analysis tool reconstruct the
// native enforcement semantics?" with evidence rather than assertion.
//
// Usage (from analyzeHeadless):
//   -postScript DecompileProbe.java <out.json> <symbol-substring>
//
// Writes JSON: whether the symbol was found, its size, the decompiled text,
// and which syscall-ish terms appear in it.
//@category XERJ

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

public class DecompileProbe extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "/tmp/ghidra_probe.json";
        String target = args.length > 1 ? args[1] : "nx_apply_protections";

        FunctionManager fm = currentProgram.getFunctionManager();
        Function fn = null;
        for (Function f : fm.getFunctions(true)) {
            if (f.getName().equals(target) || f.getName().contains(target)) {
                fn = f;
                break;
            }
        }

        StringBuilder sb = new StringBuilder();
        sb.append("{\n");

        int funcCount = 0;
        for (Function f : fm.getFunctions(true)) {
            funcCount++;
        }
        sb.append("  \"functions_total\": ").append(funcCount).append(",\n");

        List<String> exported = new ArrayList<String>();
        SymbolIterator syms = currentProgram.getSymbolTable().getAllSymbols(true);
        while (syms.hasNext()) {
            Symbol s = syms.next();
            if (s.isExternalEntryPoint()) {
                exported.add(s.getName());
            }
        }
        sb.append("  \"exported_symbols\": [");
        for (int i = 0; i < exported.size(); i++) {
            if (i > 0) sb.append(", ");
            sb.append("\"").append(exported.get(i)).append("\"");
        }
        sb.append("],\n");

        if (fn == null) {
            sb.append("  \"target\": \"").append(target).append("\",\n");
            sb.append("  \"found\": false\n");
        } else {
            sb.append("  \"target\": \"").append(fn.getName()).append("\",\n");
            sb.append("  \"found\": true,\n");
            sb.append("  \"entry\": \"").append(fn.getEntryPoint()).append("\",\n");
            sb.append("  \"body_size\": ").append(fn.getBody().getNumAddresses()).append(",\n");

            DecompInterface di = new DecompInterface();
            di.openProgram(currentProgram);
            DecompileResults res = di.decompileFunction(fn, 120, monitor);
            if (res != null && res.decompileCompleted()) {
                String code = res.getDecompiledFunction().getC();
                String lower = code.toLowerCase();
                String[] probes = {
                    "prctl", "rlimit", "setrlimit", "getrlimit",
                    "sigaction", "signal", "exit", "137", "syscall"
                };
                sb.append("  \"decompiled_chars\": ").append(code.length()).append(",\n");
                sb.append("  \"semantic_probes\": {");
                for (int i = 0; i < probes.length; i++) {
                    if (i > 0) sb.append(", ");
                    sb.append("\"").append(probes[i]).append("\": ")
                      .append(lower.contains(probes[i]));
                }
                sb.append("},\n");
                String escaped = code.replace("\\", "\\\\")
                                     .replace("\"", "\\\"")
                                     .replace("\n", "\\n")
                                     .replace("\r", "")
                                     .replace("\t", "\\t");
                sb.append("  \"decompiled\": \"").append(escaped).append("\"\n");
            } else {
                sb.append("  \"decompile_failed\": true\n");
            }
            di.dispose();
        }
        sb.append("}\n");

        PrintWriter pw = new PrintWriter(outPath, "UTF-8");
        pw.print(sb.toString());
        pw.close();
        println("WROTE " + outPath);
    }
}
