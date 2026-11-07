#!/usr/bin/env python3
"""ANATOMICA integumentary + male reproductive FMA extension
builder — Milestone 38 (FMA concept intake #4, the final
intake of the Milestones 33–38 arc).

Extends the integumentary inventory with concept records for
everything below the skin shell that Milestone 15 proved
absent from BodyParts3D 4.0 (the layers and their strata, the
epidermal cells, the cutaneous sensory corpuscles, the hair
follicle apparatus, the cutaneous glands, the nail apparatus,
the hair specialisations, and — under Milestone 15's own
ownership adjudication — the mammary gland), and the
reproductive inventory with the male remainder Milestones 14
and 37 left: the duct system entire (the deferent duct and
its course segments, the ejaculatory duct, the epididymal and
seminal ducts), the testis interior and coverings, the
epididymis parts, the prostate parts and McNeal zones, the
spermatic cord and scrotum with their coverings and contents,
and the penis as an organ with its divisions.

Sibling of tools/fma_uri_repro_map.py (Milestone 37), same
discipline:

  - License: the FMA 5.1.0 release package ships the full
    text of CC BY 4.0 as its LICENSE file
    (data/sources/fma-5.1.0/, hash-pinned in that directory's
    provenance ledger at Milestone 33). The FMA is an
    ontology: it carries NO geometry. Every record written
    here is marked geometry-absent; no mesh, coordinate or
    clinical value is created by this tool.
  - A frozen target list per system (below) names the absent
    structures. Each target is resolved mechanically against
    fma.owl under the depth-aware parser (Milestone 36
    repair): lateralised records (left/right) where the FMA
    carries both sided classes — in the prefix form ('Left
    mammary gland'), the kidney-suffix form of Milestone 37,
    or the general suffix form ('Seminiferous tubule of left
    testis') — and each sided class is an IS-A child of the
    un-sided class (parent-verified). Otherwise one un-sided
    record keyed on the un-sided class.
  - Preferred names are read entity-decoded: the OWL text
    encodes an apostrophe as an XML entity
    (Meissner&apos;s corpuscle), and the record carries the
    decoded name, which is what the independent checker's
    XML parse reads.
  - Exclusion: any candidate whose FMAID already appears in
    ANY inventory record of the Body Model is excluded and
    reported with its owner. A target whose un-sided class
    is already inventoried is excluded outright (the
    Milestone 36 pineal pattern, generalised: the class is
    the record somewhere, as with the eyebrow, whose BP3D
    record is keyed on the class itself). Five
    integumentary/reproductive targets are frozen precisely
    so this rule fires on classes the modules already own.
  - Module boundaries follow the existing inventories'
    ownership and the modules' own censuses: the mammary
    gland is integumentary by Milestone 15's adjudication;
    the cremasteric and dartos muscles and the pampiniform
    plexus are recorded under reproductive with the boundary
    stated on the record (the muscular and cardiovascular
    modules carry no records for them — verified against
    their inventories; the Milestone 37 glomerular-arteriole
    pattern).
  - The merge is idempotent BY RECORD ID: this builder
    strips exactly the records its own target list can
    produce (computed before the merge) and re-appends them;
    the Milestone 37 records of the reproductive inventory
    and every BP3D record are left byte-identical in parsed
    form.
  - The per-system intake accounting is written to
    data/fma-intake-38.json (targets, verdicts, probe
    evidence, census deltas), alongside the oculomotor
    correction section written by
    tools/fma_oculomotor_correct.py.

Usage: fma_integ_male_map.py [--report]
Stdlib only.
"""
import glob as globmod
import html
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fma_uri_repro_map import parse_owl, group_path  # noqa: E402

SRC = os.path.join(ROOT, "data", "sources", "fma-5.1.0")
WORK_OWL = os.path.join(ROOT, "work", "fma", "fma.owl")
ART_PATH = os.path.join(ROOT, "data", "fma-intake-38.json")
SOURCE_TAG = "fma-5.1.0"
DATE = "2026-11-06"

