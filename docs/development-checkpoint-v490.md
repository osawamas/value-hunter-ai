# VALUE HUNTER AI v490

The browser and publication validator now recalculate the age of ranked
SGX closes from their timestamps and the snapshot's quality-check time.
A close older than seven days cannot pass validation even if its freshness
label still says RECENT. The same calculation is shared with the importer.
The existing one-day future tolerance is unchanged. Archived snapshots
are evaluated against their saved check time so offline replay is stable.

The tests cover the exact seven-day boundary, one second beyond it, a
missing or invalid check time and a close beyond the future tolerance.
Licensed live SGX closes and independent financial verification are
still pending.
