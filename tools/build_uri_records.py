#!/usr/bin/env python3
"""ANATOMICA Milestone 12, step 2: urinary system clinical tranche.

Builds data/urinary/urinary.json from the inventory
(data/urinary/urinary-inventory.json, produced by
tools/uri_map.py).

FIELD-SOURCING RULE (precision law, same discipline as Milestones
4, 5, 9, 10 and 11): a clinical value is entered only when it
comes from a source actually consulted during this build session,
and the record cites that source per field in its `sources` map.
Anything not sourced is null plus an explicit `verify` entry. TA
names were not given by the consulted sources and are null +
verify-flagged throughout. The renal and suprarenal vessels are
cardiovascular module records (Milestone 5; artery.renal-artery
and vein.renal-vein clinical records); this tranche cites them in
notes and fields rather than duplicating them. The adrenal glands
are filed by the source release under the endocrine system (see
the inventory's adrenal_filing finding) and get no record here;
the endocrine module owns them.

The defining fact of this module: BodyParts3D 4.0 decomposes NO
urinary organ. There is no kidney part, bladder part, ureter part
or urethra part concept anywhere in the release (74 absence probes
return zero hits over the six tables — see the inventory). The
internal anatomy below is therefore sourced text carried on the
six whole-organ inventory records, and the nephron and urinary
pathway records link the organs they run through while carrying
the recorded absence for their own stations.

Sources (consulted in-session; TeachMeAnatomy abbreviated TMA):
  S1  TMA, "The Kidneys" (bilateral bean-shaped retroperitoneal
      organs, T12-L3, right lower due to the liver, ~three
      vertebrae long; layers deep to superficial — renal capsule,
      perirenal fat, renal fascia/Gerota's enclosing kidneys and
      suprarenal glands, pararenal fat; cortex and medulla,
      pyramids, papilla, minor calyx -> major calyx -> renal
      pelvis; hilum as gateway for vessels and ureter; anterior
      and posterior relations tables; renal arteries from the
      aorta immediately distal to the SMA, anterior division 75%
      / posterior 25%, five segmental end arteries, interlobar ->
      arcuate -> interlobular -> afferent arteriole -> glomerulus
      -> efferent arteriole; renal veins anterior at the hilum to
      the IVC, left vein longer anterior to the aorta; lymph to
      lateral aortic nodes; accessory arteries in ~25%)
  S2  TMA, "The Ureters" (~25 cm muscular tubes; ureteropelvic
      junction, descent on psoas major, pelvic brim crossing at
      the sacroiliac joints over the common iliac bifurcation,
      lateral pelvic walls, turn at the ischial spines, oblique
      entry into the bladder wall as a one-way valve; the three
      narrowings — UPJ, pelvic inlet, UVJ — with recent evidence
      that impaction predominates at the upper ureter and UVJ;
      abdominal supply from renal/gonadal/aortic branches, pelvic
      supply from superior and inferior vesical arteries; plexus
      innervation, sensory T11-L2; under the uterine artery in
      females, crossed by the vas deferens in males)
  S3  TMA, "The Urinary Bladder" (storage 400-600 mL with rugae;
      apex/median umbilical ligament, body, fundus, neck; trigone
      within the fundus, smooth-walled, of mesonephric-duct
      origin; detrusor smooth muscle in multiple directions;
      internal sphincter — circular smooth in males, functional
      in females; external sphincter skeletal and voluntary;
      superior vesical artery from the internal iliac, inferior
      vesical in males / vaginal in females; vesical venous plexus
      to internal iliac veins; lymph external iliac /
      internal iliac, sacral, common iliac; sympathetic hypogastric
      T12-L2 relaxes detrusor, parasympathetic pelvic S2-S4
      contracts it, pudendal S2-S4 to the external sphincter)
  S4  OpenStax, Anatomy and Physiology 2e, section 25.2 "Gross
      Anatomy of Urine Transport" (the urethra is the only urinary
      structure differing significantly between the sexes; female
      ~4 cm, orifice in the anterior vaginal wall inferior to the
      clitoris and superior to the introitus; male averaging 20 cm
      in four regions — preprostatic, prostatic, membranous,
      spongy/penile; bladder posterior to the pubic bone, anterior
      to the rectum, partially retroperitoneal, detrusor of
      crisscrossing bands, volumes to 500-600 mL; ureters ~30 cm,
      peristaltic propulsion, oblique entry a physiological
      sphincter; trigone defined by the two ureteral openings and
      the urethral orifice)
  S5  OpenStax, Anatomy and Physiology 2e, section 25.2
      "Microscopic Anatomy of the Kidney: Anatomy of the Nephron"
      (nephron the functional unit — filtration, reabsorption,
      secretion; glomerulus a high-pressure fenestrated capillary
      bed between afferent and efferent arterioles; glomerular
      (Bowman's) capsule captures the filtrate; corpuscle =
      glomerulus + capsule; tubule order PCT -> loop of Henle ->
      DCT -> collecting ducts shared by many nephrons; cortical
      nephrons with short loops, ~15% juxtamedullary with long
      loops deep into the medulla; efferent arteriole ->
      peritubular capillaries, vasa recta for juxtamedullary
      nephrons; juxtaglomerular apparatus with the macula densa)
  S6  OpenStax, Anatomy and Physiology 2e, section 25.3 "Gross
      Anatomy of the Kidney" (open mirror consulted in-session:
      renal columns of cortex radiate through the medulla
      separating the pyramids and papillae and dividing the kidney
      into 6-8 lobes; papillae are bundles of collecting ducts
      transporting urine to the calyces; the renal pelvis is
      formed from the major and minor calyces in the hilum and
      funnels urine by peristalsis into the ureter)

Record types and fields:
  organ (kidney, ureter, urinary bladder): type-specific fields
    with per-type core/soft tiers (documented at each call).
  structure (nephron, urethra): type-specific fields, core/soft.
  pathway (the urinary pathway): sequence, function. Core = both.
Tiers: A = every field sourced; B = a soft field null + flagged;
C = a core field null + flagged (the Milestone 11 finish() rule).

Geometry linkage: clinical records link inventory records by exact
record name. The nephron links the two kidney records its geometry
would subdivide (its own stations carry the recorded absence); the
pathway links all six organ records.
"""