VERIFY_FLAGS = [
    "geometry: absent — the FMA is an ontology and carries no mesh "
    "data; this record is concept-only until a geometry source clears "
    "the project's license and registration bars (Milestone 38)",
    "clinical: no clinical tranche has been authored for FMA-sourced "
    "records; no clinical values are entered",
]

# ---------------------------------------------------------------------
# Frozen target lists: (preferred-name target, subtree, note or None).
# Every name was verified present in fma.owl by probe before freezing
# (Milestone 38 build record), except the targets tagged "existing",
# which are frozen so the already-inventoried exclusion fires
# mechanically and is accounted, and 'Bulbourethral gland', which is
# frozen to record its not-in-fma verdict with evidence.
# ---------------------------------------------------------------------

INTEG_TARGETS = []
# Skin layers and strata (Milestone 15: absent entire)
for n in ["Epidermis", "Dermis", "Hypodermis"]:
    INTEG_TARGETS.append((n, "skin-layers", None))
INTEG_TARGETS.append((
    "Basal cell layer of epidermis", "skin-layers",
    "the FMA's class for the stratum basale of Milestone 15's "
    "clinical record (no class is named 'Stratum basale')"))
INTEG_TARGETS.append((
    "Prickle cell layer of epidermis", "skin-layers",
    "the FMA's class for the stratum spinosum of Milestone "
    "15's clinical record"))
INTEG_TARGETS.append((
    "Granular layer of epidermis", "skin-layers",
    "the FMA's class for the stratum granulosum of Milestone "
    "15's clinical record"))
INTEG_TARGETS.append((
    "Stratum lucidum of epidermis", "skin-layers",
    "the one stratum the FMA names in the classic Latin form"))
INTEG_TARGETS.append((
    "Horny layer of epidermis", "skin-layers",
    "the FMA's class for the stratum corneum of Milestone 15's "
    "clinical record"))
for n in ["Papillary layer of dermis", "Reticular layer of dermis"]:
    INTEG_TARGETS.append((n, "skin-layers", None))
INTEG_TARGETS.append((
    "Superficial fascia", "skin-layers",
    "the subcutaneous layer under its second name in "
    "Milestone 15's gap analysis; the release's deep fascial "
    "system is a separate filing (Milestone 15 sweep "
    "adjudication) and is not touched"))
# Skin regions (Milestone 15: 'scalp' zero-hit)
INTEG_TARGETS.append((
    "Skin of scalp", "skin-regions",
    "the scalp of Milestone 15's absence census, as skin; the "
    "class 'Scalp' (FMA46494) is a body-region aggregate, not "
    "skin, and is deferred"))
# Epidermal cells (Milestone 15: the cell names absent)
for n in ["Melanocyte", "Merkel cell", "Langerhans cell"]:
    INTEG_TARGETS.append((n, "cells", None))
INTEG_TARGETS.append((
    "Keratinized cell of epidermis", "cells",
    "the FMA carries no class named 'Keratinocyte' "
    "(absence-probed); this and the nonkeratinized cell are "
    "its epidermal keratinocyte classes"))
INTEG_TARGETS.append((
    "Nonkeratinized cell of epidermis", "cells",
    "the FMA carries no class named 'Keratinocyte' "
    "(absence-probed); this and the keratinized cell are its "
    "epidermal keratinocyte classes"))
# Cutaneous sensory structures (Milestone 15: pacinian,
# meissner zero-hit)
INTEG_TARGETS.append(("Pacinian corpuscle", "sensory", None))
INTEG_TARGETS.append((
    "Meissner's corpuscle", "sensory",
    "the lamellar/tactile corpuscle pair of Milestone 15's "
    "gap analysis; the OWL text encodes this class's "
    "preferred name with an XML entity for the apostrophe, "
    "and the record carries the decoded name"))
# Hair follicle apparatus (Milestone 15: follicle absent entire)
for n in ["Hair follicle", "Hair shaft", "Hair root",
          "Hair papilla", "Hair matrix", "Cortex of hair",
          "Cuticle of hair"]:
    INTEG_TARGETS.append((n, "appendage", None))
