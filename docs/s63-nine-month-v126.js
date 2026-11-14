/* v126: read-only S63 SGX 9M2026 presentation context, not audited PER. */
"use strict";
(function(root){
 function validate(feed,original){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_eligible_count!==0||feed.ranking_enabled!==false||
     !Array.isArray(feed.records)||
     original?.schema_version!=="sgx-s63-9m2026-update-v125"||
     original.status!=="SGX_S63_OFFICIAL_NINE_MONTH_2026_PRESENTATION")
    throw Error("Incompatible S63 9M original / feed");
  const records=feed.records.filter(r=>r.symbol==="S63"),r=original.record;
  if(records.length!==1||!r||r.status!==original.status||
     r.symbol!=="S63"||r.report_date!=="2026-11-13"||
     r.period_end_date!=="2026-09-30"||
     r.nine_month_revenue_sgd_billion_rounded!==10||
     r.nine_month_reported_revenue_yoy_pct!==10||
     r.nine_month_contract_wins_sgd_billion_rounded!==13.2||
     r.order_book_2026_09_sgd_billion_rounded!==37.7||
     r.audited_income_and_profit_for_new_per_verified!==false||
     r.current_price_or_shares_verified!==false||
     r.ranking_eligible!==false||r.valuation_recomputed!==false||
     r.source_url!==original.source_url||
     !/^https:\/\/links\.sgx\.com\/FileOpen\//.test(r.source_url||"")||
     records[0].fiscal_year!==2025||
     records[0].ranking_eligible!==false)
    throw Error("S63 9M financial context did not match");
  return Object.freeze({
    source:r.source_url,period:r.period_end_date,
    revenueSgdBillion:10,revenueYoY:10,contractWinsSgdBillion:13.2,
    orderBookSgdBillion:37.7,
    note:"2026年1〜9月期の会社発表による売上成長・受注動向。金額は概数。監査済み通期損益や現在のPERの根拠ではない。"
  });
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root)root.S63NineMonthV126={validate};
})(typeof window!=="undefined"?window:null);
