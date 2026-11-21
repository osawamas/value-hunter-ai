package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.time.LocalDate;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

public class UsMarketCoverageTest {
    private static final String NASDAQ = "Symbol|Security Name|Test Issue|ETF|NextShares\n"
            + "AAA|A Corp. Common Stock|N|N|N\n"
            + "NXT|B Corp. Common Stock|N|N|Y\n"
            + "FUND|C Fund|N|Y|N\n"
            + "File Creation Time: 1118202608:16||||\n";
    private static final String OTHER = "ACT Symbol|Security Name|Exchange|ETF|Test Issue\n"
            + "BBB|B Corp. Ordinary Shares|N|N|N\n"
            + "ARCA|C Corp. Common Stock|P|N|N\n"
            + "PREF|D Corp. Preferred Stock|N|N|N\n"
            + "File Creation Time: 1118202608:16||||\n";

    @Test public void matchesOnlyOrdinaryNonTestListingsAndLabelsTheDates() throws Exception {
        var nyse = UsMarketCoverage.directory(OTHER, false);
        var nasdaq = UsMarketCoverage.directory(NASDAQ, true);
        var closes = new JSONArray().put(
                new JSONObject().put("symbol", "AAA").put("close_usd", 10.43));
        var session = LocalDate.of(2026, 11, 17);
        var oldLedger = new JSONObject().put("trading_date_et", "2026-11-16");
        String text = UsMarketCoverage.summarize(nyse, nasdaq, closes, session, oldLedger);
        assertTrue(text.contains("監視 1 / 2銘柄"));
        assertTrue(text.contains("NYSE 0 / 1 · Nasdaq 1 / 1"));
        assertTrue(text.contains("一覧基準日 2026-11-18"));
        assertTrue(text.contains("対象取引日の台帳待ち"));
        var differentDay = UsMarketCoverage.directory(NASDAQ.replace("11182026", "11192026"), true);
        assertThrows(JSONException.class, () -> UsMarketCoverage.summarize(nyse, differentDay, closes, session, null));
    }

    @Test public void anIdentifiedClosedEndFundIsExcludedWithoutBlacklistingItsTicker() throws Exception {
        var fund = UsMarketCoverage.directory(OTHER.replace("BBB|B Corp. Ordinary Shares|N|N|N",
                "BBB|B Corp. Ordinary Shares|N|N|N\nMXE|Mexico Equity and Income Fund, Inc. Common Stock|N|N|N"), false);
        assertTrue(fund.other().contains("MXE"));
        assertFalse(fund.symbols().contains("MXE"));
        var reused = UsMarketCoverage.directory(OTHER.replace("BBB|B Corp. Ordinary Shares|N|N|N",
                "MXE|New Issuer Common Stock|N|N|N"), false);
        assertTrue(reused.symbols().contains("MXE"));
    }

    @Test public void acceptsNumericAndPaddedSecCiksAndRejectsOtherIdentities() throws Exception {
        assertTrue(UsFinancialFacts.matchesIssuer(new JSONObject().put("cik", 123), 123));
        assertTrue(UsFinancialFacts.matchesIssuer(new JSONObject().put("cik", "0000000123"), 123));
        assertFalse(UsFinancialFacts.matchesIssuer(new JSONObject().put("cik", "0000000124"), 123));
        assertFalse(UsFinancialFacts.matchesIssuer(new JSONObject().put("cik", "1.23e2"), 123));
    }
}
