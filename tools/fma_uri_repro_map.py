#!/usr/bin/env python3
"""ANATOMICA urinary + reproductive FMA extension builder —
Milestone 37.

Extends the urinary and reproductive inventories with concept
records sourced from the Foundational Model of Anatomy (FMA)
5.1.0, for the structures Milestones 12 and 14 proved absent
from BodyParts3D 4.0: the urinary interior entire (renal pelvis
and calyces, pyramids, papillae, columns, cortex/medulla, the
nephron and its segments, the bladder's parts, the ureter's
parts and junctions, the divided urethra) and the female
reproductive tract entire (ovary, uterine tube, uterus,
vagina, vulva — Milestone 14's census carried exactly one
female concept, the mons pubis, against fourteen male).

Sibling of tools/fma_lymph_endo_map.py (Milestone 36), same
discipline:

  - License: the FMA 5.1.0 release package ships the full text
    of CC BY 4.0 as its LICENSE file (data/sources/fma-5.1.0/,
    hash-pinned in that directory's provenance ledger at
    Milestone 33). The FMA is an ontology: it carries NO
    geometry. Every record written here is marked
    geometry-absent; no mesh, coordinate or clinical value is
    created by this tool.
  - A frozen target list per system (below) names the absent
    structures. Each target is resolved mechanically against
    fma.owl: lateralised records (left/right) where the FMA
    carries both sided classes, otherwise a single un-sided
    record keyed on the un-sided class. Sided classes are
    recognised in both of the FMA's naming patterns — the
    prefix form ('Left renal pelvis') and the kidney-part
    suffix form ('Cortex of left kidney') — and a sided job is
    taken only when BOTH sided classes exist AND each is an
    IS-A child of the un-sided class (parent-verified; all 21
    sided pairs of this intake verify).
  - Exclusion: any candidate whose FMAID already appears in ANY
    inventory record of the Body Model is excluded and reported
    with its owner. Four urinary targets and one reproductive
    target are frozen precisely so this rule fires on them
    mechanically: 'Kidney', 'Ureter', 'Urinary bladder' and
    'Urethra' are the Milestone 12 BP3D records' own classes
    and concepts, and 'Mons pubis' is the reproductive module's
    one female BP3D record.
  - Module boundaries follow the existing inventories'
    ownership: the kidney interior and the divided urethra are
    urinary (the urethra is the urinary module's record,
    Milestone 12/14); the female tract is reproductive. The
    perineal body — a sex-shared midline structure named
    absent on Milestone 14's shared probe line — is recorded
    under reproductive, whose module owns the perineum
    records; the call is recorded on the record itself.
  - The OWL parser counts owl:Class nesting depth (net of
    self-closing class references) — the Milestone 36 repair;
    the naive block parser is known-defective (a class's
    fma:preferred_name can sit after dozens of restriction
    axioms).
  - The merge is idempotent: records tagged source ==
    "fma-5.1.0" in these two inventories are stripped and
    re-appended; every BP3D record and census field is left
    byte-identical in parsed form.
  - The per-system intake accounting is written to
    data/fma-intake-37.json (targets, verdicts, probe
    evidence, census deltas). The plexus re-verification
    section of that artifact is written by
    tools/fma_plexus_correct.py, which also applies the
    correction it proves.

Usage: fma_uri_repro_map.py [--report]
Stdout only.
"""
import json
import os
import re
import sys
import zipfile
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "fma-5.1.0")
WORK_OWL = os.path.join(ROOT, "work", "fma", "fma.owl")
ART_PATH = os.path.join(ROOT, "data", "fma-intake-37.json")
SOURCE_TAG = "fma-5.1.0"
DATE = "2026-11-06"

VERIFY_FLAGS = [
    "geometry: absent — the FMA is an ontology and carries no mesh "
    "data; this record is concept-only until a geometry source clears "
    "the project's license and registration bars (Milestone 37)",
    "clinical: no clinical tranche has been authored for FMA-sourced "
    "records; no clinical values are entered",
]

