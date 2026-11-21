package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Pattern;

final class UsMarketCoverage {
    static final String DIRECTORY = "https://www.nasdaqtrader.com/dynamic/SymDir/";
    static final String ASSET = "us-monitor-universe.json";
    private static final Pattern FOOTER = Pattern.compile("File Creation Time: ([0-9]{8})([0-9]{2}:[0-9]{2})\\|+");
    private static final Pattern WHITESPACE = Pattern.compile("\\s+");
    private static final Pattern SYMBOL = Pattern.compile("[A-Z0-9.$+^=/_-]{1,24}");
    private static final Pattern COMMON = Pattern.compile("\\b(?:common|ordinary)\\s+(?:stock|shares?)\\b", Pattern.CASE_INSENSITIVE);
    private static final Pattern OTHER = Pattern.compile("\\b(?:depositary|depository|preferred|preference|warrants?|rights?|units?|"
            + "notes?|bonds?|debentures?)\\b", Pattern.CASE_INSENSITIVE);
    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.ofPattern("MMdduuuu")
            .withResolverStyle(ResolverStyle.STRICT);

    record Directory(LocalDate date, Set<String> symbols, Set<String> listed, Set<String> other,
                     LocalTime timestamp, java.util.Map<String, String> ordinaryNames) {
        Directory(LocalDate date, Set<String> symbols, Set<String> listed, Set<String> other) {
            this(date, symbols, listed, other, null, java.util.Map.of());
        }
    }

    static Directory directory(String file, boolean nasdaq) throws JSONException {
        String[] lines = file.replaceFirst("^\\uFEFF", "").trim().split("\\r?\\n");
        if (lines.length < 3 || lines.length > 30_000) throw new JSONException("Unexpected listing directory size");
        var header = Arrays.asList(lines[0].split("\\|", -1));
        int symbol = header.indexOf(nasdaq ? "Symbol" : "ACT Symbol");
        int market = header.indexOf(nasdaq ? "NextShares" : "Exchange");
        int name = header.indexOf("Security Name");
        int test = header.indexOf("Test Issue");
        int etf = header.indexOf("ETF");
        if (symbol < 0 || market < 0 || name < 0 || test < 0 || etf < 0) {
            throw new JSONException("Unexpected listing directory columns");
        }
        var footer = FOOTER.matcher(lines[lines.length - 1]);
        if (!footer.matches()) throw new JSONException("Missing listing directory date");
        LocalDate date;
        LocalTime time;
        try {
            date = LocalDate.parse(footer.group(1), DATE_FORMAT);
            time = LocalTime.parse(footer.group(2));
        } catch (DateTimeParseException invalid) {
            throw new JSONException("Invalid listing directory date");
        }

        var symbols = new HashSet<String>();
        var listed = new HashSet<String>();
        var other = new HashSet<String>();
        var names = new java.util.HashMap<String, String>();
        for (int i = 1; i < lines.length - 1; i++) {
            var row = lines[i].split("\\|", -1);
            if (row.length != header.size() || !SYMBOL.matcher(row[symbol]).matches()
                    || !(row[test].equals("N") || row[test].equals("Y"))
                    || !(row[etf].equals("N") || row[etf].equals("Y"))) {
                throw new JSONException("Invalid listing directory row");
            }
            if (row[test].equals("Y") || row[etf].equals("Y") || (nasdaq && row[market].equals("Y"))) continue;
            String ticker = row[symbol];
            if (!listed.add(ticker)) throw new JSONException("Duplicate listing symbol");
            if (OTHER.matcher(row[name]).find() || isVerifiedClosedEndFund(ticker, row[name])) {
                other.add(ticker);
            } else if ((nasdaq || row[market].equals("N")) && COMMON.matcher(row[name]).find()) {
                symbols.add(ticker);
                names.put(ticker, WHITESPACE.matcher(row[name].trim()).replaceAll(" ").toUpperCase(java.util.Locale.ROOT));
            }
        }
        if (symbols.isEmpty()) throw new JSONException("No ordinary stock symbols");
        return new Directory(date, symbols, listed, other, time, java.util.Map.copyOf(names));
    }

    private static boolean isVerifiedClosedEndFund(String ticker, String name) {
        // Nasdaq Trader labels these fund shares "Common Stock". The issuer confirms the fund type.
        // Match the name as well as the ticker so a subsequent reuse of MXE is not excluded.
        return "MXE".equals(ticker) && name.toUpperCase(java.util.Locale.ROOT)
                .contains("MEXICO EQUITY AND INCOME FUND");
    }

