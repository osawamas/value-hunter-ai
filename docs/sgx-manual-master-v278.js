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
  if(rows[0]?.length!==4||head.some((v,i)=>rows[0][i]!==v))
   throw Error("見出しが異なる：Trading Code,Trading Name,Listing Board,Traded Currency");
  if(rows.length<2||rows.length>1201)throw Error("取り込み可能範囲は1〜1200銘柄");
  const checked=new Set(),list=[];
  for(const fields of rows.slice(1)){
   if(fields.length!==4)throw Error("列数が不正");
   const [code,name,board,curr]=fields.map(x=>x.trim());
   if(!/^[A-Z0-9]{1,6}$/.test(code)||!name||name.length>180||
     /^[=+@\-]/.test(name)||!boards.has(board)||!currency.has(curr)||checked.has(code))
    throw Error("コード・会社名・市場区分・通貨に不正または重複");
   checked.add(code);
   list.push({code,name,board,currency:curr,sourceClassification:"USER_SUPPLIED_CSV_SOURCE_NOT_VERIFIED",
    activeListingConfirmed:false,originalCSVSourceIndependentlyVerified:false,
    investmentRankingEligible:false});
  }
  const candidateSet=new Set(candidates.candidates.map(x=>x.symbol));
  const financeSet=new Set(finance.records.map(x=>x.symbol));
  return {schema_version:"sgx-user-csv-private-research-v278",
   as_of:asOf,source_url:parsed.href,
   file_bytes_utf16:raw.length,
   number_of_rows:list.length,
   matching_third_party_candidates:list.filter(x=>candidateSet.has(x.code)).length,
   matching_registered_financial_records:list.filter(x=>financeSet.has(x.code)).length,
   sgx_source_url_actually_fetched:false,
   file_claimed_official_not_independently_verified:true,
   full_current_sgx_universe_confirmed:false,market_data_rights_verified:false,
   financial_records_modified:false,ranking_eligible_count:0,records:list};
 }
 const make=(tag,text)=>{const e=document.createElement(tag);e.textContent=text;return e;};
 async function init(){
  const form=document.getElementById("sgxManualMasterForm");
  const result=document.getElementById("sgxManualMasterResult");
  const table=document.getElementById("sgxManualMasterRows");
  if(!form||!result||!table)return;
  form.addEventListener("submit",async event=>{
   event.preventDefault();table.replaceChildren();
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
    const staged=stageCSV(content,form.elements.sourceURL.value,form.elements.asOf.value,candidates,finance);
    result.textContent="手入力CSV "+staged.number_of_rows+"件 / 第三者候補とコード一致 "+
     staged.matching_third_party_candidates+"件 / 財務登録と一致 "+
     staged.matching_registered_financial_records+
     "件。原本・全銘柄・現在上場は未検証。ランキングへの登録は行っていない。";
    const frag=document.createDocumentFragment();
    for(const rec of staged.records.slice(0,100)){
     const tr=document.createElement("tr");
     for(const v of [rec.code,rec.name,rec.board,rec.currency,"原本未検証・参考のみ"])
      tr.append(make("td",v));
     frag.append(tr);
    }
    table.replaceChildren(frag);
  }catch(err){
   result.textContent="CSV取り込み失敗： "+err.message;
   const tr=document.createElement("tr"),td=make("td","検証に失敗したため表示しない");
   td.colSpan=5;tr.append(td);table.replaceChildren(tr);
  }
 });
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={parseCSV,stageCSV};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",init);
})(typeof window!=="undefined"?window:null);
