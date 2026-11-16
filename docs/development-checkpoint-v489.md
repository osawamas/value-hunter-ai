# VALUE HUNTER AI v489

The SGX importer now rejects closes older than seven days at the feed's
quality-check timestamp before they can enter the public ranking. It
also rejects an invalid timestamp on the feed. Previously a close could
be marked stale and still be published as ranking eligible. Shared
ranking validation now rejects stale or missing prices on ranked rows.

The read-only historical comparison can still report a valuation and
its separate publication error. The live licensed SGX close source and
independent financial verification remain pending.