import json
import os
from collections import Counter

PROJECT = "/home/hatch/workspace/anatomica-project"
INV_PATH = os.path.join(PROJECT, "data/urinary/urinary-inventory.json")
OUT_PATH = os.path.join(PROJECT, "data/urinary/urinary.json")

inv = json.load(open(INV_PATH, encoding="utf-8"))
inv_by_name = {}
for r in inv["records"]:
    inv_by_name.setdefault(r["name"], []).append(r["record_id"])

SOURCES = {
    "S1": "TeachMeAnatomy, 'The Kidneys' (teachmeanatomy.info)",
    "S2": "TeachMeAnatomy, 'The Ureters' (teachmeanatomy.info)",
    "S3": "TeachMeAnatomy, 'The Urinary Bladder' "
          "(teachmeanatomy.info)",
    "S4": "OpenStax, Anatomy and Physiology 2e, section 25.2 "
          "'Gross Anatomy of Urine Transport'",
    "S5": "OpenStax, Anatomy and Physiology 2e, section 25.2 "
          "'Microscopic Anatomy of the Kidney: Anatomy of the "
          "Nephron'",
    "S6": "OpenStax, Anatomy and Physiology 2e, section 25.3 "
          "'Gross Anatomy of the Kidney'",
}

records = []
link_failures = []

ABSENCE = ("no BP3D concept: this structure has no concept in the "
           "BodyParts3D 4.0 release (see the inventory gap "
           "analysis); the record is sourced text without geometry")


