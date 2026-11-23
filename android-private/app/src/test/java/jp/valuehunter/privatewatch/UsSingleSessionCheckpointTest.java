package jp.valuehunter.privatewatch;

import org.json.JSONObject;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class UsSingleSessionCheckpointTest {
    private static final String FIRST = "a".repeat(64);
    private static final String CORRECTED = "b".repeat(64);

    @Test public void sameCloseKeepsSavedProgressAndVerdicts() throws Exception {
        var old = new JSONObject().put("quote_sha256", FIRST)
                .put("after", 123456L).put("cursor", "ZZZ")
                .put("results", new JSONObject().put("ABC", "WITHIN"));
        var retained = UsSingleSessionBudgetCheck.matchingQuoteCheckpoint(old, FIRST);
        assertEquals("WITHIN", retained.getJSONObject("results").getString("ABC"));
        assertEquals("ZZZ", retained.getString("cursor"));
        assertEquals(123456L, retained.getLong("after"));
    }

    @Test public void correctedCloseDropsPreviousVerdictsCursorAndCooldown() throws Exception {
        var old = new JSONObject().put("quote_sha256", FIRST)
                .put("after", Long.MAX_VALUE).put("cursor", "ZZZ")
                .put("results", new JSONObject().put("ABC", "WITHIN"));
        var fresh = UsSingleSessionBudgetCheck.matchingQuoteCheckpoint(old, CORRECTED);
        assertEquals(CORRECTED, fresh.getString("quote_sha256"));
        assertFalse(fresh.has("results"));
        assertFalse(fresh.has("cursor"));
        assertFalse(fresh.has("after"));
        assertTrue(old.getJSONObject("results").has("ABC"));
    }

    @Test public void correctedBytesDuringScreeningCannotBePersistedAsOriginalEvidence() {
        byte[] original = "{\\"trading_date_et\\":\\"2026-11-17\\",\\"closes\\":[1]}".getBytes(java.nio.charset.StandardCharsets.UTF_8);
        byte[] correction = "{\\"trading_date_et\\":\\"2026-11-17\\",\\"closes\\":[2]}".getBytes(java.nio.charset.StandardCharsets.UTF_8);
        String initialHash = UsReferenceAlerts.sha256(original);
        assertTrue(UsSingleSessionBudgetCheck.matchesSavedQuote(initialHash, original));
        assertFalse(UsSingleSessionBudgetCheck.matchesSavedQuote(initialHash, correction));
        assertFalse(UsSingleSessionBudgetCheck.matchesSavedQuote("", original));
    }

    @Test public void legacyCheckpointCannotReuseVerdictsWithoutQuoteHash() throws Exception {
        var legacy = new JSONObject().put("results", new JSONObject().put("ABC", "OUTSIDE"))
                .put("after", Long.MAX_VALUE);
        var fresh = UsSingleSessionBudgetCheck.matchingQuoteCheckpoint(legacy, FIRST);
        assertFalse(fresh.has("results"));
        assertFalse(fresh.has("after"));
        assertEquals(FIRST, fresh.getString("quote_sha256"));
    }
}
