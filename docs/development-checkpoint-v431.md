# VALUE HUNTER AI v431

SGX licensed closes can be prepared for the public feed using three JSON inputs:
the current feed, a provider quote array, and separately reviewed permission
evidence for that provider and product. The command writes a candidate feed to
stdout after all rows pass validation. The scheduled refresh continues to use
its existing source until a licensed feed is available.

    node scripts/stage-sgx-public-quotes.js docs/data/latest.json quotes.json grant.json

Each quote supplies `symbol`, `currency` (SGD), `close`, `source_type`
(LICENSED_SGX_EQUITY), `source_url`, `timestamp` and `ranking_score`.
The existing stock record must already clear its independent financial and
publication exclusions and contain ex-treasury shares dated to the Singapore
session. The staging command recalculates cap, PER and verified PBR and reruns
the shared publication validator. Do not redirect output to an input filename.

No provider has been connected and the published ranking has zero entries.
