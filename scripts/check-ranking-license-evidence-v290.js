"use strict";
const fs = require("node:fs");
const path = require("node:path");
const {checkFeed, validDate} = require("../docs/sgx-ranking-validation.js");
if(require.main===module){
 const feed=JSON.parse(fs.readFileSync(path.resolve(__dirname,"../docs/data/latest.json"),"utf8"));
 const errors=checkFeed(feed);
 if(errors.length){console.error(errors.join("\n"));process.exitCode=1}
 else console.log("v290 PASS: real feed fail-closed; no license inferred");
}
module.exports={checkFeed,validDate};
