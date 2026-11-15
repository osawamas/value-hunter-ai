/* v258: usable SGX historical code lookup from individually sourced issuer disclosures.
 * Snapshot research only; never a complete/current trading directory or quote feed.
 */
"use strict";
(function(root){
 const quoteViewer="https://www.sgx.com/securities/securities-prices?code=stocks";
 const codePattern=/^[A-Z0-9]{2,6}$/;
 const filingPattern=/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\/[A-Z0-9]{16}(?:\/|$)/;
 function build(index,first,second,boardLot,events,feed){
  if(index?.schema_version!=="sgx-corporate-information-indexed-page-v253"||
    index.records?.length!==20||index.trading_codes_extracted!==false||
    index.full_official_security_master_verified!==false||
    first?.schema_version!=="sgx-official-announcement-issuer-codes-v255"||
    first.records?.length!==8||first.ranking_eligible_count!==0||
    first.all_codes_currently_listed_verified!==false||
    second?.schema_version!=="sgx-net-eleven-additional-counter-identity-v256"||
    second.records?.length!==11||second.ranking_eligible_count!==0||
    second.all_current_listing_status_verified!==false||
    boardLot?.schema_version!=="sgx-official-first-batch-board-lot-v196"||
    boardLot.official_full_security_master_obtained!==false||
    boardLot.rows?.length!==11||
    events?.schema_version!=="sgx-listing-event-watch-v257"||
    events.events?.length!==2||
    feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0)
    throw Error("SGX 20-issuer lookup source boundary changed");
  const joined=new Map();
  function add(name,code,isin,source,filingDate,kind){
   if(!codePattern.test(code)||joined.has(name)||![...index.records].some(x=>x.issuer_name===name)||
    (kind!=="SGX_STATIC"&&!filingPattern.test(source))||
    (kind==="SGX_STATIC"&&source!=="https://www.sgx.com/securities/trading"))
    throw Error("Untrusted code or source");
   joined.set(name,{name,code,isin,source,filingDate,kind});
  }
  for(const r of first.records){
   if(r.current_trading_quote_verified!==false||r.ranking_eligible!==false||
     r.source_security_identity_verified_asof_announcement!==true)throw Error("Promoted v255");
   add(r.issuer_name,r.trading_code,r.isin,r.source_url,r.announced_on,"SGXNET");
  }
  for(const r of second.records){
   if(r.current_listing_verified!==false||r.ranking_eligible!==false||
     r.identity_observed_in_sgxnet_filing!==true)throw Error("Promoted v256");
   add(r.issuer_name,r.code,r.isin,r.source_url,r.announcement_date,"SGXNET");
  }
  const ocbc=boardLot.rows.find(r=>r.symbol==="O39");
  if(ocbc?.name!=="Oversea-Chinese Banking Corporation Ltd"||
    ocbc.eligible_for_valuation!==false||ocbc.trading_currency!=="SGD")
    throw Error("OCBC counter source changed");
  add("OVERSEA-CHINESE BANKING CORP","O39",null,boardLot.source_url,boardLot.effective_date,"SGX_STATIC");
  const risk=new Map(events.events.map(e=>[e.symbol,e]));
  if(risk.size!==2||!risk.has("5WA")||!risk.has("P11")||
    [...risk.values()].some(e=>e.delisted_confirmed!==false||e.ranking_eligible!==false))
    throw Error("Event alert source changed");
  const codes=new Set(),rows=[];
  for(const original of index.records){
   if(original.trading_code!==null||original.trading_currency!==null||original.ranking_eligible!==false)
    throw Error("Indexed issuer code was fabricated");
   const match=joined.get(original.issuer_name);
   if(!match||codes.has(match.code))throw Error("Incomplete or duplicate counter identity");
   codes.add(match.code);
   rows.push({...match,board:original.listing_board,
    warning:risk.has(match.code)?risk.get(match.code).detail_ja:null,
    all_current_trading_verified:false,financial_or_quote_verified:false,ranking_eligible:false});
  }
  if(rows.length!==20||codes.size!==20||rows.filter(x=>x.warning).length!==2)
   throw Error("20-issuer directory scope changed");
  return rows;
 }
 // v259 adds the remaining 10 direct SGX trading-table counters. Market board is
 // deliberately unknown: source is about board LOTS, not listing segment.
 function buildExpanded(index,first,second,boardLot,events,feed){
  const previous=build(index,first,second,boardLot,events,feed);
  const taken=new Set(previous.map(x=>x.code));
  const merged=[...previous];
  for(const official of boardLot.rows){
   if(official.symbol==="O39")continue; // Already joined by exact issuer alias.
   if(!codePattern.test(official.symbol)||taken.has(official.symbol)||
      official.provenance!=="OFFICIAL_SGX_TRADING_PAGE_STATIC_BATCH"||
      official.eligible_for_valuation!==false||
      !official.name||!["SGD","USD"].includes(official.trading_currency)||
      official.effective_date!=="2026-10-05")
    throw Error("SGX static code source mismatch");
   taken.add(official.symbol);
   merged.push({name:official.name,code:official.symbol,isin:null,
    source:boardLot.source_url,filingDate:boardLot.effective_date,
    kind:"SGX_STATIC",board:"UNKNOWN",
    warning:null,all_current_trading_verified:false,
    financial_or_quote_verified:false,ranking_eligible:false});
  }
  if(merged.length!==30||taken.size!==30||
     merged.filter(x=>x.board==="UNKNOWN").length!==10||
     merged.filter(x=>x.warning!==null).length!==2)
   throw Error("SGX partial source union does not reconcile");
  return merged;
 }
 // v262: 19 exact SGXNet originals were fetched in GitHub Actions, matching
 // issuer name, code, ISIN, announcement reference. SHA is body provenance,
 // NOT independent listed/current/quote status.
 function buildWithOriginalProof(index,first,second,boardLot,events,feed,proof){
  const rows=buildExpanded(index,first,second,boardLot,events,feed);
  if(proof?.schema_version!=="sgx-nineteen-official-html-sha256-evidence-v262"||
    proof.source_record_count!==19||proof.matching_original_html_count!==19||
    proof.replay_workflow_run_id!==43656588786||
    proof.replay_job_id!==132636341942||
    proof.sha256_of_exact_returned_html_bytes!==true||
    proof.original_html_captured_in_repo!==false||
    proof.full_sgx_security_master_verified!==false||
    proof.current_listing_active_for_all_verified!==false||
    proof.market_quote_licence_verified!==false||
    proof.independent_financial_audit_verified!==false||
    proof.ranking_eligible_count!==0||
    !Array.isArray(proof.records)||proof.records.length!==19)
   throw Error("SGX source replay proof is missing or falsely promoted");
  const map=new Map(rows.map(r=>[r.code,r]));
  const checked=new Set();
  for(const p of proof.records){
   const record=map.get(p.code);
   if(!record||record.kind!=="SGXNET"||checked.has(p.code)||
      record.name!==p.name||record.source!==p.url||record.isin!==p.isin||
      typeof p.ref!=="string"||!/^SG\d{6}[A-Z0-9]+$/.test(p.ref)||
      !/^[0-9a-f]{64}$/.test(p.original_html_sha256)||
      !Number.isInteger(p.original_html_bytes)||p.original_html_bytes<200||
      p.required_name_code_isin_reference_found!==true||
      p.source_proof_kind!=="LIVE_GITHUB_ACTIONS_DIRECT_SGXNET_HTML_CONTENT_MATCH"||
      p.current_listing_verified!==false||
      p.live_market_price_verified!==false||
      p.ranking_eligible!==false)
    throw Error("Original SGX source proof no longer matches its counter");
   checked.add(p.code);
   record.directHtmlIdentityMatched=true;
   record.originalHtmlSHA256=p.original_html_sha256;
  }
  if(checked.size!==19||rows.filter(r=>r.kind==="SGXNET"&&!r.directHtmlIdentityMatched).length||
     rows.filter(r=>r.kind==="SGX_STATIC").length!==11)
   throw Error("Some SGXNet original bodies lack proof");
  return rows.map(r=>({...r,directHtmlIdentityMatched:r.directHtmlIdentityMatched===true}));
 }
 function search(rows,query,boardFilter){
  const q=String(query||"").trim().toLocaleUpperCase("en");
  return rows.filter(x=>(boardFilter==="ALL"||x.board===boardFilter)&&
    (!q||(x.name+" "+x.code+" "+(x.isin||"")).toLocaleUpperCase("en").includes(q)));
 }
 async function render(){
  const status=document.getElementById("sgxHistoricalCodeStatus");
  const body=document.getElementById("sgxHistoricalCodeRows");
  const input=document.getElementById("sgxHistoricalCodeSearch");
  const board=document.getElementById("sgxHistoricalCodeBoard");
  const count=document.getElementById("sgxHistoricalCodeShown");
  if(!status||!body||!input||!board||!count)return;
  try{
   const names=["./data/sgx-corporate-indexed-page-v253.json",
     "./data/sgx-official-issuer-code-filings-v255.json",
     "./data/sgx-net-eleven-codes-v256.json",
     "./data/sgx-official-batch-seed-v196.json",
     "./data/sgx-material-listing-events-v257.json",
     "./data/latest.json",
     "./data/sgx-nineteen-original-html-sha-v262.json"];
   const files=await Promise.all(names.map(async url=>{
    const response=await fetch(url,{cache:"no-store"});
    if(!response.ok)throw Error("HTTP "+response.status);
    return response.json();
   }));
   const items=buildWithOriginalProof(...files);
   const paint=()=>{
    const shown=search(items,input.value,board.value);
    const frag=document.createDocumentFragment();
    for(const item of shown){
     const tr=document.createElement("tr");
     for(const value of [item.code,item.name,item.board,
       ((item.directHtmlIdentityMatched?"SGXNet原本本文一致":"SGX公式売買単位表")+"／"+(item.warning?"重要イベント要注意":"現在の取引状態は未確認"))]){
      const td=document.createElement("td");td.textContent=value;tr.append(td);
     }
     const td=document.createElement("td"),a=document.createElement("a");
     a.href=item.source;a.target="_blank";a.rel="noopener noreferrer";
     a.textContent="コードの根拠";td.append(a);tr.append(td);
     frag.append(tr);
    }
    if(!shown.length){
     const tr=document.createElement("tr"),td=document.createElement("td");
     td.colSpan=5;td.textContent="一致する企業なし";tr.append(td);frag.append(tr);
    }
    body.replaceChildren(frag);
    count.textContent=shown.length+" / 30 件（複数のSGX限定資料からの過去開示コード）";
   };
   input.addEventListener("input",paint);board.addEventListener("change",paint);
   paint();
   status.textContent="SGXNet原本HTMLの直接再取得で19銘柄を本文・SHA照合。残る11銘柄はSGX公式売買単位表。30銘柄は限定調査で、現在の上場・株価は未確認。";
  }catch(e){
   body.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="根拠の整合を取れなかったため、コード一覧は非表示";
   tr.append(td);body.append(tr);status.textContent="銘柄コード一覧の原本照合待ち";
   count.textContent="取得不可";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={build,buildExpanded,buildWithOriginalProof,search,quoteViewer};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