# ---------------------------------------------------------------------
# Frozen target lists: (preferred-name target, subtree, note or None).
# Every name was verified present in fma.owl by probe before freezing
# (Milestone 37 build record), except the five targets tagged
# "existing", which are frozen so the already-inventoried exclusion
# fires mechanically and is accounted.
# ---------------------------------------------------------------------

URI_TARGETS = []
# Kidney interior — gross (Milestone 12: absent entire)
for n in ["Cortex of kidney", "Medulla of kidney", "Renal pyramid",
          "Renal papilla", "Renal column", "Renal pelvis",
          "Major calyx", "Minor calyx", "Renal sinus", "Renal lobe",
          "Renal fascia"]:
    URI_TARGETS.append((n, "kidney-interior", None))
URI_TARGETS.append((
    "Fibrous capsule of kidney", "kidney-interior",
    "the FMA's class for the renal capsule of Milestone 12's "
    "gap analysis"))
URI_TARGETS.append(("Hilum of kidney", "kidney-interior", None))
# The nephron and its segments (Milestone 12: absent entire)
for n in ["Nephron", "Renal tubule", "Renal corpuscle",
          "Glomerulus", "Glomerular capsule",
          "Proximal convoluted tubule", "Proximal straight tubule",
          "Loop of Henle", "Descending thin limb",
          "Ascending thin limb", "Distal convoluted tubule",
          "Macula densa"]:
    URI_TARGETS.append((n, "nephron", None))
URI_TARGETS.append((
    "Collecting duct of renal tubule", "nephron",
    "the FMA's preferred name for the collecting duct"))
URI_TARGETS.append((
    "Juxtaglomerular complex", "nephron",
    "the FMA's class for the juxtaglomerular apparatus of "
    "Milestone 12's gap analysis"))
URI_TARGETS.append((
    "Afferent glomerular arteriole", "nephron",
    "a glomerular microvascular class, recorded under this "
    "module as part of the nephron apparatus censused at "
    "Milestone 12; the cardiovascular module carries no renal "
    "microvasculature records"))
URI_TARGETS.append((
    "Efferent glomerular arteriole", "nephron",
    "a glomerular microvascular class, recorded under this "
    "module as part of the nephron apparatus censused at "
    "Milestone 12; the cardiovascular module carries no renal "
    "microvasculature records"))
URI_TARGETS.append((
    "Descending vasa recta", "nephron",
    "one of the FMA's two vasa recta classes (descending and "
    "ascending); its long/short descending subdivisions are "
    "below this intake's granularity (see deferred)"))
URI_TARGETS.append((
    "Ascending vasa recta", "nephron",
    "one of the FMA's two vasa recta classes (descending and "
    "ascending)"))
URI_TARGETS.append((
    "Peritubular capillary plexus of kidney", "nephron",
    "the FMA's class for the peritubular capillary network of "
    "Milestone 12's gap analysis"))
# Bladder parts (Milestone 12 clinical record: 'no bladder
# sub-part records exist')
for n in ["Apex of urinary bladder", "Body of urinary bladder",
          "Fundus of urinary bladder", "Neck of urinary bladder",
          "Trigone of urinary bladder", "Uvula of urinary bladder",
          "Internal urethral orifice"]:
    URI_TARGETS.append((n, "bladder-parts", None))
URI_TARGETS.append((
    "Detrusor", "bladder-parts",
    "the FMA's class for the detrusor muscle"))
URI_TARGETS.append((
    "Interureteric crest", "bladder-parts",
    "the FMA's name for the interureteric ridge (bar) named in "
    "Milestone 12's clinical record"))
# Ureter parts and junctions (Milestone 12: 'the ureter record
# is one tube'; the clinical pathway names the junctions)
for n in ["Ureteropelvic junction", "Ureterovesical junction",
          "Abdominal part of ureter", "Pelvic part of ureter",
          "Intramural part of ureter"]:
    URI_TARGETS.append((n, "ureter-parts", None))
URI_TARGETS.append((
    "Ureteral orifice", "ureter-parts",
    "the FMA's spelling ('ureteral') of the ureteric orifice"))
