"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const data = JSON.parse(fs.readFileSync("docs/data/sgx-bank-corporate-actions-v190.json","utf8"));
function verify(d) {
  assert.equal(d.schema_version,"sgx-bank-corporate-actions-v190");
  assert.equal(d.ranking_eligible,false);
  assert.equal(d.financial_feed_modified,false);
  assert.equal(d.no_license_verified_quote,true);
  assert.equal(d.source_policy.licensed_timestamped_quotation_available,false);
  const observations=d.uob.observations;
  assert.equal(observations.length,2);
  for (const o of observations) {
    assert.equal(o.origin,"OFFICIAL_SGX_ANNOUNCEMENT_HTML");
    assert.equal(o.official_verified,true);
    assert.match(o.source_url,/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\//);
    assert.equal(o.cancelled,o.purchased);
    assert.equal(o.treasury_shares_after,14548000);
  }
  assert.equal(observations[0].announcement_reference,"SG261111OTHRGYNT");
  assert.equal(observations[1].announcement_reference,"SG261112OTHRSYPK");
  assert.equal(observations[0].issued_excluding_treasury_after,1646745591);
  assert.equal(observations[1].issued_excluding_treasury_after,1646711591);
  assert.equal(observations[0].issued_excluding_treasury_after - observations[1].issued_excluding_treasury_after,observations[1].cancelled);
  assert.equal(d.verified_as_of_date,observations.at(-1).date);
  assert.equal(d.uob.latest_unverified.official_verified,false);
  assert.equal(d.uob.latest_unverified.may_enter_ranking,false);
  assert.equal(d.ocbc.outstanding_change_notice.official_attachment_obtained,false);
  assert.equal(d.ocbc.outstanding_change_notice.share_change_verified,false);
  assert.equal(d.ocbc.outstanding_change_notice.may_enter_ranking,false);
  return true;
}
verify(data);
const promoted=structuredClone(data);
promoted.uob.latest_unverified.may_enter_ranking=true;
assert.throws(()=>verify(promoted));
const fabricated=structuredClone(data);
fabricated.uob.observations[1].issued_excluding_treasury_after++;
assert.throws(()=>verify(fabricated));
const rights=structuredClone(data);
rights.source_policy.licensed_timestamped_quotation_available=true;
assert.throws(()=>verify(rights));
const ocbc=structuredClone(data);
ocbc.ocbc.outstanding_change_notice.official_attachment_obtained=true;
assert.throws(()=>verify(ocbc));
console.log("v190 PASS: official UOB Nov11-Nov12 arithmetic; newer secondary share counts, OCBC PDF, quote rights and rankings remain blocked");
