package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Locale;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

final class UsDailyValuation {
    private static final BigDecimal BUDGET = new BigDecimal("100000");
    private static final BigDecimal HUNDRED = new BigDecimal("100");
    private record Issuer(String symbol, int cik) {}
    // Single common stock class for this pilot. Do not extrapolate issuer shares to unregistered classes.
    private static final Issuer[] PILOT = {
            new Issuer("IBM", 51143), new Issuer("AAPL", 320193), new Issuer("HPQ", 47217),
            new Issuer("AMD", 2488), new Issuer("INTC", 50863), new Issuer("GM", 1467858)
    };
    private static final String FX_URL =
            "https://api.frankfurter.dev/v2/rates?base=USD&quotes=JPY";
    private static final String SEC_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK";

    record Report(String text, boolean retry) {}

    static Set<String> pilotSymbols() {
        return Arrays.stream(PILOT).map(Issuer::symbol).collect(Collectors.toCollection(LinkedHashSet::new));
    }

    static String pilotSymbolsSql() {
        return pilotSymbols().stream().map(symbol -> "'" + symbol + "'")
                .collect(Collectors.joining(",", "(", ")"));
    }

    interface Fetch {
        JSONObject facts(String address) throws IOException, JSONException;
        JSONArray rates(String address) throws IOException, JSONException;
        Map<String, LocalDate> splits(LocalDate since, LocalDate session) throws IOException, JSONException;
    }

    static Report assess(JSONArray closes, LocalDate session, String source, Fetch fetch) throws IOException, JSONException {
        var quotes = new HashMap<String, BigDecimal>();
        for (int i = 0; i < closes.length(); i++) {
            var row = closes.getJSONObject(i);
            quotes.put(row.getString("symbol"), BigDecimal.valueOf(row.getDouble("close_usd")));
        }
        var rates = fetch.rates(FX_URL + "&from=" + session.minusDays(UsScreen.FX_LOOKBACK_DAYS) + "&to=" + session);
        var fx = UsScreen.readFx(rates, session);
        var split = fetch.splits(session.minusDays(150), session);
        StringBuilder message = new StringBuilder();
        boolean retry = false;
        int usable = 0;
        int candidates = 0;
        for (var issuer : PILOT) {
            String symbol = issuer.symbol;
            var close = quotes.get(symbol);
            if (close == null || close.signum() <= 0) {
                message.append("\n").append(symbol).append(" · 保留（終値なし）");
                continue;
            }
            UsFinancialFacts.Facts facts;
            try {
                String address = SEC_URL + String.format(Locale.ROOT, "%010d", issuer.cik) + ".json";
                facts = UsFinancialFacts.read(fetch.facts(address), issuer.cik, session);
            } catch (IOException | JSONException e) {
                retry = true;
                message.append("\n").append(symbol).append(" · 保留（SECデータの取得・照合に失敗）");
                continue;
            }
            if (facts == null) {
                message.append("\n").append(symbol).append(" · 保留（終値と照合できる開示が不足）");
                continue;
            }
            LocalDate splitDate = split.get(symbol);
            if (splitDate != null && !splitDate.isBefore(facts.shareDate())) {
                message.append("\n").append(symbol).append(" · 保留（株式分割後の株数を要確認）");
                continue;
            }
            usable++;
            BigDecimal cap = close.multiply(facts.shares());
            BigDecimal oneShare = close.multiply(BigDecimal.valueOf(fx.yenPerDollar()));
            int quantity = oneShare.multiply(HUNDRED).compareTo(BUDGET) <= 0 ? 100 : 1;
            BigDecimal yen = oneShare.multiply(BigDecimal.valueOf(quantity));
            var level = ValueCandidateScreen.assess(cap, facts.profit(), facts.equity());
            String status = yen.compareTo(BUDGET) > 0 ? "予算超過"
                    : facts.profit().signum() <= 0 ? "保留（直近12か月の利益が赤字またはゼロ）"
                    : facts.equity().signum() <= 0 ? "保留（自己資本がマイナスまたはゼロ）" : level.label;
            if (yen.compareTo(BUDGET) <= 0 && level.qualifies()) candidates++;
            message.append(String.format(Locale.JAPAN,
                    "\n%s · %s\n%d株 約%,.0f円 · 時価総額 %s百万USD\nPER %s · PBR %s · 株数基準日 %s · 開示日 %s",
                    symbol, status, quantity, yen, cap.movePointLeft(6).setScale(0, RoundingMode.HALF_UP),
                    ratio(cap, facts.profit()), ratio(cap, facts.equity()), facts.shareDate(), facts.filed()));
        }
        return new Report(String.format(Locale.JAPAN, "%s · %s\n参考判定 %d/%d銘柄 · 条件該当 %d件 · 為替基準日 %s",
                session, source, usable, PILOT.length, candidates, fx.date()) + message, retry);
    }

    private static String ratio(BigDecimal numerator, BigDecimal denominator) {
        if (denominator.signum() <= 0) return "算出不可";
        return numerator.divide(denominator, 2, RoundingMode.HALF_UP).toPlainString() + "倍";
    }
}