def link(rec_id, names):
    out = []
    for n in names:
        ids = inv_by_name.get(n)
        if not ids:
            link_failures.append((rec_id, n))
        else:
            out.extend(ids)
    return sorted(set(out))


def finish(rec, fields, core, soft, rec_id):
    """Sourcing discipline: values need citations, nulls need
    verify flags, empty geometry links need a recorded absence,
    tier from which fields are flagged."""
    src = rec["sources"]
    ver = rec["verify"]
    if not any(v.startswith("ta_name:") for v in ver):
        ver.append("ta_name: not given by consulted sources - verify")
    for f in fields:
        if rec[f] is None and not any(v.startswith(f + ":") for v in ver):
            ver.append(f"{f}: not sourced from consulted sources - verify")
        if rec[f] is not None and f not in src:
            raise SystemExit(f"{rec_id}: field {f} has a value but no source")
    if not rec["geometry_record_ids"] and \
            not any(v.startswith("no BP3D concept") for v in ver):
        raise SystemExit(f"{rec_id}: empty geometry link without "
                         "a recorded absence")
    if any(rec[f] is None for f in core):
        rec["sourcing_tier"] = "C"
    elif any(rec[f] is None for f in soft):
        rec["sourcing_tier"] = "B"
    else:
        rec["sourcing_tier"] = "A"
    records.append(rec)


def base(rec_id, name, rtype, group, names, verify=None, note=None):
    return {
        "id": rec_id, "name": name, "type": rtype, "group": group,
        "ta_name": None,
        "sources": {}, "verify": list(verify or []),
        "note": note,
        "geometry_record_ids": link(rec_id, names),
    }


def typed(rec_id, name, rtype, group, names, fields, sources, core,
          soft, verify=None, note=None):
    rec = base(rec_id, name, rtype, group, names, verify, note)
    rec.update(fields)
    rec["sources"] = dict(sources or {})
    finish(rec, list(fields), core=core, soft=soft, rec_id=rec_id)


