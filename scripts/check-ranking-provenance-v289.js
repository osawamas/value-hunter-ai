"use strict";
const fs = require("node:fs");
const path = require("node:path");
const {checkProvenance: checkFeed, sgxQuoteDate, validDate} = require("../docs/sgx-ranking-validation.js");
if (require.main === module) {
  const file = path.resolve(__dirname, "../docs/data/latest.json");
  const errors = checkFeed(JSON.parse(fs.readFileSync(file, "utf8")));
  if (errors.length) { console.error(errors.join("\\n")); process.exitCode = 1; }
  else console.log("v289 PASS: published feed ranking requires licensed quote plus independently verified financials");
}
module.exports = {checkFeed, sgxQuoteDate, validDate};