# The divided urethra (Milestone 12: 'un-parted, unsexed';
# Milestone 14 boundary: the urethra is this module's record)
for n in ["Male urethra", "Female urethra",
          "Pre-prostatic part of urethra",
          "Bulbous part of urethra", "Urethral crest",
          "Seminal colliculus", "External urethral sphincter",
          "External urethral orifice"]:
    URI_TARGETS.append((n, "urethra-divided", None))
URI_TARGETS.append((
    "Prostatic urethra", "urethra-divided",
    "the FMA's class name for the prostatic part of the male "
    "urethra"))
URI_TARGETS.append((
    "Membranous urethra", "urethra-divided",
    "the FMA's class name for the membranous part of the male "
    "urethra"))
URI_TARGETS.append((
    "Spongiose part of urethra", "urethra-divided",
    "the FMA's class name for the spongy (penile) part of the "
    "male urethra"))
URI_TARGETS.append((
    "Preprostatic sphincter", "urethra-divided",
    "the FMA's named sphincter of the bladder neck and "
    "pre-prostatic urethra; the FMA carries no class named "
    "'internal urethral sphincter' (see absence probes)"))
# Already-inventoried classes, frozen so the exclusion fires
# mechanically (the Milestone 36 pineal pattern)
for n, note in [
        ("Kidney", "the kidney class (FMA7203) and its two "
                   "instances are this module's Milestone 12 "
                   "BP3D records"),
        ("Ureter", "the ureter class (FMA9704) and its two "
                   "instances are this module's Milestone 12 "
                   "BP3D records"),
        ("Urinary bladder", "FMA15900 is this module's "
                            "Milestone 12 BP3D record"),
        ("Urethra", "FMA19667 is this module's Milestone 12 "
                    "BP3D record")]:
    URI_TARGETS.append((n, "existing", note))

REPRO_TARGETS = []
# Ovary (Milestone 14: absent entire — 'not a probe miss')
for n in ["Ovary", "Follicle of ovary", "Corpus luteum",
          "Corpus albicans", "Hilum of ovary",
          "Ovarian ligament", "Suspensory ligament of ovary",
          "Mesovarium"]:
    REPRO_TARGETS.append((n, "ovary", None))
# Uterine tube (Milestone 14: absent entire)
for n in ["Uterine tube", "Infundibulum of uterine tube",
          "Fimbria of uterine tube", "Ampulla of uterine tube",
          "Isthmus of uterine tube",
          "Uterine part of uterine tube", "Mesosalpinx"]:
    REPRO_TARGETS.append((n, "uterine-tube", None))
# Uterus (Milestone 14: absent entire)
for n in ["Uterus", "Body of uterus", "Fundus of uterus",
          "Endometrium", "Myometrium", "Cavity of uterus"]:
    REPRO_TARGETS.append((n, "uterus", None))
REPRO_TARGETS.append((
    "Cervix of uterus", "uterus",
    "the FMA's class name for the cervix"))
for n in ["Supravaginal part of cervix", "Vaginal part of cervix"]:
    REPRO_TARGETS.append((n, "uterus", None))
REPRO_TARGETS.append((
    "Serosa of uterus", "uterus",
    "the FMA's preferred name for the perimetrium"))
REPRO_TARGETS.append((
    "Broad ligament of uterus", "uterus",
    "the FMA's class name for the broad ligament"))
for n in ["Round ligament of uterus", "Mesometrium",
          "Uterosacral ligament"]:
    REPRO_TARGETS.append((n, "uterus", None))
REPRO_TARGETS.append((
    "Cardinal ligament", "uterus",
    "the FMA's class name for the transverse cervical "
    "(Mackenrodt) ligament"))
# Vagina (Milestone 14: absent entire)
for n in ["Vagina", "Fornix of vagina",
          "Anterior fornix of vagina", "Posterior fornix of vagina"]:
    REPRO_TARGETS.append((n, "vagina", None))
REPRO_TARGETS.append((
    "Hymen of vagina", "vagina",
    "the FMA's class name for the hymen"))
# Vulva and external genitalia (Milestone 14: absent entire)
for n in ["Vulva", "Clitoris", "Glans of clitoris",
          "Labium majus", "Labium minus", "Vestibule of vagina"]:
    REPRO_TARGETS.append((n, "vulva", None))
