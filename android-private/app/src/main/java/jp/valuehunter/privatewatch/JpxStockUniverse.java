package jp.valuehunter.privatewatch;

import android.content.Context;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Pattern;

/** The reference list of domestic ordinary shares on Prime, Standard, and Growth. */
record JpxStockUniverse(LocalDate asOf, Set<String> codes) {
    private static final Pattern CODE = Pattern.compile("[0-9][0-9A-Z]{3}");

    static JpxStockUniverse load(Context context) throws IOException {
        try (var stream = context.getAssets().open("jpx-stock-universe.txt");
             var reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.US_ASCII))) {
            String date = reader.readLine();
            if (date == null) throw new IOException("東証の銘柄一覧に基準日がない");
            LocalDate asOf;
            try {
                asOf = LocalDate.parse(date);
            } catch (DateTimeParseException error) {
                throw new IOException("東証の銘柄一覧の基準日を読み取れなかった", error);
            }
            var codes = new HashSet<String>();
            for (String line; (line = reader.readLine()) != null;) {
                if (!CODE.matcher(line).matches() || !codes.add(line)) {
                    throw new IOException("東証の銘柄一覧に不正または重複コードがある");
                }
            }
            if (codes.isEmpty()) throw new IOException("東証の銘柄一覧が空");
            return new JpxStockUniverse(asOf, Set.copyOf(codes));
        }
    }
}
