# VALUE HUNTER AI v412 — Expose the denominators behind trial valuations

Representative JSON reports and the research page's local batch CSV now include the reported annual net income and parent equity used for PER and PBR. The amounts use the row's local currency and existing annual reporting period. The browser appends these two columns after the existing export fields. Rows without a company-level calculation leave the added columns blank.

Regression checks recompute the ratios for Toyota, IBM and ST Engineering, including the SGX thousands-to-dollars conversion. The browser regression verifies the Toyota denominators in a filtered batch export. Public daily price rights and consecutive authenticated price updates remain open.