INTEG_TARGETS.append((
    "Bulb of hair follicle", "appendage",
    "the FMA's class for the hair bulb of Milestone 15's "
    "clinical record (no class is named 'Hair bulb')"))
INTEG_TARGETS.append((
    "Dermal papilla", "appendage",
    "the dermal papilla of the hair follicle; Milestone 15's "
    "gap analysis names 'the dermal papilla' absent"))
# Cutaneous glands (Milestone 15: no cutaneous gland of any kind)
for n in ["Sebaceous gland", "Sweat gland",
          "Eccrine sweat gland", "Apocrine sweat gland"]:
    INTEG_TARGETS.append((n, "glands", None))
# Nail apparatus (Milestone 15: the nail in every form absent)
for n in ["Nail", "Nail of finger", "Nail of toe",
          "Root of nail", "Nail matrix", "Lunule of nail",
          "Eponychium", "Hyponychium"]:
    INTEG_TARGETS.append((n, "nail", None))
INTEG_TARGETS.append((
    "Body of nail", "nail",
    "the FMA's class for the nail plate of Milestone 15's "
    "clinical record"))
INTEG_TARGETS.append((
    "Nail bed of finger", "nail",
    "the FMA carries the nail bed only per region — this "
    "generic and the toe generic, then per-digit classes "
    "(deferred); no class is named 'Nail bed'"))
INTEG_TARGETS.append((
    "Nail bed of toe", "nail",
    "the FMA carries the nail bed only per region — this "
    "generic and the finger generic, then per-digit classes "
    "(deferred); no class is named 'Nail bed'"))
# Hair specialisations (Milestone 15: eyelash, beard, vellus
# zero-hit)
for n in ["Eyelash", "Beard", "Vellus hair"]:
    INTEG_TARGETS.append((n, "appendage", None))
# The mammary gland (Milestone 15: absent under every name;
# ownership adjudicated to this module there)
INTEG_TARGETS.append((
    "Mammary gland", "mammary",
    "owned by this module under the Milestone 15 "
    "adjudication — a modified sweat gland; the "
    "counter-consideration (an accessory gland of the female "
    "reproductive system) is recorded on the clinical record "
    "organ.mammary-gland and stands"))
for n in ["Nipple", "Areola", "Lactiferous duct"]:
    INTEG_TARGETS.append((n, "mammary", None))
# Already-inventoried classes, frozen so the exclusion fires
# mechanically (the Milestone 36 pineal pattern)
for n, note in [
        ("Skin", "FMA7163 is this module's Milestone 15 BP3D "
                 "record"),
        ("Hair", "FMA53667 is this module's Milestone 15 BP3D "
                 "record"),
        ("Eyebrow", "FMA54237 is this module's Milestone 15 "
                    "BP3D record, keyed on the class itself")]:
    INTEG_TARGETS.append((n, "existing", note))

MALE_TARGETS = []
# The duct system (Milestone 14: 'the duct system is missing')
MALE_TARGETS.append((
    "Deferent duct", "male-pathway",
    "the FMA's preferred name for the ductus deferens of "
    "Milestone 14's gap analysis — 'ductus deferens' and "
    "'vas deferens' are this class's listed synonyms, and no "
    "class carries either as its preferred name"))
MALE_TARGETS.append((
    "Deferent duct proper", "male-pathway",
    "the deferent duct's main course segment in the FMA's "
    "subdivision of the duct"))
MALE_TARGETS.append((
    "Ampulla of deferent duct", "male-pathway",
    "the FMA's name form for the ampulla of ductus deferens"))
for n in ["Scrotal part of deferent duct",
          "Funicular part of deferent duct",
          "Inguinal part of deferent duct",
          "Pelvic part of deferent duct"]:
    MALE_TARGETS.append((
        n, "male-pathway",
        "one of the deferent duct's four course segments in "
        "the FMA — the ductus deferens segments of this "
        "intake's scope"))
MALE_TARGETS.append(("Ejaculatory duct", "male-pathway", None))
MALE_TARGETS.append((
    "Efferent ductule", "male-pathway",
    "the FMA's singular class name for the efferent ductules "
    "of Milestone 14's male pathway"))
