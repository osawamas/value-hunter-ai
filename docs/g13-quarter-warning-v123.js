/* v123 Genting Singapore Q3 2026 official filing, unaudited risk warning. */
"use strict";
(function(root){
 function validate(feed,quarter){
  if(!feed||feed.schema_version!=="value_hunter_web_v29"||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     !Array.isArray(feed.records)||
     !quarter||quarter.schema_version!=="sgx-g13-2026q3-original-v121"||
     quarter.status!=="SGX_PRIMARY_2026Q3_UNAUDITED_BUSINESS_UPDATE")
   throw new Error("G13 financial evidence unavailable");
  const matches=feed.records.filter(x=>x.symbol==="G13");
  if(matches.length!==1)throw new Error("G13 not unique");
  const f=matches[0],r=quarter.record;
  if(!r||r.status!==quarter.status||
     r.quarter_end_date!=="2026-09-30"||
     r.revenue_2026q3_sgd_thousands!==566096||
     r.revenue_2025q3_sgd_thousands!==649790||
     r.net_profit_after_tax_2026q3_sgd_thousands!==54731||
     r.net_profit_after_tax_2025q3_sgd_thousands!==94618||
     r.financials_audited!==false||r.financials_reviewed!==false||
     r.older_fy_per_cannot_be_described_as_current!==true||
     r.ranking_eligible!==false||r.annual_profit_period_compatible_for_repricing!==false||
     !/^https:\/\/links\.sgx\.com\/FileOpen\//.test(r.source_url||"")||
     f.ranking_eligible!==false||f.fiscal_year!==2025||
     f.attributable_profit_sgd_thousands!==390346)
   throw new Error("G13 Q3 risk cannot be bound to this published record");
  return {symbol:"G13",revenue2026:r.revenue_2026q3_sgd_thousands,
   revenueYoY:r.revenue_yoy_pct,profit2026:r.net_profit_after_tax_2026q3_sgd_thousands,
   profitYoY:r.net_profit_yoy_pct,source:r.source_url,
   note:"2026年7〜9月期は減収・減益。未監査・未レビューの経営数値。2025年通期PERを現在の利益水準として扱わない。"};
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root)root.G13QuarterWarningV123={validate};
})(typeof window!=="undefined"?window:null);