REPRO_TARGETS.append((
    "Greater vestibular gland", "vulva",
    "Bartholin's gland"))
REPRO_TARGETS.append(("Lesser vestibular gland", "vulva", None))
# The shared line (Milestone 14: perineal body absent). Boundary
# call: the perineal body is a sex-shared midline structure; it
# is recorded under this module, which owns the perineum
# records, and its sex_line is 'shared'.
REPRO_TARGETS.append((
    "Perineal body", "perineum-shared",
    "boundary call (Milestone 37): a sex-shared midline "
    "structure named absent on Milestone 14's shared probe "
    "line; recorded under the reproductive module, which owns "
    "the perineum records, with sex_line 'shared'"))
# Already-inventoried, frozen for the mechanical exclusion
REPRO_TARGETS.append((
    "Mons pubis", "existing",
    "FMA20218 is this module's one female BP3D record "
    "(Milestone 14)"))

SYSTEMS = {
    "urinary": {
        "inventory": "data/urinary/urinary-inventory.json",
        "geometry": "data/urinary/urinary-geometry.json",
        "prefix": "uri",
        "targets": URI_TARGETS,
        "sex_line": None,
    },
    "reproductive": {
        "inventory": "data/reproductive/reproductive-inventory.json",
        "geometry": "data/reproductive/reproductive-geometry.json",
        "prefix": "repro",
        "targets": REPRO_TARGETS,
        "sex_line": "female",
    },
}

# Per-target sex line for the reproductive intake: every target
# is a female-tract structure except the perineal body, which is
# sex-shared by anatomy and recorded 'shared'.
REPRO_SEX_LINE = {"Perineal body": "shared"}

# Absence probes: names with NO class in the FMA under the probed
# preferred name or its Left/Right prefix forms — computed, not
# asserted, and written into the accounting artifact as evidence.
# Most are the clinical/lay names whose FMA equivalents WERE
# intaken under the FMA's own preferred names (the equivalence
# is recorded on the target); the rest are genuine ontology
# absences at this granularity (internal urethral sphincter,
# cervical canal, isthmus of uterus as a zone, ovarian cortex /
# medulla, paraurethral gland as a single class).
ABSENCE_PROBES = {
    "urinary": [
        "Renal cortex", "Renal medulla", "Renal capsule",
        "Renal hilum", "Collecting duct",
        "Juxtaglomerular apparatus", "Vasa recta",
        "Peritubular capillary", "Capsule of glomerulus",
        "Nephron loop", "Detrusor muscle", "Interureteric ridge",
        "Ureteric orifice", "Spongy urethra",
        "Prostatic part of urethra", "Membranous part of urethra",
        "Internal urethral sphincter", "Thick ascending limb",
        "Thick descending limb", "Distal straight tubule",
        "Connecting tubule",
    ],
    "reproductive": [
        "Ovarian follicle", "Ligament of ovary", "Cervix",
        "Uterine cervix", "Perimetrium", "Broad ligament",
        "Hymen", "Fimbriae of uterine tube", "Cervical canal",
        "Isthmus of uterus", "External os of uterus",
        "Internal os of uterus", "Cortex of ovary",
        "Medulla of ovary", "Paraurethral gland",
    ],
}