# ------------------------------------------------------------------
# Kidney (organ): the release carries the two whole kidneys only;
# every internal field below is sourced text on that geometry
# ------------------------------------------------------------------
typed(
    "organ.kidney", "Kidney", "organ", "Kidney",
    ["right kidney", "left kidney"],
    fields={
        "position":
            "Bilateral bean-shaped organs, reddish-brown, in the "
            "posterior abdomen; they lie retroperitoneally either "
            "side of the vertebral column, typically extending "
            "from T12 to L3, the right kidney often slightly lower "
            "due to the presence of the liver; each kidney is "
            "approximately three vertebrae in length.",
        "coverings":
            "Deep to superficial: (1) renal capsule — a tough "
            "fibrous capsule; (2) perirenal fat — a collection of "
            "extraperitoneal fat; (3) renal fascia (Gerota's "
            "fascia) — encloses the kidneys and the suprarenal "
            "glands; (4) pararenal fat — mainly on the "
            "posterolateral aspect of the kidney.",
        "internal_structure":
            "The renal parenchyma divides into an outer cortex "
            "and an inner medulla. The cortex extends into the "
            "medulla (the renal columns), dividing it into "
            "triangular renal pyramids and separating the "
            "pyramids and renal papillae; the columns and "
            "pyramids together divide the kidney into 6-8 lobes. "
            "The apex of each pyramid is a renal papilla, and the "
            "papillae are bundles of collecting ducts that "
            "transport urine made by the nephrons to the calyces.",
        "drainage_sequence":
            "Renal papilla -> minor calyx (each papilla is "
            "associated with a minor calyx, which collects urine "
            "from the pyramid) -> major calyx (several minor "
            "calices merge) -> renal pelvis (the flattened, "
            "funnel-shaped expansion formed from the major and "
            "minor calyces within the hilum) -> ureter.",
        "hilum":
            "A deep fissure on the medial margin of each kidney, "
            "the gateway into the organ: normally the renal "
            "vessels and the ureter enter and exit via the hilum. "
            "The renal veins leave the hilum anteriorly to the "
            "renal arteries.",
        "arterial_supply":
            "Via the renal arteries (cardiovascular module "
            "records artery.renal-artery), arising directly from "
            "the abdominal aorta immediately distal to the origin "
            "of the superior mesenteric artery; the right renal "
            "artery is longer and crosses the inferior vena cava "
            "posteriorly. At the hilum the artery forms an "
            "anterior division (75% of supply) and a posterior "
            "division (25%), from which five segmental arteries "
            "originate; the segmental branches are end arteries "
            "with no communication between vessels. Intrarenal "
            "sequence: segmental -> interlobar (either side of "
            "every pyramid) -> arcuate -> interlobular -> "
            "afferent arteriole -> glomerulus -> efferent "
            "arteriole. Accessory renal arteries are common "
            "(in about 25% of patients).",
        "venous_drainage":
            "Via the left and right renal veins (cardiovascular "
            "module record vein.renal-vein), leaving the hilum "
            "anterior to the renal arteries and emptying directly "
            "into the inferior vena cava; the left renal vein is "
            "longer and travels anterior to the abdominal aorta "
            "below the origin of the superior mesenteric artery.",
        "lymphatics":
            "Lymph from the kidney drains into the lateral aortic "
            "(para-aortic) lymph nodes, located at the origin of "
            "the renal arteries.",
        "relations":
            "Anterior — left kidney: suprarenal gland, spleen, "
            "stomach, pancreas, left colic flexure, jejunum; "
            "right kidney: suprarenal gland, liver, duodenum, "
            "right colic flexure. Posterior — both: diaphragm, "
            "psoas major, quadratus lumborum, transversus "
            "abdominis, and the subcostal, iliohypogastric and "
            "ilioinguinal nerves; the left kidney also the 11th "
            "and 12th ribs, the right kidney the 12th rib.",
    },
    sources={
        "position": ["S1"], "coverings": ["S1"],
        "internal_structure": ["S1", "S6"],
        "drainage_sequence": ["S1", "S6"], "hilum": ["S1"],
        "arterial_supply": ["S1"], "venous_drainage": ["S1"],
        "lymphatics": ["S1"], "relations": ["S1"],
    },
    core=["position", "coverings", "internal_structure",
          "drainage_sequence"],
    soft=["hilum", "arterial_supply", "venous_drainage",
          "lymphatics", "relations"],
    verify=[
        "internal_structure: no BP3D concept exists for any "
        "internal kidney structure (cortex, medulla, pyramid, "
        "papilla, column, pelvis, calyx — 74-probe gap analysis "
        "in the inventory); the fields are sourced text on the "
        "two whole-kidney geometry records",
    ],
    note="The adrenal (suprarenal) glands sit immediately "
         "superior to the kidneys within a separate envelope of "
         "the renal fascia (S1). The source release files them "
         "under the endocrine system, not this module — see the "
         "inventory's adrenal_filing finding; they are endocrine "
         "module records, cross-referenced, never duplicated "
         "here. The renal vessels are cardiovascular module "
         "records, cited per field.",
)

