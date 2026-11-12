# SGX PDF connection probe
This is an independent connectivity/parse test, **not** a production financial screener.

Run via GitHub Actions > SGX PDF connection probe > Run workflow.
Download artifact `sgx-connection-results` and inspect `report.json`.
A successful HTTP response is not sufficient: check `pdf_magic`, `extraction_ok`, and page count.
The script does NOT calculate PER/PBR or assert financial figures from ambiguous table columns.
It checks two known FY2026 Singapore Exchange Limited (S68) official PDF endpoints.
It does not measure all SGX listed companies. No API keys required.