# Census-named structures that EXIST in the FMA but are not targets
# of this intake, with the reason (recorded, not silent).
DEFERRED = {
    "urinary": [
        {"names": "Renal calyx (FMA284558), the generic parent "
                  "class of the major and minor calyces",
         "reason": "the census names the major and minor "
                   "calyces; both are recorded. The generic "
                   "parent is not separately recorded (the "
                   "Milestone 33/36 convention: generic parents "
                   "are recorded only where the census names "
                   "the generic, as with 'Lymph node')"},
        {"names": "Renal segment (FMA15615) and its five named "
                  "segment classes (superior, anterior superior, "
                  "anterior inferior, inferior, posterior "
                  "segments of kidney)",
         "reason": "the vascular segments are not named in "
                   "Milestone 12's absence census (its kidney "
                   "interior families are pelvis/calyces, "
                   "pyramids, papillae, columns, cortex/medulla, "
                   "nephron); a named follow-on candidate"},
        {"names": "Long descending vasa recta (FMA272280), "
                  "Short descending vasa recta (FMA272282)",
         "reason": "subdivisions of the descending vasa recta "
                   "class, below this intake's granularity; the "
                   "descending and ascending classes are "
                   "recorded"},
        {"names": "Dome of urinary bladder (FMA265241)",
         "reason": "a region class overlapping the fundus/apex "
                   "zones, which are recorded; not named in "
                   "Milestone 12's census"},
        {"names": "Renal pelvis proper (FMA17658) and the "
                  "intra-/extra-renal segment classes of the "
                  "renal pelvis and ureter",
         "reason": "subdivisions of the renal pelvis class "
                   "below this intake's granularity; the pelvis "
                   "is recorded (sided)"},
        {"names": "Medullary ray (FMA74299), Cortex proper of "
                  "kidney (FMA17876) and the inner/outer cortex "
                  "and stripe classes of the medulla",
         "reason": "sub-zonal subdivisions of the cortex and "
                   "medulla classes, below this intake's "
                   "granularity; both zonal classes are recorded "
                   "(sided)"},
    ],
    "reproductive": [
        {"names": "Paraurethral glands (Skene's glands): the "
                  "FMA carries no single anatomical class — only "
                  "the set class FMA265251 'Set of paraurethral "
                  "glands' and classes for their ducts and "
                  "orifices",
         "reason": "set/aggregate classes are not records, per "
                   "the Milestone 9/33 convention; the glands "
                   "remain concept-blocked in the FMA at record "
                   "granularity (named in Milestone 14's female "
                   "probe line)"},
        {"names": "Ectocervix (FMA86484), Endocervix (FMA86485)",
         "reason": "mucosal subdivisions of the cervix below "
                   "this intake's granularity; the cervix and "
                   "its supravaginal/vaginal parts are recorded"},
        {"names": "Perineal membrane (FMA30548 probed at "
                  "Milestone 14), rectouterine and vesicouterine "
                  "pouches",
         "reason": "perineal fascial and peritoneal-pouch "
                   "classes of Milestone 14's shared probe line; "
                   "they straddle the muscular/peritoneal "
                   "boundary and are outside this intake's scope "
                   "(urinary interior + female tract); named "
                   "follow-on candidates"},
        {"names": "Uterine horn (FMA77053)",
         "reason": "a class for the lateral angle region of the "
                   "uterus, not a named part in Milestone 14's "
                   "census; the fundus and body are recorded"},
    ],
}


def slug(name):
    s = name.lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def parse_owl(path):
    """Streaming regex parse of owl:Class blocks ->
    {fid: {name, label, parents}} (name = fma:preferred_name,
    label = rdfs:label; either may be None). Block boundaries
    count owl:Class nesting depth: restriction axioms embed
    nested class expressions, and a block must not end at a
    nested close (the Milestone 36 finding)."""
    def net(line):
        opens = len(re.findall(r"<owl:Class(?=[\s>])", line))
        selfclosed = len(re.findall(r"<owl:Class[^>]*/>", line))
        return opens - selfclosed - line.count("</owl:Class>")

    classes = {}
    block = []
    depth = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if depth == 0 and "<owl:Class rdf:about=" in line:
                block = [line]
                depth = net(line)
                if depth > 0:
                    continue
            elif depth:
                block.append(line)
                depth += net(line)
                if depth > 0:
                    continue
            else:
                continue
            if block:
                text = "".join(block)
                block = []
                m = re.search(
                    r'owl:Class rdf:about="http://purl\.org/sig/ont/'
                    r'fma/fma(\d+)"', text)
                if m:
                    name = re.search(
                        r"<fma:preferred_name>([^<]+)"
                        r"</fma:preferred_name>", text)
                    label = re.search(
                        r"<rdfs:label[^>]*>([^<]+)</rdfs:label>",
                        text)
                    parents = re.findall(
                        r'<rdfs:subClassOf rdf:resource='
                        r'"http://purl\.org/sig/ont/fma/fma(\d+)"/>',
                        text)
                    classes[m.group(1)] = {
                        "name": name.group(1) if name else None,
                        "label": label.group(1) if label else None,
                        "parents": parents}
    return classes