# ------------------------------------------------------------------
# Nephron (structure): no concept, no geometry — sourced text
# ------------------------------------------------------------------
typed(
    "structure.nephron", "Nephron", "structure", "Kidney",
    ["right kidney", "left kidney"],
    fields={
        "definition":
            "The functional unit of the kidney: a renal corpuscle "
            "and a specialised tubule, with its own blood supply. "
            "Nephrons cleanse the blood of toxins and balance the "
            "constituents of the circulation to homeostatic set "
            "points through filtration, reabsorption and "
            "secretion; the filtrate they modify becomes urine.",
        "segments_in_order": [
            "renal corpuscle (glomerulus within the glomerular "
            "capsule)",
            "proximal convoluted tubule (PCT)",
            "loop of Henle (descending and ascending limbs)",
            "distal convoluted tubule (DCT)",
            "collecting duct (a common duct shared by many "
            "nephrons, draining to the renal papilla)",
        ],
        "corpuscle":
            "The glomerulus is a high-pressure capillary bed of "
            "fenestrated capillaries between the afferent and "
            "efferent arterioles. The glomerular (Bowman's) "
            "capsule surrounds it, captures the filtrate and "
            "directs it to the PCT; glomerulus and capsule "
            "together form the renal corpuscle.",
        "types":
            "All glomeruli lie in the cortex. Cortical nephrons "
            "have short loops of Henle that do not dip far beyond "
            "the cortex; about 15 percent of nephrons are "
            "juxtamedullary, with very long loops extending deep "
            "into the medulla. Blood exits the glomerulus into "
            "the efferent arteriole, which forms the peritubular "
            "capillary network around the tubule; for "
            "juxtamedullary nephrons the straight capillary "
            "portion following the loop deep into the medulla is "
            "the vasa recta.",
        "juxtaglomerular_apparatus":
            "Lying just outside the glomerular capsule: where the "
            "afferent and efferent arterioles enter and leave the "
            "capsule, the initial part of the DCT comes into "
            "direct contact with the arterioles, and the DCT "
            "wall there forms the macula densa, a part of the "
            "juxtaglomerular apparatus (JGA).",
    },
    sources={
        "definition": ["S5"], "segments_in_order": ["S5"],
        "corpuscle": ["S5"], "types": ["S5"],
        "juxtaglomerular_apparatus": ["S5"],
    },
    core=["definition", "segments_in_order", "corpuscle"],
    soft=["types", "juxtaglomerular_apparatus"],
    verify=[
        ABSENCE + " — no nephron, glomerulus, capsule, tubule "
        "segment or collecting duct concept exists; the record "
        "links the two whole-kidney records it would subdivide",
    ],
    note="The nephron is the load-bearing microscopic unit for "
         "the physiology follow-on: its segment order here is the "
         "sequence a renal compartment model must follow.",
)

# ------------------------------------------------------------------
# Ureter (organ/pathway): course and the three constrictions
# ------------------------------------------------------------------
typed(
    "organ.ureter", "Ureter", "organ", "Urinary pathway",
    ["right ureter", "left ureter"],
    fields={
        "extent":
            "Two muscular tubes, one draining each kidney. "
            "Length as consulted: approximately 25 cm (S2); "
            "OpenStax gives approximately 30 cm (S4). The "
            "consulted sources differ, so the recorded extent is "
            "the range 25-30 cm.",
        "course":
            "Arises in the abdomen as a continuation of the renal "
            "pelvis; the point at which the pelvis narrows to "
            "form the ureter is the ureteropelvic junction. "
            "Abdominal part: descends on the anterior surface of "
            "the psoas major, retroperitoneal throughout. At the "
            "sacroiliac joints it crosses the pelvic brim "
            "(crossing the bifurcation of the common iliac "
            "arteries) and enters the pelvic cavity. Pelvic part: "
            "travels down the lateral pelvic walls; at the level "
            "of the ischial spines it turns anteromedially "
            "towards the bladder and pierces the bladder wall "
            "obliquely — a one-way valve (a physiological rather "
            "than anatomical sphincter) that prevents reflux of "
            "urine into the ureter. Urine is propelled by waves "
            "of peristalsis, not passive drainage.",
        "constrictions": [
            "ureteropelvic junction (UPJ) — where the renal "
            "pelvis narrows to become the ureter",
            "pelvic inlet — where the ureter crosses the iliac "
            "vessels at the pelvic brim",
            "ureterovesical junction (UVJ) — where the ureter "
            "enters the bladder; the narrowest of the three",
        ],
        "constriction_note":
            "The three narrowings are the historically taught "
            "sites of ureteric calculus obstruction; more recent "
            "radiological and clinical evidence suggests stone "
            "impaction occurs predominantly at the upper ureter "
            "and the ureterovesical junction (S2).",
        "arterial_supply":
            "Abdominal part: renal artery, testicular/ovarian "
            "artery, and ureteral branches directly from the "
            "abdominal aorta. Pelvic part: superior and inferior "
            "vesical arteries. Venous drainage is by vessels "
            "corresponding to the arteries.",
        "innervation":
            "Via the renal, testicular/ovarian and hypogastric "
            "plexuses. Sensory fibres enter the spinal cord at "
            "T11-L2, with ureteric pain referred to those "
            "dermatomal areas.",
        "relations_at_risk":
            "Female: at the pelvic brim the ureter lies close to "
            "the ovaries (at risk in oophorectomy); about 2 cm "
            "superior to the ischial spine it runs underneath "
            "the uterine artery ('water under the bridge' — at "
            "risk in hysterectomy). Male: the vas deferens "
            "crosses the ureter anteriorly. The ureters must be "
            "identified during pelvic surgery to avoid accidental "
            "damage.",
    },
    sources={
        "extent": ["S2", "S4"], "course": ["S2", "S4"],
        "constrictions": ["S2"], "constriction_note": ["S2"],
        "arterial_supply": ["S2"], "innervation": ["S2"],
        "relations_at_risk": ["S2"],
    },
    core=["course", "constrictions"],
    soft=["extent", "constriction_note", "arterial_supply",
          "innervation", "relations_at_risk"],
    verify=[
        "constrictions: no BP3D concept exists for any ureteric "
        "junction, part or orifice (probe-verified); the "
        "constrictions are sourced text on the two whole-ureter "
        "geometry records",
    ],
)

