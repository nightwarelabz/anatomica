#!/usr/bin/env node
/* Golden-debrief harness for web/cases.js.
 *
 * For every case in cases/ with an attempt in cases/attempts/, runs
 * ANATOMICA_CASES.createRun(case, attempt, parameters).runDebrief()
 * and deep-diffs the result against the golden debrief in
 * cases/debriefs/ (the golden's inner "debrief" value).
 *
 * Diff rules: numbers within 1e-9 absolute; strings / booleans / null
 * exact; arrays order-sensitive; object key order ignored, key sets
 * must match. Prints per-case PASS/FAIL with the count of compared
 * leaves and the first mismatches, and writes the same report to
 * RESULTS.md next to this file.
 *
 * Usage: node cases-harness/run.js
 */
"use strict";

const fs = require("fs");
const path = require("path");

const ROOT = path.dirname(__dirname);
const CASES_DIR = path.join(ROOT, "cases");
const { createRun } = require(path.join(ROOT, "web", "cases.js"));

const TOL = 1e-9;
const MAX_MISMATCHES_SHOWN = 10;

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function fmt(v) {
  if (v === undefined) return "<missing>";
  const s = JSON.stringify(v);
  return s.length > 160 ? s.slice(0, 157) + "..." : s;
}

// Returns {leaves, mismatches: [{path, expected, actual}]}.
function diff(expected, actual, at, acc) {
  if (expected === null || actual === null ||
      typeof expected !== "object" || typeof actual !== "object") {
    acc.leaves += 1;
    if (typeof expected === "number" && typeof actual === "number") {
      if (!(Math.abs(expected - actual) <= TOL)) {
        acc.mismatches.push({ path: at, expected, actual });
      }
    } else if (expected !== actual) {
      acc.mismatches.push({ path: at, expected, actual });
    }
    return acc;
  }
  if (Array.isArray(expected) || Array.isArray(actual)) {
    if (!Array.isArray(expected) || !Array.isArray(actual)) {
      acc.leaves += 1;
      acc.mismatches.push({ path: at, expected, actual });
      return acc;
    }
    if (expected.length !== actual.length) {
      acc.mismatches.push({
        path: at + ".length", expected: expected.length, actual: actual.length,
      });
    }
    const n = Math.min(expected.length, actual.length);
    for (let i = 0; i < n; i++) diff(expected[i], actual[i], `${at}[${i}]`, acc);
    if (expected.length === 0 && actual.length === 0) acc.leaves += 1;
    return acc;
  }
  const eKeys = Object.keys(expected);
  const aKeys = Object.keys(actual);
  for (const k of eKeys) {
    if (!Object.prototype.hasOwnProperty.call(actual, k)) {
      acc.mismatches.push({ path: `${at}.${k}`, expected: expected[k], actual: undefined });
    }
  }
  for (const k of aKeys) {
    if (!Object.prototype.hasOwnProperty.call(expected, k)) {
      acc.mismatches.push({ path: `${at}.${k}`, expected: undefined, actual: actual[k] });
    }
  }
  for (const k of eKeys) {
    if (Object.prototype.hasOwnProperty.call(actual, k)) {
      diff(expected[k], actual[k], `${at}.${k}`, acc);
    }
  }
  if (eKeys.length === 0 && aKeys.length === 0) acc.leaves += 1;
  return acc;
}

function main() {
  const params = loadJson(path.join(CASES_DIR, "parameters.json"));

  // Attempts grouped by case_id, mirroring tools/case_run.py main().
  const attemptsByCase = new Map();
  for (const f of fs.readdirSync(path.join(CASES_DIR, "attempts")).sort()) {
    if (!f.endsWith(".json")) continue;
    const a = loadJson(path.join(CASES_DIR, "attempts", f)).attempt;
    if (!attemptsByCase.has(a.case_id)) attemptsByCase.set(a.case_id, []);
    attemptsByCase.get(a.case_id).push(a);
  }

  const lines = [];
  lines.push("# cases.js golden-debrief harness — results");
  lines.push("");
  lines.push("Port under test: `web/cases.js`. Goldens: `cases/debriefs/*.json` " +
    "(inner `debrief` value). Numbers compared within 1e-9 absolute; " +
    "strings/booleans/null exact; arrays order-sensitive; object key order ignored.");
  lines.push("");

  let totalCases = 0;
  let passed = 0;
  let totalLeaves = 0;
  let totalMismatches = 0;

  const caseFiles = fs.readdirSync(CASES_DIR)
    .filter((f) => f.startsWith("case.") && f.endsWith(".json")).sort();

  for (const f of caseFiles) {
    const caseObj = loadJson(path.join(CASES_DIR, f)).case;
    for (const attempt of attemptsByCase.get(caseObj.id) || []) {
      totalCases += 1;
      const slug = caseObj.id.replace(/\./g, "-");
      const goldenPath = path.join(
        CASES_DIR, "debriefs", `debrief.${slug}.model-learner.json`);
      let status;
      let acc = { leaves: 0, mismatches: [] };
      let error = null;
      try {
        const golden = loadJson(goldenPath).debrief;
        const actual = createRun(caseObj, attempt, params).runDebrief();
        acc = diff(golden, actual, "$", acc);
      } catch (e) {
        error = e;
      }
      totalLeaves += acc.leaves;
      totalMismatches += acc.mismatches.length;
      const ok = !error && acc.mismatches.length === 0;
      if (ok) passed += 1;
      status = ok ? "PASS" : "FAIL";
      lines.push(`## ${status} — ${caseObj.id} / ${attempt.id}`);
      lines.push("");
      lines.push(`- golden: \`cases/debriefs/debrief.${slug}.model-learner.json\``);
      lines.push(`- leaves compared: ${acc.leaves}`);
      lines.push(`- mismatches: ${acc.mismatches.length}`);
      if (error) {
        lines.push(`- error: ${error && error.stack ? error.stack.split("\n")[0] : error}`);
      }
      if (acc.mismatches.length) {
        lines.push("- first mismatches:");
        for (const m of acc.mismatches.slice(0, MAX_MISMATCHES_SHOWN)) {
          lines.push(`  - \`${m.path}\`: expected ${fmt(m.expected)}, got ${fmt(m.actual)}`);
        }
      }
      lines.push("");
    }
  }

  lines.push(`## Summary: ${passed}/${totalCases} cases PASS, ` +
    `${totalLeaves} leaves compared, ${totalMismatches} mismatches`);
  lines.push("");

  const report = lines.join("\n");
  process.stdout.write(report);
  fs.writeFileSync(path.join(__dirname, "RESULTS.md"), report);
  if (passed !== totalCases) process.exitCode = 1;
}

main();
