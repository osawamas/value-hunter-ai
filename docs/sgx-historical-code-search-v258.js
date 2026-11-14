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
     "./data/latest.json"];
   const files=await Promise.all(names.map(async url=>{
    const response=await fetch(url,{cache:"no-store"});
    if(!response.ok)throw Error("HTTP "+response.status);
    return response.json();
   }));
   const items=build(...files);
   const paint=()=>{
    const shown=search(items,input.value,board.value);
    const frag=document.createDocumentFragment();
    for(const item of shown){
     const tr=document.createElement("tr");
     for(const value of [item.code,item.name,item.board,
       item.warning?"重要イベントあり・取引状態未検証":"上場継続・取引状態未検証"]){
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
    count.textContent=shown.length+" / 20 件（限定ページの過去開示コード）";
   };
   input.addEventListener("input",paint);board.addEventListener("change",paint);
   paint();
   status.textContent="SGX企業情報の1ページに掲載された20社と、SGXNet等の過去開示を照合。現在の上場・取引状態や株価は保証されない。";
  }catch(e){
   body.replaceChildren();
   const tr=document.createElement("tr"),td=document.createElement("td");
   td.colSpan=5;td.textContent="根拠の整合を取れなかったため、コード一覧は非表示";
   tr.append(td);body.append(tr);status.textContent="銘柄コード一覧の原本照合待ち";
   count.textContent="取得不可";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={build,search,quoteViewer};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
