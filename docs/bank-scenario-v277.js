/* v277: local-only scenario valuation calculator.
 * Historical banking accounting numbers from registered issuer PDF only.
 * User-input prices/shares are NOT an SGX licensed quote feed; NEVER ranking.
 */
"use strict";
(function(root){
 const isDate=x=>{
  if(typeof x!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(x))return false;
  const value=Date.parse(x+"T00:00:00Z");
  return Number.isFinite(value)&&new Date(value).toISOString().slice(0,10)===x;
 };
 const currentSchema="value_hunter_scenario_banks_v277";
 function getBank(finance,symbol){
  if(finance?.ranking_enabled!==false||finance.ranking_eligible_count!==0||
     !Array.isArray(finance.records)||finance.records.length!==7)throw Error("Finance source gate changed");
  const rec=finance.records.find(x=>x.symbol===symbol);
  if(!rec||rec.ranking_eligible!==false)return null;
  let source,sha,profit,equity,valid=false;
  if(symbol==="D05"){
   const b=rec.banking_evidence;
   valid=b?.status==="BANK_ISSUER_FY2025_GROUP_STATEMENTS_RECONCILED"&&
     b.fiscal_year===2025&&b.unit==="SGD_millions"&&
     b.independent_cross_source_verification===false;
   if(valid){source=b.source_url;sha=b.pdf_sha256;
     profit=b.income?.["2025"]?.profit_attributable_to_parent;
     equity=b.balance?.["2025"]?.parent_shareholders_funds;}
  } else if(symbol==="O39"||symbol==="U11"){
   const b=rec.banking_audited;
   valid=b?.status==="ISSUER_AUDITED_GROUP_STATEMENTS_MATCH_HIGHLIGHTS"&&
     b.period_end==="2025-12-31"&&b.unit==="SGD_millions"&&
     b.independent_cross_source_verification===false;
   if(valid){source=b.source_url;sha=b.pdf_sha256;
     profit=b.income?.parent_profit?.["2025"];
     equity=b.balance?.parent_equity?.["2025"];}
  }
  if(!valid||!/^https:\/\//.test(source||"")||
     !/^[a-f0-9]{64}$/.test(sha||"")||
     !Number.isFinite(profit)||!Number.isFinite(equity)||equity<=0)return null;
  return {symbol:rec.symbol,name:rec.issuer,year:2025,
   parentProfitMillion:profit,parentEquityMillion:equity,
   source,sourceSHA256:sha,independentlyVerified:false,rankingEligible:false};
 }
 function calculate(finance,input){
  if(!input||typeof input.symbol!=="string")throw Error("銘柄未指定");
  const bank=getBank(finance,input.symbol);
  if(!bank)throw Error("この銘柄の2025年銀行財務は試算対象外");
  if(typeof input.price!=="string"||!/^\d{1,6}(?:\.\d{1,4})?$/.test(input.price)||
    typeof input.shares!=="string"||!/^\d{1,15}$/.test(input.shares)||
    !isDate(input.priceAsOf)||!isDate(input.sharesAsOf)||
    input.priceSource!=="USER_MANUALLY_ENTERED_NOT_RELICENSED"||
    input.sharesBasis!=="ISSUED_EXCLUDING_TREASURY_USER_DECLARED")
   throw Error("株価・株数・基準日・出典区分が不正");
  const price=Number(input.price),shares=Number(input.shares);
  if(!Number.isSafeInteger(shares)||shares<=0||!Number.isFinite(price)||price<=0)
   throw Error("数量が範囲外");
  const marketCap=price*shares;
  const annualProfit=bank.parentProfitMillion*1e6;
  const equity=bank.parentEquityMillion*1e6;
  const per=annualProfit>0?marketCap/annualProfit:null;
  const pbr=marketCap/equity;
  if(!Number.isFinite(marketCap)||!Number.isFinite(pbr)||
     (per!==null&&!Number.isFinite(per)))throw Error("計算範囲外");
  const priceDate=new Date(input.priceAsOf+"T00:00:00Z").getTime();
  const sharesDate=new Date(input.sharesAsOf+"T00:00:00Z").getTime();
  const asOfConflict=priceDate!==sharesDate;
  const warnings=["株価・株数は利用者の手入力。取引所確認・利用許諾・現在の株数の検証とは無関係",
    "FY2025の発行体公表財務。独立した数値照合は未完了",
    "発行済株式数が自己株式控除後かどうかは利用者申告のみ",
    "株価の時点と2025年財務の会計期末が異なる。正式な投資指標として使用不可"];
  if(asOfConflict)warnings.unshift("株価日付と株数基準日が異なるため、評価結果は時点不一致");
  return {schema_version:currentSchema,bank,price,shares,
   quoteDate:input.priceAsOf,sharesDate:input.sharesAsOf,
   marketCapSgd:marketCap,referencePER:per,referencePBR:pbr,
   timeMismatch:asOfConflict,allInputSelfDeclared:true,
   quoteLicensingVerified:false,sharesIndependentlyVerified:false,
   financialIndependentlyVerified:false,rankingEligible:false,
   warnings};
 }
 const make=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
 async function render(){
  const form=document.getElementById("scenarioBankForm");
  const status=document.getElementById("scenarioBankStatus");
  const result=document.getElementById("scenarioBankResult");
  const picker=document.getElementById("scenarioBankSymbol");
  if(!form||!status||!result||!picker)return;
  let feed;
  try{
   const response=await fetch("./data/latest.json",{cache:"no-store"});
   if(!response.ok)throw Error("HTTP "+response.status);
   feed=await response.json();
   const options=["D05","O39","U11"].map(s=>getBank(feed,s));
   if(options.some(x=>!x))throw Error("銀行財務が未登録");
   for(const b of options){
    const option=document.createElement("option");option.value=b.symbol;
    option.textContent=b.symbol+" / "+b.name;picker.append(option);
   }
   status.textContent="銀行3社の2025年発行体公表財務を参考に、手入力の価格・株数で仮計算。データは送信・保存しない。";
  }catch(err){
   status.textContent="銀行財務データを検証できないため参考試算は使用不可";
   form.querySelector('button[type="submit"]').disabled=true;return;
  }
  form.addEventListener("submit",event=>{
   event.preventDefault();result.replaceChildren();
   try{
    const scenario=calculate(feed,{
     symbol:picker.value,
     price:form.elements.price.value,shares:form.elements.shares.value,
     priceAsOf:form.elements.priceAsOf.value,sharesAsOf:form.elements.sharesAsOf.value,
     priceSource:"USER_MANUALLY_ENTERED_NOT_RELICENSED",
     sharesBasis:"ISSUED_EXCLUDING_TREASURY_USER_DECLARED"
    });
    const digits=n=>new Intl.NumberFormat("ja-JP",{maximumFractionDigits:2}).format(n);
    const title=make("h3",scenario.bank.symbol+"：利用者入力による参考試算（正式ランキング対象外）");
    const summary=make("p","参考時価総額 "+digits(scenario.marketCapSgd/1e8)+
     " 億SGD / 参考PER "+(scenario.referencePER===null?"算出不可":digits(scenario.referencePER)+"倍")+
     " / 参考PBR "+digits(scenario.referencePBR)+"倍");
    const dates=make("p","株価基準日 "+scenario.quoteDate+"／株数基準日 "+scenario.sharesDate+
      "／利益・持分の会計年度 FY2025");
    const notes=document.createElement("ul");
    for(const w of scenario.warnings)notes.append(make("li",w));
    const link=make("a","FY2025 発行体公表資料を開く");
    link.href=scenario.bank.source;link.target="_blank";link.rel="noopener noreferrer";
    result.append(title,summary,dates,notes,link);
    status.textContent="参考試算のみ。正式ランキング・取得済み株価・Verified財務データは変更していない。";
   }catch(err){
    result.append(make("p","入力を確認： "+err.message));
    status.textContent="試算不成立。元の財務データは変更していない。";
   }
  });
 }
 if(root)root.VALUE_HUNTER_MANUAL_BANK_CALCULATE=calculate;
 if(typeof module!=="undefined"&&module.exports)module.exports={calculate,getBank,isDate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