    static boolean sessionSnapshot(java.time.LocalTime time) {
        // The evening distribution describes the upcoming session.
        return time != null && !time.isBefore(java.time.LocalTime.of(9, 30))
                && time.isBefore(java.time.LocalTime.of(20, 45));
    }

    static boolean hasSessionEvidence(JSONObject snapshot, LocalDate day) {
        if (!day.toString().equals(snapshot.optString("day"))) return false;
        try {
            return sessionSnapshot(java.time.LocalTime.parse(snapshot.optString("time")));
        } catch (DateTimeException invalid) {
            return false;
        }
    }

    static Set<String> verifiedSupplementSymbols(JSONObject before, JSONObject after, LocalDate previous, LocalDate day) {
        if (!hasSessionEvidence(before, previous) || !hasSessionEvidence(after, day)) {
            return Set.of();
        }
        var result = new HashSet<String>();
        for (String exchange : java.util.List.of("nyse", "nasdaq")) {
            String other = "nyse".equals(exchange) ? "nasdaq" : "nyse";
            var old = before.optJSONObject(exchange);
            var current = after.optJSONObject(exchange);
            var oldOther = before.optJSONObject(other);
            var currentOther = after.optJSONObject(other);
            if (old == null || current == null || oldOther == null || currentOther == null) return Set.of();
            var tickers = current.keys();
            while (tickers.hasNext()) {
                String ticker = tickers.next();
                var identity = current.opt(ticker);
                if (identity instanceof String name && !name.isEmpty() && ticker.matches("[A-Z0-9.$+^=/_-]{1,24}")
                        && !oldOther.has(ticker) && !currentOther.has(ticker) && name.equals(old.opt(ticker))) {
                    result.add(ticker);
                }
            }
        }
        return Set.copyOf(result);
    }

    static String summarize(Directory nyse, Directory nasdaq, JSONArray closes,
                            LocalDate tradingDate, JSONObject ledger) throws JSONException {
        if (!nyse.date.equals(nasdaq.date) || !java.util.Collections.disjoint(nyse.symbols, nasdaq.symbols)) {
            throw new JSONException("Listing directories disagree");
        }
        var available = new HashSet<String>();
        for (int i = 0; i < closes.length(); i++) {
            var close = closes.getJSONObject(i);
            double price = close.getDouble("close_usd");
            if (Double.isFinite(price) && price > 0) available.add(close.getString("symbol"));
        }
        int nysePrices = count(nyse.symbols, available);
        int nasdaqPrices = count(nasdaq.symbols, available);
        int found = nysePrices + nasdaqPrices;
        int listed = nyse.symbols.size() + nasdaq.symbols.size();
        String text = "普通株候補の監視 " + found + " / " + listed + "銘柄 · 終値なし " + (listed - found)
                + "銘柄\nNYSE " + nysePrices + " / " + nyse.symbols.size()
                + " · Nasdaq " + nasdaqPrices + " / " + nasdaq.symbols.size()
                + "\n上場一覧基準日 " + nyse.date + "（米東部）";
        if (ledger == null) return text;
        if (!tradingDate.toString().equals(ledger.optString("trading_date_et"))) {
            return text + "\n財務台帳基準日 " + ledger.optString("trading_date_et") + " · 対象取引日の台帳待ち";
        }
        var dedup = new HashSet<String>();
        var rows = ledger.getJSONArray("listings");
        int financials = 0;
        int positive = 0;
        for (int i = 0; i < rows.length(); i++) {
            var row = rows.getJSONObject(i);
            String symbol = row.getString("symbol");
            String venue = row.getString("exchange");
            if (!dedup.add(symbol)) throw new JSONException("Duplicate SEC ledger symbol");
            boolean matches = ("NYSE".equals(venue) && nyse.symbols.contains(symbol))
                    || ("Nasdaq".equals(venue) && nasdaq.symbols.contains(symbol));
            if (matches && available.contains(symbol) && !row.has("hold") && row.optDouble("shares", 0) > 0) {
                financials++;
                if (row.optDouble("profit", 0) > 0 && row.optDouble("equity", 0) > 0) positive++;
            }
        }
        return text + "\nSEC財務・株数の照合 " + financials + "銘柄 · 利益・自己資本が正 " + positive + "銘柄";
    }

    private static int count(Set<String> listed, Set<String> available) {
        int found = 0;
        for (String symbol : listed) if (available.contains(symbol)) found++;
        return found;
    }
}
