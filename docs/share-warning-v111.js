/* v111: supplementary warning; never replace financial-feed quantities. */
"use strict";
(function(root) {
  function validateShareWarning(feed, sidecar) {
    if (!feed || !Array.isArray(feed.records) || !sidecar ||
        sidecar.schema_version !== "sgx-share-snapshot-difference-v110" ||
        sidecar.symbol !== "S63" ||
        sidecar.new_sgx_primary_announcement_reference !== "SG261113OTHRPXGV" ||
        sidecar.new_sgx_primary_snapshot_date !== "2026-11-13" ||
        sidecar.published_reference_is_older !== true ||
        sidecar.current_shares_verified !== false ||
        sidecar.price_or_per_pbr_recomputed !== false ||
        sidecar.financial_feed_modified !== false ||
        sidecar.ranking_eligible !== false) {
      throw new Error("Historical share-snapshot warning cannot be trusted");
    }
    const matches=feed.records.filter(x=>x.symbol==="S63");
    if (matches.length!==1)throw new Error("S63 not unique in current feed");
    const s=matches[0];
    if (!Number.isSafeInteger(s.shares_outstanding) ||
        s.shares_outstanding!==sidecar.published_financial_shares ||
        s.shares_as_of_date!==sidecar.published_financial_record_as_of_date ||
        !Number.isSafeInteger(sidecar.new_sgx_primary_issued_ex_treasury) ||
        sidecar.new_sgx_primary_issued_ex_treasury<=0 ||
        sidecar.new_sgx_primary_issued_ex_treasury-sidecar.published_financial_shares!==
          sidecar.new_minus_published_shares ||
        !/^https:\/\/links\.sgx\.com\//.test(sidecar.new_sgx_primary_source_url || "")) {
      throw new Error("Historical share-snapshot warning does not match live financial record");
    }
    return Object.freeze({
      symbol:"S63",
      oldDate:s.shares_as_of_date,
      newDate:sidecar.new_sgx_primary_snapshot_date,
      oldShares:s.shares_outstanding,
      newShares:sidecar.new_sgx_primary_issued_ex_treasury,
      delta:sidecar.new_minus_published_shares,
      sourceUrl:sidecar.new_sgx_primary_source_url
    });
  }
  const api={validateShareWarning};
  if (typeof module!=="undefined"&&module.exports)module.exports=api;
  if (root)root.ShareAuditV111=api;
})(typeof window!=="undefined"?window:null);