def display_name(fid, classes):
    c = classes.get(fid) or {}
    return c.get("name") or c.get("label")


def group_path(fid, classes):
    """BFS over named IS-A parents to FMA62955 'Anatomical entity';
    ancestor names are preferred names, falling back to rdfs:label
    for the classes that carry no preferred name."""
    target = "62955"
    from collections import deque
    prev = {fid: None}
    queue = deque([fid])
    found = None
    while queue:
        cur = queue.popleft()
        if cur == target:
            found = cur
            break
        for p in classes.get(cur, {}).get("parents", []):
            if p not in prev and p in classes:
                prev[p] = cur
                queue.append(p)
    if found is None:
        return [display_name(fid, classes)]
    chain = []
    cur = found
    while cur is not None:
        chain.append(display_name(cur, classes))
        cur = prev[cur]
    return chain


def global_exclusions():
    """fid -> [owners] over every inventory record of the Body
    Model. This builder's OWN records — the tagged records of
    the two inventories it rebuilds — never exclude: they are
    stripped and re-derived on every run, which is what makes
    the builder idempotent (the Milestone 36 lesson)."""
    import glob as globmod
    owners = defaultdict(list)
    own_files = {os.path.join(ROOT, cfg["inventory"])
                 for cfg in SYSTEMS.values()}
    for path in sorted(globmod.glob(
            os.path.join(ROOT, "data", "*", "*-inventory.json"))):
        doc = json.load(open(path))
        system = os.path.basename(os.path.dirname(path))
        for r in doc.get("records", []):
            if r.get("source") == SOURCE_TAG and path in own_files:
                continue  # this run's own records: rebuilt below
            ids = list(r.get("concept_ids") or [])
            if r.get("class_concept_id"):
                ids.append(r["class_concept_id"])
            for cid in ids:
                if r.get("source") == SOURCE_TAG:
                    owners[cid].append(
                        f"fma-intake:{system}:{r['record_id']}")
                else:
                    owners[cid].append(
                        f"bp3d:{system}:{r['record_id']}")
    return owners


def sided_candidates(target, unsided_fid, byname, classes):
    """Both naming patterns, parent-verified. Returns
    (form, [(side, fid), ...]) or (None, [])."""
    forms = [
        ("prefix", f"Left {target}", f"Right {target}"),
        ("suffix", target.replace(" of kidney", " of left kidney"),
         target.replace(" of kidney", " of right kidney")),
    ]
    for form, lname, rname in forms:
        if lname == target or rname == target:
            continue
        lf = byname.get(lname.lower(), [])
        rf = byname.get(rname.lower(), [])
        if lf and rf and unsided_fid is not None:
            if all(unsided_fid in classes[f]["parents"]
                   for f in (lf[0], rf[0])):
                return form, [("left", lf[0]), ("right", rf[0])]
    return None, []


