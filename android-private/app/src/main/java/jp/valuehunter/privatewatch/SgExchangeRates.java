package jp.valuehunter.privatewatch;

import org.json.JSONArray;
import org.json.JSONException;

import java.io.IOException;
import java.time.LocalDate;

final class SgExchangeRates {
    private static final String URL = "https://api.frankfurter.dev/v2/rates?base=SGD&quotes=JPY";

    interface Fetch {
        JSONArray get(String url) throws IOException, JSONException;
    }

    private final LocalDate latest;
    private final LocalDate firstSession;
    private final Fetch fetch;
    private JSONArray snapshot;

    SgExchangeRates(SgCloseCheck.Pair pair, boolean includePrevious, Fetch fetch) {
        this.fetch = fetch;
        latest = pair.latest().session();
        LocalDate previous = pair.previous().session();
        firstSession = includePrevious && !previous.isBefore(latest.minusWeeks(1)) ? previous : latest;
    }

    UsScreen.Fx forSession(LocalDate session) throws IOException, JSONException {
        if (session.isBefore(firstSession) || session.isAfter(latest)) {
            return UsScreen.readFx(request(session, session), session, "SGD");
        }
        if (snapshot == null) snapshot = request(firstSession, latest);
        return UsScreen.readFx(snapshot, session, "SGD");
    }

    private JSONArray request(LocalDate fromSession, LocalDate toSession) throws IOException, JSONException {
        return fetch.get(URL + "&from=" + fromSession.minusDays(UsScreen.FX_LOOKBACK_DAYS) + "&to=" + toSession);
    }
}
