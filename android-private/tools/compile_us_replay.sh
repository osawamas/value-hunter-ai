#!/usr/bin/env bash
set -euo pipefail
dir=$1
cd "$(dirname "$0")/.."
src=app/src/main/java/jp/valuehunter/privatewatch
# The replay does not invoke outcome tracking. Stub only its Android-bound
# type references so the pure-Java replay can compile outside Android.
cat > "$dir/AlertOutcomes.java" <<'JAVA'
package jp.valuehunter.privatewatch;
import java.time.LocalDate;
final class AlertOutcomes {
    static final int MAX_BATCH = 32;
    record Window(LocalDate entry, LocalDate exit) {}
    record Prices(double entry, double exit) {}
    static boolean validSymbol(String symbol) {
        return symbol.matches("[A-Z0-9.$+^=/_-]{1,24}");
    }
}
JAVA
javac --release 17 -cp "$dir/json.jar" -d "$dir/classes" \
  "$src"/{UsFinancialFacts,UsDeviceFinancials,UsReferenceAlerts,ValueCandidateScreen,UsDoltCloses,UsScreen,UsDailyValuation,UsMarketCoverage,JapanScreen,UsDailyCloses,UsNasdaqOfficialClose,UsMonthlyHistory,UsSingleSessionBudget,ValueAlertMeter,FlexibleValueMeter,UsDisclosureEvidence}.java \
  "$dir/AlertOutcomes.java" tools/{UsRetryReplay,UsDatedRetryReplay,UsLiveCoverage}.java