def build_system(system, cfg, classes, byname, owners, report):
    inv = json.load(open(os.path.join(ROOT, cfg["inventory"])))
    geo = json.load(open(os.path.join(ROOT, cfg["geometry"])))
    bp3d_records = [r for r in inv["records"]
                    if r.get("source") != SOURCE_TAG]
    bp3d_ids = {r["record_id"] for r in bp3d_records}

    new_records = []
    entries = []
    for target, subtree, note in cfg["targets"]:
        unsided = byname.get(target.lower(), [])
        unsided_fid = unsided[0] if unsided else None
        form, sided = sided_candidates(target, unsided_fid,
                                       byname, classes)
        jobs = sided if sided else (
            [(None, unsided_fid)] if unsided_fid else [])
        if not jobs:
            entries.append({"target": target, "subtree": subtree,
                            "verdict": "not-in-fma",
                            "evidence": "no class carries this "
                                        "preferred name or its "
                                        "sided forms in fma.owl",
                            "records": []})
            continue
        class_id = f"FMA{unsided_fid}" if unsided_fid else None
        rec_ids = []
        excluded_hit = []
        for side, fid in jobs:
            owner = owners.get(f"FMA{fid}")
            if owner:
                excluded_hit.append((side, fid, owner))
                continue
            name = display_name(fid, classes)
            assert name is not None, (target, fid)
            if side is not None:
                rid = f"{cfg['prefix']}.{side}-{slug(target)}"
            else:
                rid = f"{cfg['prefix']}.{slug(name)}"
            assert rid not in bp3d_ids, f"record id collision: {rid}"
            assert all(x["record_id"] != rid for x in new_records), rid
            rec = {
                "record_id": rid,
                "name": name,
                "side": side,
                "representation": "fma-concept",
                "class_concept_id": class_id,
                "concept_ids": [f"FMA{fid}"],
                "subtree": subtree,
            }
            if cfg["sex_line"] is not None:
                rec["sex_line"] = REPRO_SEX_LINE.get(
                    target, cfg["sex_line"])
            rec["group_path"] = group_path(fid, classes)
            rec["source"] = SOURCE_TAG
            rec["geometry"] = "absent"
            rec["verify"] = list(VERIFY_FLAGS)
            rec["note"] = note
            new_records.append(rec)
            rec_ids.append(rid)
        if excluded_hit and not rec_ids:
            entries.append({
                "target": target, "subtree": subtree,
                "verdict": "excluded",
                "evidence": "; ".join(
                    f"FMA{fid} already inventoried "
                    f"({', '.join(dict.fromkeys(own))})"
                    for _s, fid, own in excluded_hit),
                "records": []})
        else:
            assert not excluded_hit, (target, excluded_hit)
            entries.append({
                "target": target, "subtree": subtree,
                "verdict": "resolved",
                "form": form if sided else "un-sided",
                "records": rec_ids,
                "fmaids": [r["concept_ids"][0] for r in new_records
                           if r["record_id"] in rec_ids],
                "sided": sum(1 for r in new_records
                             if r["record_id"] in rec_ids
                             and r["side"] is not None)})
    unresolved = [e for e in entries if e["verdict"] == "not-in-fma"]
    print(f"[{system}] targets: {len(cfg['targets'])}  new records: "
          f"{len(new_records)}  excluded: "
          f"{sum(1 for e in entries if e['verdict'] == 'excluded')}  "
          f"not-in-fma: {len(unresolved)}")
    for e in entries:
        if e["verdict"] != "resolved":
            print(f"  {e['verdict'].upper()}: {e['target']} — "
                  f"{e['evidence']}")
    if report:
        return None

    inv["records"] = bp3d_records + new_records
    inv["meta"]["record_count"] = len(inv["records"])
    reps = {}
    for r in inv["records"]:
        reps[r["representation"]] = reps.get(r["representation"], 0) + 1
    inv["meta"]["record_representations"] = reps
    by_sub = {}
    for r in inv["records"]:
        by_sub[r["subtree"]] = by_sub.get(r["subtree"], 0) + 1
    inv["meta"]["records_by_subtree"] = by_sub
    if cfg["sex_line"] is not None:
        by_sex = {}
        for r in inv["records"]:
            by_sex[r["sex_line"]] = by_sex.get(r["sex_line"], 0) + 1
        inv["meta"]["records_by_sex_line"] = by_sex
    inv["meta"]["fma_extension"] = {
        "milestone": 37,
        "source": "Foundational Model of Anatomy (FMA) 5.1.0, "
                  "data/sources/fma-5.1.0/ (CC BY 4.0)",
        "records_added": len(new_records),
        "geometry_absent": len(new_records),
        "counting_convention": "one record per lateralised instance "
                               "where the FMA carries both sided "
                               "classes (prefix or kidney-suffix "
                               "naming, IS-A parent-verified); "
                               "one record keyed on the un-sided "
                               "class otherwise — mirroring the "
                               "Milestone 33/36 convention",
        "accounting": "data/fma-intake-37.json",
    }
    with open(os.path.join(ROOT, cfg["inventory"]), "w") as f:
        json.dump(inv, f, indent=1)

    geo_bp3d = [r for r in geo["records"]
                if r.get("source") != SOURCE_TAG]
    geo_new = []
    for r in new_records:
        g = {
            "record_id": r["record_id"],
            "name": r["name"],
            "side": r["side"],
            "representation": "fma-concept",
        }
        if cfg["sex_line"] is not None:
            g["sex_line"] = r["sex_line"]
        g["concept_ids"] = r["concept_ids"]
        g["concept_names"] = [r["name"]]
        g["source"] = SOURCE_TAG
        g["geometry_status"] = (
            "absent — FMA concept record; the FMA "
            "carries no mesh data (Milestone 37)")
        g["isa_meshes"] = []
        g["partof_meshes"] = []
        g["totals"] = {"isa": {"files": 0, "vertices": 0, "faces": 0},
                       "partof": {"files": 0, "vertices": 0,
                                  "faces": 0},
                       "combined_files": 0}
        g["bbox_isa"] = None
        g["bbox_partof"] = None
        geo_new.append(g)
    geo["records"] = geo_bp3d + geo_new
    cov = dict(geo["meta"]["coverage"])
    cov["records"] = len(geo["records"])
    cov["records_with_meshes"] = len(geo_bp3d)
    cov["records_without_meshes"] = len(geo_new)
    if "by_sex_line" in cov:
        by_sex = {}
        for g in geo["records"]:
            line = by_sex.setdefault(
                g["sex_line"], {"records": 0,
                                "records_with_meshes": 0})
            line["records"] += 1
            if g["isa_meshes"] or g["partof_meshes"]:
                line["records_with_meshes"] += 1
        cov["by_sex_line"] = by_sex
    geo["meta"]["coverage"] = cov
    with open(os.path.join(ROOT, cfg["geometry"]), "w") as f:
        json.dump(geo, f, indent=1)
    print(f"[{system}] inventory records: {len(bp3d_records)} BP3D + "
          f"{len(new_records)} FMA = {len(inv['records'])}")
    return {
        "records_before": len(bp3d_records),
        "records_after": len(inv["records"]),
        "records_added": len(new_records),
        "targets": entries,
    }


