# VALUE HUNTER AI v392 — Validate SGX ranking data at each refresh

The daily SGX refresh applies the existing ranking provenance and market-data license validator to the generated feed before recording history. The publish step checks the resulting feed again after rebasing onto main and before every push. A validation failure stops the refresh from publishing the invalid feed.

The validator checks the same Singapore date for the closing-price timestamp and the share count on eligible rows, along with the existing ranking provenance and license evidence. The current feed still has zero eligible rows. Public daily close usage rights and two consecutive authenticated refreshes of a public-use feed remain open.
