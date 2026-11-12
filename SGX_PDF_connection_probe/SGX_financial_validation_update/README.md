# SGX financial validation — GitHub Actions update

Upload the contents of this ZIP to the **repository root**, preserving `SGX_PDF_connection_probe/` and `.github/workflows/`.

Run Actions > SGX PDF connection probe > Run workflow.

Download `sgx-connection-results` artifact. Inspect `results/report.json` and `results/S68_verified_financials.json` (only emitted if the PDF passes strict S68 FY2026 regression validation).

**Limitations**: This is an S68-specific real-PDF extraction test, not a general SGX annual statement parser and not an Android app integration. It deliberately fails closed if the PDF layout differs or values cannot be verified. The expected values were transcribed from the official FY2026 income statement and thus do not constitute independent cross-source verification. The program never fabricates missing balance-sheet metrics, PER, PBR, or debt ratio.