def main():
    report = "--report" in sys.argv
    if not os.path.exists(WORK_OWL):
        os.makedirs(os.path.dirname(WORK_OWL), exist_ok=True)
        with zipfile.ZipFile(os.path.join(SRC, "fma.zip")) as zf:
            zf.extract("fma.owl", os.path.dirname(WORK_OWL))
    classes = parse_owl(WORK_OWL)
    byname = defaultdict(list)
    for fid, c in classes.items():
        if c["name"]:
            byname[c["name"].lower()].append(fid)
    owners = global_exclusions()

    artifact = {
        "meta": {
            "milestone": "M37", "date": DATE,
            "scope": "FMA 5.1.0 concept intake #3: the urinary "
                     "interior and the female reproductive "
                     "tract — the structures Milestones 12 and "
                     "14 proved absent from BodyParts3D 4.0",
            "method": "tools/fma_uri_repro_map.py (frozen "
                      "targets, mechanical resolution) — checked "
                      "by tools/fma_uri_repro_check.py "
                      "(independent)",
            "rule": "lateralised records where the FMA carries "
                    "both sided classes (prefix or kidney-suffix "
                    "naming, IS-A parent-verified), one un-sided "
                    "record otherwise; any FMAID already "
                    "inventoried anywhere in the Body Model is "
                    "excluded and accounted with its owner",
            "source": "Foundational Model of Anatomy (FMA) "
                      "5.1.0, data/sources/fma-5.1.0/ (CC BY 4.0)",
        },
        "systems": {},
    }
    for system, cfg in SYSTEMS.items():
        result = build_system(system, cfg, classes, byname, owners,
                              report)
        probes = []
        for p in ABSENCE_PROBES[system]:
            hits = (byname.get(p.lower(), [])
                    + byname.get(f"left {p}".lower(), [])
                    + byname.get(f"right {p}".lower(), []))
            probes.append({"probe": p,
                           "preferred_name_hits": len(hits)})
        if result is not None:
            result["absence_probes"] = probes
            result["deferred"] = DEFERRED[system]
            artifact["systems"][system] = result
    if not report:
        with open(ART_PATH, "w") as f:
            json.dump(artifact, f, indent=1)
        print(f"accounting -> {ART_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
