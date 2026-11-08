#!/usr/bin/env python3
"""ANATOMICA README drift guard — Milestone 50.

Asserts that every load-bearing number stated in README.md equals the
value computed live from the tree, so the README can never silently
drift from the system it describes. Ground truth is the data files
and the sibling checkers' own printed output — never the milestone
dossiers (dossiers are claims; checkers and data are evidence).

Sections:
  R1  Body Model census table (per system + totals) vs the data
      files, using the same file map as tools/assembly_check_all.py.
  R2  Concept-only decomposition (total - geometry; FMA intake count
      from the TA2 ledger) and clinical tier split vs the data.
  R3  TA2 totals vs data/ta2-name-pass.json (the pass ledger).
  R4  Geometry packs vs web/data/manifest.json + delivery.json.
  R5  Physiology counts vs physiology/parameters.json; the resting
      trace hash stated in the README vs the hash recorded in the
      physiology-linked case files.
  R6  Theatre counts (procedures / traces / debriefs / phases /
      steps / microsteps / sources / parameters / instruments) vs
      the theatre data files.
  R7  Case counts (case files; source-register extent) vs cases/.
  R8  Imaging counts (DICOM instances per subject; crosswalk totals;
      series geometry) vs data/imaging/.
  R9  Checker totals: runs tools/theatre_check.py,
      tools/case_check.py, tools/imaging_toolkit_check.py and
      tools/verify_web.js and compares their printed totals with
      the README's Verification table; runs the native verifier and
      compares its PASS/FAIL assertion counts (its GPU render stage
      cannot initialise headless — the data assertions are what is
      compared; FAIL count must be 0).
  R10 Milestone index: a row for every milestone 1..50 plus the
      Milestone 7 fix, each naming a file that exists; every
      MILESTONE-*.md in the milestones/ folder has a row.
  R11 File index: the README's per-directory file lists vs the
      tracked set regenerated under the documented exclusion rule
      (adopted source binaries, build output, and regenerable
      artifacts excluded — see MILESTONE-50.md). The film-engine/
      group is REPORTED, not gated: those files live in the
      repository (landed by PR, Milestone 15 index) but not in this
      local tree, so they cannot be recomputed here.
  R12 Status language: the precise status statements the README is
      required to carry (expert-review gate UNMET, formative-only
      scores, the geometry ruling — Tier B intaken at Milestone 63,
      Tier C gated, Tier D excluded, deferent-duct meshes claimed —
      DICOM defect found and repaired) are present verbatim.

Stdlib only (subprocesses use python3 / node / cargo, as the sibling
checkers do). Exit 0 iff all gated checks pass.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
README = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
# Prose figures are matched against a whitespace-flattened copy so a
# line wrap inside a phrase can never silently break (or fake) a match.
# Structure (tables, indexes) is parsed from the raw text.
FLAT = re.sub(r"\s+", " ", README)

FAILS = []


def report(ok, label, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(label)


def note(label, detail=""):
    print(f"[REPORT] {label}" + (f" — {detail}" if detail else ""))


def num(s):
    return int(s.replace(",", "").replace("**", ""))


def find_int(pattern, label):
    m = re.search(pattern, FLAT)
    if not m:
        report(False, label, "figure not found in README")
        return None
    return num(m.group(1))


# ---------------------------------------------------------------- R1/R2
SYSTEMS = {
    "skeletal": ("data/skeletal/skeleton-geometry.json",
                 "data/skeletal/skeleton-assembled.json", ()),
    "muscular": ("data/muscular/muscle-geometry.json",
                 "data/muscular/muscles-assembled.json",
                 ("data/muscular/muscles.json",)),
    "cardiovascular": ("data/cardiovascular/cv-geometry.json",
                       "data/cardiovascular/cv-assembled.json",
                       ("data/cardiovascular/cardiovascular.json",)),
    "nervous": ("data/nervous/nervous-geometry.json",
                "data/nervous/nervous-assembled.json",
                ("data/nervous/nervous.json",
                 "data/nervous/major-nerves.json")),
    "respiratory": ("data/respiratory/respiratory-geometry.json",
                    "data/respiratory/respiratory-assembled.json",
                    ("data/respiratory/respiratory.json",)),
    "digestive": ("data/digestive/digestive-geometry.json",
                  "data/digestive/digestive-assembled.json",
                  ("data/digestive/digestive.json",)),
    "urinary": ("data/urinary/urinary-geometry.json",
                "data/urinary/urinary-assembled.json",
                ("data/urinary/urinary.json",)),
    "lymphatic": ("data/lymphatic/lymphatic-geometry.json",
                  "data/lymphatic/lymphatic-assembled.json",
                  ("data/lymphatic/lymphatic.json",)),
    "endocrine": ("data/endocrine/endocrine-geometry.json",
                  "data/endocrine/endocrine-assembled.json",
                  ("data/endocrine/endocrine.json",)),
    "reproductive": ("data/reproductive/reproductive-geometry.json",
                     "data/reproductive/reproductive-assembled.json",
                     ("data/reproductive/reproductive.json",)),
    "integumentary": ("data/integumentary/integumentary-geometry.json",
                      "data/integumentary/integumentary-assembled.json",
                      ("data/integumentary/integumentary.json",)),
}

census = {}
tiers = {}
tot_inv = tot_geo = tot_clin = 0
for key, (geom_rel, asm_rel, clin_files) in SYSTEMS.items():
    geom = json.load(open(os.path.join(ROOT, geom_rel)))
    asm = json.load(open(os.path.join(ROOT, asm_rel)))
    n_clin = 0
    for cf in clin_files:
        clin = json.load(open(os.path.join(ROOT, cf)))
        n_clin += len(clin["records"])
        for r in clin["records"]:
            t = r.get("sourcing_tier")
            tiers[t] = tiers.get(t, 0) + 1
    census[key] = (len(geom["records"]), len(asm["records"]), n_clin)
    tot_inv += census[key][0]
    tot_geo += census[key][1]
    tot_clin += n_clin

rows = {}
for line in README.splitlines():
    m = re.match(r"\| ([a-z]+) \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \|", line)
    if m and m.group(1) in SYSTEMS:
        rows[m.group(1)] = tuple(num(m.group(i)) for i in (2, 3, 4))
report(rows == census, "R1 census table == data files",
       "; ".join(f"{k}: README {rows.get(k)} vs data {v}"
                 for k, v in census.items() if rows.get(k) != v) or
       f"11 systems, totals {tot_inv}/{tot_geo}/{tot_clin}")

m = re.search(r"\| \*\*Total\*\* \| \*\*([\d,]+)\*\* \| \*\*([\d,]+)\*\* \| "
              r"\*\*([\d,]+)\*\*", README)
report(bool(m) and (num(m.group(1)), num(m.group(2)), num(m.group(3)))
       == (tot_inv, tot_geo, tot_clin),
       "R1 census Total row == computed totals",
       f"README {m.groups() if m else None} vs {(tot_inv, tot_geo, tot_clin)}")

ledger = json.load(open(os.path.join(ROOT, "data/ta2-name-pass.json")))
fma_records = sum(v["records"] for k, v in ledger.items()
                  if k.startswith("fma_inventory"))
concept_only = tot_inv - tot_geo
v = find_int(r"\*\*([\d,]+) concept records carry no geometry", "R2 concept-only count")
report(v == concept_only, "R2 concept-only == inventory - geometry",
       f"README {v} vs computed {concept_only}")
v = find_int(r"\(([\d,]+) of them FMA 5\.1\.0 concept records", "R2 FMA concept count")
report(v == fma_records, "R2 FMA concept records == TA2 ledger intake sum",
       f"README {v} vs computed {fma_records}")

v = find_int(r"Tier A ([\d,]+) / Tier B \d+ / Tier C \d+", "R2 Tier A count")
report(v == tiers.get("A"), "R2 Tier A == clinical files", f"README {v} vs {tiers.get('A')}")
v = find_int(r"Tier A \d+ / Tier B ([\d,]+) / Tier C \d+", "R2 Tier B count")
report(v == tiers.get("B"), "R2 Tier B == clinical files", f"README {v} vs {tiers.get('B')}")
v = find_int(r"Tier A \d+ / Tier B \d+ / Tier C ([\d,]+)", "R2 Tier C count")
report(v == tiers.get("C"), "R2 Tier C == clinical files", f"README {v} vs {tiers.get('C')}")

# ---------------------------------------------------------------- R3
# The ledger stores per-section outcomes as counts in the clinical
# sections and as lists in the FMA sections; L() reads either form.
def L(x):
    return len(x) if isinstance(x, list) else x


ta2_clin = ledger["systems"]
ta2_fma = [v for k, v in ledger.items() if k.startswith("fma_inventory")]
ta2_cov = sum(v["records"] for v in ta2_clin.values()) + fma_records
ta2_res = sum(L(v["resolved"]) for v in ta2_clin.values()) + \
    sum(L(v["resolved"]) for v in ta2_fma)
ta2_amb = sum(L(v["ambiguous"]) for v in ta2_clin.values()) + \
    sum(L(v["ambiguous"]) for v in ta2_fma)
ta2_nf = sum(L(v["not_found"]) for v in ta2_clin.values()) + \
    sum(L(v["not_found"]) for v in ta2_fma)
v = find_int(r"resolved for \*\*([\d,]+) of the [\d,]+ records", "R3 TA2 resolved")
report(v == ta2_res, "R3 TA2 resolved == ledger", f"README {v} vs {ta2_res}")
v = find_int(r"resolved for \*\*[\d,]+ of the ([\d,]+) records", "R3 TA2 covered")
report(v == ta2_cov, "R3 TA2 covered == ledger", f"README {v} vs {ta2_cov}")
v = find_int(r"\*\*([\d,]+) ambiguous\*\*", "R3 TA2 ambiguous")
report(v == ta2_amb, "R3 TA2 ambiguous == ledger", f"README {v} vs {ta2_amb}")
v = find_int(r"\*\*([\d,]+) not found\*\*", "R3 TA2 not found")
report(v == ta2_nf, "R3 TA2 not found == ledger", f"README {v} vs {ta2_nf}")

# ---------------------------------------------------------------- R4
manifest = json.load(open(os.path.join(ROOT, "web/data/manifest.json")))
delivery = json.load(open(os.path.join(ROOT, "web/data/delivery.json")))
pack_bytes = sum(l["bytes"] for l in manifest["layers"].values())
pack_tris = sum(l["indices"] for l in manifest["layers"].values()) // 3
gz_bytes = delivery["compressed_total_bytes"]
v = find_int(r"\*\*([\d,]+) triangles\*\*", "R4 pack triangles")
report(v == pack_tris, "R4 triangles == manifest", f"README {v} vs {pack_tris}")
v = find_int(r"\(([\d,]+) bytes canonical", "R4 pack bytes")
report(v == pack_bytes, "R4 canonical bytes == manifest", f"README {v} vs {pack_bytes}")
v = find_int(r"([\d,]+) bytes as gzip", "R4 gzip bytes")
report(v == gz_bytes, "R4 gzip bytes == delivery.json", f"README {v} vs {gz_bytes}")

# ---------------------------------------------------------------- R5
phys = json.load(open(os.path.join(ROOT, "physiology/parameters.json")))
for pat, key, label in [
        (r"\*\*([\d,]+) parameters\*\*", "parameters", "parameters"),
        (r"\*\*([\d,]+) sources\*\*", "sources", "sources"),
        (r"([\d,]+) validation ranges", "validation_ranges", "validation ranges"),
        (r"([\d,]+) perturbation cases", "perturbation_cases", "perturbation cases")]:
    v = find_int(pat, f"R5 physiology {label}")
    report(v == len(phys[key]), f"R5 physiology {label} == parameters.json",
           f"README {v} vs {len(phys[key])}")
status_counts = {}
for p in phys["parameters"]:
    status_counts[p.get("status")] = status_counts.get(p.get("status"), 0) + 1
for pat, st in [(r"([\d,]+) cited,", "cited"),
                (r"([\d,]+) calibrated within cited ranges,", "calibrated"),
                (r"([\d,]+) verify-flagged\)", "verify")]:
    v = find_int(pat, f"R5 physiology status {st}")
    report(v == status_counts.get(st), f"R5 physiology status {st} == parameters.json",
           f"README {v} vs {status_counts.get(st)}")

m = re.search(r"resting trace hash `(0x[0-9a-f]+)`", FLAT)
hash_ok = False
if m:
    h = m.group(1)
    hash_ok = all(h in open(os.path.join(ROOT, f)).read() for f in
                  ("cases/case.ruq-pain.001.json",
                   "cases/case.appendicitis.003.json",
                   "cases/case.acute-dyspnea.006.json"))
report(hash_ok, "R5 resting trace hash == hash recorded in physiology-linked cases",
       m.group(1) if m else "hash not found in README")

# ---------------------------------------------------------------- R6
import glob
procs = sorted(glob.glob(os.path.join(ROOT, "theatre/procedures/*.json")))
ph = st = ms = 0
for f in procs:
    d = json.load(open(f))["procedure"]
    ph += len(d["phases"])
    st += sum(len(p["steps"]) for p in d["phases"])
    ms += sum(len(s["microsteps"]) for p in d["phases"] for s in p["steps"])
tparam = json.load(open(os.path.join(ROOT, "theatre/parameters.json")))
tinstr = json.load(open(os.path.join(ROOT, "theatre/instruments.json")))
n_verify = sum(1 for p in tparam["parameters"] if p.get("status") == "verify")
for pat, want, label in [
        (r"\*\*([\d,]+) authored procedures\*\*", len(procs), "procedures"),
        (r"([\d,]+) phases / [\d,]+ steps / [\d,]+ microsteps", ph, "phases"),
        (r"[\d,]+ phases / ([\d,]+) steps / [\d,]+ microsteps", st, "steps"),
        (r"[\d,]+ phases / [\d,]+ steps / ([\d,]+) microsteps", ms, "microsteps"),
        (r"([\d,]+) scripted traces", len(glob.glob(os.path.join(ROOT, "theatre/traces/*.json"))), "traces"),
        (r"\*\*([\d,]+) sources\*\* \(T1", len(tparam["sources"]), "sources"),
        (r"T41\), \*\*([\d,]+) parameters\*\*", len(tparam["parameters"]), "parameters"),
        (r"([\d,]+) of them verify-flagged", n_verify, "verify-flagged parameters"),
        (r"\*\*([\d,]+) instruments\*\*", len(tinstr["instruments"]), "instruments")]:
    if want is None:
        continue
    v = find_int(pat, f"R6 theatre {label}")
    report(v == want, f"R6 theatre {label} == data", f"README {v} vs {want}")
n_traces = len(glob.glob(os.path.join(ROOT, "theatre/traces/*.json")))
n_debriefs = len(glob.glob(os.path.join(ROOT, "theatre/debriefs/*.json")))
report(n_traces == n_debriefs, "R6 traces == debriefs on disk",
       f"{n_traces} traces, {n_debriefs} debriefs")

# ---------------------------------------------------------------- R7
case_files = sorted(glob.glob(os.path.join(ROOT, "cases/case.*.json")))
cparam = json.load(open(os.path.join(ROOT, "cases/parameters.json")))
last_src = cparam["sources"][-1]["id"]
v = find_int(r"\*\*([\d,]+) cases\*\*", "R7 case count")
report(v == len(case_files), "R7 case files == cases/", f"README {v} vs {len(case_files)}")
v = find_int(r"source register \(([\d,]+) sources, C1", "R7 register size")
report(v == len(cparam["sources"]), "R7 register size == parameters.json",
       f"README {v} vs {len(cparam['sources'])}")
report(f"C1–{last_src}" in FLAT, "R7 register extent stated",
       f"last source id in register: {last_src}")

# ---------------------------------------------------------------- R8
for subj, dims_pat in [("s0778", r"s0778 \(([\d,]+) DICOM instances"),
                       ("s1090", r"s1090 \(([\d,]+) DICOM instances")]:
    n_dcm = len(glob.glob(os.path.join(ROOT, f"data/imaging/{subj}/dicom/*.dcm")))
    v = find_int(dims_pat, f"R8 {subj} instances")
    report(v == n_dcm, f"R8 {subj} DICOM instances == files", f"README {v} vs {n_dcm}")
    cw = json.load(open(os.path.join(ROOT, f"data/imaging/{subj}/crosswalk.json")))
    reach = cw["totals"]["records_reachable_from_present_labels"]
    v = find_int(rf"{subj}.{{0,80}}?reach ([\d,]+) Body Model records", f"R8 {subj} reachable")
    report(v == reach, f"R8 {subj} reachable records == crosswalk",
           f"README {v} vs {reach}")
cw0 = json.load(open(os.path.join(ROOT, "data/imaging/s0778/crosswalk.json")))
v = find_int(r"\*\*([\d,]+) of the 104 labels mapped\*\*", "R8 labels mapped")
report(v == cw0["totals"]["labels_mapped"], "R8 labels mapped == crosswalk",
       f"README {v} vs {cw0['totals']['labels_mapped']}")

# ---------------------------------------------------------------- R9
def run(cmd, cwd=ROOT):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


rc, out = run([sys.executable, "tools/theatre_check.py"])
m = re.search(r"theatre_check: ([\d,]+) checks, 0 failures", out)
v = find_int(r"\| `tools/theatre_check\.py` \| ([\d,]+) checks, 0 failures", "R9 theatre_check total")
report(rc == 0 and m and v == num(m.group(1)), "R9 theatre_check total == its printed output",
       f"README {v} vs printed {m.group(1) if m else 'n/a'}, exit {rc}")

rc, out = run([sys.executable, "tools/case_check.py"])
m = re.search(r"ALL CHECKS PASS: ([\d,]+) passed, 0 failed", out)
v = find_int(r"\| `tools/case_check\.py` \| ([\d,]+) checks passed, 0 failed", "R9 case_check total")
report(rc == 0 and m and v == num(m.group(1)), "R9 case_check total == its printed output",
       f"README {v} vs printed {m.group(1) if m else 'n/a'}, exit {rc}")

rc, out = run([sys.executable, "tools/imaging_toolkit_check.py"])
n_pass = len(re.findall(r"^PASS", out, re.M))
v = find_int(r"\| `tools/imaging_toolkit_check\.py` \| ([\d,]+) hard checks PASS", "R9 imaging total")
report(rc == 0 and "ALL HARD CHECKS PASS" in out and v == n_pass,
       "R9 imaging_toolkit_check PASS count == its printed output",
       f"README {v} vs printed {n_pass}, exit {rc}")

rc, out = run(["node", "tools/verify_web.js"])
wset = sorted(set(re.findall(r"\[PASS\] (W\d+)", out)))
v = find_int(r"ALL CHECKS PASS \(W1–W([\d,]+)\)", "R9 verify_web extent")
report(rc == 0 and "ALL CHECKS PASS" in out and v == len(wset),
       "R9 verify_web ALL CHECKS PASS, W-set size == its printed output",
       f"README W1–W{v} vs printed {wset}, exit {rc}")

cargo = "cargo" if subprocess.run(["which", "cargo"], capture_output=True).returncode == 0 \
    else os.path.expanduser("~/.cargo/bin/cargo")
rc, out = run([cargo, "run", "--release", "--quiet", "--", "verify"],
              cwd=os.path.join(ROOT, "native"))
npass = len(re.findall(r"\[PASS\]", out))
nfail = len(re.findall(r"\[FAIL\]", out))
v = find_int(r"\| native `verify` \| ([\d,]+) data/pack assertions PASS, 0 FAIL", "R9 native total")
report(v == npass and nfail == 0, "R9 native verify assertion counts == its printed output",
       f"README {v} vs printed {npass} PASS / {nfail} FAIL (exit {rc}; "
       "nonzero exit is the headless GPU stage, not a data assertion)")

# ---------------------------------------------------------------- R10
disk_ms = sorted(int(re.match(r"MILESTONE-(\d+)\.md", f).group(1))
                 for f in os.listdir(os.path.join(ROOT, "milestones"))
                 if re.match(r"MILESTONE-\d+\.md", f))
readme_ms = sorted(int(x) for x in re.findall(r"\| (\d+) \| `MILESTONE-\d+\.md`", README))
report(readme_ms == disk_ms, "R10 milestone index rows == MILESTONE-*.md on disk",
       f"README rows {len(readme_ms)} vs disk {len(disk_ms)}")
report("| 7 (fix) | `MILESTONE-7-FIX.md`" in README and
       os.path.exists(os.path.join(ROOT, "milestones", "MILESTONE-7-FIX.md")),
       "R10 Milestone 7 fix row present, file exists")

# ---------------------------------------------------------------- R11
EXCL_ANYWHERE = {"__pycache__", "target"}


def tracked():
    out = []
    for dp, dns, fns in os.walk(ROOT):
        rel = os.path.relpath(dp, ROOT)
        dns[:] = [d for d in dns
                  if d not in EXCL_ANYWHERE and not d.startswith(".")
                  and not (rel == "." and d == "work")
                  and not (rel == "native" and d == "frames")]
        for fn in fns:
            p = fn if rel == "." else f"{rel}/{fn}"
            if p.startswith("data/sources/"):
                if p.rsplit(".", 1)[-1].lower() in ("zip", "obj", "glb"):
                    continue
                if p.endswith(".nii.gz") or "/subset/" in p or "/extracted/" in p:
                    continue
            if "/dicom/" in p:
                continue
            if p.startswith("web/data/") and (p.endswith(".bin")
                                              or p.endswith(".bin.gz")):
                continue
            if p.startswith("web/data/imaging/") or p == "web/data/imaging.json":
                continue
            out.append(p)
    return sorted(out)


want_groups = {}
for p in tracked():
    g = p.split("/")[0] if "/" in p else "Root"
    want_groups.setdefault(g, []).append(p)

idx = README.split("## File index", 1)[1].split("## License", 1)[0]
got_groups = {}
cur = None
for line in idx.splitlines():
    m = re.match(r"### (?:Root|`([a-z0-9-]+)/`) — (\d+) files", line)
    if m:
        cur = m.group(1) or "Root"
        got_groups[cur] = []
        continue
    m = re.match(r"- `([^`]+)`", line)
    if m and cur:
        got_groups[cur].append(m.group(1))

for g in sorted(set(want_groups) | set(got_groups)):
    if g == "film-engine":
        note("R11 film-engine/ group carried over, not locally verifiable",
             f"{len(got_groups.get(g, []))} entries in README; the files live "
             "in the repository (Milestone 15 index, PR-landed), not in this tree")
        continue
    report(got_groups.get(g) == want_groups.get(g),
           f"R11 file index [{g}] == tracked set",
           f"README {len(got_groups.get(g, []))} vs tree {len(want_groups.get(g, []))}")
total_stated = find_int(r"All ([\d,]+) files in this repository", "R11 total")
total_actual = sum(len(v) for v in got_groups.values())
report(total_stated == total_actual, "R11 stated total == sum of index groups",
       f"README {total_stated} vs index sum {total_actual}")

# ---------------------------------------------------------------- R12
REQUIRED = [
    ("expert-review gate is UNMET", "expert-review gate UNMET"),
    ("formative-only", "formative-only labeling"),
    ("Tier B geometry was intaken at Milestone 63", "Tier B intake at Milestone 63"),
    ("Tier C remains gated on a validating derivation", "Tier C gated"),
    ("Tier D is excluded permanently", "Tier D excluded permanently"),
    ("the deferent-duct meshes are claimed", "deferent-duct meshes claimed"),
    ("found and repaired", "DICOM defect found and repaired"),
]
for text, label in REQUIRED:
    report(text in FLAT, f"R12 status statement present: {label}", f"“{text}”")

print(f"\n{'ALL CHECKS PASS' if not FAILS else 'FAILURES: ' + ', '.join(FAILS)}")
sys.exit(0 if not FAILS else 1)
