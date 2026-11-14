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
 async function render(){
  const status=document.getElementById("officialCurrencyPairStatus");
  const tbody=document.getElementById("officialCurrencyPairRows");
  if(!status||!tbody)return;
  try{
   const [a,b,c]=await Promise.all(
    ["./data/sgx-official-multicurrency-subset-v220.json",
     "./data/sgx-universe-candidates.json","./data/latest.json"].map(async p=>{
      const res=await fetch(p,{cache:"no-store"});
      if(!res.ok)throw Error("Source HTTP "+res.status);
      return res.json();
     }));
   const rows=validate(a,b,c),frag=document.createDocumentFragment();
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
   status.textContent="SGX取引案内の3商品・6通貨別カウンターの例。第三者182候補と一致はAWXのみ。カウンター6件を発行体6社と数えない。全銘柄一覧ではなく株価・許諾付き投資ランキングの証拠でもない。";
  }catch(e){
   const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=6;
   td.textContent="公式カウンターと候補台帳が一致しないため非表示";
   tr.append(td);tbody.replaceChildren(tr);
   status.textContent="台帳の再照合が必要";
  }
 }
 if(typeof module!=="undefined"&&module.exports)module.exports={validate};
 if(root?.document)root.document.addEventListener("DOMContentLoaded",render);
})(typeof window!=="undefined"?window:null);