# ------------------------------------------------------------------
# Urinary pathway (the drainage sequence, organ to exterior)
# ------------------------------------------------------------------
typed(
    "pathway.urinary-pathway", "Urinary pathway", "pathway",
    "Urinary pathway",
    ["right kidney", "left kidney", "right ureter", "left ureter",
     "urinary bladder", "urethra"],
    fields={
        "sequence": [
            "renal papilla (collecting ducts deliver urine)",
            "minor calyx",
            "major calyx",
            "renal pelvis",
            "ureter (peristaltic propulsion)",
            "urinary bladder (storage)",
            "urethra",
            "exterior (external urethral orifice)",
        ],
        "function":
            "Urine formed by the nephrons drains from the "
            "collecting ducts at the renal papillae into the "
            "minor calyces, which merge into the major calyces "
            "and the funnel-shaped renal pelvis in the hilum; "
            "the pelvis funnels urine by peristalsis into the "
            "ureter, which propels it to the bladder, where it "
            "is stored until micturition expels it through the "
            "urethra.",
    },
    sources={"sequence": ["S1", "S6"], "function": ["S6", "S4"]},
    core=["sequence", "function"], soft=[],
    verify=[
        "sequence: the intrarenal stations (papilla, minor and "
        "major calyx, renal pelvis) have no BP3D concepts "
        "(probe-verified); the pathway is sourced text linking "
        "the six whole-organ geometry records",
    ],
)

