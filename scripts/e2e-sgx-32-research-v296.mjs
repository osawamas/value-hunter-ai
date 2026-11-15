import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import {chromium} from "playwright-core";
const base=process.env.VALUE_HUNTER_URL||"http://127.0.0.1:8765";
const dir=fs.mkdtempSync(path.join(os.tmpdir(),"sgx-32-v296-"));
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||"/usr/bin/google-chrome",args:["--no-sandbox","--disable-dev-shm-usage"]});
try{
 const page=await browser.newPage({acceptDownloads:true});
 const errors=[];page.on("pageerror",e=>errors.push(e.message));
 await page.goto(base+"/sgx-32-research.html",{waitUntil:"domcontentloaded"});
 await page.locator("#research32Count").getByText(/33 \/ 33件/).waitFor({timeout:25000});
 assert.equal(await page.locator("#research32Rows tr").count(),33);
 
 await page.locator("#sgxIpoFinancialStatus").getByText(/監査済み実績/).waitFor({timeout:25000});
 const financeRows=page.locator("#sgxIpoFinancialRows tr");
 assert.equal(await financeRows.count(),6,"two issuers times three audited fiscal years");
 const delugeAudit=financeRows.filter({hasText:"9DC"}).filter({hasText:"2026-03-31"});
 assert.equal(await delugeAudit.count(),1);
 assert.match(await delugeAudit.innerText(),/116,662/);
 assert.doesNotMatch(await delugeAudit.innerText(),/116,567/);
 assert.deepEqual((await delugeAudit.locator("td").allTextContents()).slice(-4),
  ["48.0%","17,966","15.4%","-26.7%"]);
 const miAudit=financeRows.filter({hasText:"MIM"}).filter({hasText:"2025-12-31"});
 assert.equal(await miAudit.count(),1);
 assert.match(await miAudit.innerText(),/65,335/);
 assert.deepEqual((await miAudit.locator("td").allTextContents()).slice(-4),
  ["73.2%","—","—","—"]);
 assert.match(await page.locator("#sgxIpoFinancialStatus").innerText(),/未監査.*70\.6%/);
 const businessUpdate=page.locator("#sgxIpoBusinessUpdate");
 const updateText=await businessUpdate.innerText();
 assert.match(updateText,/未監査.*91\.5百万USD.*税引後利益 25\.5百万USD.*調整後税引後利益 25\.7百万USD.*前四半期比 \+15\.6%/);
 assert.match(updateText,/MIMの米ドル建て前年同期売上は資料に記載なし/);
 assert.match(updateText,/半導体材料部門.*185,667千MYR.*368,216千MYR.*前年同期比 \+98\.3%/);
 assert.match(await businessUpdate.getByRole("link",{name:"発表資料PDF",exact:true}).getAttribute("href"),/FileID=909744$/);
 const shareCapital=page.locator("#sgxIpoListingCapitalRows tr");
 assert.match(await shareCapital.filter({hasText:"9DC"}).innerText(),/2026-10-16.*145,000,000/s);
 assert.match(await shareCapital.filter({hasText:"MIM"}).filter({hasText:"2026-10-28"}).innerText(),/2026-10-28.*495,000,000.*500万株は加算しない/s);
 const mimFollowup=shareCapital.filter({hasText:"MIM"}).filter({hasText:"2026-11-06"});
 assert.match(await mimFollowup.innerText(),/495,000,000.*発行済普通株式数/s);
 assert.match(await mimFollowup.getByRole("link",{name:"11月10日の株主開示PDF"}).getAttribute("href"),/910861_/);
 const metCapital=shareCapital.filter({hasText:"MET"});
 assert.match(await metCapital.innerText(),/2026-11-03.*166,617,000.*自己株式控除後/s);
 assert.match(await metCapital.getByRole("link",{name:"HKEX割当完了PDF"}).getAttribute("href"),/^https:\/\/www1\.hkexnews\.hk\//);
 assert.match(await metCapital.innerText(),/11月2日残高.*168,000,000株.*1,383,000株/);
 assert.match(await metCapital.getByRole("link",{name:"HKEX翌日開示PDF"}).getAttribute("href"),/2026110400313\.pdf$/);
 const metFinancials=page.locator("#sgxMetFinancialRows tr");
 assert.equal(await metFinancials.count(),5);
 assert.match(await metFinancials.filter({hasText:"2026-06-30"}).innerText(),/26,978.*4,929.*\+8\.9%.*-56\.4%/s);
 assert.match(await page.locator("#sgxMetFinancialSources").innerText(),/再測定益約640万SGD/);

 await page.locator("#research32Type").selectOption("IPO");
 await page.locator("#research32Count").getByText(/3 \/ 33件/).waitFor();
 const ipo=await page.locator("#research32Rows").innerText();
 assert.match(ipo,/9DC/);assert.match(ipo,/MIM/);
 assert.match(ipo,/SGXE96931105/);assert.match(ipo,/SGXE49931863/);
 assert.match(ipo,/KYG9R41B1017/);
 const urls=await page.locator("#research32Rows a").evaluateAll(as=>as.map(a=>a.href));
 assert.equal(urls.length,3);assert.ok(urls.every(x=>x.startsWith("https://links.sgx.com/")));
 await page.locator("#research32Query").fill("MIM");
 assert.equal(await page.locator("#research32Rows tr").count(),1);
 const promise=page.waitForEvent("download");
 await page.locator("#research32Export").click();
 const download=await promise;const out=path.join(dir,"catalog.csv");
 await download.saveAs(out);
 const csv=fs.readFileSync(out,"utf8");
 assert.match(csv,/MIM/);assert.doesNotMatch(csv,/9DC/);
 assert.match(csv,/SGXE49931863/);
 await page.locator("#research32Query").fill("");
 await page.locator("#research32Type").selectOption("ALL");
 await page.locator("#research32Finance").selectOption("YES");
 await page.locator("#research32Count").getByText(/4 \/ 33件/).waitFor();
 assert.equal(await page.locator("#research32Rows tr").count(),4);
 await page.goto(base+"/market-research.html",{waitUntil:"domcontentloaded"});
 await page.locator("#marketCount").getByText(/16 \/ 16件/).waitFor({timeout:25000});
 assert.deepEqual(await page.locator("#marketCoverageRows td").allTextContents(),
  ["5","4","0","4","4","0","7","4","0"]);
 await page.locator("#marketFilter").selectOption("JP");
 await page.locator("#marketQuery").fill("７２０３");
 await page.getByRole("button",{name:"財務を見る"}).click();
 assert.match(await page.locator("#marketDetailTitle").innerText(),/トヨタ/);
 assert.match(await page.locator("#marketFinancialRows tr").last().innerText(),/50,684,952,000,000/);
 await page.getByRole("checkbox",{name:"トヨタ自動車を比較"}).check();
 await page.locator("#marketQuery").fill("7201");
 await page.getByRole("button",{name:"財務を見る"}).click();
 await page.locator("#scenarioDate").fill("2026-03-31");
 await page.locator("#scenarioPrice").fill("300");
 await page.locator("#scenarioShares").fill("3496382520");
 await page.getByRole("button",{name:"試算する"}).click();
 assert.match(await page.locator("#marketScenarioResult").innerText(),/参考時価総額 1,048,914,756,000 JPY、PER —、PBR 0\.22倍/);
 await page.locator("#personalQuoteFile").setInputFiles({
  name:"quotes.csv", mimeType:"text/csv",
  buffer:Buffer.from("market_id,date,currency,close\nJP:7201,2026-03-31,JPY,300\nUS:AAPL,2026-11-13,USD,356"),
 });
 await page.locator("#personalQuoteStatus").getByText(/終値を 2件/).waitFor();
 await page.getByRole("button",{name:"CSV終値を使う"}).click();
 assert.equal(await page.locator("#scenarioShares").inputValue(),"3496382520");
 assert.equal(await page.locator("#scenarioPrice").inputValue(),"300");
 await page.locator("#marketFilter").selectOption("US");
 await page.locator("#marketQuery").fill("AAPL");
 await page.getByRole("button",{name:"財務を見る"}).click();
 assert.match(await page.locator("#marketDetailCurrency").innerText(),/USD/);
 await page.getByRole("button",{name:"CSV終値を使う"}).click();
 assert.equal(await page.locator("#scenarioPrice").inputValue(),"356");
 assert.equal(await page.locator("#scenarioDate").inputValue(),"2026-11-13");
 assert.equal(await page.locator("#scenarioShares").inputValue(),"");
 await page.locator("#personalShareFile").setInputFiles({
  name:"shares.csv", mimeType:"text/csv",
  buffer:Buffer.from("market_id,date,shares_excluding_treasury\nUS:AAPL,2026-11-12,14500000001\nUS:AAPL,2026-11-13,14500000000\nJP:7201,2026-03-31,1"),
 });
 await page.locator("#personalShareStatus").getByText(/株数を 3件/).waitFor();
 await page.getByRole("button",{name:"CSV終値を使う"}).click();
 assert.equal(await page.locator("#scenarioShares").inputValue(),"14500000000");
 await page.locator("#scenarioDate").fill("2026-11-12");
 assert.equal(await page.locator("#scenarioPrice").inputValue(),"");
 assert.equal(await page.locator("#scenarioShares").inputValue(),"");
 await page.getByRole("button",{name:"CSV終値を使う"}).click();
 await page.locator("#personalShareFile").setInputFiles([]);
 assert.equal(await page.locator("#scenarioShares").inputValue(),"");
 assert.equal(await page.locator("#scenarioPrice").inputValue(),"356");
 await page.locator("#personalShareFile").setInputFiles({
  name:"conflict.csv", mimeType:"text/csv",
  buffer:Buffer.from("market_id,date,shares_excluding_treasury\nJP:7201,2026-03-31,1"),
 });
 await page.locator("#personalShareStatus").getByText(/株数を 1件/).waitFor();
 await page.locator("#marketFilter").selectOption("JP");
 await page.locator("#marketQuery").fill("7201");
 await page.getByRole("button",{name:"財務を見る"}).click();
 assert.match(await page.locator("#personalQuoteMatch").innerText(),/不一致/);
 await page.getByRole("button",{name:"CSV終値を使う"}).click();
 assert.equal(await page.locator("#scenarioShares").inputValue(),"");
 await page.locator("#marketFilter").selectOption("US");
 await page.locator("#marketQuery").fill("AAPL");
 await page.getByRole("button",{name:"財務を見る"}).click();
 await page.getByRole("checkbox",{name:"Appleを比較"}).check();
 assert.equal(await page.locator("#marketCompareRows tr").count(),2);
 assert.match(await page.locator("#marketCompareRows tr").first().innerText(),/トヨタ.*JPY/s);
 assert.match(await page.locator("#marketCompareRows tr").last().innerText(),/Apple.*USD/s);
 await page.getByRole("button",{name:"トヨタ自動車を比較から外す"}).click();
 assert.equal(await page.locator("#marketCompareRows tr").count(),1);
 assert.match(await page.locator("#marketShareCount").innerText(),/14,532,182,000.*2026-10-23/);
 await page.locator("#marketQuery").fill("AMZN");
 await page.getByRole("button",{name:"財務を見る"}).click();
 assert.match(await page.locator("#marketFinancialRows tr").last().innerText(),/716,924,000,000/);
 assert.match(await page.locator("#marketQuarterlyRows tr").last().innerText(),/2026-09-30.*201,944,000,000.*28,076,000,000/s);
 assert.match(await page.getByRole("link",{name:"SEC Form 10-Q"}).getAttribute("href"),/000101872426000040/);
 await page.locator("#marketQuery").fill("NVDA");
 await page.getByRole("button",{name:"財務を見る"}).click();
 assert.match(await page.locator("#marketShareCount").innerText(),/約24,300,000,000/);
 await page.locator("#marketFilter").selectOption("SG");
 await page.locator("#marketQuery").fill("S20");
 await page.locator("#marketRows").getByRole("checkbox").check();
 assert.equal(await page.locator("#marketCompareRows tr").count(),2);
 assert.match(await page.locator("#marketCompareRows tr").last().innerText(),/S20.*FY2025.*SGD.*623,300,000.*10\.4%.*—.*40\.7%.*照合途中/s);
 await page.locator("#marketQuery").fill("U11");
 assert.equal(await page.locator("#marketRows").getByRole("checkbox").count(),0);
 assert.match(await page.locator("#marketRows").innerText(),/U11.*SGX財務画面/s);
 assert.deepEqual(errors,[]);
 console.log("v296 PASS "+(base.startsWith("file:")?"file offline":"HTTP ZIP")+": Chrome 33 codes, IPO/finance filter, search, source links, downloaded CSV");
}finally{await browser.close();fs.rmSync(dir,{recursive:true,force:true});}