MALE_TARGETS.append(("Duct of epididymis", "male-pathway", None))
MALE_TARGETS.append(("Duct of seminal vesicle",
                     "male-pathway", None))
# Testis interior and coverings (Milestone 14: scrotum,
# tunica, seminiferous, rete testis zero-hit)
MALE_TARGETS.append((
    "Seminiferous tubule of testis", "testis-interior",
    "the FMA's name form for the seminiferous tubule (no "
    "class is named 'Seminiferous tubule')"))
MALE_TARGETS.append((
    "Straight seminiferous tubule of testis", "testis-interior",
    "the straight tubules (tubuli recti) of Milestone 14's "
    "male pathway, recorded separately because the pathway "
    "names them as a station"))
MALE_TARGETS.append(("Rete testis", "testis-interior", None))
for n in ["Lobule of testis", "Septum of testis"]:
    MALE_TARGETS.append((n, "testis-interior", None))
MALE_TARGETS.append((
    "Mediastinum of testis", "testis-interior",
    "the FMA's name form ('Mediastinum testis' names no "
    "class)"))
MALE_TARGETS.append(("Tunica albuginea of testis",
                     "testis-interior", None))
MALE_TARGETS.append((
    "Tunica vaginalis of testis", "testis-interior",
    "the FMA's name form (no class is named 'Tunica "
    "vaginalis')"))
for n in ["Visceral layer of tunica vaginalis of testis",
          "Parietal layer of tunica vaginalis of testis"]:
    MALE_TARGETS.append((n, "testis-interior", None))
# Epididymis parts
for n in ["Head of epididymis", "Body of epididymis",
          "Tail of epididymis"]:
    MALE_TARGETS.append((n, "epididymis-parts", None))
# Prostate parts and zones (Milestone 14 clinical record: the
# McNeal zones in order)
for n in ["Apex of prostate", "Base of prostate",
          "Lobe of prostate", "Central zone of prostate",
          "Peripheral zone of prostate"]:
    MALE_TARGETS.append((n, "prostate-parts", None))
MALE_TARGETS.append((
    "Transition zone of prostate", "prostate-parts",
    "the FMA's class for the transitional zone of McNeal "
    "named in Milestone 14's clinical record"))
MALE_TARGETS.append((
    "Anterior fibromuscular stroma of prostate",
    "prostate-parts",
    "the FMA's spelling ('fibromuscular') of the anterior "
    "fibromuscular stroma"))
# Spermatic cord, scrotum, coverings and contents (Milestone
# 14: spermatic, scrotum, dartos, cremaster zero-hit)
for n in ["Spermatic cord", "Scrotum",
          "External spermatic fascia", "Internal spermatic "
          "fascia", "Cremasteric fascia"]:
    MALE_TARGETS.append((n, "cord-scrotum", None))
MALE_TARGETS.append((
    "Cremasteric muscle", "cord-scrotum",
    "boundary: a muscle, recorded here because Milestone "
    "14's male-line census names the cremaster absent and "
    "the muscular module carries no cremaster record "
    "(verified against its inventory); the FMA's class name "
    "for the cremaster"))
MALE_TARGETS.append((
    "Dartos muscle", "cord-scrotum",
    "boundary: the tunica dartos of the scrotum, named "
    "absent on Milestone 14's male line; the muscular module "
    "carries no dartos record (verified against its "
    "inventory)"))
MALE_TARGETS.append((
    "Pampiniform plexus", "cord-scrotum",
    "boundary: a venous plexus, recorded here as a "
    "spermatic cord content; the cardiovascular module "
    "carries no pampiniform record (verified against its "
    "inventory) — the Milestone 37 glomerular-arteriole "
    "pattern"))
# The penis and its divisions (Milestone 14: the penis as an
# organ concept absent — only its erectile parts exist)
MALE_TARGETS.append((
    "Penis", "penis-parts",
    "the organ class itself: Milestone 14 found the penis "
    "in the release only as its erectile parts and its "
    "cardiovascular vessels, with no organ concept"))
