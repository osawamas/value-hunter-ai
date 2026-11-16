# VALUE HUNTER AI v492

A routine SGX refresh can use the validated closes that the provider
returns when some configured symbols are absent. It preserves those
symbols' existing records and logs each missing close. Strict runs
and preflight still require every configured symbol. An empty reply,
duplicate symbols or a batch with no usable close produces no new feed.

The HTTPS regression compares a missing G13 close with a returned but
ineligible G13 close and confirms the same S63 update in both cases.
Live licensed price access and independent financial verification remain
pending.