# ------------------------------------------------------------------
# Urinary bladder (organ): parts, trigone, detrusor, control
# ------------------------------------------------------------------
typed(
    "organ.urinary-bladder", "Urinary bladder", "organ",
    "Lower urinary tract",
    ["urinary bladder"],
    fields={
        "position":
            "A pelvic organ posterior to the pubic bone and "
            "anterior to the rectum; in females it lies anterior "
            "to the uterus, in males the prostate lies inferior "
            "to it. It is partially retroperitoneal: only its "
            "dome carries a peritoneal covering, which projects "
            "into the abdomen when the bladder is distended. "
            "When full it is oval; when empty it is flattened by "
            "the overlying bowel.",
        "function":
            "Two roles: temporary storage of urine — a hollow "
            "organ with distensible walls and a folded internal "
            "lining (rugae) — and assistance in the expulsion of "
            "urine, its musculature contracting during "
            "micturition with concomitant relaxation of the "
            "sphincters.",
        "capacity":
            "400-600 mL in healthy adults (S3); OpenStax gives "
            "adult volumes ranging to 500-600 mL (S4).",
        "parts": [
            "apex — located superiorly, pointing towards the "
            "pubic symphysis; connected to the umbilicus by the "
            "median umbilical ligament, a remnant of the urachus",
            "body — the main part of the bladder, between the "
            "apex and the fundus",
            "fundus (base) — located posteriorly, "
            "triangular-shaped with the tip of the triangle "
            "pointing backwards",
            "neck — formed by the convergence of the fundus and "
            "the two inferolateral surfaces; continuous with the "
            "urethra",
        ],
        "trigone":
            "A triangular area within the fundus marked by the "
            "three orifices: the two ureteric orifices (urine "
            "enters from the ureters) and the internal urethral "
            "orifice (urine exits). Unlike the rest of the "
            "internal bladder, the trigone has smooth walls, "
            "explained by its different embryological origin — "
            "it develops by the integration of the two "
            "mesonephric ducts at the base of the bladder.",
        "musculature":
            "The bladder wall's specialised smooth muscle is the "
            "detrusor: irregular crisscrossing bands whose fibres "
            "run in all directions, retaining structural "
            "integrity when stretched and reducing the size of "
            "the organ when it empties. The interior surface is "
            "transitional epithelium, suited to the bladder's "
            "large volume fluctuations. Detrusor fibres often "
            "become hypertrophic (prominent trabeculae) when "
            "bladder emptying workload increases.",
        "vasculature":
            "Primarily derived from the internal iliac vessels. "
            "Arterial supply via the superior vesical branch of "
            "the internal iliac artery, supplemented in males by "
            "the inferior vesical artery and in females by the "
            "vaginal arteries (the obturator and inferior gluteal "
            "arteries may contribute small branches). Venous "
            "drainage by the vesical venous plexus into the "
            "internal iliac veins. Lymphatics: the superolateral "
            "aspect drains to the external iliac nodes; the neck "
            "and fundus drain to the internal iliac, sacral and "
            "common iliac nodes.",
        "innervation":
            "Sympathetic — hypogastric nerve (T12-L2): relaxes "
            "the detrusor, promoting urine retention. "
            "Parasympathetic — pelvic nerve (S2-S4): contracts "
            "the detrusor, stimulating micturition. Somatic — "
            "pudendal nerve (S2-S4): supplies the external "
            "urethral sphincter, giving voluntary control. "
            "Sensory nerves in the bladder wall report filling "
            "to the brain.",
    },
    sources={
        "position": ["S4", "S3"], "function": ["S3"],
        "capacity": ["S3", "S4"], "parts": ["S3"],
        "trigone": ["S3", "S4"], "musculature": ["S3", "S4"],
        "vasculature": ["S3"], "innervation": ["S3"],
    },
    core=["parts", "trigone", "musculature"],
    soft=["position", "function", "capacity", "vasculature",
          "innervation"],
    verify=[
        "parts: no BP3D concept exists for any bladder part or "
        "feature (apex, body, fundus, neck, trigone, detrusor — "
        "probe-verified); the fields are sourced text on the "
        "single whole-bladder geometry record",
        "vasculature: no vesical artery or vein has a BP3D "
        "concept ('vesical artery'/'vesical vein' probes return "
        "zero hits) and the cardiovascular census carries no "
        "vesical record; the supply is sourced text (S3) only",
    ],
)