for n in ["Root of penis", "Body of penis", "Bulb of penis",
          "Neck of glans penis", "Fascia of penis"]:
    MALE_TARGETS.append((n, "penis-parts", None))
MALE_TARGETS.append((
    "Prepuce of penis", "penis-parts",
    "the FMA's class for the prepuce (no class is named "
    "'Prepuce')"))
MALE_TARGETS.append((
    "Frenulum of penis", "penis-parts",
    "the FMA's class for the frenulum of the prepuce"))
MALE_TARGETS.append((
    "Corona of glans penis", "penis-parts",
    "the FMA's name form for the corona of the glans"))
# Already-inventoried classes, frozen for the exclusion
for n, note in [
        ("Testis", "the testis class (FMA7210) and its two "
                   "instances are this module's Milestone 14 "
                   "BP3D records"),
        ("Epididymis", "the epididymis class (FMA18255) and "
                       "its two instances are this module's "
                       "Milestone 14 BP3D records"),
        ("Seminal vesicle", "the seminal vesicle class "
                            "(FMA19386) and its two instances "
                            "are this module's Milestone 14 "
                            "BP3D records"),
        ("Prostate", "FMA9600 is this module's Milestone 14 "
                     "BP3D record"),
        ("Glans penis", "FMA18247 is this module's Milestone "
                        "14 BP3D record (its zone class "
                        "FMA20247 is carried as class_concept_id)")]:
    MALE_TARGETS.append((n, "existing", note))
# Frozen to record its verdict: the FMA carries no class for
# the gland itself (see DEFERRED for its duct).
MALE_TARGETS.append((
    "Bulbourethral gland", "male-glands",
    "frozen to record the verdict with evidence: the FMA "
    "carries this gland's duct classes (FMA20091 and its "
    "sided forms) but no class for the gland itself — a gap "
    "inside the source, of the same kind as the paraurethral "
    "glands at Milestone 37"))

SYSTEMS = {
    "integumentary": {
        "inventory": "data/integumentary/integumentary-inventory.json",
        "geometry": "data/integumentary/integumentary-geometry.json",
        "prefix": "integ",
        "targets": INTEG_TARGETS,
        "sex_line": None,
        "line_of": {
            "skin-layers": "skin", "skin-regions": "skin",
            "cells": "skin", "sensory": "skin",
            "appendage": "appendage", "glands": "appendage",
            "nail": "appendage", "mammary": "appendage",
        },
    },
    "reproductive": {
        "inventory": "data/reproductive/reproductive-inventory.json",
        "geometry": "data/reproductive/reproductive-geometry.json",
        "prefix": "repro",
        "targets": MALE_TARGETS,
        "sex_line": "male",
        "line_of": None,
    },
}

# Absence probes: names with NO class in the FMA under the probed
# preferred name or its Left/Right prefix forms — computed, not
# asserted, and written into the accounting artifact as evidence.
ABSENCE_PROBES = {
    "integumentary": [
        "Stratum basale", "Stratum spinosum",
        "Stratum granulosum", "Stratum corneum", "Keratinocyte",
        "Subcutaneous tissue", "Nail bed", "Lunule", "Lunula",
        "Hair bulb", "Fingernail", "Toenail", "Arrector pili",
        "Arrector pili muscle", "Cuticle", "Lanugo",
        "Scalp hair", "Free nerve ending", "Tactile corpuscle",
        "Lamellar corpuscle", "Meissner corpuscle",
        "Dermal papilla of hair",
    ],
    "reproductive": [
        "Ductus deferens", "Vas deferens",
        "Ampulla of ductus deferens", "Seminiferous tubule",
        "Bulbourethral gland", "Crus of penis", "Prepuce",
        "Frenulum of prepuce", "Corona of glans",
        "Tunica vaginalis", "Mediastinum testis",
        "Transitional zone of prostate", "Straight tubule",
        "Tubuli recti", "Cremaster",
    ],
}

