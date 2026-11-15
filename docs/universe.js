/* SGX issuer DISCOVERY (third-party only), v272 strict cross-source provenance join.
 * A source-level identity is not proof of current listing, finance quality or investability.
 */
"use strict";
(function(root){
 function validateUniverse(data){
  if(!data||data.schema_version!=="sgx-third-party-company-candidates-v99"||
    data.coverage!=="PARTIAL_UNVERIFIED"||
    data.full_sgx_listing_completeness_verified!==false||
    data.eligible_for_ranking!==false||
    data.records_not_added_to_verified_financial_feed!==true||
    !Array.isArray(data.candidates)||
    data.candidates.length!==data.provider_accepted_candidate_count||
    data.candidates.length<20||data.candidates.length>1200)
   throw Error("未検証の企業一覧が不正、または出典の検証状態が不明");
  const symbols=new Set();
  for(const row of data.candidates){
   if(typeof row.symbol!=="string"||!/^[A-Z0-9]{1,6}$/.test(row.symbol)||
      typeof row.display_name!=="string"||row.display_name.length<3||
      symbols.has(row.symbol)||row.financial_verification!==false||
      row.ranking_eligible!==false||
      row.source_verification!=="THIRD_PARTY_CANDIDATE_NOT_EXCHANGE_VERIFIED")
    throw Error("企業一覧の銘柄名・重複・検証状態に矛盾");
   symbols.add(row.symbol);
  }
  return data;
 }
 function joinCandidates(candidates,officialRows,feed){
  const validated=validateUniverse(candidates);
  if(!Array.isArray(officialRows)||officialRows.length!==30||
    officialRows.some(x=>x.ranking_eligible!==false||x.all_current_trading_verified!==false||
     !/^[A-Z0-9]{2,6}$/.test(x.code))||
    feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0||
    !Array.isArray(feed.records)||feed.records.length!==7||
    feed.records.some(x=>x.ranking_eligible!==false))
    throw Error("SGX research/finance candidate overlay evidence gate failed");
  const official=new Map();
  for(const x of officialRows){
   if(official.has(x.code))throw Error("Duplicate official source research code");
   official.set(x.code,x);
  }
  const finance=new Map();
  for(const r of feed.records){
   if(finance.has(r.symbol))throw Error("Duplicate finance symbol");
   finance.set(r.symbol,r);
  }
  return validated.candidates.map(row=>{
   const named=official.get(row.symbol);
   const financial=finance.get(row.symbol);
   return {symbol:row.symbol,name:row.display_name,officialHistoricalCode:Boolean(named),
    originalHtmlProof:Boolean(named?.directHtmlIdentityMatched),
    officialCodeSource:named?.source||null,
    financialRegistered:Boolean(financial),
    financialExclusionCount:financial?.exclusion_reasons?.length||0,
    listedCurrentlyVerified:false,rankingEligible:false};
  });
 }
 function filterCandidates(rows,query,sourceFilter="ALL"){
  const q=String(query||"").trim().toLocaleUpperCase("en");
  return rows.filter(r=>
    (sourceFilter==="ALL"||
     (sourceFilter==="OFFICIAL"&&r.officialHistoricalCode)||
     (sourceFilter==="FINANCIAL"&&r.financialRegistered)||
     (sourceFilter==="UNVERIFIED"&&!r.officialHistoricalCode&&!r.financialRegistered))&&
    (r.symbol+" "+r.name).toLocaleUpperCase("en").includes(q));
 }
 function make(tag,text,cls){
  const n=document.createElement(tag);
  if(cls)n.className=cls;
  if(text!==undefined)n.textContent=String(text);
  return n;
 }
 async function load(){
  const count=document.getElementById("universeCandidateCount");
  const status=document.getElementById("universeCandidateStatus");
  const search=document.getElementById("universeCandidateSearch");
  const body=document.getElementById("universeCandidateRows");
  const tableCount=document.getElementById("universeCandidateShown");
  const filter=document.getElementById("universeCandidateProvenance");
  if(!count||!status||!search||!body||!tableCount||!filter)return;
  try{
   const files=["./data/sgx-universe-candidates.json",
    "./data/sgx-corporate-indexed-page-v253.json",
    "./data/sgx-official-issuer-code-filings-v255.json",
    "./data/sgx-net-eleven-codes-v256.json",
    "./data/sgx-official-batch-seed-v196.json",
    "./data/sgx-material-listing-events-v257.json",
    "./data/latest.json",
    "./data/sgx-nineteen-original-html-sha-v262.json"];
   const loadJson=async url=>{
    const response=await fetch(url,{cache:"no-store"});
    if(!response.ok)throw Error("HTTP "+response.status);
    return response.json();
   };
   // Source classes fail independently: SGXNet failure must not hide the
   // unverified third-party discovery list. Never mark fallback rows verified.
   const candidates=validateUniverse(await loadJson(files[0]));
   let rows=candidates.candidates.map(item=>({
    symbol:item.symbol,name:item.display_name,officialHistoricalCode:false,
    originalHtmlProof:false,officialCodeSource:null,financialRegistered:false,
    financialExclusionCount:0,listedCurrentlyVerified:false,rankingEligible:false
   }));
   let sourceOverlayLoaded=false;
   try{
    const evidence=await Promise.all(files.slice(1).map(loadJson));
    const builder=root?.SGX_SOURCE_DIRECTORY_READONLY?.buildWithOriginalProof;
    if(typeof builder!=="function")throw Error("SGX original proof validator not loaded");
    const historic=builder(...evidence);
    rows=joinCandidates(candidates,historic,evidence[5]);
    sourceOverlayLoaded=true;
   }catch(err){
    console.warn("SGX primary-source overlay unavailable; 182 candidates shown without verified assertions:",err.message);
   }
   const known=rows.filter(x=>x.officialHistoricalCode).length;
   const financed=rows.filter(x=>x.financialRegistered).length;
   count.textContent=rows.length.toLocaleString("ja-JP");
   status.textContent=sourceOverlayLoaded?
    "第三者候補"+rows.length+"件中、SGX過去開示のコードと一致"+known+
    "件、財務登録あり"+financed+"件（重複あり）。現在の上場・投資適格は確認していない。":
    "第三者候補"+rows.length+"件のみ表示中。SGX原本・財務の照合が利用できず、確認済みの表示を一時停止している。";
   const repaint=()=>{
    const visible=filterCandidates(rows,search.value,filter.value);
    const frag=document.createDocumentFragment();
    for(const item of visible){
     const tr=make("tr");
     tr.append(make("td",item.symbol),make("td",item.name));
     const state=make("td",item.officialHistoricalCode?
      (item.originalHtmlProof?"SGXNet原本の過去コード一致":"SGX公式静的表の過去コード一致"):
      "第三者候補のみ・コード未照合");
     if(item.officialHistoricalCode&&item.officialCodeSource){
      const a=make("a","コード根拠を開く");
      a.href=item.officialCodeSource;a.target="_blank";a.rel="noopener noreferrer";
      state.append(make("span"," / "),a);
     }
     tr.append(state);
     const finance=make("td",item.financialRegistered?
      "財務登録済・ランキング除外":"財務未登録");
     if(item.financialRegistered){
      const a=make("a","財務詳細を見る");
      a.href="#issuer="+item.symbol;
      finance.append(make("span"," / "),a);
     }
     tr.append(finance);frag.append(tr);
    }
    if(!visible.length){
     const tr=make("tr"),td=make("td","該当候補なし");
     td.colSpan=4;tr.append(td);frag.append(tr);
    }
    body.replaceChildren(frag);
    tableCount.textContent=visible.length+"件表示 / 候補総数"+rows.length+
      "件。SGX公式全銘柄や現在上場の証明ではない。";
   };
   search.addEventListener("input",repaint);
   filter.addEventListener("change",repaint);
   repaint();
  }catch(error){
   status.textContent="候補・公式コード・財務の照合は利用できない。推測で情報を補完しない。";
   body.replaceChildren();
   const tr=make("tr"),td=make("td","検証できないため候補一覧を表示しない");
   td.colSpan=4;tr.append(td);body.append(tr);
   tableCount.textContent="取得不可";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validateUniverse,joinCandidates,filterCandidates};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",load);
})(typeof window!=="undefined"?window:null);
