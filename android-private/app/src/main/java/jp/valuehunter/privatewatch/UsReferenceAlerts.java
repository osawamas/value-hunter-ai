package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

final class UsReferenceAlerts {
    private static final Set<String> SCREENED = Set.of("priority", "reference", "outside_budget", "outside_valuation");

    record Observation(int cik, String exchange, String status, int quantity) {
        boolean candidate() {
            return "priority".equals(status) || "reference".equals(status);
        }

        boolean sameSecurity(Observation previous) {
            return previous != null && cik == previous.cik && exchange.equals(previous.exchange);
        }

        boolean enteredFrom(Observation previous) {
            return candidate() && sameSecurity(previous) && (!previous.candidate() || ("priority".equals(status) && "reference".equals(previous.status)));
        }
    }

    record Screen(LocalDate day, String provider, String hash, Map<String, Observation> rows) {}

    private UsReferenceAlerts() {}

    static String meterKey(String exchange, int cik, String ticker) {
        return exchange + ":" + cik + ":" + ticker;
    }

    static Map<String, String> comparableMeterSymbols(Screen previous, Screen current) {
        var symbols = new HashMap<String, String>();
        current.rows().forEach((ticker, observation) -> {
            if (observation.sameSecurity(previous.rows().get(ticker))) {
                symbols.put(meterKey(observation.exchange(), observation.cik(), ticker), ticker);
            }
        });
        return symbols;
    }

    static boolean hasTradeDateFx(JSONObject ledger, LocalDate day) {
        var screen = ledger == null ? null : ledger.optJSONObject("reference_screen");
        return screen != null && day.toString().equals(screen.optString("fx_date"));
    }

    static Screen read(JSONObject ledger) throws JSONException {
        try {
            var day = LocalDate.parse(ledger.getString("trading_date_et"));
            var screen = ledger.getJSONObject("reference_screen");
            var provider = screen.getString("provider");
            var hash = screen.getString("close_sha256");
            var observations = screen.getJSONArray("observations");
            if (!hasTradeDateFx(ledger, day) || !hash.matches("[a-f0-9]{64}")
                    || !Set.of(UsDoltCloses.SOURCE, UsDailyCloses.MASSIVE_SOURCE).contains(provider)
                    || observations.length() > 12_000) throw new JSONException("Invalid US reference screen");
            var rows = new HashMap<String, Observation>();
            for (int i = 0; i < observations.length(); i++) {
                var row = observations.getJSONObject(i);
                String ticker = row.getString("symbol");
                String exchange = row.getString("exchange");
                String status = row.getString("status");
                int quantity = row.getInt("quantity");
                int cik = row.getInt("cik");
                if (!ticker.matches("[A-Z0-9.$+^=/_-]{1,24}") || !Set.of("NYSE", "Nasdaq").contains(exchange)
                        || !SCREENED.contains(status) || (quantity != 1 && quantity != 100) || cik <= 0
                        || rows.put(ticker, new Observation(cik, exchange, status, quantity)) != null) {
                    throw new JSONException("Invalid US reference observation");
                }
            }
            return new Screen(day, provider, hash, rows);
        } catch (DateTimeParseException e) {
            throw new JSONException("Invalid US reference screen date");
        }
    }

    static List<String> entrants(Screen previous, Screen current) {
        return List.copyOf(entrantRows(previous, current, Set.of()).values());
    }

    static Map<String, String> entrantRows(Screen previous, Screen current, Set<String> alreadyQueued) {
        if (previous == null || !current.provider.equals(previous.provider) || !current.day.isAfter(previous.day)
                || previous.day.isBefore(current.day.minusDays(7))) return Map.of();
        var alerts = new java.util.LinkedHashMap<String, String>();
        current.rows.entrySet().stream()
                .filter(row -> !alreadyQueued.contains(row.getKey())
                        && row.getValue().enteredFrom(previous.rows.get(row.getKey())))
                .sorted(java.util.Comparator.<Map.Entry<String, Observation>>comparingInt(
                                row -> -row.getValue().quantity)
                        .thenComparing(row -> !"priority".equals(row.getValue().status))
                        .thenComparing(Map.Entry::getKey))
                .forEach(row -> alerts.put(row.getKey(), row.getKey() + " · " + row.getValue().quantity + "株"
                        + ("priority".equals(row.getValue().status) ? " · 優先候補" : " · 参考候補")));
        return alerts;
    }

    static String sha256(byte[] bytes) {
        try {
            var hash = new StringBuilder(64);
            for (byte value : MessageDigest.getInstance("SHA-256").digest(bytes)) {
                hash.append(Character.forDigit((value & 0xf0) >>> 4, 16));
                hash.append(Character.forDigit(value & 0x0f, 16));
            }
            return hash.toString();
        } catch (NoSuchAlgorithmException impossible) {
            throw new AssertionError(impossible);
        }
    }
}
