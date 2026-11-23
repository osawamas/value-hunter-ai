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
        byte[] original = "original-session-price".getBytes(java.nio.charset.StandardCharsets.UTF_8);
        byte[] correction = "corrected-session-price".getBytes(java.nio.charset.StandardCharsets.UTF_8);
        String initialHash = UsReferenceAlerts.sha256(original);
        assertTrue(UsSingleSessionBudgetCheck.matchesSavedQuote(initialHash, original));
        assertFalse(UsSingleSessionBudgetCheck.matchesSavedQuote(initialHash, correction));
        assertFalse(UsSingleSessionBudgetCheck.matchesSavedQuote("", original));
    }

    @Test public void sameQuoteWithNewListingEvidenceDiscardsOldBudgetResults() throws Exception {
        var listing = UsSingleSessionBudgetCheck.listingEvidenceHash(
                java.util.Map.of("ABC", "NYSE"), java.util.Set.of("ABC"),
                java.util.Map.of(MarketCoverage.Reason.FINANCIALS, java.util.List.of("ABC")),
                java.util.Set.of("ABC"));
        var reordered = UsSingleSessionBudgetCheck.listingEvidenceHash(
                java.util.Map.of("ABC", "NYSE"), java.util.Set.of("ABC"),
                java.util.Map.of(MarketCoverage.Reason.FINANCIALS, java.util.List.of("ABC")),
                java.util.Set.of("ABC"));
        var changed = UsSingleSessionBudgetCheck.listingEvidenceHash(
                java.util.Map.of("ABC", "NASDAQ"), java.util.Set.of("ABC"),
                java.util.Map.of(MarketCoverage.Reason.FINANCIALS, java.util.List.of("ABC")),
                java.util.Set.of("ABC"));
        assertEquals(listing, reordered);
        assertFalse(listing.equals(changed));
        var old = new JSONObject().put("quote_sha256", FIRST).put("listing_sha256", listing)
                .put("cursor", "ABC").put("after", Long.MAX_VALUE)
                .put("results", new JSONObject().put("ABC", "WITHIN"));
        var retained = UsSingleSessionBudgetCheck.matchingEvidenceCheckpoint(old, FIRST, listing);
        assertEquals("WITHIN", retained.getJSONObject("results").getString("ABC"));
        var invalidated = UsSingleSessionBudgetCheck.matchingEvidenceCheckpoint(old, FIRST, changed);
        assertFalse(invalidated.has("results"));
        assertFalse(invalidated.has("cursor"));
        assertFalse(invalidated.has("after"));
        assertEquals(FIRST, invalidated.getString("quote_sha256"));
    }

    @Test public void changesInPriorEvidenceOrCoverageInvalidateCheckpoint() throws Exception {
        var old = UsSingleSessionBudgetCheck.listingEvidenceHash(
                java.util.Map.of("ABC", "NYSE"), java.util.Set.of(),
                java.util.Map.of(MarketCoverage.Reason.CLOSE, java.util.List.of("ABC")),
                java.util.Set.of());
        var priorNowPresent = UsSingleSessionBudgetCheck.listingEvidenceHash(
                java.util.Map.of("ABC", "NYSE"), java.util.Set.of(),
                java.util.Map.of(MarketCoverage.Reason.CLOSE, java.util.List.of("ABC")),
                java.util.Set.of("ABC"));
        var reasonChanged = UsSingleSessionBudgetCheck.listingEvidenceHash(
                java.util.Map.of("ABC", "NYSE"), java.util.Set.of(),
                java.util.Map.of(MarketCoverage.Reason.DATED_LISTING, java.util.List.of("ABC")),
                java.util.Set.of());
        assertFalse(old.equals(priorNowPresent));
        assertFalse(old.equals(reasonChanged));
        var legacy = new JSONObject().put("quote_sha256", FIRST)
                .put("results", new JSONObject().put("ABC", "OUTSIDE"));
        assertFalse(UsSingleSessionBudgetCheck.matchingEvidenceCheckpoint(legacy, FIRST, old)
                .has("results"));
    }

    @Test public void evidenceChangeDuringFetchMustBlockCheckpointCommit() {
        var before = UsSingleSessionBudgetCheck.listingEvidenceHash(
                java.util.Map.of("ABC", "NYSE"), java.util.Set.of("ABC"),
                java.util.Map.of(MarketCoverage.Reason.CLOSE, java.util.List.of("ABC")),
                java.util.Set.of());
        var after = UsSingleSessionBudgetCheck.listingEvidenceHash(
                java.util.Map.of("ABC", "NYSE"), java.util.Set.of("ABC"),
                java.util.Map.of(MarketCoverage.Reason.CLOSE, java.util.List.of("ABC")),
                java.util.Set.of("ABC"));
        assertTrue(UsSingleSessionBudgetCheck.matchesEvidenceHash(before, before));
        assertFalse(UsSingleSessionBudgetCheck.matchesEvidenceHash(before, after));
        assertFalse(UsSingleSessionBudgetCheck.matchesEvidenceHash("", before));
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
