/* v278: local user-supplied SGX security master research importer.
 * No uploads, automatic quote collection, verification promotion or persistent changes.
 */
"use strict";
(function(root){
 const head=["Trading Code","Trading Name","Listing Board","Traded Currency"];
 const boards=new Set(["MAINBOARD","CATALIST","GLOBAL LISTING BOARD"]);
 const currency=new Set(["SGD","USD","HKD","EUR","GBP","AUD","JPY","CNY","MYR","IDR","THB","PHP","CHF","CAD","NZD"]);
 function parseCSV(input){
  if(typeof input!=="string"||input.length>4*1024*1024)throw Error("CSVが4MBを超える、または文字データではない");
  const text=input.charCodeAt(0)===0xfeff?input.slice(1):input;
  let row=[],cell="",quoted=false,closed=false,rows=[];
  for(let i=0;i<text.length;i++){
   const ch=text[i];
   if(quoted){
    if(ch==='"'&&text[i+1]==='"'){cell+='"';i++}
    else if(ch==='"'){quoted=false;closed=true}
    else cell+=ch;
   }else if(closed){
    if(ch===","){row.push(cell);cell="";closed=false}
    else if(ch==="\n"||ch==="\r"){
     row.push(cell);rows.push(row);row=[];cell="";closed=false;
     if(ch==="\r"&&text[i+1]==="\n")i++;
    }else throw Error("CSVの引用符以降の文字が不正");
   }else if(ch==='"'){
    if(cell)throw Error("CSVにエスケープされていない引用符");
    quoted=true;
   }else if(ch===","){row.push(cell);cell=""}
   else if(ch==="\r"||ch==="\n"){
    row.push(cell);rows.push(row);row=[];cell="";
    if(ch==="\r"&&text[i+1]==="\n")i++;
   }else cell+=ch;
   if(cell.length>2000)throw Error("1セルが長すぎる");
  }
  if(quoted)throw Error("CSVの引用符が閉じていない");
  if(cell!==""||row.length||closed){row.push(cell);rows.push(row)}
  return rows.filter(cells=>cells.some(x=>x.trim()!==""));
 }
 const headerAliases={
  code:["trading code","stock code","security code","ticker","code"],
  name:["trading name","stock name","security name","company name","issuer name","name"],
  board:["listing board","market board","listing market","board"],
  currency:["traded currency","trading currency","currency","ccy"]
 };
 function mapHeaders(header){
  if(!Array.isArray(header)||header.length<2||header.length>40)
   throw Error("CSV列数が不正");
  const normalized=header.map(v=>String(v).trim().toLocaleLowerCase("en").replace(/[ _-]+/g," "));
  const pos={};
  for(const [key,aliases] of Object.entries(headerAliases)){
   const matches=normalized.map((label,i)=>aliases.includes(label)?i:-1).filter(i=>i>=0);
   if(matches.length>1)throw Error("同じ意味の列が重複");
   pos[key]=matches.length?matches[0]:-1;
  }
  if(pos.code<0||pos.name<0||pos.code===pos.name)
   throw Error("Trading Code と Trading Name に相当する列が必要");
  return {positions:pos,extraColumns:header.length-
    Object.values(pos).filter(i=>i>=0).length};
 }
 function stageCSV(raw,url,asOf,candidates,finance){
  let parsed;
  try{parsed=new URL(url)}catch{throw Error("SGXの原本出典URLが不正");}
  if(parsed.protocol!=="https:"||
   !["www.sgx.com","sgx.com","links.sgx.com"].includes(parsed.hostname)||
   parsed.username||parsed.password||parsed.hash||parsed.port)
   throw Error("SGX公式ドメインのHTTPS原本URLが必要（ただし入力したURLの実在は未検証）");
  if(typeof asOf!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(asOf)||
   !Number.isFinite(Date.parse(asOf+"T00:00:00Z"))||
   new Date(asOf+"T00:00:00Z").toISOString().slice(0,10)!==asOf)
   throw Error("CSVの基準日が不正");
  if(candidates?.schema_version!=="sgx-third-party-company-candidates-v99"||
   candidates.full_sgx_listing_completeness_verified!==false||
   candidates.eligible_for_ranking!==false||
   candidates.candidates?.length!==182||
   finance?.ranking_enabled!==false||
   finance.ranking_eligible_count!==0||finance.records?.length!==7)
   throw Error("既存の候補または財務データの状態が不正");
  const rows=parseCSV(raw);
  const {positions,extraColumns}=mapHeaders(rows[0]||[]);
  if(rows.length<2||rows.length>1201)throw Error("取り込み可能範囲は1〜1200銘柄");
  const checked=new Set(),list=[];
  for(const fields of rows.slice(1)){
   if(fields.length!==rows[0].length)throw Error("列数が不正");
   const code=fields[positions.code].trim().toUpperCase();
   const name=fields[positions.name].trim();
   let board=positions.board<0?"UNKNOWN":fields[positions.board].trim().toUpperCase();
   let curr=positions.currency<0?"UNKNOWN":fields[positions.currency].trim().toUpperCase();
   if(board==="MAIN BOARD")board="MAINBOARD";
   if(curr==="S$")curr="SGD";
   if(curr==="US$")curr="USD";
   if(!/^[A-Z0-9]{1,6}$/.test(code)||!name||name.length>180||
     /[\x00-\x1F\x7F]/.test(name)||/^[=+@\-]/.test(name)||
     !new Set([...boards,"UNKNOWN"]).has(board)||
     !new Set([...currency,"UNKNOWN"]).has(curr)||checked.has(code))
    throw Error("コード・会社名・市場区分・通貨に不正または重複");
   checked.add(code);
   list.push({code,name,board,currency:curr,sourceClassification:"USER_SUPPLIED_CSV_SOURCE_NOT_VERIFIED",
    activeListingConfirmed:false,originalCSVSourceIndependentlyVerified:false,
    investmentRankingEligible:false});
  }
  const candidateSet=new Set(candidates.candidates.map(x=>x.symbol));
  const financeSet=new Set(finance.records.map(x=>x.symbol));
  if(financeSet.size!==7||finance.records.some(x=>x.ranking_eligible!==false))
   throw Error("財務登録一覧の信頼性が不足");
  const missingFinance=[...financeSet].filter(code=>!checked.has(code)).sort();
  const missingPartialCandidates=[...candidateSet].filter(code=>!checked.has(code)).sort();
  return {schema_version:"sgx-user-csv-private-research-v278",
   as_of:asOf,source_url:parsed.href,
   file_bytes_utf16:raw.length,
   number_of_rows:list.length,
   imported_header_mode:positions.board<0||positions.currency<0?"TWO_REQUIRED_FIELDS_OPTIONAL_METADATA":"FOUR_CORE_FIELDS",
   ignored_unmapped_input_columns:extraColumns,
   optional_listing_board_supplied:positions.board>=0,
   optional_traded_currency_supplied:positions.currency>=0,
   market_prices_extracted:false,
   matching_third_party_candidates:list.filter(x=>candidateSet.has(x.code)).length,
   matching_registered_financial_records:list.filter(x=>financeSet.has(x.code)).length,
   registered_financial_codes_absent:missingFinance,
   third_party_candidate_codes_absent_count:missingPartialCandidates.length,
   imported_codes_outside_partial_candidates_count:list.filter(x=>!candidateSet.has(x.code)).length,
   sgx_source_url_actually_fetched:false,
   file_claimed_official_not_independently_verified:true,
   full_current_sgx_universe_confirmed:false,market_data_rights_verified:false,
   financial_records_modified:false,ranking_eligible_count:0,records:list};
 }
 const PAGE_SIZE=50;
 function pageOf(staged,query,page,size=PAGE_SIZE){
  if(staged?.schema_version!=="sgx-user-csv-private-research-v278"||
     staged.ranking_eligible_count!==0||
     staged.full_current_sgx_universe_confirmed!==false||
     staged.sgx_source_url_actually_fetched!==false||
     !Array.isArray(staged.records)||staged.records.length!==staged.number_of_rows||
     !Number.isInteger(page)||page<0||!Number.isInteger(size)||size<1||size>100)
   throw Error("CSV閲覧条件・根拠データが不正");
  const q=String(query||"").trim().toLocaleUpperCase("en");
  const filtered=staged.records.filter(x=>
   x.investmentRankingEligible===false&&x.activeListingConfirmed===false&&
   (x.code+" "+x.name+" "+x.board+" "+x.currency).toLocaleUpperCase("en").includes(q));
  const maxPage=Math.max(0,Math.ceil(filtered.length/size)-1);
  const current=Math.min(page,maxPage);
  return {records:filtered.slice(current*size,(current+1)*size),
   matched:filtered.length,total:staged.records.length,
   page:current,pageCount:maxPage+1,hasPrevious:current>0,
   hasNext:current<maxPage};
 }
 const make=(tag,text)=>{const e=document.createElement(tag);e.textContent=text;return e;};
 async function init(){
  const form=document.getElementById("sgxManualMasterForm");
  const result=document.getElementById("sgxManualMasterResult");
  const table=document.getElementById("sgxManualMasterRows");
  const search=document.getElementById("sgxManualMasterSearch");
  const pageStatus=document.getElementById("sgxManualMasterPageStatus");
  const previous=document.getElementById("sgxManualMasterPrevious");
  const next=document.getElementById("sgxManualMasterNext");
  const template=document.getElementById("sgxManualMasterTemplate");
  if(!form||!result||!table||!search||!pageStatus||!previous||!next||!template)return;
  let staged=null,visiblePage=0;
  const repaint=()=>{
   if(!staged){
    pageStatus.textContent="CSV未取込";
    previous.disabled=true;next.disabled=true;
    return;
   }
   const view=pageOf(staged,search.value,visiblePage);
   visiblePage=view.page;
   const frag=document.createDocumentFragment();
   for(const rec of view.records){
    const tr=document.createElement("tr");
    for(const v of [rec.code,rec.name,rec.board,rec.currency,"原本未検証・参考のみ"])
     tr.append(make("td",v));
    frag.append(tr);
   }
   if(!view.records.length){
    const tr=document.createElement("tr"),td=make("td","一致する銘柄はない");
    td.colSpan=5;tr.append(td);frag.append(tr);
   }
   table.replaceChildren(frag);
   previous.disabled=!view.hasPrevious;next.disabled=!view.hasNext;
   pageStatus.textContent="検索一致 "+view.matched+" / "+view.total+
    "件・"+(view.page+1)+"/"+view.pageCount+"ページ（50件ずつ）";
  };
  search.addEventListener("input",()=>{visiblePage=0;repaint();});
  previous.addEventListener("click",()=>{if(visiblePage>0){visiblePage--;repaint();}});
  next.addEventListener("click",()=>{if(staged){visiblePage++;repaint();}});
  template.addEventListener("click",()=>{
   const header=head.join(",")+"\r\n";
   const blob=new Blob(["\uFEFF"+header],{type:"text/csv;charset=utf-8"});
   const url=URL.createObjectURL(blob);
   const a=document.createElement("a");
   a.href=url;a.download="sgx-source-template-unverified.csv";a.click();
   URL.revokeObjectURL(url);
  });
  form.addEventListener("submit",async event=>{
   event.preventDefault();
   staged=null;visiblePage=0;table.replaceChildren();repaint();
   try{
    const file=form.elements.masterFile.files?.[0];
    if(!file||file.size>4*1024*1024)throw Error("4MB以下のCSVを選択して");
    const content=await file.text();
    const [candidates,finance]=await Promise.all(["./data/sgx-universe-candidates.json","./data/latest.json"]
     .map(async url=>{
      const response=await fetch(url,{cache:"no-store"});
      if(!response.ok)throw Error("HTTP "+response.status);
      return response.json();
     }));
    staged=stageCSV(content,form.elements.sourceURL.value,form.elements.asOf.value,candidates,finance);
    result.textContent="手入力CSV "+staged.number_of_rows+"件（余分な"+staged.ignored_unmapped_input_columns+
     "列は無視。株価・時価総額の取込なし） / 第三者候補とコード一致 "+
     staged.matching_third_party_candidates+"件 / 財務登録と一致 "+
     staged.matching_registered_financial_records+
     "件。原本・全銘柄・現在上場は未検証。ランキングへの登録は行っていない。";
    const gaps=document.getElementById("sgxManualMasterCoverageGaps");
    if(gaps){
     gaps.replaceChildren();
     const summary=make("summary","取り込んだCSVと既存データの差分を確認");
     const list=document.createElement("ul");
     list.append(make("li","財務登録7社のうちCSVで確認できないコード: "+
       (staged.registered_financial_codes_absent.join(", ")||"なし")));
     list.append(make("li","第三者候補182社のうちCSVにないコード: "+
       staged.third_party_candidate_codes_absent_count+"件"));
     list.append(make("li","CSVのうち第三者候補182社にないコード: "+
       staged.imported_codes_outside_partial_candidates_count+"件"));
     list.append(make("li","差分は資料の対象範囲の違いを示すだけ。上場廃止・新規上場の確定ではない。"));
     gaps.append(summary,list);
    }
    repaint();
  }catch(err){
   staged=null;result.textContent="CSV取り込み失敗： "+err.message;
   document.getElementById("sgxManualMasterCoverageGaps")?.replaceChildren();
   const tr=document.createElement("tr"),td=make("td","検証に失敗したため表示しない");
   td.colSpan=5;tr.append(td);table.replaceChildren(tr);repaint();
  }
 });
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={parseCSV,stageCSV,pageOf,mapHeaders};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",init);
})(typeof window!=="undefined"?window:null);
