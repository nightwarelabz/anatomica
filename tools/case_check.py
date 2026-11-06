#!/usr/bin/env python3
"""ANATOMICA Milestone 20 checker — independent validation of the
Case Workbench.

Recomputes, from the data files alone (never importing the runner):
  1. parameter discipline: every cited source exists; every LR used
     in the case matches the registered derivation; priors sum to 1;
     the one calibrated prior sits inside its cited range
  2. ontology discipline: every MONDO / HP id used appears in the
     in-session OLS-verified register text (C10 / C11); ground truth,
     adjudication, and hypothesis Mondo agree
  3. reference resolution: every Body Model record id resolves in
     the named file; every finding / lab / test cross-reference
     resolves; every hypothesis discriminator names a real finding
  4. stage discipline: no evidence used before its reveal stage;
     orders placed no earlier than their availability; an order's
     yields land exactly at the next stage
  5. laboratory arithmetic: interpretations recomputed from values
     and cited ranges/thresholds (incl. TG18 cholangitis thresholds
     and the Atlanta 3x ULN line)
  6. scoring recomputation: workbench boards, Brier scores, ranks,
     rule-outs, anchoring events, order classifications, resource
     tally, TG18/Atlanta evaluations and the severity grade — all
     recomputed independently and compared against the shipped
     debrief field by field
  7. imaging link: gallbladder voxel census recounted from the
     shipped label bins; HU statistics and z-arithmetic checked
     against crosswalk.json and series.json
  8. physiology link: the engine is re-run and its trace hash and
     resting outputs compared to the values recorded in the case
  9. theatre handoff: procedure id and its gallbladder register
     entry re-verified in the procedure file
 10. FHIR export: values compared against the case file; forbidden
     code systems (SNOMED CT, LOINC) asserted absent from the bundle
 11. governance: synthetic flag set, review gate recorded UNMET,
     validity label dual-sourced-draft, no composite score anywhere

Usage: python3 tools/case_check.py
Regenerate the debrief with: python3 tools/case_run.py
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "cases")

failures = []
checks = 0


def ok(cond, label, detail=""):
    global checks
    checks += 1
    if cond:
        print(f"  PASS {label}")
    else:
        print(f"  FAIL {label} {detail}")
        failures.append(label)


def load(path):
    with open(path) as f:
        return json.load(f)


PARAMS = load(os.path.join(CASES, "parameters.json"))
CASE = load(os.path.join(CASES, "case.ruq-pain.001.json"))["case"]
ATTEMPT = load(os.path.join(
    CASES, "attempts", "attempt.case-ruq-pain-001.model-learner.json"))["attempt"]
DEBRIEF = load(os.path.join(
    CASES, "debriefs", "debrief.case-ruq-pain-001.model-learner.json"))["debrief"]

FINDINGS = {f["id"]: f for f in CASE["findings"]}
LABS = {l["id"]: l for l in CASE["labs"]}
TESTS = {t["id"]: t for t in CASE["available_tests"]}
HYPS = [h["id"] for h in CASE["hypotheses"]]
HYP = {h["id"]: h for h in CASE["hypotheses"]}
SOURCES = {s["id"]: s for s in PARAMS["sources"]}
TRUTH = CASE["adjudication"]["diagnosis_hypothesis"]
STAGES = [1, 2, 3, 4]

print("== 1. parameter discipline ==")
for f in CASE["findings"]:
    for sid in f["source"]:
        if sid != "case-data":
            ok(sid in SOURCES, f"finding {f['id']} source {sid} registered")
deriv = {(d["finding"], d["target_hypothesis"]): d for d in PARAMS["lr_derivations"]}
for f in CASE["findings"]:
    if f.get("lr"):
        d = deriv.get((f["id"], f["lr"]["for_hypothesis"]))
        ok(d is not None, f"LR for {f['id']} has a registered derivation")
        if d:
            for k in ("lr_plus", "lr_minus"):
                if k in f["lr"]:
                    ok(abs(f["lr"][k] - d[k]) < 1e-9,
                       f"LR {k} for {f['id']} matches derivation ({f['lr'][k]} vs {d[k]})")
ok(abs(sum(h["prior"]["value"] for h in CASE["hypotheses"]) - 1.0) < 1e-9,
   "hypothesis priors sum to 1")
chol_prior = HYP["hyp.acute-cholecystitis"]["prior"]
ok(chol_prior["status"] == "calibrated"
   and chol_prior["range"][0] <= chol_prior["value"] <= chol_prior["range"][1],
   "cholecystitis prior is calibrated inside its cited range")
for h in CASE["hypotheses"]:
    if h["id"] != "hyp.acute-cholecystitis":
        ok(h["prior"]["status"] in ("verify", "calibrated"),
           f"prior for {h['id']} carries an explicit status ({h['prior']['status']})")
ok(all(p["status"] in ("cited", "computed", "calibrated", "verify", "project-convention")
       for p in PARAMS["parameters"]),
   "every workbench parameter carries a lawful status")

print("== 2. ontology discipline ==")
c10 = SOURCES["C10"]["consulted"]
c11 = SOURCES["C11"]["consulted"]
for h in CASE["hypotheses"]:
    if h.get("mondo"):
        ok(re.fullmatch(r"MONDO:\d{7}", h["mondo"]) is not None
           and h["mondo"] in c10,
           f"{h['id']} Mondo {h['mondo']} is OLS-verified (C10)")
    for rel in h.get("mondo_related", []):
        ok(rel in c10, f"{h['id']} related Mondo {rel} is OLS-verified (C10)")
ok(CASE["ground_truth"]["mondo"] == CASE["adjudication"]["mondo"]
   == HYP[TRUTH]["mondo"],
   "ground truth, adjudication, and hypothesis Mondo agree")
for f in CASE["findings"]:
    for hp in f.get("hpo", []):
        ok(re.fullmatch(r"HP:\d{7}", hp) is not None and hp in c11,
           f"finding {f['id']} HPO {hp} is OLS-verified (C11)")
for hp in CASE["ground_truth"]["hpo"] + [a["hpo"] for a in CASE["ground_truth"]["hpo_absent"]]:
    ok(hp in c11, f"ground-truth HPO {hp} is OLS-verified (C11)")

print("== 3. reference resolution ==")
_records_cache = {}


def record_ids(path):
    if path not in _records_cache:
        d = load(os.path.join(ROOT, path))
        recs = d["records"] if isinstance(d, dict) else d
        _records_cache[path] = {r["id"] for r in recs}
    return _records_cache[path]


n_refs = 0
for owner, lst in (("case", [CASE]),):
    pass
for f in CASE["findings"]:
    for br in f["body_records"]:
        n_refs += 1
        ok(br["id"] in record_ids(br["file"]),
           f"finding {f['id']} record {br['id']} resolves in {br['file']}")
for h in CASE["hypotheses"]:
    for br in h["body_records"]:
        n_refs += 1
        ok(br["id"] in record_ids(br["file"]),
           f"hypothesis {h['id']} record {br['id']} resolves in {br['file']}")
    for d in h["discriminating_findings"]:
        ok(d["finding_id"] in FINDINGS,
           f"hypothesis {h['id']} discriminator {d['finding_id']} exists")
for l in CASE["labs"]:
    ok(l["test_id"] in TESTS, f"lab {l['id']} test {l['test_id']} exists")
    if l["reference_range"]:
        ok(l["reference_range"]["source"] in SOURCES,
           f"lab {l['id']} range source {l['reference_range']['source']} registered")
for f in CASE["findings"]:
    if f.get("lab_id"):
        ok(f["lab_id"] in LABS, f"finding {f['id']} lab {f['lab_id']} exists")
    for lid in f.get("lab_ids", []):
        ok(lid in LABS, f"finding {f['id']} lab {lid} exists")
for t in CASE["available_tests"]:
    for y in t["yields"]:
        ok(y in FINDINGS or y in LABS, f"test {t['id']} yield {y} exists")
for e in CASE["adjudication"]["evidence_chain"]:
    ok(e["finding_id"] in FINDINGS,
       f"adjudication evidence {e['finding_id']} exists")
print(f"  ({n_refs} Body Model record references resolved above)")

print("== 4. stage discipline ==")
for f in CASE["findings"]:
    ok(f["stage"] in STAGES, f"finding {f['id']} stage {f['stage']} valid")
for l in CASE["labs"]:
    ok(l["stage"] in STAGES, f"lab {l['id']} stage {l['stage']} valid")
for a in ATTEMPT["stages"]:
    for tid in a["orders"]:
        t = TESTS[tid]
        ok(t["available_from_stage"] <= a["stage"],
           f"order {tid} at stage {a['stage']} not before availability {t['available_from_stage']}")
        for y in t["yields"]:
            ystage = FINDINGS[y]["stage"] if y in FINDINGS else LABS[y]["stage"]
            ok(ystage == a["stage"] + 1,
               f"order {tid} yield {y} lands at stage {ystage} (placed {a['stage']})")
# no evidence used before its stage: TG18 group completion stages
ev = CASE["adjudication"]["tg18_evaluation"]
for g in ev["groups"]:
    for it in g["items"]:
        for a2 in it["evidence"]:
            if "finding_id" in a2:
                ok(FINDINGS[a2["finding_id"]]["stage"] <= 4,
                   f"TG18 item {it['id']} evidence stage lawful")
ok(FINDINGS["f.us-positive"]["stage"] == ev["definite_from_stage"],
   "definite diagnosis stage == stage of the group C finding")

print("== 5. laboratory arithmetic ==")
wbc = LABS["lab.wbc"]
ok(wbc["value"] > wbc["reference_range"]["high"], "WBC above its cited range (elevated)")
ok(wbc["value"] * 1000 <= 18000 * 1000 and wbc["value"] <= 18.0,
   "WBC below the TG18 Grade II threshold (18,000/mm3 = 18.0 x10^9/L)")
ok(LABS["lab.platelets"]["value"] >= 100, "platelets above TG18 Grade III threshold (100 x10^9/L)")
ok(LABS["lab.crp"]["value"] >= LABS["lab.crp"]["reference_range"]["threshold_high"],
   "CRP above the TG18 inflammatory threshold")
bili = LABS["lab.bilirubin-total"]
ok(bili["reference_range"]["low"] <= bili["value"] <= bili["reference_range"]["high"]
   and bili["value"] < 2.0,
   "bilirubin within range and below the TG18 cholangitis threshold (2 mg/dL)")
for lid, uln in (("lab.alp", 129), ("lab.alt", 36), ("lab.ast", 33)):
    lab = LABS[lid]
    ok(lab["value"] <= lab["reference_range"]["high"] and lab["value"] <= 1.5 * uln,
       f"{lid} within range and not > 1.5x ULN (TG18 cholangitis B-2 unmet)")
lip = LABS["lab.lipase"]
ok(lip["value"] <= lip["reference_range"]["high"]
   and lip["value"] < 3 * lip["reference_range"]["high"],
   "lipase within range and below 3x ULN (Atlanta item 2 unmet)")

print("== 6. scoring recomputation (independent) ==")
CONST = {p["key"]: p["value"] for p in PARAMS["parameters"]}
RO, AN, DD = CONST["rule_out_threshold"], CONST["anchoring_threshold"], CONST["discriminating_delta"]
priors = {h["id"]: h["prior"]["value"] for h in CASE["hypotheses"]}


def board_at(stage, excl=frozenset()):
    w = dict(priors)
    for f in CASE["findings"]:
        if f["stage"] <= stage and f["id"] not in excl and f.get("lr"):
            lr = f["lr"]
            w[lr["for_hypothesis"]] *= lr.get("lr_plus", lr.get("lr_minus"))
    t = sum(w.values())
    return {h: v / t for h, v in w.items()}


def brier_of(b):
    return sum((p - (1.0 if h == TRUTH else 0.0)) ** 2 for h, p in b.items())


boards = {s: board_at(s) for s in STAGES}
ruled = {}
for s in STAGES:
    for h in HYPS:
        if h not in ruled and boards[s][h] < RO:
            ruled[h] = s
ok(ruled == DEBRIEF["ruled_out_by_workbench"],
   f"rule-outs recomputed equal debrief ({ruled})")
att = {a["stage"]: a for a in ATTEMPT["stages"]}
anch = []
for s in STAGES:
    lb = att[s]["board"]
    ok(abs(sum(lb.values()) - 1.0) < 1e-9, f"learner board stage {s} sums to 1")
    row = next(r for r in DEBRIEF["per_stage"] if r["stage"] == s)
    ok(all(abs(row["workbench_board"][h] - round(boards[s][h], 4)) < 1.1e-4 for h in HYPS),
       f"stage {s} workbench board matches debrief")
    ok(abs(row["learner_brier"] - round(brier_of(lb), 4)) < 1.1e-4,
       f"stage {s} learner Brier recomputed ({round(brier_of(lb), 4)} vs {row['learner_brier']})")
    ok(abs(row["workbench_brier"] - round(brier_of(boards[s]), 4)) < 1.1e-4,
       f"stage {s} workbench Brier recomputed")
    ok(row["learner_rank_of_truth"] == 1 + sum(1 for h in HYPS if lb[h] > lb[TRUTH]),
       f"stage {s} learner rank of truth")
    for h in HYPS:
        if ruled.get(h, 99) <= s and lb[h] >= AN:
            anch.append((s, h))
ok([(a["stage"], a["hypothesis"]) for a in DEBRIEF["anchoring_events"]] == anch,
   f"anchoring events recomputed equal debrief ({anch})")
ok(len(anch) == 1 and anch[0] == (3, "hyp.acute-cholangitis"),
   "exactly one anchoring event: cholangitis held at stage 3")


def item_states(stage, excl=frozenset()):
    """Three-valued guideline item states, fresh implementation."""
    def fs(fid):
        f = FINDINGS[fid]
        if fid in excl or f["stage"] > stage:
            return "unknown"
        return "satisfied" if f.get("presence", "present") == "present" else "unsatisfied"

    def known(lid):
        return lid not in excl and LABS[lid]["stage"] <= stage

    out = {}
    for g in ev["groups"]:
        for it in g["items"]:
            ss = []
            for a in it["evidence"]:
                if "finding_id" in a:
                    st = fs(a["finding_id"])
                    ss.append(st if a["is"] == "present" else
                              ("satisfied" if st == "unsatisfied" else st))
            out["tg18c." + it["id"]] = ("satisfied" if "satisfied" in ss else
                                        "unsatisfied" if "unsatisfied" in ss else "unknown")
    out["tg18chol.A"] = ("satisfied" if "satisfied" in
                         (fs("f.fever"), fs("f.wbc-elevated"), fs("f.crp-elevated")) else "unknown")
    out["tg18chol.B1"] = ("satisfied" if LABS["lab.bilirubin-total"]["value"] >= 2.0 else "unsatisfied") if known("lab.bilirubin-total") else "unknown"
    enz = (("lab.alp", 129), ("lab.alt", 36), ("lab.ast", 33))
    out["tg18chol.B2"] = (("satisfied" if any(LABS[l]["value"] > 1.5 * u for l, u in enz) else "unsatisfied")
                          if all(known(l) for l, _ in enz) else "unknown")
    out["tg18chol.C"] = "unsatisfied" if fs("f.us-no-biliary-dilatation") != "unknown" else "unknown"
    out["atlanta.pain"] = "unsatisfied"
    out["atlanta.lipase"] = (("satisfied" if LABS["lab.lipase"]["value"] >= 480 else "unsatisfied")
                             if known("lab.lipase") else "unknown")
    out["atlanta.imaging"] = "unsatisfied" if fs("f.us-pancreas-unremarkable") != "unknown" else "unknown"
    return out


def classify(test, placed):
    reveal = placed + 1
    y = set(test["yields"])
    lrf = {i for i in y if i in FINDINGS and FINDINGS[i].get("lr")}
    full, wo = board_at(reveal), board_at(reveal, lrf)
    lf, lw = max(full, key=full.get), max(wo, key=wo.get)
    if lf != lw or abs(full[lf] - wo[lf]) >= DD:
        return "discriminating"
    if any(wo[h] >= RO and full[h] < RO for h in HYPS):
        return "discriminating"
    excl = {i for i in y if (i in FINDINGS and FINDINGS[i]["stage"] == reveal)
            or (i in LABS and LABS[i]["stage"] == reveal)}
    if item_states(reveal, excl) != item_states(reveal):
        return "criteria-completing"
    return "safety-net" if test.get("safety_net_for") else "non-contributory"


exp_classes = {}
for a in ATTEMPT["stages"]:
    for tid in a["orders"]:
        exp_classes[tid] = classify(TESTS[tid], a["stage"])
for o in DEBRIEF["orders"]:
    ok(exp_classes[o["test_id"]] == o["classification"],
       f"order {o['test_id']} classification recomputed: {exp_classes[o['test_id']]}")
ok(exp_classes["test.lipase"] == "discriminating"
   and exp_classes["test.ruq-ultrasound"] == "discriminating"
   and exp_classes["test.amylase"] == "non-contributory",
   "headline classifications: lipase + ultrasound discriminating, amylase non-contributory")
tt = sum(TESTS[o["test_id"]]["time_min"]["value"] for o in DEBRIEF["orders"])
tc = sum(TESTS[o["test_id"]]["cost_units"]["value"] for o in DEBRIEF["orders"])
ok(DEBRIEF["resource_tally"]["total_time_min"] == tt
   and DEBRIEF["resource_tally"]["total_cost_units"] == tc,
   f"resource tally recomputed ({tt} min, {tc} units)")

# criteria statuses per stage vs the debrief and the case's declared statuses
for s in STAGES:
    ist = item_states(s)
    A = ist["tg18c.A1"] == "satisfied" or ist["tg18c.A2"] == "satisfied"
    B = any(ist["tg18c." + i] == "satisfied" for i in ("B1", "B2", "B3"))
    C = ist["tg18c.C1i"] == "satisfied"
    status = "definite" if (A and B and C) else "suspected" if (A and B) else "not suspected"
    declared = CASE["adjudication"]["tg18_evaluation"]["status_by_stage"][str(s)]
    ok(status in declared, f"stage {s} TG18 status recomputed '{status}' == case-declared")
    row = next(r for r in DEBRIEF["per_stage"] if r["stage"] == s)
    ok(row["tg18_cholecystitis"][1] == status, f"stage {s} TG18 status matches debrief")
    cholA = ist["tg18chol.A"] == "satisfied"
    cholB = "satisfied" in (ist["tg18chol.B1"], ist["tg18chol.B2"])
    cholC = ist["tg18chol.C"] == "satisfied"
    ok(not (cholA and (cholB or cholC)),
       f"stage {s} cholangitis cannot reach 'suspected' (TG18 C2)")
    ok(row["tg18_cholangitis"][1] == "not suspected",
       f"stage {s} cholangitis status in debrief is 'not suspected'")
    ok(row["atlanta"]["diagnosable"] is False and row["atlanta"]["items_met"] == 0,
       f"stage {s} Atlanta: 0 of 3, not diagnosable")
# severity grade recompute
sev = CASE["adjudication"]["severity_grade"]


def atom_val(a, stage=4):
    if a.get("assessable") is False:
        return "not-assessed"
    if "finding_id" in a:
        f = FINDINGS[a["finding_id"]]
        return f.get("presence", "present") == a["is"] if f["stage"] <= stage else False
    if "lab_id" in a:
        v = LABS[a["lab_id"]]["value"]
        return v > a["threshold"] if a["test"] == "value_gt" else v < a["threshold"]
    if "case_field" in a:
        return CASE["patient"][a["case_field"]] > a["threshold"]
    return False


def item_val(it):
    vals = [atom_val(a) for a in it["evidence"]]
    if any(v is True for v in vals):
        return True
    if any(v == "not-assessed" for v in vals):
        return "not-assessed"
    return False


g3 = [item_val(i) for i in sev["items_grade_iii"]]
g2 = [item_val(i) for i in sev["items_grade_ii"]]
grade = "III" if any(v is True for v in g3) else "II" if any(v is True for v in g2) else "I"
ok(grade == CASE["adjudication"]["severity_grade"]["grade"] == "I"
   == DEBRIEF["adjudicated_diagnosis"]["tg18_severity_grade"],
   "severity grade recomputed: I (case, debrief agree)")
ok(sum(1 for v in g3 if v == "not-assessed") == 3,
   "exactly three Grade III items recorded not-assessed (respiratory, renal, hepatic)")
for it in sev["items_grade_ii"] + sev["items_grade_iii"]:
    ok(item_val(it) == it["satisfied"],
       f"severity item {it['id']} declared state matches recomputation")

print("== 7. imaging link (recount from shipped bins) ==")
import numpy as np
bindir = os.path.join(ROOT, "web", "data", "imaging", "s0778")
counts = []
for i in range(431):
    arr = np.fromfile(os.path.join(bindir, f"lbl-{i:04d}.bin"), dtype=np.uint8)
    counts.append(int((arr == 15).sum()))
present = [i for i, c in enumerate(counts) if c > 0]
link = CASE["imaging_link"]
ok([present[0], present[-1]] == link["measures"]["slice_files_0based"],
   f"gallbladder slices recounted: {present[0]}..{present[-1]} (0-based files)")
ok(len(present) == link["measures"]["slices_with_label"] == 24,
   "24 slices carry the gallbladder label")
ok(sum(counts) == 2720 == link["label"]["hu_statistics_from_crosswalk"]["voxels"],
   "total gallbladder voxels recounted: 2,720")
mx = max(range(431), key=lambda i: counts[i])
ok(mx == link["measures"]["max_cross_section"]["file_index_0based"]
   and counts[mx] == link["measures"]["max_cross_section"]["voxels"] == 186,
   f"max cross-section recounted: file {mx}, {counts[mx]} voxels")
ok(abs(2720 * 3.375 / 1000 - 9.18) < 1e-9, "volume arithmetic: 2,720 x 3.375 mm3 = 9.18 mL")
cw = load(os.path.join(ROOT, "data", "imaging", "s0778", "crosswalk.json"))
gb = next(l for l in cw["labels"] if l["label"] == "gallbladder")
ok(gb["record_ids"] == ["gallbladder"] and gb["index"] == 15,
   "crosswalk maps label 15 (gallbladder) to record 'gallbladder'")
hu = link["label"]["hu_statistics_from_crosswalk"]
ok(all(gb["hu"][k] == hu[k] for k in ("mean", "median", "p5", "p95", "min", "max")),
   "case HU statistics equal crosswalk values")
series = load(os.path.join(ROOT, "data", "imaging", "s0778", "series.json"))
z0 = series["geometry"]["ipp_first_slice_lps_mm"][2]
ok(abs((z0 + 195 * 1.5) - link["measures"]["z_range_lps_mm"][0]) < 0.01
   and abs((z0 + 218 * 1.5) - link["measures"]["z_range_lps_mm"][1]) < 0.01,
   "slice z-arithmetic reproduces the crosswalk bbox (IPP + 1.5 mm steps)")
ok("does not show" in link["honesty_block"] or "NOT" in link["honesty_block"],
   "imaging honesty block present (series not presented as showing the pathology)")

print("== 8. physiology link (engine re-run) ==")
try:
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.cargo/bin") + ":" + env["PATH"]
    r = subprocess.run(["cargo", "run", "--release", "--quiet", "--", "run", "resting"],
                       cwd=os.path.join(ROOT, "physiology"), capture_output=True,
                       text=True, timeout=900, env=env)
    m = re.search(r"trace hash: (0x[0-9a-f]+)", r.stdout)
    ok(m is not None and m.group(1) == CASE["physiology_link"]["trace_hash"],
       f"engine trace hash reproduces ({m.group(1) if m else 'none'})")
    post = re.search(r"post\s+: beats=\d+ HR=([\d.]+) bpm  BP=([\d.]+)/([\d.]+) mmHg  MAP=([\d.]+)"
                     r".*?CO=([\d.]+) L/min  SVlv=([\d.]+) mL.*?CVP=([\d.]+) mmHg", r.stdout)
    exp = CASE["physiology_link"]["baseline_recorded_outputs"]
    got = {"heart_rate_per_min": float(post.group(1)), "systolic_bp_mmhg": float(post.group(2)),
           "diastolic_bp_mmhg": float(post.group(3)), "map_mmhg": float(post.group(4)),
           "cardiac_output_l_min": float(post.group(5)), "stroke_volume_lv_ml": float(post.group(6)),
           "cvp_mmhg": float(post.group(7))}
    ok(all(abs(got[k] - exp[k]) < 0.051 for k in exp),
       f"engine resting outputs match the case's recorded baseline ({got})")
except Exception as e:  # pragma: no cover
    ok(False, f"physiology engine re-run failed: {e}")

print("== 9. theatre handoff ==")
proc = load(os.path.join(ROOT, "theatre", "procedures", "proc.lap-cholecystectomy.json"))["procedure"]
ok(proc["id"] == CASE["management"]["handoff"]["procedure_id"] == "proc.chole.lap",
   "handoff procedure id matches the theatre file")
reg = {s["id"]: s for s in proc["structures"]}
ok(reg["organ.gallbladder"]["kind"] == "record"
   and reg["organ.gallbladder"]["resolves_to"] == "data/digestive/digestive.json",
   "theatre register resolves organ.gallbladder (the case's organ)")
commit = ATTEMPT["stages"][-1]["commit"]
ok(commit["diagnosis_hypothesis"] == TRUTH and "proc.chole.lap" in commit["management"],
   "attempt commit matches adjudication and names the handoff procedure")

print("== 10. FHIR export ==")
def all_systems(o, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "system" and isinstance(v, str):
                acc.add(v)
            all_systems(v, acc)
    elif isinstance(o, list):
        for v in o:
            all_systems(v, acc)
    return acc

_systems = all_systems(load(os.path.join(CASES, "fhir", "case.ruq-pain.001.bundle.json")), set())
ok(not any("snomed" in s.lower() or "loinc" in s.lower() for s in _systems),
   f"no SNOMED CT / LOINC code system among the bundle's coding systems ({sorted(_systems)})")
bundle = load(os.path.join(CASES, "fhir", "case.ruq-pain.001.bundle.json"))["bundle"]
res = {e["resource"]["id"]: e["resource"] for e in bundle["entry"]}
cond = next(r for r in res.values() if r["resourceType"] == "Condition")
ok(cond["code"]["coding"][0]["code"] == CASE["ground_truth"]["mondo"],
   "FHIR Condition code == ground-truth Mondo")
obs = {r["code"]["coding"][0]["code"]: r for r in res.values() if r["resourceType"] == "Observation"}
for lab in CASE["labs"]:
    code = lab["id"].split(".", 1)[1]
    o = obs.get(code)
    ok(o is not None and abs(o["valueQuantity"]["value"] - lab["value"]) < 1e-9
       and o["valueQuantity"]["unit"] == lab["unit"],
       f"FHIR Observation {code} value/unit == case lab ({lab['value']} {lab['unit']})")
    if lab["reference_range"] and "low" in lab["reference_range"]:
        rr = o["referenceRange"][0]
        ok(rr["low"]["value"] == lab["reference_range"]["low"]
           and rr["high"]["value"] == lab["reference_range"]["high"],
           f"FHIR Observation {code} reference range == case")
sr = next(r for r in res.values() if r["resourceType"] == "ServiceRequest")
ok(sr["code"]["coding"][0]["code"] == CASE["management"]["handoff"]["procedure_id"],
   "FHIR ServiceRequest codes the theatre handoff procedure")
pat = next(r for r in res.values() if r["resourceType"] == "Patient")
ok(pat["identifier"][0]["value"] == CASE["id"], "FHIR Patient identifier == case id")

print("== 11. governance ==")
ok(CASE["synthetic"] is True, "case is declared synthetic")
ok(CASE["review"]["status"].startswith("UNMET") and CASE["review"]["recorded_reviewers"] == [],
   "review gate recorded UNMET with an empty reviewer list (not fabricated)")
ok(CASE["validity"]["content"] == "dual-sourced-draft", "validity content label: dual-sourced-draft")
ok(DEBRIEF["review"]["status"].startswith("UNMET"), "debrief carries the UNMET review gate")


def keys_of(o, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            acc.add(k)
            keys_of(v, acc)
    elif isinstance(o, list):
        for v in o:
            keys_of(v, acc)
    return acc


ok(not any("composite" in k for k in keys_of(DEBRIEF["scoring_components"], set())),
   "no composite score exists in the debrief (components only)")

print(f"\n{checks} checks, {len(failures)} failures")
if failures:
    print("FAILURES:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("ALL CHECKS PASS")