# Census-named structures that EXIST in the FMA but are not targets
# of this intake, with the reason (recorded, not silent).
DEFERRED = {
    "integumentary": [
        {"names": "Scalp (FMA46494)",
         "reason": "a body-region aggregate (skin, fascia and "
                   "muscle of the scalp region), not a skin "
                   "class; the skin of the scalp is recorded"},
        {"names": "Ceruminous gland (FMA323077)",
         "reason": "a regional sweat-gland specialisation of "
                   "the external acoustic meatus, below this "
                   "intake's granularity; the sweat gland "
                   "generic and its eccrine/apocrine types are "
                   "recorded"},
        {"names": "Anagen / catagen / telogen hair follicle "
                  "(FMA70679 / FMA71072 / FMA70996)",
         "reason": "growth-cycle states of the one follicle, "
                   "not parts or kinds of it; the follicle is "
                   "recorded"},
        {"names": "Per-digit nail classes (nail beds and "
                  "lunules of the individual digits)",
         "reason": "the FMA subdivides the nail apparatus "
                   "per digit below the finger/toe generics, "
                   "which are recorded"},
        {"names": "Gland of epidermis (FMA59153)",
         "reason": "a generic grouping class over the "
                   "cutaneous glands; the sebaceous and sweat "
                   "gland classes are recorded directly"},
    ],
    "reproductive": [
        {"names": "Duct of bulbourethral gland (FMA20091) and "
                  "its sided classes",
         "reason": "the gland itself has no FMA class (the "
                   "not-in-fma verdict recorded for "
                   "'Bulbourethral gland'); its duct alone is "
                   "not recorded — the Milestone 37 "
                   "paraurethral-gland pattern. The gland "
                   "remains concept-blocked inside the source"},
        {"names": "Wall / lumen / mucosa / adventitia layer "
                  "classes of the deferent duct, epididymis "
                  "and seminal vesicle",
         "reason": "histological layer classes below this "
                   "intake's granularity; the organs, their "
                   "ducts and their named parts are recorded"},
        {"names": "Convoluted seminiferous tubule of testis "
                  "(FMA19826) and its sided classes",
         "reason": "a subdivision of the recorded seminiferous "
                   "tubule generic; the straight tubule is "
                   "recorded separately because Milestone 14's "
                   "pathway names it as a station"},
        {"names": "Appendix of epididymis (FMA18268) and the "
                  "appendix of testis",
         "reason": "vestigial remnants, not named in "
                   "Milestone 14's census"},
        {"names": "Diverticulum / wall / lumen classes of the "
                  "seminal vesicle",
         "reason": "sub-organ classes below this intake's "
                   "granularity; the gland is a Milestone 14 "
                   "record and its duct is recorded here"},
    ],
}


def slug(name):
    s = name.lower().replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def load_classes():
    """Depth-aware parse with preferred names and labels
    entity-decoded (the OWL text writes an apostrophe as an
    XML entity; the decoded form is the name the XML-based
    checker reads)."""
    classes = parse_owl(WORK_OWL)
    for c in classes.values():
        for k in ("name", "label"):
            if c.get(k):
                c[k] = html.unescape(c[k])
    return classes


def display_name(fid, classes):
    c = classes.get(fid) or {}
    return c.get("name") or c.get("label")


def sided_candidates(target, unsided_fid, byname, classes):
    """Prefix and general-suffix naming patterns,
    parent-verified. Returns (form, [(side, fid), ...]) or
    (None, [])."""
    forms = [("prefix", f"Left {target}", f"Right {target}")]
    if " of " in target:
        head, tail = target.rsplit(" of ", 1)
        forms.append(("suffix", f"{head} of left {tail}",
                      f"{head} of right {tail}"))
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


def producible_ids(cfg, classes, byname):
    """Every record id this builder can produce for a system —
    computed from the frozen targets before the merge, so the
    merge can strip exactly its own prior output (the
    Milestone 38 records) and nothing else."""
    ids = set()
    for target, _subtree, _note in cfg["targets"]:
        unsided = byname.get(target.lower(), [])
        unsided_fid = unsided[0] if unsided else None
        _form, sided = sided_candidates(target, unsided_fid,
                                        byname, classes)
        if sided:
            for side, _fid in sided:
                ids.add(f"{cfg['prefix']}.{side}-{slug(target)}")
        elif unsided_fid:
            name = display_name(unsided_fid, classes)
            ids.add(f"{cfg['prefix']}.{slug(name)}")
    return ids


