"use strict";
/* Read-only directory of historically sourced SGX security identifiers.
 * Never treat an IPO admission or a historical filing as current active listing.
 */
(function(root){
 const $=id=>root?.document?.getElementById(id);
 const paths=[
  "./data/sgx-corporate-indexed-page-v253.json",
  "./data/sgx-official-issuer-code-filings-v255.json",
  "./data/sgx-net-eleven-codes-v256.json",
  "./data/sgx-official-batch-seed-v196.json",
  "./data/sgx-material-listing-events-v257.json",
  "./data/latest.json",
  "./data/sgx-nineteen-original-html-sha-v262.json",
  "./data/sgx-october-ipo-listing-v294.json",
  "./data/sgx-metasurface-listing-v304.json"
 ];
 function createDirectory(historical,ipo,feed,met){
  if(!Array.isArray(historical)||historical.length!==30||
     historical.some(x=>x.ranking_eligible!==false||
       x.financialRankingEligible!==false||
       x.all_current_trading_verified!==false)||
     ipo?.schema_version!=="sgx-october-ipo-official-listing-v294"||
     ipo.ranking_eligible_count!==0||
     ipo.ranking_enabled!==false||
     ipo.full_active_sgx_master_verified!==false||
     ipo.market_data_display_rights_verified!==false||
     ipo.market_data_non_display_rights_verified!==false||
     !Array.isArray(ipo.issuer_listing_confirmations)||
     ipo.issuer_listing_confirmations.length!==2||
     !Array.isArray(feed?.records)||feed.records.length!==7||
     feed.ranking_enabled!==false||feed.ranking_eligible_count!==0)
   throw Error("検証済みの調査データ形式と一致しない");
  const rows=[],taken=new Set();
  for(const r of historical){
   if(!/^[A-Z0-9]{2,6}$/.test(r.code)||taken.has(r.code)||
      !r.source||!/^https:\/\//.test(r.source))
    throw Error("過去資料のコードが不正");
   taken.add(r.code);
   rows.push({code:r.code,name:r.name,isin:r.isin||"",
    board:r.board,kind:r.kind==="SGXNET"?"過去のSGXNet原本":"公式の静的資料",
    source:r.source,eventDate:r.filingDate||"",financialRegistered:r.financialRegistered===true,
    rankingEligible:false,activeVerified:false,ipo:false});
  }
  const expected={ "9DC":{name:"DELUGE CORPORATION LIMITED",isin:"SGXE96931105",
    date:"2026-10-16"},MIM:{name:"MI MATERIAL HOLDING LIMITED",isin:"SGXE49931863",
    date:"2026-10-28"}};
  const seenIPO=new Set();
  for(const r of ipo.issuer_listing_confirmations){
   const e=expected[r?.trading_code];
   if(!e||seenIPO.has(r.trading_code)||taken.has(r.trading_code)||
      r.issuer_name!==e.name||r.isin!==e.isin||
      r.effective_trading_date!==e.date||
      r.event_type!=="EQUITY_LISTING_CONFIRMATION"||
      r.listed_trading_confirmed_asof_event!==true||
      r.currently_active_listing_verified!==false||
      r.ranking_eligible!==false||r.financials_verified!==false||
      r.quote_verified!==false||r.shares_ex_treasury_verified!==false||
      !/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\//.test(r.source_url||""))
    throw Error("IPOの原本根拠が不正");
   seenIPO.add(r.trading_code);taken.add(r.trading_code);
   rows.push({code:r.trading_code,name:r.issuer_name,isin:r.isin,
    board:r.board,kind:"2026年10月SGX正式上場確認",
    source:r.source_url,eventDate:r.effective_trading_date,financialRegistered:false,
    rankingEligible:false,activeVerified:false,ipo:true});
  }
  if(seenIPO.size!==2)throw Error("10月の上場資料の照合に失敗");
  if(met?.symbol!=="MET"||met.isin!=="KYG9R41B1017"||
     met.issuer_name!=="METASURFACE TECHNOLOGIES HOLDINGS LIMITED"||
     met.board!=="CATALIST"||met.effective_trading_date!=="2026-11-04"||
     met.reference!=="SG261103OTHRWUG1"||met.current_active_verified!==false||
     met.ranking_eligible!==false||taken.has(met.symbol)||
     !/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\//.test(met.source?.url||""))
   throw Error("11月の上場資料の照合に失敗");
  rows.push({code:met.symbol,name:met.issuer_name,isin:met.isin,board:met.board,
   kind:"2026年11月SGX正式上場確認",source:met.source.url,eventDate:met.effective_trading_date,
   financialRegistered:false,rankingEligible:false,activeVerified:false,ipo:true});
  rows.sort((a,b)=>a.code.localeCompare(b.code,"en"));
  return rows;
 }
 function filterDirectory(rows,query="",type="ALL",financial="ALL"){
  const q=String(query).trim().toUpperCase();
  return rows.filter(x=>
   (type==="ALL"||(type==="IPO"?x.ipo:type==="ORIGINAL"?!x.ipo&&x.kind==="過去のSGXNet原本":type==="STATIC"?!x.ipo&&x.kind==="公式の静的資料":false))&&
   (financial==="ALL"||(financial==="YES"?x.financialRegistered:financial==="NO"?!x.financialRegistered:false))&&
   (!q||(x.code+" "+x.name+" "+x.isin+" "+x.board).toUpperCase().includes(q))
  );
 }
 function toCSV(rows){
  const escape=v=>{let s=String(v??"");if(/^[=+@-]/.test(s.trimStart()))s="'"+s;return '"'+s.replace(/"/g,'""')+'"'};
  const h=["銘柄コード","企業名","ISIN","市場区分","資料種別","資料日付","財務登録","現在上場確認","ランキング対象","原本URL"];
  const lines=[h.map(escape).join(",")];
  for(const x of rows){
   if(x.rankingEligible!==false||x.activeVerified!==false||
      !/^https:\/\//.test(x.source)||!/^[A-Z0-9]{2,6}$/.test(x.code))
    throw Error("不正な輸出対象");
   lines.push([x.code,x.name,x.isin,x.board,x.kind,x.eventDate,
     x.financialRegistered?"財務登録のみ":"未登録","未確認","除外",x.source].map(escape).join(","));
  }
  return "\uFEFF"+lines.join("\r\n")+"\r\n";
 }
 function make(tag,value){const x=root.document.createElement(tag);x.textContent=String(value);return x;}
 async function init(){
  const body=$("research32Rows"),status=$("research32Status"),count=$("research32Count");
  const query=$("research32Query"),type=$("research32Type"),finance=$("research32Finance");
  const exportButton=$("research32Export");
  if(!body||!status||!count||!query||!type||!finance||!exportButton)return;
  try{
   const response=await Promise.all(paths.map(async u=>{
    const r=await fetch(u,{cache:"no-store"});
    if(!r.ok)throw Error("ソース取得失敗 HTTP "+r.status);
    return r.json();
   }));
   const builder=root.SGX_SOURCE_DIRECTORY_READONLY?.buildWithOriginalProof;
   if(typeof builder!=="function")throw Error("既存SGXNet照合機能を読み込めない");
   const prior=builder(...response.slice(0,7));
   const rows=createDirectory(prior,response[7],response[5],response[8]);
   function paint(){
    const filtered=filterDirectory(rows,query.value,type.value,finance.value);
    const fragment=root.document.createDocumentFragment();
    for(const r of filtered){
     const tr=root.document.createElement("tr");
     for(const v of [r.code,r.name,r.isin||"未取得",r.board,r.kind,
       r.financialRegistered?"登録済み・除外":"未登録・除外"]){
      tr.append(make("td",v));
     }
     const td=root.document.createElement("td"),a=make("a","原本を見る");
     a.href=r.source;a.target="_blank";a.rel="noopener noreferrer";
     td.append(a);tr.append(td);fragment.append(tr);
    }
    if(!filtered.length){const tr=make("tr","");const td=make("td","一致する銘柄なし");td.colSpan=7;tr.append(td);fragment.append(tr);}
    body.replaceChildren(fragment);
    count.textContent=filtered.length+" / "+rows.length+"件（現在の上場・株価は未確認）";
   }
   for(const e of [query,type,finance])e.addEventListener(e===query?"input":"change",paint);
   exportButton.addEventListener("click",()=>{
    const csv=toCSV(filterDirectory(rows,query.value,type.value,finance.value));
    const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
    const link=root.document.createElement("a");link.href=url;link.download="value-hunter-sgx-historical-research.csv";link.click();
    URL.revokeObjectURL(url);
   });
   status.textContent="SGXNet原本本文照合19件、公式静的資料11件、10〜11月の上場確認原本3件。現在の上場状態と全銘柄台帳は未照合。";
   paint();
  }catch(e){body.replaceChildren();const tr=make("tr",""),td=make("td","原本整合に失敗したため非表示: "+e.message);td.colSpan=7;tr.append(td);body.append(tr);status.textContent="データ照合エラー";count.textContent="表示できない";}
 }
 if(root?.document)root.document.addEventListener("DOMContentLoaded",init);
 if(typeof module!=="undefined"&&module.exports)module.exports={createDirectory,filterDirectory,toCSV};
})(typeof window!=="undefined"?window:null);
