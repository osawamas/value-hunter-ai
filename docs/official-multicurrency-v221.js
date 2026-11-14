/* v221: official SGX multi-currency examples, identity only; not market universe. */
"use strict";
(function(root){
 function validate(data,candidates,feed){
  if(data?.schema_version!=="sgx-official-multicurrency-subset-v220"||
     data.complete_sgx_list!==false||data.quote_fields_included!==false||
     data.source_terms_or_market_data_rights_verified!==false||
     data.ranking_eligible_count!==0||
     candidates?.full_sgx_listing_completeness_verified!==false||
     feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0||
     !Array.isArray(data.groups)||data.groups.length!==3||
     !Array.isArray(candidates.candidates))
   throw Error("Official subset/data rights or ranking gate changed");
  const expected=[
   ["AWX","SGD","XWA","USD","POTENTIAL_EQUITY"],
   ["GRN","SGD","GRE","USD","ETF"],
   ["EVS","SGD","EVD","USD","ETF"]
  ];
  const third=new Set(candidates.candidates.map(r=>r.symbol));
  const rows=[],codes=new Set();
  for(let i=0;i<3;i++){
   const g=data.groups[i],want=expected[i];
   if(g.counter_pair?.length!==2||g.category!==want[4]||g.may_count_as_two_issuers!==false)
    throw Error("Counter type mismatch");
   const [p,s]=g.counter_pair;
   if([p.code,p.currency,s.code,s.currency].some((x,j)=>x!==want[j])||
    p.is_primary!==true||s.is_primary!==false||
    !g.underlying_display)
    throw Error("Official counter identity changed");
   for(const c of [p,s]){
    if(codes.has(c.code))throw Error("Duplicate multi-currency counter");
    codes.add(c.code);
   }
   rows.push({instrument:g.underlying_display,category:g.category,
    primary_code:p.code,primary_currency:p.currency,secondary_code:s.code,
    secondary_currency:s.currency,
    primary_third_party:third.has(p.code),
    secondary_third_party:third.has(s.code),
    independently_verified_as_unique_issuer:false,
    eligible_for_ranking:false});
  }
  if(rows.filter(r=>r.primary_third_party||r.secondary_third_party).length!==1||
     !rows[0].primary_third_party||rows.some(r=>r.secondary_third_party))
    throw Error("Third-party coverage baseline changed");
  return rows;
 }
 function validateExpanded(base,extended,candidates,feed){
  const rows=validate(base,candidates,feed);
  if(extended?.schema_version!=="sgx-dual-currency-identity-research-v224"||
     extended.source_url!=="https://www.sgx.com/securities/trading"||
     extended.scope!=="SELECTED_OFFICIAL_PAIRS_NOT_EXHAUSTIVE"||
     extended.complete_official_sgx_security_master!==false||
     extended.quote_fields_collected!==false||
     extended.public_redistribution_rights_verified!==false||
     extended.ranking_eligible_count!==0||
     extended.new_pair_count!==18||extended.new_counter_count!==36||
     !Array.isArray(extended.new_pairs)||extended.new_pairs.length!==18)
   throw Error("Extended SGX counter evidence unavailable");
  const expected=[
    "NS8U|USD|P7VU|SGD|BUSINESS_TRUST","M62|USD|QS0|SGD|ETF",
    "P5P|USD|QR9|SGD|ETF","O9P|USD|QL3|SGD|ETF","N6M|USD|QL2|SGD|ETF",
    "I98|USD|QK9|SGD|ETF","BS6|SGD|SO7|RMB|POTENTIAL_EQUITY",
    "BYI|USD|BYJ|SGD|ETF","CFA|SGD|COI|USD|ETF","SET|EUR|SEB|SGD|STAPLED_SECURITY",
    "LG9|USD|TID|SGD|ETF","CYC|SGD|CYB|USD|ETF","MMS|SGD|MMT|USD|ETF",
    "ZHY|RMB|ZHD|USD|ETF","HST|SGD|HSS|USD|ETF","O87|USD|GSD|SGD|ETF",
    "YYY|SGD|YYR|RMB|ETF","UD1U|SGD|8U7U|EUR|REIT"
  ];
  const codes=new Set(rows.flatMap(r=>[r.primary_code,r.secondary_code]));
  const third=new Set(candidates.candidates.map(r=>r.symbol));
  for(let i=0;i<18;i++){
   const p=extended.new_pairs[i];
   const id=p?.primary?.code+"|"+p?.primary?.currency+"|"+p?.secondary?.code+"|"+p?.secondary?.currency+"|"+p?.instrument_category;
   if(id!==expected[i]||p.same_instrument_pair_source!=="SGX_OFFICIAL_STATIC_TRADING_TABLE"||
    p.ranking_eligible!==false||p.official_current_listing_independently_verified!==false||
    p.issuer_financial_data_verified!==false||!p.underlying_name||
    !/^[A-Z]{3}$/.test(p.primary.currency)||!/^[A-Z]{3}$/.test(p.secondary.currency))
     throw Error("Official currency counter evidence changed");
   for(const code of [p.primary.code,p.secondary.code]){
    if(codes.has(code))throw Error("Duplicate traded counter");
    codes.add(code);
   }
   rows.push({instrument:p.underlying_name,category:p.instrument_category,
    primary_code:p.primary.code,primary_currency:p.primary.currency,
    secondary_code:p.secondary.code,secondary_currency:p.secondary.currency,
    primary_third_party:third.has(p.primary.code),
    secondary_third_party:third.has(p.secondary.code),
    independently_verified_as_unique_issuer:false,eligible_for_ranking:false});
  }
  if(codes.size!==42||
    rows.filter(r=>r.primary_third_party||r.secondary_third_party).length!==3||
    rows.some(r=>r.secondary_third_party))
   throw Error("SGX counter count/coverage changed");
  return rows;
 }
 function validateAll(base,first,second,candidates,feed){
  const rows=validateExpanded(base,first,candidates,feed);
  if(second?.schema_version!=="sgx-official-dual-currency-extra-research-v227"||
    second.source_url!=="https://www.sgx.com/securities/trading"||
    second.scope!=="SECOND_SELECTED_BATCH_STATIC_IDENTITY_ONLY"||
    second.not_a_complete_sgx_security_master!==true||
    second.free_public_market_data_redistribution_authorized!==false||
    second.current_sgx_listing_independently_authenticated!==false||
    second.ranking_eligible_count!==0||
    second.new_pair_count!==20||second.new_counter_count!==40||
    !Array.isArray(second.pairs)||second.pairs.length!==20)
   throw Error("Official additional currency counter evidence changed");
  const expected=[
   "SRT|SGD|SRU|USD|ETF","ESG|SGD|ESU|USD|ETF",
   "LCU|USD|LCS|SGD|ETF","CXS|SGD|CXU|USD|ETF",
   "SQU|USD|SQQ|SGD|ETF","VND|USD|VNM|SGD|ETF",
   "ICU|USD|ICM|SGD|ETF","GRO|SGD|GRU|USD|ETF",
   "JJJ|SGD|JUS|USD|ETF","MCN|SGD|MCS|USD|ETF",
   "YLD|SGD|YLU|USD|ETF","JK8|SGD|VK8|USD|ETF",
   "EAA|SGD|EAU|USD|ETF","INC|SGD|ICH|CNH|ETF",
   "A93|SGD|A94|USD|ETF","CXN|RMB|CXO|USD|ETF",
   "SBO|SGD|SBV|USD|ETF","MXNU|GBP|MENU|SGD|REIT",
   "GLU|USD|GLS|SGD|ETF","ULG|USD|UGS|SGD|POTENTIAL_EQUITY"
  ];
  const allCodes=new Set(rows.flatMap(x=>[x.primary_code,x.secondary_code]));
  const third=new Set(candidates.candidates.map(x=>x.symbol));
  for(let i=0;i<20;i++){
   const p=second.pairs[i];
   if([p?.primary?.code,p?.primary?.currency,p?.secondary?.code,
       p?.secondary?.currency,p?.instrument_category].join("|")!==expected[i]||
      p.official_table_source!=="SGX_SECURITIES_TRADING_DUAL_CURRENCY"||
      p.issuer_entity_identity_independently_verified!==false||
      p.valuation_ready!==false||p.ranking_eligible!==false||
      !p.underlying_name)
    throw Error("New dual-currency pair has changed");
   for(const code of [p.primary.code,p.secondary.code]){
    if(allCodes.has(code))throw Error("Duplicate instrument counter");
    allCodes.add(code);
   }
   rows.push({instrument:p.underlying_name,category:p.instrument_category,
    primary_code:p.primary.code,primary_currency:p.primary.currency,
    secondary_code:p.secondary.code,secondary_currency:p.secondary.currency,
    primary_third_party:third.has(p.primary.code),
    secondary_third_party:third.has(p.secondary.code),
    independently_verified_as_unique_issuer:false,eligible_for_ranking:false});
  }
  if(rows.length!==41||allCodes.size!==82||
     rows.filter(x=>x.primary_third_party||x.secondary_third_party).length!==4||
     rows.some(x=>x.secondary_third_party))
    throw Error("Official subset/candidate counts have drifted");
  return rows;
 }
 async function render(){
  const status=document.getElementById("officialCurrencyPairStatus");
  const tbody=document.getElementById("officialCurrencyPairRows");
  if(!status||!tbody)return;
  try{
   const [a,b,c,d,e]=await Promise.all(
    ["./data/sgx-official-multicurrency-subset-v220.json",
     "./data/sgx-universe-candidates.json","./data/latest.json",
     "./data/sgx-dual-currency-research-v224.json",
     "./data/sgx-dual-currency-extra-v227.json"].map(async p=>{
      const res=await fetch(p,{cache:"no-store"});
      if(!res.ok)throw Error("Source HTTP "+res.status);
      return res.json();
     }));
   const rows=validateAll(a,d,e,b,c),frag=document.createDocumentFragment();
   for(const x of rows){
    const tr=document.createElement("tr");
    for(const v of [x.instrument,x.category,
      x.primary_code+" / "+x.primary_currency,
      x.secondary_code+" / "+x.secondary_currency,
      x.primary_third_party?"あり":"なし",
      x.secondary_third_party?"あり":"なし"]){
     const td=document.createElement("td");td.textContent=v;tr.append(td);
    }
    frag.append(tr);
   }
   tbody.replaceChildren(frag);
   status.textContent="SGX取引案内からの限定的な41商品・82通貨別カウンター。第三者182候補と一致するコードはAWX・BS6・CFA・MXNUの4件。82カウンターを82発行体と数えない。全銘柄一覧ではなく株価・許諾付き投資ランキングの証拠でもない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=6;
   td.textContent="公式カウンターと候補台帳が一致しないため非表示";
   tr.append(td);tbody.replaceChildren(tr);
   status.textContent="台帳の再照合が必要";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate,validateExpanded,validateAll};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
