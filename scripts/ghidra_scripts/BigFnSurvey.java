// Ghidra headless survey: is the PAYLOAD recoverable from the shipped blob?
//
// Symbol counts do not answer this -- strip can remove every name while
// leaving every instruction. So this decompiles the largest functions (where
// payload logic lives) and looks for caller-supplied needles: payload
// identifiers and literals that must NOT be visible.
//
// Usage (from analyzeHeadless):
//   -postScript BigFnSurvey.java <out.json> "<needle1;needle2;...>"
//
//@category XERJ

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Listing;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

public class BigFnSurvey extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = args.length > 0 ? args[0] : "/tmp/bigfn.json";
        String needlesArg = args.length > 1 ? args[1] : "";

        FunctionManager fm = currentProgram.getFunctionManager();
        List<Function> all = new ArrayList<Function>();
        for (Function f : fm.getFunctions(true)) {
            all.add(f);
        }
        Collections.sort(all, new Comparator<Function>() {
            public int compare(Function a, Function b) {
                return Long.compare(b.getBody().getNumAddresses(),
                                    a.getBody().getNumAddresses());
            }
        });

        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);

        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"decompiled_top\": [");
        int done = 0, withNeedle = 0;
        StringBuilder hits = new StringBuilder();
        for (Function f : all) {
            if (done >= 8) break;
            long sz = f.getBody().getNumAddresses();
            if (sz < 200) break;
            DecompileResults r = di.decompileFunction(f, 90, monitor);
            if (r == null || !r.decompileCompleted()) continue;
            String c = r.getDecompiledFunction().getC();
            if (done > 0) sb.append(",");
            sb.append("\n    {\"name\": \"").append(f.getName())
              .append("\", \"bytes\": ").append(sz)
              .append(", \"chars\": ").append(c.length());
            boolean hit = false;
            if (needlesArg != null && needlesArg.length() > 0) {
                for (String needle : needlesArg.split(";")) {
                    if (needle.length() == 0) continue;
                    if (c.contains(needle)) {
                        hit = true;
                        hits.append(needle).append(" ");
                    }
                }
            }
            sb.append(", \"needle_hit\": ").append(hit).append("}");
            if (hit) withNeedle++;
            done++;
        }
        di.dispose();
        sb.append("\n  ],\n");
        sb.append("  \"top_n\": ").append(done).append(",\n");
        sb.append("  \"with_payload_needle\": ").append(withNeedle).append(",\n");
        sb.append("  \"needles_hit\": \"").append(hits.toString()).append("\",\n");

        int stringHits = 0;
        StringBuilder sh = new StringBuilder();
        Listing listing = currentProgram.getListing();
        DataIterator it = listing.getDefinedData(true);
        while (it.hasNext()) {
            Object v = it.next().getValue();
            if (!(v instanceof String)) continue;
            String s = (String) v;
            for (String needle : needlesArg.split(";")) {
                if (needle.length() == 0) continue;
                if (s.contains(needle)) {
                    stringHits++;
                    if (sh.length() < 400) sh.append(s).append(" | ");
                }
            }
        }
        sb.append("  \"string_needle_hits\": ").append(stringHits).append(",\n");
        sb.append("  \"string_hits_sample\": \"")
          .append(sh.toString().replace("\\", "\\\\").replace("\"", "\\\""))
          .append("\"\n");
        sb.append("}\n");

        PrintWriter pw = new PrintWriter(outPath, "UTF-8");
        pw.print(sb.toString());
        pw.close();
        println("WROTE " + outPath);
    }
}
