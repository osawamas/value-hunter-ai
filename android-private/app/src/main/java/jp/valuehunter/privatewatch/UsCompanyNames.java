package jp.valuehunter.privatewatch;

import android.content.Context;
import android.util.AtomicFile;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/** Official Nasdaq Trader symbol-directory names cached locally for offline alert inspection. */
final class UsCompanyNames {
    private static final String FILE = "us-notification-company-names.json";
    private UsCompanyNames() {}

    static void save(Context context, UsMarketCoverage.Directory nyse, UsMarketCoverage.Directory nasdaq)
            throws IOException {
        var names = new JSONObject();
        try {
            for (var entry : nyse.ordinaryNames().entrySet()) names.put(entry.getKey(),entry.getValue());
            for (var entry : nasdaq.ordinaryNames().entrySet()) names.put(entry.getKey(),entry.getValue());
        } catch (JSONException invalid) {
            throw new IOException("Invalid Nasdaq Trader issuer names",invalid);
        }
        AtomicFile file = new AtomicFile(new File(context.getNoBackupFilesDir(), FILE));
        java.io.FileOutputStream out = file.startWrite();
        try {
            out.write(names.toString().getBytes(StandardCharsets.UTF_8));
            file.finishWrite(out);
        } catch (IOException failed) {
            file.failWrite(out);
            throw failed;
        }
    }

    static Map<String,String> read(Context context) {
        try {
            var names = new JSONObject(new String(new AtomicFile(
                    new File(context.getNoBackupFilesDir(),FILE)).readFully(),StandardCharsets.UTF_8));
            var result = new java.util.HashMap<String,String>();
            for (var key = names.keys();key.hasNext();) {
                String code=key.next(),name=names.optString(code,"");
                if (code.matches("[A-Z0-9.$+^=/_-]{1,24}") && !name.isBlank()) result.put(code,name);
            }
            return Map.copyOf(result);
        } catch (IOException | JSONException unavailable) {
            return Map.of();
        }
    }

    /** Add a verified exchange-listed name to a line that starts with its ticker. */
    static String decorate(String line, Map<String,String> names) {
        if (line == null || names.isEmpty()) return line;
        int delimiter=line.indexOf(" · ");
        if (delimiter<=0) return line;
        String ticker=line.substring(0,delimiter);
        String name=names.get(ticker);
        return name==null?line:ticker+" ("+name+")"+line.substring(delimiter);
    }
}
