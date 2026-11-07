/* ANATOMICA Case Workbench runner — JavaScript port of tools/case_run.py.
 *
 * Faithful port: computes, from a case object, an attempt object and
 * cases/parameters.json, the workbench board per stage, the criteria
 * block evaluations per stage, the attempt scores, the per-order
 * evidence classification and the resource tally, and builds the
 * PEARLS debrief object (the inner "debrief" value of the golden
 * files in cases/debriefs/).
 *
 * UMD: attaches `window.ANATOMICA_CASES` in a browser, uses
 * `module.exports` in Node. No dependencies.
 *
 * API: createRun(caseObj, attemptObjOrNull, paramsObj)
 *   caseObj / attemptObj are the UNWRAPPED objects (the values of the
 *   "case" / "attempt" keys of the JSON files); paramsObj is the
 *   parsed cases/parameters.json document.
 */
(function (root, factory) {
  if (typeof module === "object" && module !== null && typeof module.exports === "object") {
    module.exports = factory();
  } else {
    root.ANATOMICA_CASES = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // ---------- Python semantics helpers ------------------------------

  function has(obj, key) {
    return obj !== null && obj !== undefined &&
      Object.prototype.hasOwnProperty.call(obj, key);
  }

  // Python truthiness: None/False/0/0.0/""/empty list/empty dict are
  // falsy; NaN is (unlike JS) truthy in Python.
  function pyTruthy(v) {
    if (v === null || v === undefined || v === false) return false;
    if (typeof v === "number") return v !== 0;
    if (typeof v === "string") return v.length > 0;
    if (Array.isArray(v)) return v.length > 0;
    if (typeof v === "object") return Object.keys(v).length > 0;
    return Boolean(v);
  }

  // Python == for the scalar values compared in criteria rules
  // (booleans, numbers, strings, None): True == 1 and False == 0.
  function pyEq(a, b) {
    if (a === b) return true;
    var aNum = typeof a === "boolean" || typeof a === "number";
    var bNum = typeof b === "boolean" || typeof b === "number";
    if (aNum && bNum) return Number(a) === Number(b);
    if ((a === null || a === undefined) && (b === null || b === undefined)) return true;
    return false;
  }

  function getOr(obj, key, dflt) {
    return has(obj, key) ? obj[key] : dflt;
  }

  function getOrNull(obj, key) {
    if (!has(obj, key)) return null;
    return obj[key] === undefined ? null : obj[key];
  }

  function toSet(x) {
    if (x === null || x === undefined) return new Set();
    if (x instanceof Set) return x;
    if (Array.isArray(x)) return new Set(x);
    if (x instanceof Map) return new Set(x.keys());
    if (typeof x === "object") return new Set(Object.keys(x));
    return new Set([x]);
  }

  function dictEq(a, b) {
    var ka = Object.keys(a);
    if (ka.length !== Object.keys(b).length) return false;
    for (var i = 0; i < ka.length; i++) {
      if (!has(b, ka[i]) || a[ka[i]] !== b[ka[i]]) return false;
    }
    return true;
  }

  // Python max(d, key=d.get): first maximal key in insertion order.
  function maxKey(obj) {
    var keys = Object.keys(obj);
    if (keys.length === 0) throw new Error("ValueError: max() arg is an empty sequence");
    var best = keys[0];
    for (var i = 1; i < keys.length; i++) {
      if (obj[keys[i]] > obj[best]) best = keys[i];
    }
    return best;
  }

  // ---------- exact round-half-even on the binary double ------------
  // Python round(x, 4) and format(x, ".4f") round the EXACT binary
  // value of the double, ties to even. JS toFixed / Math.round do not
  // do this, so decompose the double with BigInt and round the exact
  // rational value mantissa * 2^exp * 10^ndigits.

  function roundedScaledInt(absX, ndigits) {
    var view = new DataView(new ArrayBuffer(8));
    view.setFloat64(0, absX, false);
    var bits = view.getBigUint64(0, false);
    var expBits = Number((bits >> 52n) & 0x7ffn);
    var frac = bits & ((1n << 52n) - 1n);
    var mantissa, exp;
    if (expBits === 0) {
      mantissa = frac;
      exp = -1074;
    } else {
      mantissa = frac | (1n << 52n);
      exp = expBits - 1075;
    }
    var numerator = mantissa * (10n ** BigInt(ndigits));
    var denominator = 1n;
    if (exp >= 0) {
      numerator <<= BigInt(exp);
    } else {
      denominator <<= BigInt(-exp);
    }
    var q = numerator / denominator;
    var r = numerator % denominator;
    var twice = r * 2n;
    if (twice > denominator || (twice === denominator && (q & 1n) === 1n)) {
      q += 1n;
    }
    return q;
  }

  function pyRound(x, ndigits) {
    if (ndigits === undefined) ndigits = 4;
    if (typeof x !== "number" || !isFinite(x)) return x;
    if (ndigits < 0) throw new Error("pyRound: negative ndigits not supported");
    var neg = x < 0 || Object.is(x, -0);
    var q = roundedScaledInt(Math.abs(x), ndigits);
    if (q === 0n) return neg ? -0 : 0;
    var signed = neg ? -q : q;
    return Number(signed) / Number(10n ** BigInt(ndigits));
  }

  // Python f"{x:.4f}".
  function format4(x) {
    if (typeof x !== "number" || !isFinite(x)) return String(x);
    var neg = x < 0 || Object.is(x, -0);
    var q = roundedScaledInt(Math.abs(x), 4);
    var intPart = q / 10000n;
    var fracPart = q % 10000n;
    return (neg ? "-" : "") + intPart.toString() + "." +
      fracPart.toString().padStart(4, "0");
  }

  // Python 3.12+ built-in sum() over floats uses Neumaier
  // (compensated) summation, not a naive left-to-right add; the
  // unrounded board probabilities in the goldens are bit-exact only
  // with the compensated form, so board totals and Brier scores use
  // it. Integer sums are exact either way and do not need it.
  function pySum(values) {
    var sum = 0.0;
    var c = 0.0;
    for (var i = 0; i < values.length; i++) {
      var x = values[i];
      var t = sum + x;
      if (Math.abs(sum) >= Math.abs(x)) {
        c += (sum - t) + x;
      } else {
        c += (x - t) + sum;
      }
      sum = t;
    }
    return sum + c;
  }

  // Python str() of a score item's points, for the criteria_items
  // "satisfied:<points>" state strings. JSON points are ints or
  // non-integral floats (1.5, 3.5, 4.5), for which JS String() matches
  // Python str() exactly.
  function pointsStr(points) {
    return String(points);
  }

  // ---------- the run -----------------------------------------------

  function indexBy(arr) {
    var out = {};
    for (var i = 0; i < arr.length; i++) out[arr[i].id] = arr[i];
    return out;
  }

  function createRun(caseObj, attemptObj, paramsObj) {
    if (!caseObj) throw new Error("createRun: case object required");
    if (!paramsObj || !Array.isArray(paramsObj.parameters)) {
      throw new Error("createRun: params object with a parameters array required");
    }
    var CONST = {};
    paramsObj.parameters.forEach(function (p) { CONST[p.key] = p.value; });
    var RULE_OUT = CONST["rule_out_threshold"];
    var ANCHOR = CONST["anchoring_threshold"];
    var DISC_DELTA = CONST["discriminating_delta"];

    var attempt = attemptObj === undefined ? null : attemptObj;

    var run = {
      case: caseObj,
      attempt: attempt,
      params: paramsObj,
      constants: CONST,
      ruleOutThreshold: RULE_OUT,
      anchoringThreshold: ANCHOR,
      discriminatingDelta: DISC_DELTA,
      findings: indexBy(caseObj.findings),
      labs: indexBy(caseObj.labs),
      tests: indexBy(caseObj.available_tests),
      measurements: indexBy(getOr(caseObj, "measurements", [])),
      hyps: caseObj.hypotheses.map(function (h) { return h.id; }),
      priors: {},
      truth: caseObj.adjudication.diagnosis_hypothesis,
      stages: caseObj.presentation_stages.map(function (s) { return s.stage; }),
      blocks: null, // filled below
    };
    caseObj.hypotheses.forEach(function (h) { run.priors[h.id] = h.prior.value; });

    // ---------- criteria blocks (all declared in the case file) ----
    function buildBlocks() {
      var blocks = [];
      var ev = caseObj.adjudication ? getOr(caseObj.adjudication, "tg18_evaluation", undefined) : undefined;
      if (pyTruthy(ev)) { // Milestone 20 form: the TG18 cholecystitis block
        blocks.push({
          id: "tg18_cholecystitis", kind: "grouped",
          groups: ev.groups, status_rules: ev.status_rules,
          default_status: ev.default_status,
        });
      }
      (getOr(caseObj, "criteria_blocks", [])).forEach(function (b) { blocks.push(b); });
      return blocks;
    }
    run.blocks = buildBlocks();

    // ---------- atoms ----------------------------------------------
    function refStage(atom) {
      if (has(atom, "finding_id")) return run.findings[atom.finding_id].stage;
      if (has(atom, "lab_id")) return run.labs[atom.lab_id].stage;
      if (has(atom, "measurement_id")) return run.measurements[atom.measurement_id].stage;
      return null;
    }
    run._refStage = refStage;

    function atomExcluded(atom, excl) {
      var keys = ["finding_id", "lab_id", "measurement_id"];
      for (var i = 0; i < keys.length; i++) {
        if (has(atom, keys[i]) && excl.has(atom[keys[i]])) return true;
      }
      if (has(atom, "measurement_id")) {
        var m = run.measurements[atom.measurement_id];
        var src = m ? getOr(m, "finding_id", null) : null;
        if (excl.has(src)) return true;
      }
      return false;
    }
    run._atomExcluded = atomExcluded;

    // three=false: true / false / "not-assessed" (unrevealed = false).
    // three=true: "satisfied" / "unsatisfied" / "unknown".
    function atomFn(atom, stage, excl, three) {
      var exclSet = toSet(excl);
      var isThree = Boolean(three);
      if (getOr(atom, "assessable", undefined) === false) {
        return !isThree ? "not-assessed" : "unknown";
      }
      if (has(atom, "constant")) {
        var cv = pyTruthy(atom.constant);
        return !isThree ? cv : (cv ? "satisfied" : "unsatisfied");
      }
      if (atomExcluded(atom, exclSet)) {
        return isThree ? "unknown" : false;
      }
      var rs = refStage(atom);
      if (rs !== null && rs !== undefined && rs > stage) {
        return isThree ? "unknown" : false;
      }
      var v, t;
      if (has(atom, "finding_id")) {
        var f = run.findings[atom.finding_id];
        v = getOr(f, "presence", "present") === atom.is;
      } else if (has(atom, "lab_id")) {
        var lab = run.labs[atom.lab_id];
        v = lab.value;
        t = atom.test;
        if (t === "value_gt") v = v > atom.threshold;
        else if (t === "value_lt") v = v < atom.threshold;
        else if (t === "value_gte") v = v >= atom.threshold;
        else if (t === "value_lte") v = v <= atom.threshold;
        else if (t === "above_reference") v = v > lab.reference_range.high;
        else if (t === "value_gt_uln_multiple") v = v > atom.factor * lab.reference_range.high;
        else if (t === "value_gte_uln_multiple") v = v >= atom.factor * lab.reference_range.high;
        else throw new Error("ValueError: " + JSON.stringify(atom));
      } else if (has(atom, "measurement_id")) {
        v = run.measurements[atom.measurement_id].value;
        t = atom.test;
        if (t === "value_gt") v = v > atom.threshold;
        else if (t === "value_lt") v = v < atom.threshold;
        else if (t === "value_gte") v = v >= atom.threshold;
        else if (t === "value_lte") v = v <= atom.threshold;
        else throw new Error("ValueError: " + JSON.stringify(atom));
      } else if (has(atom, "case_field")) {
        v = caseObj.patient[atom.case_field];
        if (atom.test === "value_gt") v = v > atom.threshold;
        else if (atom.test === "value_lt") v = v < atom.threshold;
        else throw new Error("ValueError: " + JSON.stringify(atom));
      } else {
        throw new Error("ValueError: " + JSON.stringify(atom));
      }
      return !isThree ? v : (v ? "satisfied" : "unsatisfied");
    }
    run.atom = atomFn;

    function itemBool(item, stage) {
      var states = item.evidence.map(function (a) { return atomFn(a, stage); });
      if (states.some(function (s) { return s === true; })) return true;
      if (states.some(function (s) { return s === "not-assessed"; })) return "not-assessed";
      return false;
    }
    run.itemBool = itemBool;
    run.item_bool = itemBool;

    function itemThree(item, stage, excl) {
      var exclSet = toSet(excl);
      var states = item.evidence.map(function (a) { return atomFn(a, stage, exclSet, true); });
      if (states.indexOf("satisfied") !== -1) return "satisfied";
      if (states.every(function (s) { return s === "unsatisfied"; })) return "unsatisfied";
      return "unknown";
    }
    run.itemThree = itemThree;
    run.item_three = itemThree;

    // ---------- block evaluation ------------------------------------
    function scoreItem(item, stage, excl) {
      var exclSet = toSet(excl);
      var tiers = has(item, "tiers") ? item.tiers : [
        { points: item.points, evidence: item.evidence }];
      var states = [];
      tiers.forEach(function (tier) {
        var vals = tier.evidence.map(function (a) { return atomFn(a, stage, exclSet, true); });
        if (vals.indexOf("satisfied") !== -1) states.push("satisfied");
        else if (vals.length && vals.every(function (s) { return s === "unsatisfied"; })) states.push("unsatisfied");
        else states.push("unknown");
      });
      for (var i = 0; i < tiers.length; i++) {
        if (states[i] === "satisfied") return { state: "satisfied", points: tiers[i].points };
      }
      if (states.length && states.every(function (s) { return s === "unsatisfied"; })) {
        return { state: "unsatisfied", points: 0 };
      }
      return { state: "unknown", points: 0 };
    }
    run.scoreItem = scoreItem;
    run.score_item = scoreItem;

    function evalBlock(block, stage) {
      var kind = block.kind;
      if (kind === "grouped") {
        var groups = {};
        block.groups.forEach(function (g) {
          groups[g.group] = g.items.some(function (it) { return itemBool(it, stage) === true; });
        });
        var status = block.default_status;
        for (var ri = 0; ri < block.status_rules.length; ri++) {
          var rule = block.status_rules[ri];
          var req = getOr(rule, "require", {});
          var anyof = getOr(rule, "require_any", {});
          var reqOk = Object.keys(req).every(function (g) { return pyEq(groups[g], req[g]); });
          var anyOk = !pyTruthy(anyof) ||
            Object.keys(anyof).some(function (g) { return pyEq(groups[g], anyof[g]); });
          if (reqOk && anyOk) { status = rule.status; break; }
        }
        return { groups: groups, status: status };
      }
      if (kind === "k_of_n") {
        var items = {};
        block.items.forEach(function (it) { items[it.id] = itemBool(it, stage) === true; });
        var met = Object.keys(items).reduce(function (n, k) { return n + (items[k] ? 1 : 0); }, 0);
        return { items: items, items_met: met, diagnosable: met >= block.k };
      }
      if (kind === "classification") {
        var inputs = {};
        block.inputs.forEach(function (inp) {
          var states = inp.atoms.map(function (a) { return atomFn(a, stage, undefined, true); });
          if (states.indexOf("satisfied") !== -1) inputs[inp.id] = true;
          else if (states.every(function (s) { return s === "unsatisfied"; })) inputs[inp.id] = false;
          else inputs[inp.id] = "unknown";
        });
        for (var i = 0; i < block.rules.length; i++) {
          var rule2 = block.rules[i];
          var when = rule2.when;
          var ok = Object.keys(when).every(function (k) { return pyEq(inputs[k], when[k]); });
          if (ok) {
            return { status: "classified", result: rule2.result, rule_index: i, inputs: inputs };
          }
        }
        return {
          status: getOr(block, "pending_label", "not yet classifiable"),
          result: null, rule_index: null, inputs: inputs,
        };
      }
      if (kind === "score") {
        var sItems = {};
        var total = 0;
        var notAssessed = [];
        block.items.forEach(function (it) {
          var r = scoreItem(it, stage);
          sItems[it.id] = r;
          total += r.points;
          if (r.state === "unknown") notAssessed.push(it.id);
        });
        var sStatus = block.default_status;
        for (var bi = 0; bi < block.bands.length; bi++) {
          var band = block.bands[bi];
          if (band.min <= total && total <= band.max) { sStatus = band.status; break; }
        }
        return {
          items: sItems, total: total, max_total: block.max_total,
          not_assessed: notAssessed, partial: notAssessed.length > 0, status: sStatus,
        };
      }
      throw new Error("ValueError: " + String(kind));
    }
    run.evalBlock = evalBlock;
    run.eval_block = evalBlock;

    function criteriaItems(stage, excl) {
      var exclSet = toSet(excl);
      var out = {};
      run.blocks.forEach(function (block) {
        if (block.kind === "grouped" || block.kind === "k_of_n") {
          var groupsArr = block.kind === "grouped" ? block.groups : [{ items: block.items }];
          groupsArr.forEach(function (g) {
            g.items.forEach(function (it) {
              out[block.id + "." + it.id] = itemThree(it, stage, exclSet);
            });
          });
        } else if (block.kind === "classification") {
          block.inputs.forEach(function (inp) {
            out[block.id + "." + inp.id] = itemThree({ evidence: inp.atoms }, stage, exclSet);
          });
        } else if (block.kind === "score") {
          block.items.forEach(function (it) {
            var r = scoreItem(it, stage, exclSet);
            out[block.id + "." + it.id] =
              r.state === "satisfied" ? "satisfied:" + pointsStr(r.points) : r.state;
          });
        }
      });
      return out;
    }
    run.criteriaItems = criteriaItems;
    run.criteria_items = criteriaItems;

    // Python returns the tuple (grade, items_grade_iii, items_grade_ii).
    function severity(stage) {
      var sev = caseObj.adjudication.severity_grade;
      var iii = {};
      sev.items_grade_iii.forEach(function (it) { iii[it.id] = itemBool(it, stage); });
      var ii = {};
      sev.items_grade_ii.forEach(function (it) { ii[it.id] = itemBool(it, stage); });
      var grade;
      if (Object.keys(iii).some(function (k) { return iii[k] === true; })) grade = "III";
      else if (Object.keys(ii).some(function (k) { return ii[k] === true; })) grade = "II";
      else grade = "I";
      return [grade, iii, ii];
    }
    run.severity = severity;

    // ---------- the board -------------------------------------------
    function board(stage, excludeFindings) {
      var exclSet = toSet(excludeFindings);
      var w = {};
      Object.keys(run.priors).forEach(function (h) { w[h] = run.priors[h]; });
      Object.keys(run.findings).forEach(function (fid) {
        var f = run.findings[fid];
        if (f.stage > stage || exclSet.has(fid)) return;
        var lr = getOr(f, "lr", undefined);
        if (!pyTruthy(lr)) return;
        var h = lr.for_hypothesis;
        if (has(lr, "lr_plus")) w[h] *= lr.lr_plus;
        if (has(lr, "lr_minus")) w[h] *= lr.lr_minus;
      });
      var total = pySum(Object.keys(w).map(function (h) { return w[h]; }));
      var out = {};
      Object.keys(w).forEach(function (h) { out[h] = w[h] / total; });
      return out;
    }
    run.board = board;

    function brier(probs) {
      var terms = Object.keys(probs).map(function (h) {
        var d = probs[h] - (h === run.truth ? 1.0 : 0.0);
        return d * d;
      });
      return pySum(terms);
    }
    run.brier = brier;

    function rankOf(probs, hyp) {
      var ordered = Object.keys(probs).map(function (h) { return [h, probs[h]]; });
      // Stable sort by -value, exactly Python
      // sorted(probs.items(), key=lambda kv: -kv[1]).
      ordered.sort(function (a, b) { return (-a[1]) - (-b[1]); });
      for (var i = 0; i < ordered.length; i++) {
        if (ordered[i][0] === hyp) return i + 1;
      }
      throw new Error("ValueError: " + String(hyp) + " is not in list");
    }
    run.rankOf = rankOf;
    run.rank_of = rankOf;

    // ---------- order classification ---------------------------------
    function classifyOrder(test, placedStage) {
      var reveal = placedStage + 1;
      var yielded = new Set(test.yields);
      var lrFindings = new Set();
      yielded.forEach(function (fid) {
        if (has(run.findings, fid) && pyTruthy(getOr(run.findings[fid], "lr", undefined))) {
          lrFindings.add(fid);
        }
      });
      var full = board(reveal);
      var without = board(reveal, lrFindings);
      var leadFull = maxKey(full);
      var leadWo = maxKey(without);
      if (leadFull !== leadWo ||
          Math.abs(full[leadFull] - without[leadFull]) >= DISC_DELTA) {
        return ["discriminating",
          "leading hypothesis posterior moves " +
          format4(without[leadFull]) + " -> " + format4(full[leadFull])];
      }
      for (var hi = 0; hi < run.hyps.length; hi++) {
        var h = run.hyps[hi];
        if (without[h] >= RULE_OUT && full[h] < RULE_OUT) {
          return ["discriminating",
            h + " crosses the rule-out line (" +
            format4(without[h]) + " -> " + format4(full[h]) + ")"];
        }
      }
      var excl = new Set();
      yielded.forEach(function (y) {
        if ((has(run.findings, y) && run.findings[y].stage === reveal) ||
            (has(run.labs, y) && run.labs[y].stage === reveal) ||
            (has(run.measurements, y) && run.measurements[y].stage === reveal)) {
          excl.add(y);
        }
      });
      var fullItems = criteriaItems(reveal);
      var exclItems = criteriaItems(reveal, excl);
      if (!dictEq(exclItems, fullItems)) {
        var changed = Object.keys(fullItems).filter(function (k) {
          return exclItems[k] !== fullItems[k];
        });
        changed.sort();
        return ["criteria-completing",
          "settles guideline item(s): " + changed.join(", ")];
      }
      if (pyTruthy(getOr(test, "safety_net_for", undefined))) {
        return ["safety-net",
          "excludes must-not-miss " + test.safety_net_for + " (unquantified pair)"];
      }
      return ["non-contributory", "no posterior, criteria, or safety-net effect"];
    }
    run.classifyOrder = classifyOrder;
    run.classify_order = classifyOrder;

    // ---------- shaping for the debrief -------------------------------
    function shape(block, result) {
      if (block.kind === "grouped") {
        if (block.id === "tg18_cholecystitis" || block.id === "tg18_cholangitis") {
          return [result.groups, result.status];
        }
        return result;
      }
      if (block.kind === "k_of_n") {
        if (block.id === "atlanta") {
          var out = {};
          Object.keys(result.items).forEach(function (k) { out[k] = result.items[k]; });
          out.items_met = result.items_met;
          out.diagnosable = result.diagnosable;
          return out;
        }
        return result;
      }
      return result;
    }
    run.shape = shape;
    run._shape = shape;

    // ---------- main --------------------------------------------------
    function runDebrief() {
      if (!attempt) throw new Error("runDebrief: an attempt object is required");
      var caseO = caseObj;
      var boardsMap = new Map();
      run.stages.forEach(function (s) { boardsMap.set(s, board(s)); });

      var ruledOut = {};
      run.stages.forEach(function (s) {
        run.hyps.forEach(function (h) {
          if (!has(ruledOut, h) && boardsMap.get(s)[h] < RULE_OUT) ruledOut[h] = s;
        });
      });

      var attemptStages = new Map();
      attempt.stages.forEach(function (a) { attemptStages.set(a.stage, a); });

      var perStage = [];
      var anchoring = [];
      run.stages.forEach(function (s) {
        var lb = attemptStages.get(s).board;
        var lbSum = pySum(Object.keys(lb).map(function (k) { return lb[k]; }));
        if (!(Math.abs(lbSum - 1.0) < 1e-9)) {
          throw new Error("stage " + s + " board sums to " + lbSum);
        }
        run.hyps.forEach(function (h) {
          var ruledStage = has(ruledOut, h) ? ruledOut[h] : 99;
          if (ruledStage <= s && lb[h] >= ANCHOR) {
            anchoring.push({
              stage: s, hypothesis: h,
              learner_probability: lb[h],
              workbench_probability: boardsMap.get(s)[h],
              ruled_out_at_stage: ruledOut[h],
            });
          }
        });
        var criteria = {};
        var row = { stage: s };
        run.blocks.forEach(function (block) {
          var res = evalBlock(block, s);
          criteria[block.id] = res;
          row[block.id] = shape(block, res);
        });
        var wb = boardsMap.get(s);
        var workbenchBoard = {};
        run.hyps.forEach(function (h) { workbenchBoard[h] = pyRound(wb[h], 4); });
        row.workbench_board = workbenchBoard;
        row.learner_board = lb;
        row.workbench_top = maxKey(wb);
        row.learner_top = maxKey(lb);
        row.workbench_rank_of_truth = rankOf(wb, run.truth);
        row.learner_rank_of_truth = rankOf(lb, run.truth);
        row.workbench_probability_on_truth = pyRound(wb[run.truth], 4);
        row.learner_probability_on_truth = lb[run.truth];
        row.workbench_brier = pyRound(brier(wb), 4);
        row.learner_brier = pyRound(brier(lb), 4);
        row.criteria = criteria;
        perStage.push(row);
      });

      var orders = [];
      var tallyTime = 0;
      var tallyCost = 0;
      attempt.stages.forEach(function (a) {
        a.orders.forEach(function (tid) {
          var t = run.tests[tid];
          var clsWhy = classifyOrder(t, a.stage);
          orders.push({
            test_id: tid, placed_at_stage: a.stage,
            results_stage: a.stage + 1,
            classification: clsWhy[0], basis: clsWhy[1],
            time_min: t.time_min.value,
            cost_units: t.cost_units.value,
          });
          tallyTime += t.time_min.value;
          tallyCost += t.cost_units.value;
        });
      });

      var final = run.stages[run.stages.length - 1];
      var criteriaFinal = {};
      run.blocks.forEach(function (b) { criteriaFinal[b.id] = evalBlock(b, final); });
      var adj = {
        hypothesis: run.truth,
        mondo: getOrNull(caseO.adjudication, "mondo"),
        criteria_final: criteriaFinal,
      };
      if (has(caseO.adjudication, "classification")) {
        adj.classification = caseO.adjudication.classification;
      }
      if (has(criteriaFinal, "tg18_cholecystitis")) {
        adj.tg18_status_final = criteriaFinal.tg18_cholecystitis.status;
      }
      if (has(caseO.adjudication, "severity_grade")) {
        var sevRes = severity(final);
        adj.tg18_severity_grade = sevRes[0];
        adj.severity_items_grade_iii = sevRes[1];
        adj.severity_items_grade_ii = sevRes[2];
      }

      var text = getOr(attempt, "debrief_text", {});
      var orderClassCounts = {};
      ["discriminating", "criteria-completing", "safety-net", "non-contributory"]
        .forEach(function (c) {
          orderClassCounts[c] = orders.reduce(function (n, o) {
            return n + (o.classification === c ? 1 : 0);
          }, 0);
        });
      var learnerBrierByStage = {};
      var workbenchBrierByStage = {};
      var learnerProbByStage = {};
      perStage.forEach(function (r) {
        learnerBrierByStage[String(r.stage)] = r.learner_brier;
        workbenchBrierByStage[String(r.stage)] = r.workbench_brier;
        learnerProbByStage[String(r.stage)] = r.learner_probability_on_truth;
      });

      return {
        case_id: caseO.id,
        attempt_id: attempt.id,
        generated_by: "tools/case_run.py (Milestone 20 machinery, generalised at Milestone 22)",
        structure: "PEARLS (design/07 step 6; Eppich & Cheng 2015, as cited by Milestone 17's T10)",
        adjudicated_diagnosis: adj,
        per_stage: perStage,
        ruled_out_by_workbench: ruledOut,
        anchoring_events: anchoring,
        orders: orders,
        resource_tally: {
          total_time_min: tallyTime,
          total_cost_units: tallyCost,
          status: "verify — case-author accounting placeholders (design/07 requires tests to carry cost and time; no prices were consulted)",
        },
        scoring_components: {
          note: "Components only. Design/07 defines Brier-style calibration scoring, anchoring, and evidence quality, and no weights; no composite is computed.",
          learner_brier_by_stage: learnerBrierByStage,
          workbench_brier_by_stage: workbenchBrierByStage,
          learner_probability_on_truth_by_stage: learnerProbByStage,
          anchoring_event_count: anchoring.length,
          order_class_counts: orderClassCounts,
        },
        pearls: {
          reactions: getOr(text, "reactions", ""),
          description: getOr(text, "description", ""),
          analysis: getOr(text, "analysis", ""),
          summary: getOr(text, "summary", ""),
        },
        validity: caseO.validity,
        review: caseO.review,
      };
    }
    run.runDebrief = runDebrief;

    return run;
  }

  return {
    createRun: createRun,
    pyRound: pyRound,
    format4: format4,
  };
});
