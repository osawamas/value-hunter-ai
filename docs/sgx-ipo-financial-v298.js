"use strict";
/* v298: safe dated SGX IPO audited historical trends, NOT current quote/ranking. */
(function(root){
 const KNOWN={
  "9DC":{currency:"SGD",fyEnd:"03-31",sha:"6472db7e48bc45db8a056d196157d03589bf4ef880ee94eba3fd837b53c028de"},
  "MIM":{currency:"USD",fyEnd:"12-31",sha:"d6b49948af8167e6d2443ae22f7538907c46e94d62b414843e8444abc05f342c"}
 };
 function compare(a,b){
  if(!Number.isFinite(a)||!Number.isFinite(b)||a<=0)return null;
  return 100*(b-a)/a;
 }
 const money=x=>typeof x==="number"?x.toLocaleString("ja-JP"):"—";
 const pct=x=>x==null?"—":(x>=0?"+":"")+x.toFixed(1)+"%";
 const ratio=x=>x==null?"—":x.toFixed(1)+"%";
 const validAssets=(assets,equity)=>Number.isSafeInteger(assets)&&assets>=equity;
 function build(doc,feed){
  if(doc?.schema_version!=="sgx-ipo-audited-historical-financials-v298"||
    doc.ranking_enabled!==false||doc.ranking_eligible_count!==0||
    doc.universe_master_verified!==false||doc.licensed_quote_available!==false||
    doc.independent_current_financial_reverification!==false||
    !Array.isArray(doc.issuers)||doc.issuers.length!==2||
    feed?.ranking_enabled!==false||feed.ranking_eligible_count!==0||feed.records?.length!==7)
   throw Error("財務出典や投資適格の検証条件に不一致");
  const seen=new Set(), result=[];
  for(const s of doc.issuers){
   const known=KNOWN[s.symbol];
   if(!known||seen.has(s.symbol)||s.currency!==known.currency||
      s.fiscal_year_end_month_day!==known.fyEnd||
      s.source_pdf_sha256!==known.sha||
      !/^https:\/\/links\.sgx\.com\/FileOpen\//.test(s.source_pdf_url||"")||
      s.audit_report_in_prospectus!==true||
      s.not_current_reverified_financials!==true||
      !Array.isArray(s.periods)||s.periods.length!==3)
     throw Error("IPO原本・通貨・監査対象年度に不正");
   seen.add(s.symbol);
   const expected=s.symbol==="9DC"?["2024-03-31","2025-03-31","2026-03-31"]:
    ["2023-12-31","2024-12-31","2025-12-31"];
   const hasSegmentResult=s.symbol==="9DC";
   const operatingBasis=hasSegmentResult?"SEGMENT_NOTE_PROFIT_FROM_OPERATIONS":
    "NO_SEPARATE_OPERATING_PROFIT_SUBTOTAL";
   if(s.operating_result_basis!==operatingBasis)throw Error("営業損益の出典区分が不正");
   for(let i=0;i<3;i++){
    const p=s.periods[i];
    if(p.period_end!==expected[i]||p.audit_status!=="AUDITED"||
      [p.revenue,p.gross_profit,p.profit_for_year,p.total_equity].some(v=>!Number.isInteger(v)||v<=0)||
      p.revenue<p.gross_profit||!validAssets(p.total_assets,p.total_equity)||
      (hasSegmentResult?!Number.isSafeInteger(p.segment_operating_result):p.segment_operating_result!==null))
     throw Error("監査済み年度行が不正");
   }
   const p=s.periods;
   const metrics=p.map((x,i)=>({
    period:x.period_end,revenue:x.revenue,gross:x.gross_profit,
    profit:x.profit_for_year,equity:x.total_equity,
    totalAssets:x.total_assets,equityRatio:100*x.total_equity/x.total_assets,
    segmentOperatingResult:x.segment_operating_result,
    segmentOperatingMargin:hasSegmentResult?100*x.segment_operating_result/x.revenue:null,
    segmentOperatingGrowth:hasSegmentResult&&i?
     compare(p[i-1].segment_operating_result,x.segment_operating_result):null,
    grossMargin:100*x.gross_profit/x.revenue,
    revenueGrowth:i?compare(p[i-1].revenue,x.revenue):null,
    profitGrowth:i?compare(p[i-1].profit_for_year,x.profit_for_year):null,
    auditStatus:"AUDITED_HISTORICAL"
   }));
   let interim=null,businessUpdate=null;
   if(s.symbol==="9DC"){
    const pro=s.rejected_lookalike_pro_forma;
    if(pro?.audit_status!=="UNAUDITED_PRO_FORMA"||
      pro.period_end!=="2026-03-31"||pro.not_used_in_audited_growth!==true||
      pro.revenue!==116567||pro.gross_profit!==38738||pro.profit_for_year!==11489||
      p[2].revenue===pro.revenue)throw Error("未監査プロフォーマを監査済みに誤採用");
   }else{
    if(!Array.isArray(s.interim)||s.interim.length!==2)
      throw Error("MIM中間決算境界が不正");
    const [a,b]=s.interim;
    if(a.period_start!=="2025-01-01"||a.period_end!=="2025-06-30"||
       b.period_start!=="2026-01-01"||b.period_end!=="2026-06-30"||
       a.audit_status!=="UNAUDITED_INTERIM"||b.audit_status!=="UNAUDITED_INTERIM"||
       a.total_equity!==null||a.total_assets!==null||b.total_equity!==109052||
       !validAssets(b.total_assets,b.total_equity)||
       [a.revenue,b.revenue,a.gross_profit,b.gross_profit,a.profit_for_year,b.profit_for_year].some(v=>!Number.isInteger(v)||v<=0))
       throw Error("同一期間の未監査比較に不正");
    interim={date:"2026-06-30",revenueYoY:compare(a.revenue,b.revenue),
     grossProfitYoY:compare(a.gross_profit,b.gross_profit),
     profitYoY:compare(a.profit_for_year,b.profit_for_year),
     equityRatio:100*b.total_equity/b.total_assets,
     period:"H1 2026 vs H1 2025",audited:false};
    const update=s.business_update;
    if(update?.audit_status!=="UNAUDITED_ISSUER_UPDATE"||update.period_end!=="2026-09-30"||
      update.prior_year_same_period_revenue!==null||
      !/^https:\/\/links\.sgx\.com\/FileOpen\//.test(update.source_pdf_url||"")||
      [update.revenue_usd_millions,update.gross_margin_percent,update.adjusted_pat_usd_millions,
       update.pat_usd_millions,update.q3_revenue_qoq_percent].some(x=>!Number.isFinite(x))||
      !/^https:\/\/links\.sgx\.com\/1\.0\.0\/corporate-announcements\//.test(update.presentation_source?.url||""))
     throw Error("MIMの9か月の発行体業績資料に不一致");
    const segment=update.parent_segment_comparison;
    if(segment?.basis!=="MITB_SMBU_EXTERNAL_CUSTOMER_REVENUE"||segment.currency!=="MYR"||
       segment.prior_period_end!=="2025-09-30"||segment.current_period_end!==update.period_end||
       !/^https:\/\/miequipment\.listedcompany\.com\/newsroom\//.test(segment.source?.url||"")||
       [segment.prior_revenue_thousands,segment.current_revenue_thousands].some(x=>!Number.isSafeInteger(x)||x<=0))
     throw Error("親会社の半導体材料部門データに不一致");
    businessUpdate={...update,segmentRevenueYoY:compare(segment.prior_revenue_thousands,segment.current_revenue_thousands)};
   }
   result.push({symbol:s.symbol,issuer:s.name,currency:s.currency,unit:"thousand",
    source:s.source_pdf_url,sha:s.source_pdf_sha256,
    historical:metrics,interim,businessUpdate,listingShareCapital:validateListingShareCapital(s),
    financials_independently_reverified_today:false,
    current_shares_verified:false,market_quote_licensed:false,rankEligible:false});
  }
  if(result.length!==2)throw Error("SGX IPO2銘柄未照合");
  return result;
 }
 function validateListingShareCapital(stock){
  const capital=stock.listing_share_capital;
  const mim=stock.symbol==="MIM";
  if(capital?.basis!==(mim?"PROSPECTUS_POST_OFFERING_OUTSTANDING":"POST_OFFERING_SHARE_CAPITAL")||
     capital.listing_date!==(mim?"2026-10-28":"2026-10-16")||
     capital.current_shares_verified!==false||
     !Number.isSafeInteger(capital.shares)||capital.shares<=0||
     !/^https:\/\/links\.sgx\.com\//.test(capital.balloting_source?.url||"")||
     (mim&&capital.borrowed_overallotment_shares!==5000000))
   throw Error("上場時の株数資料に不一致");
  return capital;
 }
 function init(){
  const body=root.document.getElementById("sgxIpoFinancialRows");
  const status=root.document.getElementById("sgxIpoFinancialStatus");
  const business=root.document.getElementById("sgxIpoBusinessUpdate");
  const capitalRows=root.document.getElementById("sgxIpoListingCapitalRows");
  if(!body||!status||!business||!capitalRows)return;
  const td=v=>{const c=root.document.createElement("td");c.textContent=String(v);return c;};
  Promise.all(["./data/sgx-ipo-audited-historical-v298.json","./data/latest.json","./data/sgx-metasurface-listing-v304.json"].map(async u=>{
   const r=await fetch(u,{cache:"no-store"});if(!r.ok)throw Error("データ HTTP "+r.status);return r.json();
  })).then(([doc,feed,met])=>{
   const rows=build(doc,feed),fragment=root.document.createDocumentFragment();
   for(const stock of rows){
    for(const fy of stock.historical){
     const tr=root.document.createElement("tr");
     for(const x of [stock.symbol,fy.period,stock.currency,money(fy.revenue),
       money(fy.gross),money(fy.profit),ratio(fy.grossMargin),pct(fy.revenueGrowth),
       ratio(fy.equityRatio),money(fy.segmentOperatingResult),
       ratio(fy.segmentOperatingMargin),pct(fy.segmentOperatingGrowth)]){tr.append(td(x));}
     fragment.append(tr);
    }
   }
   body.replaceChildren(fragment);
   const {interim,businessUpdate:update}=rows.find(x=>x.symbol==="MIM");
   status.textContent="SGX原本PDFの監査済み実績。MIMの2026年上期（未監査）は売上前年比"+
     pct(interim.revenueYoY)+"、6月末の自己資本比率"+ratio(interim.equityRatio)+"。";
   const sourceLink=(url,label)=>{
    const link=root.document.createElement("a");
    link.href=url;
    link.textContent=label;
    return link;
   };
   const capitalFragment=root.document.createDocumentFragment();
   for(const stock of rows){
    const capital=stock.listingShareCapital;
    const row=root.document.createElement("tr");
    const proof=td("");
    if(stock.symbol==="MIM")proof.append(sourceLink(stock.source,"目論見書PDF"),"・");
    proof.append(sourceLink(capital.balloting_source.url,"割当結果PDF"));
    row.append(td(stock.symbol),td(capital.listing_date),td(money(capital.shares)),
     td(stock.symbol==="MIM"?"親会社から借りた追加割当500万株は加算しない":"募集・コーナーストーン割当後"),proof);
    capitalFragment.append(row);
   }
   const placed=met.placement_capital;
   if(met.symbol!=="MET"||met.isin!=="KYG9R41B1017"||met.ranking_eligible!==false||
      placed?.effective_date!=="2026-11-03"||placed.current_shares_verified!==false||
      [placed.shares_before_ex_treasury,placed.new_shares,placed.shares_after_ex_treasury].some(x=>!Number.isSafeInteger(x)||x<=0)||
      placed.shares_before_ex_treasury+placed.new_shares!==placed.shares_after_ex_treasury||
      !/^https:\/\/www1\.hkexnews\.hk\/listedco\//.test(placed.source?.url||""))
    throw Error("METの割当完了時の株数に不一致");
   const metRow=root.document.createElement("tr"),proof=td("");
   proof.append(sourceLink(placed.source.url,"HKEX割当完了PDF"));
   metRow.append(td(met.symbol),td(placed.effective_date),td(money(placed.shares_after_ex_treasury)),
    td("上場前日の割当完了時点・自己株式控除後"),proof);
   capitalFragment.append(metRow);
   capitalRows.replaceChildren(capitalFragment);
   const segment=update.parent_segment_comparison;
   business.replaceChildren(
    "MIM 2026年1–9月（発行体公表・未監査）。売上 "+update.revenue_usd_millions.toFixed(1)+
    "百万USD、粗利益率 "+ratio(update.gross_margin_percent)+"、税引後利益 "+update.pat_usd_millions.toFixed(1)+
    "百万USD、調整後税引後利益 "+
    update.adjusted_pat_usd_millions.toFixed(1)+"百万USD。2026年第3四半期の売上は前四半期比 "+
    pct(update.q3_revenue_qoq_percent)+"。MIMの米ドル建て前年同期売上は資料に記載なし。 ",
    sourceLink(update.source_pdf_url,"発表資料PDF"),"・",sourceLink(update.presentation_source.url,"業績説明資料PDF"),
    root.document.createElement("br"),
    "親会社Mi Technovationの半導体材料部門（SMBU）の外部顧客売上。2025年1–9月 "+
    money(segment.prior_revenue_thousands)+"千MYR、2026年1–9月 "+money(segment.current_revenue_thousands)+
    "千MYR、前年同期比 "+pct(update.segmentRevenueYoY)+"。 ",sourceLink(segment.source.url,"親会社の四半期報告書PDF"));
  }).catch(e=>{body.replaceChildren();capitalRows.replaceChildren();status.textContent="資料照合エラー："+e.message;});
 }
 if(root?.document)root.document.addEventListener("DOMContentLoaded",init);
 if(typeof module!=="undefined"&&module.exports)module.exports={build,compare,pct};
})(typeof window!=="undefined"?window:null);
