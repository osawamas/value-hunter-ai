/* v283: issuer-source FY2024/FY2025 bank comparisons.
 * Audit figures are sourced from each bank annual report, not independently
 * cross-verified; never infer quoted price, stock ranking or company-wide SGX
 * source coverage from this historical group-level view.
 */
"use strict";
(function(root){
 function one(finance,code){
  if(finance?.ranking_enabled!==false||finance.ranking_eligible_count!==0||
     !Array.isArray(finance.records)||finance.records.length!==7)return null;
  const rec=finance.records.find(x=>x.symbol===code);
  if(!rec||rec.ranking_eligible!==false)return null;
  let income,profits,parents,assets,src,sha,valid=false;
  if(code==="D05"){
   const b=rec.banking_evidence;
   valid=b?.status==="BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED"&&
    b.fiscal_year===2025&&b.unit==="SGD_millions"&&
    b.independent_cross_source_verification===false;
   if(valid){
    income=[b.income?.["2024"]?.total_income,b.income?.["2025"]?.total_income];
    profits=[b.income?.["2024"]?.profit_attributable_to_parent,b.income?.["2025"]?.profit_attributable_to_parent];
    parents=[b.balance?.["2024"]?.parent_shareholders_funds,b.balance?.["2025"]?.parent_shareholders_funds];
    assets=[b.balance?.["2024"]?.total_assets,b.balance?.["2025"]?.total_assets];
    src=b.source_url;sha=b.pdf_sha256;
   }
  }else if(code==="O39"||code==="U11"){
   const b=rec.banking_audited;
   valid=b?.status==="ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS"&&
    b.period_end==="2025-12-31"&&b.unit==="SGD_millions"&&
    b.independent_cross_source_verification===false;
   if(valid){
    income=[b.income?.total_income?.["2024"],b.income?.total_income?.["2025"]];
    profits=[b.income?.parent_profit?.["2024"],b.income?.parent_profit?.["2025"]];
    parents=[b.balance?.parent_equity?.["2024"],b.balance?.parent_equity?.["2025"]];
    assets=[b.balance?.total_assets?.["2024"],b.balance?.total_assets?.["2025"]];
    src=b.source_url;sha=b.pdf_sha256;
   }
  }
  if(!valid||!/^https:\/\//.test(src||"")||!/^[a-f0-9]{64}$/.test(sha||"")||
     ![...income,...profits,...parents,...assets].every(Number.isFinite)||
     income.some(x=>x<=0)||parents.some(x=>x<=0)||assets.some(x=>x<=0)||
     income.some((x,i)=>x>=assets[i])||
     profits.some((p,i)=>p>income[i])||
     parents.some((p,i)=>p>=assets[i]))return null;
  const pct=(a,b)=>b===0?null:(a/b-1)*100;
  const roeProxy=profits[1]/((parents[0]+parents[1])/2)*100;
  return {code,name:rec.issuer,unit:"SGD_millions",year:2025,
   totalIncome2024:income[0],totalIncome2025:income[1],
   incomeGrowthPct:pct(income[1],income[0]),
   parentProfit2024:profits[0],parentProfit2025:profits[1],
   profitGrowthPct:pct(profits[1],profits[0]),
   parentEquity2024:parents[0],parentEquity2025:parents[1],
   parentEquityGrowthPct:pct(parents[1],parents[0]),
   assets2024:assets[0],assets2025:assets[1],
   approximateAverageEquityROEPct:roeProxy,
   source:src,pdfSHA256:sha,
   sourceYear:2025,independentSecondSourceConfirmed:false,
   marketPriceUsed:false,currentShareCountVerified:false,
   investorRankingEligible:false};
 }
 function compare(finance){
  const rows=["D05","O39","U11"].map(s=>one(finance,s));
  if(rows.some(x=>!x)||new Set(rows.map(x=>x.code)).size!==3)
   throw Error("銀行3社の年次報告書が整合しないため比較を停止");
  return rows;
 }
 const cell=(tag,value)=>{const el=document.createElement(tag);el.textContent=String(value);return el;};
 async function mount(){
  const tbody=document.getElementById("bankAnnualCompareRows");
  const status=document.getElementById("bankAnnualCompareStatus");
  if(!tbody||!status)return;
  try{
   const response=await fetch("./data/latest.json",{cache:"no-store"});
   if(!response.ok)throw Error("HTTP "+response.status);
   const rows=compare(await response.json());
   const fmt=n=>new Intl.NumberFormat("ja-JP",{maximumFractionDigits:2}).format(n);
   const fragment=document.createDocumentFragment();
   for(const r of rows){
    const tr=document.createElement("tr");
    for(const value of [r.code,r.name,fmt(r.totalIncome2025),
     fmt(r.incomeGrowthPct)+"%",fmt(r.parentProfit2025),
     fmt(r.profitGrowthPct)+"%",fmt(r.parentEquity2025),
     fmt(r.approximateAverageEquityROEPct)+"%"])
     tr.append(cell("td",value));
    const td=document.createElement("td"),a=cell("a","FY2025原本PDF");
    a.href=r.source;a.target="_blank";a.rel="noopener noreferrer";
    a.title="原本SHA256："+r.pdfSHA256;
    td.append(a);tr.append(td);fragment.append(tr);
   }
   tbody.replaceChildren(fragment);
   status.textContent="発行体FY2025資料を比較。前年比はFY2024比、ROE参考値は2025年利益÷2024/25年末親会社持分平均。独立再照合・最新株価・正式ランキング未対応。";
  }catch(error){
   const tr=document.createElement("tr"),td=cell("td","財務原本の整合が取れないため非表示");
   td.colSpan=9;tr.append(td);tbody.replaceChildren(tr);
   status.textContent="銀行財務の比較は利用不可。未検証の数値を表示しない。";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={compare,one};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",mount);
})(typeof window!=="undefined"?window:null);
