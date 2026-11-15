/* v285 local reference valuation side-by-side, never a live investment ranking.
 * No quote retrieval, price redistribution, saved user input or feed mutation.
 */
"use strict";
(function(root){
 const symbols=["D05","O39","U11"];
 function compareManual(finance,entries){
  if(finance?.ranking_enabled!==false||finance.ranking_eligible_count!==0||
     !Array.isArray(finance.records)||finance.records.length!==7||
     !Array.isArray(entries)||entries.length!==3)
   throw Error("試算対象の銀行または財務根拠が不正");
  const calc=typeof module!=="undefined"&&module.exports?
    require("./bank-scenario-v277.js").calculate:
    root?.VALUE_HUNTER_MANUAL_BANK_CALCULATE;
  if(typeof calc!=="function")throw Error("単一銀行の試算検証器が未接続");
  if(new Set(entries.map(e=>e?.symbol)).size!==3||
     entries.some(e=>!symbols.includes(e?.symbol)))
   throw Error("3銘柄が重複・欠落している");
  const rows=entries.map(input=>calc(finance,{
   symbol:input.symbol,price:input.price,shares:input.shares,
   priceAsOf:input.priceAsOf,sharesAsOf:input.sharesAsOf,
   priceSource:"USER_MANUALLY_ENTERED_NOT_RELICENSED",
   sharesBasis:"ISSUED_EXCLUDING_TREASURY_USER_DECLARED"
  }));
  const dates=new Set(rows.map(x=>x.quoteDate));
  const stocksDates=new Set(rows.map(x=>x.sharesDate));
  const crossCompanyDateMismatch=dates.size!==1||stocksDates.size!==1||
   rows.some(x=>x.timeMismatch);
  return {schema_version:"value_hunter_manual_bank_compare_v285",
   rows:rows.map(x=>({
    symbol:x.bank.symbol,name:x.bank.name,
    quoteDate:x.quoteDate,sharesDate:x.sharesDate,
    estimatedMarketCapSgd:x.marketCapSgd,illustrativePER:x.referencePER,
    illustrativePBR:x.referencePBR,
    underlyingIssuerProfitMillion:x.bank.parentProfitMillion,
    underlyingIssuerEquityMillion:x.bank.parentEquityMillion,
    issuerSource:x.bank.source,issuerSourceSHA256:x.bank.sourceSHA256,
    sourceOfficialIssuerNotIndependent:true,
    sharesBasisSelfDeclared:true,quoteSelfDeclared:true,
    rankingEligible:false
   })).sort((a,b)=>a.illustrativePBR-b.illustrativePBR),
   crossCompanyDateMismatch,
   rankedInvestmentRecommendation:false,
   licensedMarketQuotesAvailable:false,
   independentFinancialEvidenceComplete:false,
   comparisonIsIllustrativeOnly:true
  };
 }
 function el(tag,text){
  const n=document.createElement(tag);
  if(text!==undefined)n.textContent=String(text);
  return n;
 }
 async function load(){
  const form=document.getElementById("manualBankCompareForm");
  const result=document.getElementById("manualBankCompareResults");
  const status=document.getElementById("manualBankCompareStatus");
  if(!form||!result||!status)return;
  let finance;
  try{
   const response=await fetch("./data/latest.json",{cache:"no-store"});
   if(!response.ok)throw Error("HTTP "+response.status);
   finance=await response.json();
   if(finance.ranking_enabled!==false||finance.ranking_eligible_count!==0||
      finance.records?.length!==7)
    throw Error("財務源の検証が不十分");
   status.textContent="株価と自己株式控除後の株数・基準日を3社分入力。データは送信・保存されず、正式な割安ランキングではない。";
  }catch{
   status.textContent="3銀行の財務根拠を取得できないため試算不可";
   form.querySelector("button[type=submit]").disabled=true;
   return;
  }
  form.addEventListener("submit",event=>{
   event.preventDefault();result.replaceChildren();
   try{
    const entries=symbols.map(symbol=>({
     symbol,
     price:form.elements["price"+symbol].value.trim(),
     shares:form.elements["shares"+symbol].value.trim(),
     priceAsOf:form.elements["priceDate"+symbol].value,
     sharesAsOf:form.elements["sharesDate"+symbol].value
    }));
    const compare=compareManual(finance,entries);
    const table=document.createElement("table");
    const head=document.createElement("thead"),header=document.createElement("tr");
    for(const text of ["銘柄","参考PER","参考PBR","参考時価総額（億SGD）","入力株価日／株数日","発行体資料"]){
     header.append(el("th",text));
    }
    head.append(header);table.append(head);
    const tbody=document.createElement("tbody");
    const fmt=n=>new Intl.NumberFormat("ja-JP",{maximumFractionDigits:2}).format(n);
    for(const rec of compare.rows){
     const tr=document.createElement("tr");
     for(const text of [rec.symbol,rec.illustrativePER===null?"算出不可":fmt(rec.illustrativePER)+"倍",
      fmt(rec.illustrativePBR)+"倍",fmt(rec.estimatedMarketCapSgd/1e8),
      rec.quoteDate+" / "+rec.sharesDate])tr.append(el("td",text));
     const td=document.createElement("td"),a=el("a","FY2025原本PDF");
     a.href=rec.issuerSource;a.target="_blank";a.rel="noopener noreferrer";
     a.title=rec.issuerSourceSHA256;td.append(a);tr.append(td);tbody.append(tr);
    }
    table.append(tbody);
    result.append(el("h3","手入力による参考PBRの低い順（投資推奨・正式ランキングではない）"));
    if(compare.crossCompanyDateMismatch)
     result.append(el("p","警告：銀行間の株価・株数の基準日が一致していない。比較の時点が異なる。"));
    result.append(table);
    result.append(el("p","3社とも自己株式控除後株数は入力者申告。独立財務検証なし・株価の利用権未確認。FY2025財務と異なる時点の数値を混在させた参考値であり、正式な投資ランキングには反映しない。"));
    status.textContent="端末内で参考試算した。正式ランキング適格0社は変更していない。";
   }catch(err){
    result.append(el("p","試算不可： "+err.message));
    status.textContent="入力不備。正式なランキング・財務・株価データへの変更はない。";
   }
  });
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={compareManual};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",load);
})(typeof window!=="undefined"?window:null);
