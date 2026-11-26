import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

public class ScanFuncs extends GhidraScript {
    public void run() throws Exception {
        String outPath = getScriptArgs().length > 0 ? getScriptArgs()[0] : "/tmp/scan.json";
        FunctionManager fm = currentProgram.getFunctionManager();
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        List<String> hits = new ArrayList<String>();
        for (Function f : fm.getFunctions(true)) {
            DecompileResults res = di.decompileFunction(f, 60, monitor);
            if (res != null && res.decompileCompleted()) {
                String code = res.getDecompiledFunction().getC();
                String low = code.toLowerCase();
                if (low.contains("keystream") || low.contains("seal") || low.contains("secret") || low.contains("hidden") || low.contains("vector")) {
                    hits.add(f.getName() + " @ " + f.getEntryPoint() + " size=" + f.getBody().getNumAddresses());
                    // write decompiled to separate file per hit
                }
            }
        }
        di.dispose();
        PrintWriter pw = new PrintWriter(outPath, "UTF-8");
        pw.println("{ \"hits\": [");
        for (int i=0;i<hits.size();i++){ if(i>0) pw.println(","); pw.print("\""+hits.get(i).replace("\"","\\\"")+"\""); }
        pw.println("] }");
        pw.close();
        println("WROTE "+outPath+" hits="+hits.size());
    }
}
