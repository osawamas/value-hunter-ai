# VALUE HUNTER AI v483

The licensed SGX importer and both read-only preflights accept an optional
`daily_close_bearer_token` in the private `SGX_CLOSE_GRANT_JSON` secret
(or local grant file). When present, the importer sends it in the HTTPS
Authorization header. The candidate feed only receives the existing
public grant fields. The importer rejects malformed credentials before
retrieval and rejects redirects. Endpoints without a token keep working.

The local TLS fixture verifies the Authorization header, the unchanged
public result, rejection before fetch for malformed tokens, and that
redirects are not followed. A real licensed endpoint and independent
financial verification are still pending.