def global_exclusions(own_ids_by_file):
    """fid -> [owners] over every inventory record of the Body
    Model. This builder's OWN records — the producible ids in
    the two inventories it rebuilds — never exclude: they are
    stripped and re-derived on every run, which is what makes
    the builder idempotent."""
    owners = defaultdict(list)
    own_files = {os.path.join(ROOT, cfg["inventory"]): ids
                 for cfg, ids in own_ids_by_file}
    for path in sorted(globmod.glob(
            os.path.join(ROOT, "data", "*", "*-inventory.json"))):
        doc = json.load(open(path))
        system = os.path.basename(os.path.dirname(path))
        own = own_files.get(path, set())
        for r in doc.get("records", []):
            if r["record_id"] in own:
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


def build_system(system, cfg, classes, byname, owners, own_ids,
                 report):
    inv = json.load(open(os.path.join(ROOT, cfg["inventory"])))
    geo = json.load(open(os.path.join(ROOT, cfg["geometry"])))
    kept_records = [r for r in inv["records"]
                    if r["record_id"] not in own_ids]
    before_fma = [r for r in inv["records"]
                  if r.get("source") == SOURCE_TAG
                  and r["record_id"] not in own_ids]
    kept_ids = {r["record_id"] for r in kept_records}

    new_records = []
    entries = []
    for target, subtree, note in cfg["targets"]:
        unsided = byname.get(target.lower(), [])
        unsided_fid = unsided[0] if unsided else None
        # exclusion first: the un-sided class is already
        # inventoried somewhere in the Body Model
        if unsided_fid is not None and \
                owners.get(f"FMA{unsided_fid}"):
            entries.append({
                "target": target, "subtree": subtree,
                "verdict": "excluded",
                "evidence": f"FMA{unsided_fid} already "
                            f"inventoried ("
                            f"{', '.join(dict.fromkeys(owners[f'FMA{unsided_fid}']))})",
                "records": []})
            continue
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
            assert rid not in kept_ids, \
                f"record id collision: {rid}"
            assert all(x["record_id"] != rid
                       for x in new_records), rid
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
                rec["sex_line"] = cfg["sex_line"]
            if cfg["line_of"] is not None:
                rec["line"] = cfg["line_of"][subtree]
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
                "fmaids": [r["concept_ids"][0]
                           for r in new_records
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

    inv["records"] = kept_records + new_records
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
    if cfg["line_of"] is not None:
        by_line = {}
        for r in inv["records"]:
            by_line[r["line"]] = by_line.get(r["line"], 0) + 1
        inv["meta"]["records_by_line"] = by_line
    ext_block = {
        "milestone": 38,
        "source": "Foundational Model of Anatomy (FMA) 5.1.0, "
                  "data/sources/fma-5.1.0/ (CC BY 4.0)",
        "records_added": len(new_records),
        "geometry_absent": len(new_records),
        "counting_convention": "one record per lateralised "
                               "instance where the FMA carries "
                               "both sided classes (prefix or "
                               "suffix naming, IS-A "
                               "parent-verified); one record "
                               "keyed on the un-sided class "
                               "otherwise — mirroring the "
                               "Milestone 33/36/37 convention",
        "accounting": "data/fma-intake-38.json",
    }
    if system == "reproductive":
        # the Milestone 37 fma_extension block stands; this
        # intake is the second extension of the same file
        inv["meta"]["fma_extension_38"] = ext_block
    else:
        inv["meta"]["fma_extension"] = ext_block
    with open(os.path.join(ROOT, cfg["inventory"]), "w") as f:
        json.dump(inv, f, indent=1)

    geo_kept = [r for r in geo["records"]
                if r["record_id"] not in own_ids]
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
        if cfg["line_of"] is not None:
            g["line"] = r["line"]
        g["concept_ids"] = r["concept_ids"]
        g["concept_names"] = [r["name"]]
        g["source"] = SOURCE_TAG
        g["geometry_status"] = (
            "absent — FMA concept record; the FMA "
            "carries no mesh data (Milestone 38)")
        g["isa_meshes"] = []
        g["partof_meshes"] = []
        g["totals"] = {"isa": {"files": 0, "vertices": 0, "faces": 0},
                       "partof": {"files": 0, "vertices": 0,
                                  "faces": 0},
                       "combined_files": 0}
        g["bbox_isa"] = None
        g["bbox_partof"] = None
        geo_new.append(g)
    geo["records"] = geo_kept + geo_new
    cov = dict(geo["meta"]["coverage"])
    cov["records"] = len(geo["records"])
    cov["records_with_meshes"] = sum(
        1 for g in geo["records"]
        if g["isa_meshes"] or g["partof_meshes"])
    cov["records_without_meshes"] = len(geo["records"]) - \
        cov["records_with_meshes"]
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
    if "by_line" in cov:
        by_line = {k: {"records": 0, "records_with_meshes": 0}
                   for k in cov["by_line"]}
        for g in geo["records"]:
            line = by_line.setdefault(
                g["line"], {"records": 0,
                            "records_with_meshes": 0})
            line["records"] += 1
            if g["isa_meshes"] or g["partof_meshes"]:
                line["records_with_meshes"] += 1
        cov["by_line"] = by_line
    geo["meta"]["coverage"] = cov
    with open(os.path.join(ROOT, cfg["geometry"]), "w") as f:
        json.dump(geo, f, indent=1)
    print(f"[{system}] inventory records: {len(kept_records)} kept "
          f"({len(before_fma)} prior FMA) + {len(new_records)} new "
          f"= {len(inv['records'])}")
    return {
        "records_before": len(kept_records),
        "records_after": len(inv["records"]),
        "records_added": len(new_records),
        "prior_fma_records": len(before_fma),
        "targets": entries,
    }


def main():
    report = "--report" in sys.argv
    if not os.path.exists(WORK_OWL):
        import zipfile
        os.makedirs(os.path.dirname(WORK_OWL), exist_ok=True)
        with zipfile.ZipFile(os.path.join(SRC, "fma.zip")) as zf:
            zf.extract("fma.owl", os.path.dirname(WORK_OWL))
    classes = load_classes()
    byname = defaultdict(list)
    for fid, c in classes.items():
        if c["name"]:
            byname[c["name"].lower()].append(fid)
    own_ids = {system: producible_ids(cfg, classes, byname)
               for system, cfg in SYSTEMS.items()}
    owners = global_exclusions(
        [(cfg, own_ids[system]) for system, cfg in SYSTEMS.items()])

    artifact = {}
    if os.path.exists(ART_PATH):
        artifact = json.load(open(ART_PATH))
    artifact["meta"] = {
        "milestone": "M38", "date": DATE,
        "scope": "FMA 5.1.0 concept intake #4 (final): the "
                 "integumentary layers and appendages below "
                 "the skin shell, and the male reproductive "
                 "remainder — the structures Milestones 15 and "
                 "14 proved absent from BodyParts3D 4.0; plus "
                 "the oculomotor name-provenance correction "
                 "(section written by "
                 "tools/fma_oculomotor_correct.py)",
        "method": "tools/fma_integ_male_map.py (frozen "
                  "targets, mechanical resolution) — checked "
                  "by tools/fma_integ_male_check.py "
                  "(independent)",
        "rule": "lateralised records where the FMA carries "
                "both sided classes (prefix or suffix naming, "
                "IS-A parent-verified), one un-sided record "
                "otherwise; any FMAID already inventoried "
                "anywhere in the Body Model is excluded and "
                "accounted with its owner",
        "source": "Foundational Model of Anatomy (FMA) "
                  "5.1.0, data/sources/fma-5.1.0/ (CC BY 4.0)",
    }
    artifact.setdefault("systems", {})
    for system, cfg in SYSTEMS.items():
        result = build_system(system, cfg, classes, byname,
                              owners, own_ids[system], report)
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