# ------------------------------------------------------------------
# Urethra (structure): one unsexed inventory record; the sexed
# anatomy the sources describe is carried here as text
# ------------------------------------------------------------------
typed(
    "structure.urethra", "Urethra", "structure",
    "Lower urinary tract",
    ["urethra"],
    fields={
        "function":
            "Transports urine from the bladder to the outside of "
            "the body for disposal. It is the only urologic "
            "organ that shows any significant anatomic "
            "difference between males and females; all other "
            "urine transport structures are identical. In the "
            "male it also transports semen.",
        "female":
            "Short — about 4 cm. The external urethral orifice "
            "is embedded in the anterior vaginal wall, inferior "
            "to the clitoris, superior to the vaginal opening "
            "(introitus) and medial to the labia minora. Its "
            "short length is less of a barrier to fecal bacteria "
            "than the longer male urethra — the best explanation "
            "for the greater incidence of urinary tract "
            "infection in women.",
        "male":
            "Averages 20 cm, in four regions in order: (1) "
            "preprostatic urethra — very short, incorporated "
            "into the bladder wall; (2) prostatic urethra — "
            "passes through the prostate gland immediately "
            "inferior to the bladder, receiving sperm via the "
            "ejaculatory ducts and secretions from the seminal "
            "vesicles; (3) membranous urethra — passes through "
            "the deep muscles of the perineum, invested by the "
            "urethral sphincters; (4) spongy (penile) urethra — "
            "passes through the corpus spongiosum and exits at "
            "the external urethral orifice at the tip of the "
            "penis.",
        "sphincters":
            "Internal urethral sphincter — smooth muscle under "
            "involuntary autonomic control at the bladder neck: "
            "in males, circular smooth fibres thought to prevent "
            "seminal regurgitation during ejaculation; in "
            "females, a functional sphincter formed by the "
            "anatomy of the bladder neck and proximal urethra "
            "(no sphincteric muscle present). External urethral "
            "sphincter — skeletal muscle under voluntary "
            "control, of the same structure in both sexes, "
            "innervated by the pudendal nerve (S2-S4); in males "
            "its mechanism is more complex, correlating with "
            "fibres of the rectourethralis and levator ani.",
        "epithelium":
            "In both sexes the proximal urethra is lined by "
            "transitional epithelium and the terminal portion "
            "by nonkeratinized stratified squamous epithelium; "
            "in the male, pseudostratified columnar epithelium "
            "lines the urethra between these two.",
    },
    sources={
        "function": ["S4"], "female": ["S4"], "male": ["S4"],
        "sphincters": ["S3", "S4"], "epithelium": ["S4"],
    },
    core=["function", "female", "male"],
    soft=["sphincters", "epithelium"],
    verify=[
        "female: no BP3D concept — the release carries a single "
        "unsexed, undivided urethra (probes for 'male urethra', "
        "'female urethra' and every named part return zero "
        "hits); the sexed anatomy is sourced text on the one "
        "urethra geometry record",
        "male: no BP3D concept — as for female: no sexed form "
        "and no prostatic/membranous/spongy part exists in the "
        "release",
    ],
    note="The inventory's single urethra record is unsexed "
         "because the source release is; this record states the "
         "sex difference from the consulted sources and flags "
         "that neither sex's urethra has geometry of its own.",
)

if link_failures:
    raise SystemExit(f"link failures: {link_failures}")

doc = {
    "meta": {
        "title": "ANATOMICA urinary system clinical records — "
                 "Milestone 12",
        "generated_by": "tools/build_uri_records.py",
        "sources": SOURCES,
        "record_count": len(records),
        "tiers": dict(Counter(r["sourcing_tier"] for r in records)),
        "groups": dict(Counter(r["group"] for r in records)),
        "sourcing_rule":
            "every non-null field cites a source actually "
            "consulted during the build in the record's `sources` "
            "map; every null field carries a verify flag; TA "
            "names were not given by the consulted sources and "
            "are null + flagged on all records",
    },
    "records": records,
}
with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=1, ensure_ascii=False)
    fh.write("\n")
print(f"records: {len(records)}")
print("tiers:", dict(Counter(r["sourcing_tier"] for r in records)))
print("groups:", dict(Counter(r["group"] for r in records)))
for r in records:
    print(f"  {r['id']} [{r['sourcing_tier']}] links="
          f"{r['geometry_record_ids']}")
print(f"wrote {OUT_PATH}")
