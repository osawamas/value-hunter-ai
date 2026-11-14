/* v100: SGX candidate issuer directory, kept separate from verified 7-stock feed.
 * Neither candidate presence nor source market capitalization is a verified
 * ticker, price, accounting number, or an investable recommendation.
 */
"use strict";
(function() {
 function validateUniverse(data) {
  if (!data || data.schema_version!=="sgx-third-party-company-candidates-v99" ||
      data.coverage!=="PARTIAL_UNVERIFIED" ||
      data.full_sgx_listing_completeness_verified!==false ||
      data.eligible_for_ranking!==false ||
      data.records_not_added_to_verified_financial_feed!==true ||
      !Array.isArray(data.candidates) ||
      data.candidates.length!==data.provider_accepted_candidate_count ||
      data.candidates.length<20 || data.candidates.length>1200) {
   throw new Error("未検証の企業一覧が不正、または出典の検証状態が不明");
  }
  const symbols=new Set();
  for (const row of data.candidates) {
   if (typeof row.symbol!=="string" ||
       !/^[A-Z0-9]{1,6}$/.test(row.symbol) ||
       typeof row.display_name!=="string" ||
       row.display_name.length<3 ||
       symbols.has(row.symbol) ||
       row.financial_verification!==false ||
       row.ranking_eligible!==false ||
       row.source_verification!=="THIRD_PARTY_CANDIDATE_NOT_EXCHANGE_VERIFIED") {
    throw new Error("企業一覧の銘柄名・重複・検証状態に矛盾");
   }
   symbols.add(row.symbol);
  }
  return data;
 }
 function make(tag,text,cls) {
  const n=document.createElement(tag);
  if (cls)n.className=cls;
  if (text!==undefined)n.textContent=String(text);
  return n;
 }
 async function load() {
  const count=document.getElementById("universeCandidateCount");
  const status=document.getElementById("universeCandidateStatus");
  const search=document.getElementById("universeCandidateSearch");
  const body=document.getElementById("universeCandidateRows");
  const tableCount=document.getElementById("universeCandidateShown");
  if (!count || !status || !search || !body || !tableCount)return;
  let payload=null;
  try {
   const response=await fetch("./data/sgx-universe-candidates.json",{cache:"no-store"});
   if (!response.ok)throw new Error("HTTP "+response.status);
   payload=validateUniverse(await response.json());
  } catch(error) {
   status.textContent="銘柄候補台帳はまだ取得できていない。検証済み7社の比較画面はそのまま利用できる。";
   return;
  }
  count.textContent=payload.candidates.length.toLocaleString("ja-JP");
  status.textContent="第三者APIから取得した不完全な候補一覧。取引所公式の全銘柄一覧ではない。既存の検証済み7社とは別管理。";
  const repaint=()=>{
   const query=search.value.trim().toUpperCase();
   const matching=payload.candidates.filter(r=>(r.symbol+" "+r.display_name).toUpperCase().includes(query));
   body.replaceChildren();
   for (const item of matching.slice(0,100)) {
    const tr=make("tr");
    const a=make("td",item.symbol);
    const b=make("td",item.display_name);
    const c=make("td","候補・財務未検証");
    tr.append(a,b,c);
    body.append(tr);
   }
   if (!matching.length) {
    const tr=make("tr"),td=make("td","該当候補なし");
    td.colSpan=3;tr.append(td);body.append(tr);
   }
   tableCount.textContent=matching.length+"件一致（画面表示は最大100件） / 候補総数"+payload.candidates.length+"件";
  };
  search.addEventListener("input",repaint);
  repaint();
 }
 if (typeof module!=="undefined" && module.exports)
  module.exports={validateUniverse};
 if(typeof document!=="undefined")document.addEventListener("DOMContentLoaded",load);
})();
