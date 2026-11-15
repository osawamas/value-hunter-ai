"use strict";
/* v292: keep official SGX issuer events distinct from non-original monthly claims.
 * This classification never infers IPO trading codes, individual listings,
 * licensed market data, or portfolio-ranking eligibility.
 */
const fs=require("node:fs"),path=require("node:path");
function assess(research,snapshot){
 const errors=[];
 if(!research || research.schema_version!=="sgx-october-official-release-research-v292" ||
    research.period!=="2026-10" || research.release_date!=="2026-11-12" ||
    !/^https:\/\/www\.sgxgroup\.com\/media-centre\//.test(research.issuer_owned_release_url||"") ||
    research.issuer_release_ipo_count!==2 ||
    !Array.isArray(research.issuer_release_confirmed_ipo_names) ||
    research.issuer_release_confirmed_ipo_names.length!==2)
   errors.push("official issuer release metadata or scoped IPO evidence invalid");
 if(research.original_sgx_monthly_statistics_pdf_url!==null ||
    research.original_monthly_statistics_sha256!==null ||
    research.original_sgxnet_pdf_url!==null ||
    research.original_sgxnet_pdf_sha256!==null)
   errors.push("missing original files must not receive fabricated original proof");
 const oct=research.sgx_securities_end_oct_2026_reported_605;
 const sep=research.sgx_securities_end_sep_2026_reported_604;
 for(const [name,claim,val] of [["oct",oct,605],["sep",sep,604]]){
  if(claim?.value!==val || claim?.status!=="SECONDARY_REPOST_NOT_SGX_ORIGINAL_PDF_VERIFIED" ||
     !/^https:\/\//.test(claim?.source_url||""))
   errors.push(name+" secondary claim incorrectly certified");
 }
 const aug=research.sgx_original_aug_2026_listings;
 if(aug?.mainboard!==406 || aug?.catalist!==198 || aug?.total!==604 ||
    aug?.mainboard+aug?.catalist!==aug?.total ||
    !/^https:\/\/links\.sgx\.com\//.test(research.sgx_original_aug_report_url||""))
   errors.push("august original monthly-count baseline corrupted");
 if(research.ranking_enabled!==false || research.ranking_eligible_count!==0 ||
    research.full_active_security_master_verified!==false ||
    research.price_redistribution_permitted!==false ||
    research.issuer_release_ipo_trading_codes!==null)
   errors.push("research may not promote market data or invent IPO codes");
 if(snapshot!==undefined){
   if(!snapshot || snapshot.schema_version!=="sgx-manual-security-list-staging-v199" ||
      snapshot.full_sgx_universe_verified!==false ||
      snapshot.ranking_enabled!==false || !Array.isArray(snapshot.items))
     errors.push("unknown or promoted security snapshot");
 }
 const assessedSnapshot=snapshot&&Array.isArray(snapshot.items)?{
  as_of_date:snapshot.as_of_date,
  candidate_rows:snapshot.items.length,
  classification:"UNVERIFIED_COUNTER_SNAPSHOT",
  comparable_to_official_aug_listing_count:false,
  reason:"Trading counters and SGX monthly listed securities differ in scope and as-of date; cannot infer completeness or IPOs"
 }:null;
 return {
  verdict:errors.length?"FAIL":"SOURCE_SCOPE_CHECK_PASS",
  errors,
  evidence:{october_ipo_names:research.issuer_release_confirmed_ipo_names,
   october_ipo_count:research.issuer_release_ipo_count,
   october_ipo_codes_verified:false,
   october_listing_count_official_original_verified:false,
   august_listing_count_official_original_published:aug?.total||null,
   october_secondary_count_reference:oct?.value||null},
  snapshot:assessedSnapshot,
  no_official_master_claim:true,no_price_rights_claim:true,ranking_eligible_count:0
 };
}
if(require.main===module){
 const doc=JSON.parse(fs.readFileSync(path.resolve(__dirname,"../docs/data/sgx-october-release-v292.json"),"utf8"));
 const result=assess(doc);
 if(result.errors.length){console.error(result.errors.join("\n"));process.exitCode=1}
 else console.log("v292 PASS: SGX issuer IPO announcement scoped; October 605 remains SECONDARY ONLY");
}
module.exports={assess};
