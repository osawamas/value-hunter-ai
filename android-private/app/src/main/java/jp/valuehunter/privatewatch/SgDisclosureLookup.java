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

    enum Source {
        ONLINE(""),
        CACHED("開示台帳は端末に保存したデータを使用"),
        BUNDLED("開示台帳はアプリに同梱したデータを使用");

        final String note;

        Source(String note) {
            this.note = note;
        }
    }

    record Lookup(SgShareLedger.Disclosure disclosure, Source source) {}

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
        try {
            if (updateFailure != null) throw updateFailure;
            if (updated == null) {
                downloaded = fetch.get();
                updated = new JSONObject(downloaded);
            }
            var disclosure = SgShareLedger.read(updated, session, checkedAt);
            verifiedUpdate = downloaded;
            return new Lookup(disclosure, Source.ONLINE);
        } catch (IOException error) {
            updateFailure = error;
            int status = error instanceof UsScanWorker.HttpFailure failure ? failure.status : 0;
            if (SgCheckWorker.shouldRetry(status, 0)) {
                try {
                    boolean hasCache = !cache.isEmpty();
                    var local = hasCache ? new JSONObject(cache) : bundled;
                    if (local != null) {
                        var disclosure = SgShareLedger.read(local, session, checkedAt);
                        if (disclosure != null) return new Lookup(disclosure, hasCache ? Source.CACHED : Source.BUNDLED);
                    }
                } catch (JSONException ignored) {
                    // Report the retrieval failure when no local row can be verified.
                }
            }
            throw error;
        }
    }
}
