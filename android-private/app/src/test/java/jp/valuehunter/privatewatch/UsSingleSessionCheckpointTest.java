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

    @Test public void displayHidesOldVerdictsAfterQuoteOrListingRevision() throws Exception {
        byte[] rawQuote = "verified-quote".getBytes(java.nio.charset.StandardCharsets.UTF_8);
        byte[] corrected = "corrected-quote".getBytes(java.nio.charset.StandardCharsets.UTF_8);
        String hash = UsReferenceAlerts.sha256(rawQuote);
        String listing = "listing-v1";
        var saved = new JSONObject().put("quote_sha256", hash)
                .put("listing_sha256", listing)
                .put("results", new JSONObject().put("ABC", "WITHIN"));
        assertTrue(UsSingleSessionBudgetCheck.displayEvidenceMatches(saved, rawQuote, listing));
        assertFalse(UsSingleSessionBudgetCheck.displayEvidenceMatches(saved, corrected, listing));
        assertFalse(UsSingleSessionBudgetCheck.displayEvidenceMatches(saved, rawQuote, "listing-v2"));
        assertFalse(UsSingleSessionBudgetCheck.displayEvidenceMatches(
                new JSONObject().put("results", new JSONObject().put("ABC", "WITHIN")),
                rawQuote, listing));
    }

    @Test public void malformedSavedVerdictsAreRecheckedInsteadOfSkipped() throws Exception {
        var results = new JSONObject()
                .put("VALID_IN", "WITHIN")
                .put("VALID_OUT", "OUTSIDE")
                .put("TEXT", "UNKNOWN")
                .put("NUMBER", 1)
                .put("NULL", JSONObject.NULL)
                .put("WRONG_CASE", "within")
                .put("REMOVED", "WITHIN");
        var eligible = java.util.Set.of("VALID_IN", "VALID_OUT", "TEXT", "NUMBER", "NULL", "WRONG_CASE");
        UsSingleSessionBudgetCheck.discardInvalidVerdicts(results, eligible);
        assertEquals(2, results.length());
        assertEquals("WITHIN", results.getString("VALID_IN"));
        assertEquals("OUTSIDE", results.getString("VALID_OUT"));
        for (var code : java.util.List.of("TEXT", "NUMBER", "NULL", "WRONG_CASE", "REMOVED")) {
            assertFalse(results.has(code));
        }
    }

    @Test public void malformedEligibleVerdictSignalsImmediateRetryButRemovedSymbolDoesNot() throws Exception {
        var malformed = new JSONObject().put("A", "UNKNOWN").put("B", "WITHIN");
        assertTrue(UsSingleSessionBudgetCheck.discardInvalidVerdicts(
                malformed, java.util.Set.of("A", "B")));
        assertFalse(malformed.has("A"));
        assertEquals("WITHIN", malformed.getString("B"));

        var obsolete = new JSONObject().put("OLD", "OUTSIDE").put("B", "WITHIN");
        assertFalse(UsSingleSessionBudgetCheck.discardInvalidVerdicts(
                obsolete, java.util.Set.of("B")));
        assertFalse(obsolete.has("OLD"));
        assertEquals("WITHIN", obsolete.getString("B"));

        var clean = new JSONObject().put("B", "WITHIN");
        assertFalse(UsSingleSessionBudgetCheck.discardInvalidVerdicts(
                clean, java.util.Set.of("B")));
    }

    @Test public void corruptedDisplayVerdictsNeverBecomeOrdinaryWaitingCounts() throws Exception {
        assertTrue(UsSingleSessionBudgetCheck.validDisplayVerdicts(new JSONObject()
                .put("ABC", "WITHIN").put("DEF", "OUTSIDE"), 3));
        assertFalse(UsSingleSessionBudgetCheck.validDisplayVerdicts(new JSONObject()
                .put("ABC", "UNKNOWN"), 2));
        assertFalse(UsSingleSessionBudgetCheck.validDisplayVerdicts(new JSONObject()
                .put("ABC", JSONObject.NULL), 2));
        assertFalse(UsSingleSessionBudgetCheck.validDisplayVerdicts(new JSONObject()
                .put("ABC", "WITHIN").put("DEF", "OUTSIDE"), 1));
        assertFalse(UsSingleSessionBudgetCheck.validDisplayVerdicts(null, 2));
        assertFalse(UsSingleSessionBudgetCheck.validDisplayVerdicts(new JSONObject(), -1));
    }

    @Test public void priorClosePriceCorrectionInvalidatesBudgetEvenWithIdenticalSymbols() throws Exception {
        var venues = java.util.Map.of("ABC", "NYSE");
        var priorSymbols = java.util.Set.of("ABC");
        var groups = java.util.Map.of(MarketCoverage.Reason.FINANCIALS,
                java.util.List.of("ABC"));
        String oldPrior = UsReferenceAlerts.sha256(
                "ABC=9.10".getBytes(java.nio.charset.StandardCharsets.UTF_8));
        String correctedPrior = UsReferenceAlerts.sha256(
                "ABC=9.25".getBytes(java.nio.charset.StandardCharsets.UTF_8));
        String oldEvidence = UsSingleSessionBudgetCheck.listingEvidenceHash(
                venues, java.util.Set.of("ABC"), groups, priorSymbols, oldPrior);
        String newEvidence = UsSingleSessionBudgetCheck.listingEvidenceHash(
                venues, java.util.Set.of("ABC"), groups, priorSymbols, correctedPrior);
        assertFalse(oldEvidence.equals(newEvidence));
        var checkpoint = new JSONObject().put("quote_sha256", FIRST)
                .put("listing_sha256", oldEvidence)
                .put("results", new JSONObject().put("ABC", "WITHIN"))
                .put("after", Long.MAX_VALUE).put("cursor", "ABC");
        var invalidated = UsSingleSessionBudgetCheck.matchingEvidenceCheckpoint(
                checkpoint, FIRST, newEvidence);
        assertFalse(invalidated.has("results"));
        assertFalse(invalidated.has("after"));
        assertFalse(invalidated.has("cursor"));
        assertEquals(oldEvidence, UsSingleSessionBudgetCheck.listingEvidenceHash(
                venues, java.util.Set.of("ABC"), groups, priorSymbols, oldPrior));
    }

    @Test public void coverageDayAdvancingDuringFetchMustNotPersistPriorSessionResults() {
        var original = java.time.LocalDate.of(2026, 11, 17);
        var next = java.time.LocalDate.of(2026, 11, 18);
        assertTrue(UsSingleSessionBudgetCheck.sameCoverageDay(original, original));
        assertFalse(UsSingleSessionBudgetCheck.sameCoverageDay(original, next));
        assertFalse(UsSingleSessionBudgetCheck.sameCoverageDay(original, null));
        assertFalse(UsSingleSessionBudgetCheck.sameCoverageDay(null, original));
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
