#!/usr/bin/env python3
"""Build a double-click file:// browser preview with embedded pre-existing public JSON.
Do NOT fetch network data, include third-party secrets or turn dated data into live prices.
Output is a distinct reproducible folder, not a mutation of source docs/.
"""
import json
import pathlib
import shutil
import sys

ROOT=pathlib.Path(__file__).resolve().parent.parent
DOCS=ROOT/"docs"
OUT=ROOT/"build/release-v279"
STANDALONE=OUT/"standalone"
BOOT="offline-data-v279.js"
MAX_BYTES=12_000_000

def build():
    if STANDALONE.exists():
        shutil.rmtree(STANDALONE)
    shutil.copytree(DOCS,STANDALONE/"docs")
    site=STANDALONE/"docs"
    blobs={}
    total=0
    for source in sorted((DOCS/"data").rglob("*.json")):
        relative=source.relative_to(DOCS).as_posix()
        raw=source.read_bytes()
        total+=len(raw)
        if total>MAX_BYTES:
            raise ValueError("Packaged public data exceeds 12MB bound")
        json.loads(raw)
        blobs["./"+relative]=raw.decode("utf-8")
    required={
     "./data/latest.json",
     "./data/sgx-universe-candidates.json",
     "./data/sgx-nineteen-original-html-sha-v262.json",
     "./data/sgx-official-issuer-code-filings-v255.json",
     "./data/sgx-net-eleven-codes-v256.json"}
    if not required.issubset(blobs) or len(blobs)<20:
        raise ValueError("Missing required public data snapshots")
    # JSON encoded as JS quoted string values; serialized twice, never raw HTML.
    payload=json.dumps(blobs,ensure_ascii=True,separators=(",",":"))
    script="""/* v279: file:// local preview support.
 * Every bundled JSON blob comes from public docs/data at packaging time.
 * No external fetches, storage, analytics, quotes or background updates.
 */
(function(){
 "use strict";
 if(location.protocol!=="file:")return;
 const DATA=Object.freeze(PAYLOAD);
 const upstream=window.fetch.bind(window);
 window.fetch=function(input,options){
   const raw=typeof input==="string"?input:input?.url;
   if(typeof raw==="string"&&Object.prototype.hasOwnProperty.call(DATA,raw)){
      return Promise.resolve(new Response(DATA[raw],{
        status:200,headers:{"Content-Type":"application/json;charset=utf-8",
         "X-Value-Hunter-Provenance":"BUNDLED_DATED_PUBLIC_SNAPSHOT"}
      }));
   }
   // Local mode never asks the network for an updated stock/market feed.
   return Promise.reject(new TypeError("Local preview only: data is a fixed, dated bundle"));
 };
 window.VALUE_HUNTER_OFFLINE_MODE=Object.freeze({
   active:true,fileCount:Object.keys(DATA).length,
   liveMarketData:false,rankingOverride:false});
})();
""".replace("PAYLOAD",payload)
    (site/BOOT).write_text(script,encoding="utf-8")
    path=site/"index.html"
    html=path.read_text(encoding="utf-8")
    head='<head>'
    if head not in html or BOOT in html:raise ValueError("Offline bootstrap placement conflict")
    html=html.replace(head,head+'\n  <script src="./'+BOOT+'"></script>',1)
    path.write_text(html,encoding="utf-8")
    (STANDALONE/"START-HERE.txt").write_text(
        "VALUE HUNTER AI — クリックで起動するローカルプレビュー\n"
        "1. ZIPを解凍する\n"
        "2. docs フォルダの index.html をChromeで開く\n"
        "3. 固定日時の同梱データを表示。ネットワーク更新・株価自動取得なし\n"
        "4. 銀行PER/PBRの手入力参考試算やCSV照合は端末内だけ\n"
        "注意：公式SGX全銘柄、現在の上場や財務の独立照合は未完了。\n"
        "ランキング適格0社、投資助言ではない。\n"
        "最新データはGitHubの新しい配布版を取得して更新する。\n",encoding="utf-8")
    manifest={"schema_version":"value_hunter_local_file_bundle_v279",
      "number_of_bundled_public_json_files":len(blobs),
      "original_public_data_bytes":total,
      "live_market_data":False,"full_sgx_master":False,
      "ranking_eligible_override":False,"original_git_docs_modified":False}
    (OUT/"manifest-v279.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"v279 staged: {len(blobs)} public JSON files, {total} bytes, NO server required, NO live price")
if __name__=="__main__":build()
