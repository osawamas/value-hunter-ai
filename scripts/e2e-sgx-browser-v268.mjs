import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import {chromium} from "playwright-core";

const base=process.env.VALUE_HUNTER_URL||"http://127.0.0.1:8765";
const binary=process.env.CHROME_BIN||"/usr/bin/google-chrome";
const dir=fs.mkdtempSync(path.join(os.tmpdir(),"sgx-browser-v268-"));
const screenshot=process.env.VALUE_HUNTER_E2E_SCREENSHOT||path.join(dir,"sgx-browser-v268.png");
fs.mkdirSync(path.dirname(screenshot),{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:binary,args:["--no-sandbox","--disable-dev-shm-usage"]});
const page=await browser.newPage({acceptDownloads:true,viewport:{width:1370,height:980}});
const failures=[];
page.on("pageerror",e=>failures.push(e.message));
try {
 await page.goto(base+"/index.html",{waitUntil:"domcontentloaded"});
 const count=page.locator("#sgxHistoricalCodeShown");
 await count.getByText(/30 \/ 30 件/).waitFor({timeout:25000});
 assert.equal(await page.locator("#sgxHistoricalCodeRows tr").count(),30,"full researched list");
 // v278 user-supplied SGX research CSV stays inside Chrome and must never
 // activate ranking, independent financial confirmation, or a server upload.
 const localCsv="Trading Code,Trading Name,Listing Board,Traded Currency\r\n"+
   "D05,DBS Group Holdings Ltd,MAINBOARD,SGD\r\n"+
   "O39,Oversea-Chinese Banking Corporation Ltd,MAINBOARD,SGD\r\n";
 await page.locator('#sgxManualMasterForm input[name="masterFile"]').setInputFiles({
  name:"sgx-sample.csv",mimeType:"text/csv",buffer:Buffer.from(localCsv,"utf8")
 });
 await page.locator('#sgxManualMasterForm input[name="sourceURL"]').fill("https://www.sgx.com/securities/trading");
 await page.locator('#sgxManualMasterForm input[name="asOf"]').fill("2026-11-15");
 await page.locator('#sgxManualMasterForm button[type="submit"]').click();
 await page.locator("#sgxManualMasterResult").getByText(/手入力CSV 2件/).waitFor({timeout:15000});
 assert.equal(await page.locator("#sgxManualMasterRows tr").count(),2);
 assert.match(await page.locator("#sgxManualMasterResult").innerText(),/原本・全銘柄・現在上場は未検証/);

 // v280: import more than one page and verify browser search/pagination.
 const largeCsv="Trading Code,Trading Name,Listing Board,Traded Currency\r\n"+
  Array.from({length:120},(_,i)=>i.toString(36).toUpperCase().padStart(4,"0")+
    ",Local Test Stock "+i+",MAINBOARD,SGD").join("\r\n")+"\r\n";
 await page.locator('#sgxManualMasterForm input[name="masterFile"]').setInputFiles({
  name:"sgx-many.csv",mimeType:"text/csv",buffer:Buffer.from(largeCsv,"utf8")
 });
 await page.locator('#sgxManualMasterForm button[type="submit"]').click();
 await page.locator("#sgxManualMasterResult").getByText(/手入力CSV 120件/).waitFor({timeout:12000});
 await page.locator("#sgxManualMasterPageStatus").getByText(/1\/3ページ/).waitFor();
 assert.equal(await page.locator("#sgxManualMasterRows tr").count(),50);
 await page.locator("#sgxManualMasterNext").click();
 await page.locator("#sgxManualMasterPageStatus").getByText(/2\/3ページ/).waitFor();
 await page.locator("#sgxManualMasterNext").click();
 await page.locator("#sgxManualMasterPageStatus").getByText(/3\/3ページ/).waitFor();
 assert.equal(await page.locator("#sgxManualMasterRows tr").count(),20);
 await page.locator("#sgxManualMasterSearch").fill("Local Test Stock 119");
 await page.locator("#sgxManualMasterPageStatus").getByText(/検索一致 1 \/ 120件/).waitFor();
 assert.equal(await page.locator("#sgxManualMasterRows tr").count(),1);
 assert.match(await page.locator("#sgxManualMasterRows").innerText(),/Local Test Stock 119/);
 await page.locator("#sgxManualMasterSearch").fill("");
 const templateDownload=page.waitForEvent("download");
 await page.locator("#sgxManualMasterTemplate").click();
 const template=await templateDownload;
 assert.equal(template.suggestedFilename(),"sgx-source-template-unverified.csv");
 assert.ok(fs.readFileSync(await template.path(),"utf8").includes("Trading Code,Trading Name,Listing Board,Traded Currency"));


 // v277: actual bank FY2025 what-if remains local-only even after input.
 await page.locator("#scenarioBankStatus").getByText(/銀行3社の2025年/).waitFor({timeout:25000});
 await page.locator("#scenarioBankSymbol").selectOption("O39");
 await page.locator('#scenarioBankForm input[name="price"]').fill("40.50");
 await page.locator('#scenarioBankForm input[name="shares"]').fill("1800000000");
 await page.locator('#scenarioBankForm input[name="priceAsOf"]').fill("2026-11-13");
 await page.locator('#scenarioBankForm input[name="sharesAsOf"]').fill("2026-11-12");
 await page.locator('#scenarioBankForm button[type="submit"]').click();
 const scenarioOutput=page.locator("#scenarioBankResult");
 await scenarioOutput.getByText(/参考PER/).waitFor();
 assert.match(await scenarioOutput.innerText(),/時点不一致/);
 assert.match(await scenarioOutput.innerText(),/参考PBR/);
 assert.match(await page.locator("#scenarioBankStatus").innerText(),/正式ランキング/);

 await page.locator("#universeCandidateCount").getByText("182").waitFor({timeout:25000});
 assert.equal(await page.locator("#universeCandidateRows tr").count(),182);
 await page.locator("#universeCandidateProvenance").selectOption("FINANCIAL");
 await page.locator("#universeCandidateShown").getByText(/7件表示/).waitFor();
 assert.equal(await page.locator("#universeCandidateRows tr").count(),7);
 await page.locator("#universeCandidateProvenance").selectOption("OFFICIAL");
 const officialCount=await page.locator("#universeCandidateRows tr").count();
 assert.ok(officialCount>0&&officialCount<=30);
 await page.locator("#universeCandidateProvenance").selectOption("ALL");

 assert.equal(await page.locator("#sgxHistoricalCodeRows tr").filter({hasText:"SGXNet原本本文一致"}).count(),19);
 assert.equal(await page.locator("#sgxHistoricalCodeRows tr").filter({hasText:"SGX公式売買単位表"}).count(),11);
 const finance=page.locator("#sgxHistoricalCodeFinance");
 await finance.selectOption("REGISTERED");
 await count.getByText(/4 \/ 30 件/).waitFor();
 assert.equal(await page.locator("#sgxHistoricalCodeRows tr").count(),4);
 assert.equal(await page.locator("#sgxHistoricalCodeRows a:has-text('財務詳細を見る')").count(),4);
 const o39=page.locator("#sgxHistoricalCodeRows tr").filter({hasText:"O39"});
 await o39.locator("summary:has-text('除外理由を表示')").click();
 assert.equal(await o39.locator("details[open] li").count()>0,true);
 assert.ok((await o39.locator("details[open]").innerText()).includes("未"));
 await o39.locator("a:has-text('財務詳細を見る')").click();
 await page.waitForURL(/#issuer=O39$/);
 await page.locator("#detailContent h3").getByText(/O39/).waitFor({timeout:12000});
 assert.ok((await page.locator("#detailContent").innerText()).includes("ランキングから除外"));
 await page.locator("#sgxHistoricalCodeBoard").selectOption("UNKNOWN");
 await count.getByText(/3 \/ 30 件/).waitFor();
 const downloadPromise=page.waitForEvent("download");
 await page.locator("#sgxHistoricalCodeExport").click();
 const download=await downloadPromise;
 assert.equal(download.suggestedFilename(),"value-hunter-sgx-research-counters.csv");
 const csv=fs.readFileSync(await download.path(),"utf8");
 assert.equal(csv.charCodeAt(0),0xFEFF);
 assert.equal(csv.trim().split("\r\n").length,4,"header plus three UNKNOWN-board financials");
 assert.ok(csv.includes('"D05"')&&csv.includes('"S68"')&&csv.includes('"U11"'));
 assert.ok(csv.includes('"originalHtmlSHA256"'));
 assert.ok(csv.includes('"financialExclusionReasonsJa"'));
 assert.ok(!csv.includes('"O39"'),"MAINBOARD not among UNKNOWN records");
 // Direct hash before feed load must still resolve, not require earlier click.
 const second=await browser.newPage({viewport:{width:390,height:844}});
 second.on("pageerror",e=>failures.push(e.message));
 await second.goto(base+"/index.html#issuer=U11",{waitUntil:"domcontentloaded"});
 await second.locator("#detailContent h3").getByText(/U11/).waitFor({timeout:25000});
 await second.screenshot({path:screenshot,fullPage:false});
 await second.goto(base+"/index.html#issuer=FAKE",{waitUntil:"domcontentloaded"});
 await second.locator("#sgxHistoricalCodeShown").getByText(/30 \/ 30 件/).waitFor({timeout:25000});
 assert.equal((await second.locator("#detailContent h3").allInnerTexts()).some(s=>s.includes("FAKE")),false);
 // v274: a failed SGX original-source request may suppress evidence badges,
 // but must NOT erase the third-party discovery directory.
 if(!base.startsWith("file:")){
 const degraded=await browser.newPage();
 degraded.on("pageerror",e=>failures.push(e.message));
 await degraded.route("**/data/sgx-nineteen-original-html-sha-v262.json",route=>route.abort());
 await degraded.goto(base+"/index.html",{waitUntil:"domcontentloaded"});
 await degraded.locator("#universeCandidateCount").getByText("182").waitFor({timeout:25000});
 assert.equal(await degraded.locator("#universeCandidateRows tr").count(),182);
 assert.equal(await degraded.locator("#universeCandidateRows a:has-text('コード根拠を開く')").count(),0);
 assert.equal(await degraded.locator("#universeCandidateRows a:has-text('財務詳細を見る')").count(),0);
 assert.match(await degraded.locator("#universeCandidateStatus").innerText(),/一時停止/);
 await degraded.close();
 }
 assert.deepEqual(failures,[],"JavaScript browser errors");
 console.log("v279 PASS ("+(base.startsWith("file:")?"file:// offline bundle":"HTTP served docs")+"): real Chromium, 182 candidates, 30 researched SGX codes, bank scenario, manual CSV import, finance links, export and mobile");
 console.log("v268 screenshot "+screenshot);
} finally {await browser.close();}
