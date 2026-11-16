package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;
import org.junit.Test;

import java.io.IOException;
import java.time.Instant;
import java.time.LocalDate;

import static org.junit.Assert.*;

public class SgDisclosureLookupTest {
    private static final LocalDate DATE = LocalDate.parse("2026-11-16");
    private static final Instant CHECKED_AT = Instant.parse("2026-11-17T03:00:00Z");
    private static final String LEDGER = """
            {"schema":1,"symbol":"S63","records":[{
                "date":"2026-11-16", "shares":3115347115, "disclosed_at":"2026-11-16T18:21:27+08:00",
                "source":"https://links.sgx.com/1.0.0/corporate-announcements/EE91Z8VP8VZN8PJN/"
            }]}
            """;

    @Test public void savesVerifiedUpdateAndFallsBackOnlyForTheSameSessionOnTemporaryError() throws Exception {
        var online = new SgDisclosureLookup(null, "", CHECKED_AT, () -> LEDGER);
        assertEquals(SgDisclosureLookup.Source.ONLINE, online.forSession(DATE).source());
        assertEquals(LEDGER, online.verifiedUpdate());

        var requests = new java.util.concurrent.atomic.AtomicInteger();
        var fallback = new SgDisclosureLookup(null, online.verifiedUpdate(), CHECKED_AT, () -> {
            requests.incrementAndGet();
            throw new UsScanWorker.HttpFailure(503);
        });
        var result = fallback.forSession(DATE);
        assertEquals(SgDisclosureLookup.Source.CACHED, result.source());
        assertEquals(3_115_347_115L, result.disclosure().shares());
        assertThrows(IOException.class, () -> fallback.forSession(DATE.plusDays(1)));
        assertEquals(1, requests.get());
    }

    @Test public void onlineCorrectionOverridesBundledSharesAndLocalFallbackUsesIt() throws Exception {
        var bundled = new JSONObject(LEDGER);
        var corrected = LEDGER.replace("3115347115", "3115347000");
        var online = new SgDisclosureLookup(bundled, LEDGER, CHECKED_AT, () -> corrected);
        assertEquals(3_115_347_000L, online.forSession(DATE).disclosure().shares());

        SgDisclosureLookup.Fetch unavailable = () -> { throw new UsScanWorker.HttpFailure(503); };
        var cached = new SgDisclosureLookup(bundled, online.verifiedUpdate(), CHECKED_AT, unavailable);
        assertEquals(3_115_347_000L, cached.forSession(DATE).disclosure().shares());
        var freshInstall = new SgDisclosureLookup(bundled, "", CHECKED_AT, unavailable);
        assertEquals(SgDisclosureLookup.Source.BUNDLED, freshInstall.forSession(DATE).source());
    }

    @Test public void doesNotHideInvalidOrRemovedOnlineEvidence() throws Exception {
        var invalid = new SgDisclosureLookup(null, LEDGER, CHECKED_AT, () -> "{}");
        assertThrows(JSONException.class, () -> invalid.forSession(DATE));
        var forbidden = new SgDisclosureLookup(null, LEDGER, CHECKED_AT,
                () -> { throw new UsScanWorker.HttpFailure(403); });
        assertThrows(IOException.class, () -> forbidden.forSession(DATE));
        var bundled = new JSONObject(LEDGER);
        var removed = new SgDisclosureLookup(bundled, LEDGER, CHECKED_AT,
                () -> "{\"schema\":1,\"symbol\":\"S63\",\"records\":[]}");
        assertNull(removed.forSession(DATE).disclosure());
        assertNotNull(removed.verifiedUpdate());
        var offlineAfterRemoval = new SgDisclosureLookup(bundled, removed.verifiedUpdate(), CHECKED_AT,
                () -> { throw new UsScanWorker.HttpFailure(503); });
        assertThrows(IOException.class, () -> offlineAfterRemoval.forSession(DATE));
    }
}
