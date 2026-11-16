package jp.valuehunter.privatewatch;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.time.Instant;
import java.time.LocalDate;

final class SgDisclosureLookup {
    interface Fetch {
        String get() throws IOException;
    }

    record Lookup(SgShareLedger.Disclosure disclosure, boolean cached) {}

    private final JSONObject bundled;
    private final String cache;
    private final Instant checkedAt;
    private final Fetch fetch;
    private JSONObject updated;
    private String downloaded;
    private String verifiedUpdate;
    private IOException updateFailure;

    SgDisclosureLookup(JSONObject bundled, String cache, Instant checkedAt, Fetch fetch) {
        this.bundled = bundled;
        this.cache = cache;
        this.checkedAt = checkedAt;
        this.fetch = fetch;
    }

    String verifiedUpdate() {
        return verifiedUpdate;
    }

    Lookup forSession(LocalDate session) throws IOException, JSONException {
        if (bundled != null) {
            try {
                var disclosure = SgShareLedger.read(bundled, session, checkedAt);
                if (disclosure != null) return new Lookup(disclosure, false);
            } catch (JSONException ignored) {
                // A bad bundled row can be replaced by a verified row from the updated ledger.
            }
        }
        try {
            if (updateFailure != null) throw updateFailure;
            if (updated == null) {
                downloaded = fetch.get();
                updated = new JSONObject(downloaded);
            }
            var disclosure = SgShareLedger.read(updated, session, checkedAt);
            verifiedUpdate = downloaded;
            return new Lookup(disclosure, false);
        } catch (IOException error) {
            updateFailure = error;
            int status = error instanceof UsScanWorker.HttpFailure failure ? failure.status : 0;
            if (!cache.isEmpty() && SgCheckWorker.shouldRetry(status, 0)) {
                try {
                    var disclosure = SgShareLedger.read(new JSONObject(cache), session, checkedAt);
                    if (disclosure != null) return new Lookup(disclosure, true);
                } catch (JSONException ignored) {
                    // Keep the original retrieval error if the cached row cannot be verified.
                }
            }
            throw error;
        }
    }
}
