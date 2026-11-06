#!/usr/bin/env python3
"""ANATOMICA Milestone 13 — endocrine system clinical tranche.

Field-sourcing rule (set in Milestone 4, binding since): every
field value comes only from the sources actually consulted in
this session, and the record cites the source(s) it used for
that field in its `sources` map. A field the consulted sources
do not support is null and carries a `verify` entry instead.

Sources consulted in-session, 2026-11-06:
  S1  TeachMeAnatomy — "The Pituitary Gland" (teachmeanatomy.
      info): sella position and relations, the two lobes and
      their embryology, the hypophyseal portal system, arterial
      supply and venous drainage, the optic-chiasm consequence
      of an adenoma.
  S2  TeachMeAnatomy — "The Thyroid Gland" (teachmeanatomy.
      info): C5–T1 position, lobes and isthmus, relations,
      superior and inferior thyroid arteries and the nerves
      beside them, thyroid venous drainage, lymphatic drainage,
      the recurrent laryngeal nerve's course and its surgical
      risk.
  S3  TeachMeAnatomy — "The Adrenal Glands" (teachmeanatomy.
      info): suprarenal position and relations, perinephric
      fascia, cortical zones and their products in order,
      medullary chromaffin cells and catecholamines, the three
      arterial tiers, the asymmetric venous drainage, coeliac
      and splanchnic innervation, lumbar lymphatic drainage.
  S4  OpenStax Anatomy and Physiology 2e, §17.3 (incl. Table
      17.3) (openstax.org): the pituitary product list —
      anterior GH, PRL, TSH, ACTH, FSH, LH; intermediate-zone
      MSH; posterior release of ADH and oxytocin; the
      hypothalamus as the diencephalic neural-endocrine link.
  S5  OpenStax §17.4: thyroid follicles and colloid, thyroxine
      (T4) and triiodothyronine (T3), calcitonin from the
      parafollicular cells, TSH regulation and the TRH–TSH
      feedback loop, parathyroid glands embedded in the lobes.
  S6  OpenStax §17.5: the parathyroid glands — number, posterior
      thyroid position, chief cells and parathyroid hormone,
      oxyphil cells, PTH's actions on bone, kidney and
      calcitriol, calcitonin as antagonist.
  S7  OpenStax §17.7: the pineal gland — diencephalic position,
      pinealocytes and melatonin, the retinal–SCN–spinal
      pathway that gates secretion, circadian effects.
  S8  OpenStax §17.9: the pancreatic islets — the four cell
      varieties with their proportions and products (alpha
      glucagon, beta insulin, delta somatostatin, PP cells),
      the pancreas as a primarily exocrine organ posterior to
      the stomach.

The tranche's shape follows the dataset's: the pituitary and
the two adrenals are the only endocrine glands the release
carries as geometry, and they get geometry-linked records. The
thyroid, the parathyroids and the pancreatic islets have no
concept in the release at all — probe-verified over all six
tables — and get sourced-text records with the absence recorded
(the Milestone 9 pattern); the thyroid record carries the
recurrent-laryngeal-nerve relation because thyroid surgery is
where that nerve is lost, cross-referencing the nervous
module's vagus record. The pineal gland's geometry is the
nervous module's record brain.pineal-body (the release files
the pineal body inside the nervous tree); its clinical record
lives here, where its function belongs, and says so instead of
duplicating the mesh link. Hormone names are asserted only
where the consulted sources list them.

Tiers: A = every field valued and cited; B = a soft field is
null; C = a core field is null. Tier discipline is enforced by
finish() and re-derived independently by tools/endo_check.py.
"""
import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "data", "endocrine", "endocrine-inventory.json")
OUT = os.path.join(ROOT, "data", "endocrine", "endocrine.json")

SOURCES = OrderedDict([
    ("S1", "TeachMeAnatomy — The Pituitary Gland "
           "(teachmeanatomy.info): sella turcica position, "
           "relations incl. the optic chiasm and cavernous "
           "sinuses, adenohypophysis from Rathke's pouch and its "
           "three parts, neurohypophysis as a hypothalamic "
           "extension, the hypophyseal portal system, arterial "
           "supply and drainage"),
    ("S2", "TeachMeAnatomy — The Thyroid Gland "
           "(teachmeanatomy.info): anterior-neck position C5–T1, "
           "lobes, isthmus and pretracheal fascia, relations, "
           "superior thyroid artery (first branch of the "
           "external carotid) and inferior thyroid artery "
           "(thyrocervical trunk), thyroid ima frequency, venous "
           "and lymphatic drainage, the recurrent laryngeal "
           "nerve's course and surgical risk"),
    ("S3", "TeachMeAnatomy — The Adrenal Glands "
           "(teachmeanatomy.info): suprarenal position, "
           "pyramidal right and semi-lunar left forms, "
           "perinephric fascia, relations, cortical zones and "
           "products in order, medullary chromaffin cells, the "
           "three-tier arterial supply, right-to-IVC and "
           "left-to-renal-vein drainage, innervation, lymphatics"),
    ("S4", "OpenStax Anatomy and Physiology 2e, §17.3 incl. "
           "Table 17.3 (openstax.org): pituitary products — "
           "anterior GH, PRL, TSH, ACTH, FSH, LH; intermediate "
           "MSH; posterior release of ADH and oxytocin "
           "synthesised in the supraoptic and paraventricular "
           "nuclei; the hypothalamus as diencephalic link"),
    ("S5", "OpenStax §17.4: thyroid follicles and colloid, "
           "thyroxine (T4) and triiodothyronine (T3), calcitonin "
           "from parafollicular cells, TSH regulation and the "
           "TRH–TSH negative feedback loop, parathyroid glands "
           "embedded on the posterior surfaces of the lobes"),
    ("S6", "OpenStax §17.5: parathyroid number and posterior "
           "thyroid position, separating capsule, chief cells "
           "and parathyroid hormone, oxyphil cells of unclear "
           "function, PTH actions on bone, kidney and "
           "calcitriol, calcitonin as the antagonist hormone"),
    ("S7", "OpenStax §17.7: pineal position in the "
           "diencephalon, pinealocytes secreting melatonin, the "
           "retina–SCN–spinal-cord control pathway, light "
           "inhibition and darkness stimulation of secretion, "
           "circadian effects"),
    ("S8", "OpenStax §17.9: pancreatic islets and their four "
           "cell varieties with proportions — alpha ~20% "
           "glucagon, beta ~75% insulin, delta ~4% somatostatin, "
           "PP ~1% pancreatic polypeptide; the pancreas as a "
           "primarily exocrine organ posterior to the stomach"),
])

ABSENCE = ("no BP3D 4.0 concept exists for this structure "
           "(probe-verified over all six release tables by "
           "tools/endo_map.py); the record is sourced text only "
           "and links no geometry")
HELD = ("geometry held by the nervous module: the release "
        "files the pineal body inside the nervous system tree, "
        "where it is the nervous inventory record "
        "brain.pineal-body (FMA62033, Milestone 9); this record "
        "carries the gland's endocrine account and does not "
        "duplicate the mesh link")


def base(rid, name, typ, group):
    return OrderedDict([
        ("id", rid), ("name", name), ("type", typ), ("group", group),
        ("ta_name", None), ("sources", OrderedDict()),
        ("verify", []), ("note", None), ("geometry_record_ids", []),
    ])


def link(rec, inv_by_name, names):
    for n in names:
        rec["geometry_record_ids"].append(inv_by_name[n]["record_id"])


def typed(rec, fields):
    for k, v in fields.items():
        rec[k] = v
    return rec


def finish(rec, core, soft):
    """Assign the sourcing tier and enforce the sourcing rule.

    An empty geometry link is acceptable only when a verify
    entry records either the dataset absence (ABSENCE) or that
    another module holds the geometry (HELD) — the pineal case.
    """
    problems = []
    for fname in core + soft:
        val = rec.get(fname)
        if val is None:
            if not any(fname in v for v in rec["verify"]):
                problems.append(
                    f"{rec['id']}: null field {fname} has no verify "
                    "entry naming it")
        else:
            if fname not in rec["sources"]:
                problems.append(
                    f"{rec['id']}: valued field {fname} has no "
                    "sources entry")
    if not rec["geometry_record_ids"]:
        if not any(ABSENCE in v or HELD in v for v in rec["verify"]):
            problems.append(
                f"{rec['id']}: no geometry links and no absence or "
                "held-by verify entry")
    if problems:
        raise SystemExit("\n".join(problems))
    core_null = any(rec.get(f) is None for f in core)
    soft_null = any(rec.get(f) is None for f in soft)
    rec["sourcing_tier"] = "C" if core_null else ("B" if soft_null
                                                   else "A")
    return rec


def main():
    inv = json.load(open(INV))
    inv_by_name = {r["name"]: r for r in inv["records"]}
    records = []

    # ---------------- the pituitary gland ----------------
    r = base("gland.pituitary-gland", "Pituitary gland", "gland",
             "Pituitary")
    link(r, inv_by_name, ["pituitary gland"])
    typed(r, {
        "position":
            "A pea-sized oval gland suspended from the underside "
            "of the brain by the infundibulum, seated in the "
            "sella turcica of the sphenoid bone and roofed by the "
            "diaphragma sellae (S1).",
        "parts":
            "Two functionally distinct parts. The anterior lobe "
            "(adenohypophysis) is glandular epithelium derived "
            "from Rathke's pouch, an ectodermal outpouching of "
            "the roof of the pharynx; its regions are the pars "
            "distalis — the largest and most hormonally active — "
            "the pars intermedia and the pars tuberalis (S1). "
            "The posterior lobe (neurohypophysis) is "
            "neurosecretory tissue derived from the embryonic "
            "forebrain and is functionally an extension of the "
            "hypothalamus (S1). The release carries the gland as "
            "an undivided leaf in both tables: no lobe or part of "
            "it exists as a concept (probe-verified), so the "
            "parts are sourced text on this record.",
        "products":
            "Anterior lobe (S4, Table 17.3): growth hormone "
            "(GH), prolactin (PRL), thyroid-stimulating hormone "
            "(TSH), adrenocorticotropic hormone (ACTH), "
            "follicle-stimulating hormone (FSH) and luteinising "
            "hormone (LH). Intermediate zone: melanocyte-"
            "stimulating hormone (MSH) (S4). Posterior lobe: it "
            "synthesises nothing itself — it stores and releases "
            "antidiuretic hormone (ADH) and oxytocin, which are "
            "synthesised in the supraoptic and paraventricular "
            "nuclei of the hypothalamus (S1, S4).",
        "relations":
            "Anteriorly the sphenoid sinus — the route of "
            "trans-sphenoidal surgical access. Superiorly the "
            "diaphragma sellae and the optic chiasm: an expanding "
            "pituitary adenoma presses on the chiasm and produces "
            "bitemporal hemianopia. Laterally the cavernous "
            "sinuses. Posteriorly the posterior intercavernous "
            "sinus, the dorsum sellae, the basilar artery and the "
            "pons; inferiorly the sphenoid sinus again (S1).",
        "vasculature":
            "The anterior lobe is fed through the hypophyseal "
            "portal system: the superior hypophyseal artery, a "
            "branch of the internal carotid, supplies a primary "
            "capillary plexus in the median eminence; portal "
            "veins carry that blood to a secondary plexus in the "
            "anterior lobe, delivering hypothalamic releasing and "
            "inhibiting hormones at high concentration (S1). The "
            "posterior lobe is supplied by the superior "
            "hypophyseal, infundibular and inferior hypophyseal "
            "arteries; the gland drains by hypophyseal veins "
            "(S1).",
        "control":
            "The hypothalamus — the nervous module's record "
            "brain.hypothalamus, the floor of the diencephalon "
            "anterior and inferior to the thalamus — is both a "
            "neural and an endocrine structure (S4): it governs "
            "the anterior lobe through the portal blood supply "
            "(S1) and owns the posterior lobe's hormones outright, "
            "the lobe being its own axonal extension (S1, S4).",
    })
    r["sources"] = OrderedDict([
        ("position", ["S1"]),
        ("parts", ["S1"]),
        ("products", ["S1", "S4"]),
        ("relations", ["S1"]),
        ("vasculature", ["S1"]),
        ("control", ["S1", "S4"]),
    ])
    r["verify"] = [
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("The release's only intracranial endocrine gland "
                 "with geometry, and one of only three endocrine "
                 "glands it carries at all.")
    records.append(finish(r,
                          core=["position", "parts", "products"],
                          soft=["relations", "vasculature",
                                "control"]))

    # ---------------- the thyroid gland ----------------
    r = base("gland.thyroid-gland", "Thyroid gland", "gland",
             "Thyroid and parathyroid")
    typed(r, {
        "position":
            "In the anterior neck, spanning vertebral levels C5 "
            "to T1: two lobes joined across the midline by a "
            "central isthmus, the whole gland butterfly-shaped, "
            "its lobes wrapping the cricoid cartilage and the "
            "superior tracheal rings, enclosed in the pretracheal "
            "fascia of the visceral compartment of the neck (S2).",
        "structure":
            "The working unit is the thyroid follicle: spheres of "
            "follicular cells around a colloid store, and the "
            "follicles are the site of hormone production (S5). "
            "Between them sit the parafollicular cells (S5). Each "
            "lobe carries parathyroid glands embedded in it, "
            "primarily on its posterior surface (S5) — see the "
            "companion record gland.parathyroid-glands.",
        "products":
            "The follicles produce the metabolic hormones "
            "thyroxine (T4) and triiodothyronine (T3), for which "
            "iodine is an essential component; they raise the "
            "basal metabolic rate (S5). The parafollicular cells "
            "produce calcitonin, which lowers blood calcium (S5).",
        "arterial_supply":
            "The superior thyroid artery, the first branch of the "
            "external carotid artery, descends to the upper pole "
            "close to the external branch of the superior "
            "laryngeal nerve. The inferior thyroid artery arises "
            "from the thyrocervical trunk of the subclavian "
            "artery and approaches the gland close to the "
            "recurrent laryngeal nerve. In about 10% of people a "
            "thyroid ima artery arises from the brachiocephalic "
            "trunk (S2).",
        "venous_drainage":
            "A venous plexus on the gland drains by the superior, "
            "middle and inferior thyroid veins: the superior and "
            "middle veins end in the internal jugular vein, the "
            "inferior veins in the brachiocephalic vein (S2).",
        "nerves_at_risk":
            "The recurrent laryngeal nerve — a branch of the "
            "vagus (the nervous module's clinical record "
            "nerve.cn-10-vagus) — is the surgically load-bearing "
            "relation of this gland. It branches from the vagus "
            "in the chest, hooks around the right subclavian "
            "artery on the right and around the arch of the aorta "
            "on the left, ascends in the tracheoesophageal groove "
            "and passes underneath the thyroid gland to reach the "
            "larynx it innervates; it lies close to the inferior "
            "thyroid artery and is at risk in thyroid surgery "
            "(S2). The external branch of the superior laryngeal "
            "nerve runs close to the superior thyroid artery at "
            "the upper pole (S2).",
        "lymphatic_drainage":
            "Lymph drains to the paratracheal and deep cervical "
            "lymph nodes (S2). Neither group exists as a concept "
            "in the release — the lymphatic module's census "
            "carries no lymph node of any kind — so this drainage "
            "is sourced text only.",
        "control":
            "Secretion is not under direct nervous control — the "
            "sympathetic fibres the gland receives do not govern "
            "it (S2); it is pituitary-regulated: thyrotropin-"
            "releasing hormone drives thyroid-stimulating "
            "hormone, TSH drives T4 and T3 release, and the "
            "thyroid hormones feed back negatively on the axis "
            "(S2, S5).",
    })
    r["sources"] = OrderedDict([
        ("position", ["S2"]),
        ("structure", ["S2", "S5"]),
        ("products", ["S5"]),
        ("arterial_supply", ["S2"]),
        ("venous_drainage", ["S2"]),
        ("nerves_at_risk", ["S2"]),
        ("lymphatic_drainage", ["S2"]),
        ("control", ["S2", "S5"]),
    ])
    r["verify"] = [
        ABSENCE + " — the release contains no thyroid gland "
        "concept in either parts list; every 'thyroid' name it "
        "carries is the thyroid cartilage (skeletal module), "
        "the inferior thyroid arteries (cardiovascular module) "
        "or the sternothyroid and cricothyroid muscles "
        "(muscular module)",
        "arterial_supply: the inferior thyroid arteries are "
        "cardiovascular inventory records "
        "(artery.left-inferior-thyroid-artery, "
        "artery.right-inferior-thyroid-artery), resolved by the "
        "checker; the superior thyroid artery has no "
        "cardiovascular record of its own because its parent, "
        "the external carotid artery, is one of the concepts "
        "Milestone 5 found absent from the release",
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("Sourced-text record: the dataset carries the "
                 "gland's arteries, its cartilage namesake and "
                 "the muscles named for it, but not the gland.")
    records.append(finish(r,
                          core=["position", "structure", "products"],
                          soft=["arterial_supply", "venous_drainage",
                                "nerves_at_risk",
                                "lymphatic_drainage", "control"]))

    # ---------------- the parathyroid glands ----------------
    r = base("gland.parathyroid-glands", "Parathyroid glands",
             "gland", "Thyroid and parathyroid")
    typed(r, {
        "position":
            "Tiny, round glands usually embedded in the "
            "posterior surface of the thyroid gland (S6); most "
            "people have four, though occasionally more are found "
            "in the tissues of the neck or chest (S6). Each is "
            "separated from the thyroid tissue by its own thick "
            "connective-tissue capsule (S6).",
        "products":
            "Parathyroid hormone (PTH), produced and secreted by "
            "the glands' chief cells in response to low blood "
            "calcium (S6).",
        "function":
            "PTH defends blood calcium: it stimulates osteoclasts "
            "to release calcium from bone, inhibits osteoblasts, "
            "increases calcium reabsorption in the kidney "
            "tubules, and initiates the production of calcitriol, "
            "the active form of vitamin D (S6). Its antagonist "
            "is calcitonin, secreted by the thyroid's "
            "parafollicular cells (S6) — the pairing that makes "
            "the two glands one surgical field.",
        "cells":
            "The chief cells are the primary functional cells of "
            "the gland, producing and secreting PTH; the oxyphil "
            "cells' function is not clear (S6).",
        "relations":
            "The glands sit within the posterior surface of the "
            "thyroid lobes, inside the thyroid's surgical field "
            "and separated from its tissue only by their capsule "
            "(S6) — which is why they, and the recurrent "
            "laryngeal nerve beside them, are what thyroid surgery "
            "must not take with the gland (see "
            "gland.thyroid-gland, nerves_at_risk).",
        "arterial_supply": None,
    })
    r["sources"] = OrderedDict([
        ("position", ["S6"]),
        ("products", ["S6"]),
        ("function", ["S6"]),
        ("cells", ["S6"]),
        ("relations", ["S6"]),
    ])
    r["verify"] = [
        ABSENCE + " — 'parathyroid' scores zero hits in both "
        "parts lists and in all six release tables",
        "arterial_supply: no value asserted — none of the "
        "sources consulted in this session states the "
        "parathyroid glands' arterial supply in citable form; "
        "the field stays null rather than unsourced",
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("Sourced-text record; the glands' surgical "
                 "weight is inverse to their size, and the "
                 "dataset carries no trace of them.")
    records.append(finish(r,
                          core=["position", "products", "function"],
                          soft=["cells", "relations",
                                "arterial_supply"]))

    # ---------------- the adrenal glands ----------------
    r = base("gland.adrenal-gland", "Adrenal glands", "gland",
             "Adrenal")
    link(r, inv_by_name, ["right adrenal gland",
                          "left adrenal gland"])
    typed(r, {
        "position":
            "Paired glands seated over the medial aspect of the "
            "upper poles of the kidneys, in the posterior abdomen "
            "between the superomedial kidney and the diaphragm; "
            "retroperitoneal, with parietal peritoneum on their "
            "anterior surface only (S3). The right gland is "
            "pyramidal, the left semi-lunar (S3). The perinephric "
            "(renal, Gerota) fascia encloses each gland with its "
            "kidney and attaches to the diaphragmatic crura, but "
            "fibrous tissue separates gland from kidney within it "
            "(S3) — the anatomical basis on which the urinary "
            "module censused these glands as this module's "
            "cross-reference rather than its own.",
        "cortex":
            "The outer zone of the gland, derived from embryonic "
            "mesoderm, yellowish, secreting the cholesterol-"
            "derived corticosteroids and androgens (S3). Its "
            "three zones run superficial to deep in a fixed "
            "order: the zona glomerulosa secretes the "
            "mineralocorticoids (aldosterone); the zona "
            "fasciculata secretes the corticosteroids (cortisol) "
            "and a small amount of androgens; the zona "
            "reticularis secretes the androgens "
            "(dehydroepiandrosterone) and a small amount of "
            "corticosteroids (S3).",
        "medulla":
            "The central zone, dark brown, derived from "
            "ectodermal neural crest: its chromaffin cells "
            "secrete the catecholamines (adrenaline) and "
            "enkephalins, the hormonal arm of the flight-or-fight "
            "response (S3).",
        "products":
            "Cortex: mineralocorticoids — aldosterone (zona "
            "glomerulosa); corticosteroids — cortisol (zona "
            "fasciculata); androgens — dehydroepiandrosterone "
            "(zona reticularis) (S3). Medulla: catecholamines, "
            "principally adrenaline, with enkephalins (S3). "
            "Hormone names are asserted here only as the "
            "consulted source names them.",
        "relations":
            "Right gland: anteriorly the inferior vena cava and "
            "the right lobe of the liver, posteriorly the right "
            "crus of the diaphragm. Left gland: anteriorly the "
            "stomach, the pancreas and the spleen, posteriorly "
            "the left crus (S3). Arteries and nerves enter at "
            "numerous sites around each gland, while veins and "
            "lymphatics leave through a hilum (S3).",
        "arterial_supply":
            "Three tiers (S3): the superior adrenal arteries from "
            "the inferior phrenic arteries; the middle adrenal "
            "arteries directly from the abdominal aorta; the "
            "inferior adrenal arteries from the renal arteries. "
            "The cardiovascular module carries the middle and "
            "inferior tiers under the release's own naming as the "
            "middle and inferior suprarenal arteries (records "
            "artery.left-middle-suprarenal-artery, "
            "artery.right-middle-suprarenal-artery, "
            "artery.left-inferior-suprarenal-artery, "
            "artery.right-inferior-suprarenal-artery), resolved "
            "by the checker.",
        "venous_drainage":
            "Asymmetric, and surgically load-bearing for it: the "
            "right adrenal vein drains directly into the inferior "
            "vena cava, the left adrenal vein into the left renal "
            "vein (S3). The cardiovascular module carries both as "
            "the suprarenal veins (vein.right-suprarenal-vein, "
            "vein.left-suprarenal-vein).",
        "innervation":
            "From the coeliac plexus and the greater splanchnic "
            "nerves (S3); the medulla is driven directly by "
            "myelinated preganglionic fibres, mainly from T10 to "
            "L1 — the medulla is, in effect, a sympathetic "
            "ganglion that secretes into the blood (S3).",
        "lymphatics":
            "Lymph drains to the lumbar lymph nodes through two "
            "plexuses, one deep to the capsule and one within the "
            "medulla (S3). No lumbar node exists as a concept in "
            "the release (lymphatic module census).",
    })
    r["sources"] = OrderedDict([
        ("position", ["S3"]),
        ("cortex", ["S3"]),
        ("medulla", ["S3"]),
        ("products", ["S3"]),
        ("relations", ["S3"]),
        ("arterial_supply", ["S3"]),
        ("venous_drainage", ["S3"]),
        ("innervation", ["S3"]),
        ("lymphatics", ["S3"]),
    ])
    r["verify"] = [
        "no BP3D 4.0 concept exists for the adrenal cortex, the "
        "adrenal medulla or any cortical zone (probe-verified "
        "over all six release tables); the cortex and medulla "
        "fields are sourced text on the two whole-gland records",
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("Owned by this module per the release's own "
                 "filing (Milestone 12 finding): the glands are "
                 "direct members of the endocrine system in "
                 "PART-OF and instances of the adrenal class in "
                 "IS-A; Milestone 12's urinary census pointed here "
                 "and this record closes that pointer.")
    records.append(finish(r,
                          core=["position", "cortex", "medulla",
                                "products"],
                          soft=["relations", "arterial_supply",
                                "venous_drainage", "innervation",
                                "lymphatics"]))

    # ---------------- the pineal gland ----------------
    r = base("gland.pineal-gland", "Pineal gland", "gland",
             "Pineal")
    typed(r, {
        "position":
            "A tiny endocrine gland of the diencephalon, lying "
            "inferior but somewhat posterior to the thalamus "
            "(S7). The release files the pineal body inside the "
            "nervous system tree — under the epithalamus — and "
            "the nervous module holds its geometry; this record "
            "is its endocrine account.",
        "products":
            "Melatonin, an amine hormone derived from serotonin, "
            "produced and secreted by the gland's pinealocytes "
            "(S7).",
        "function":
            "Melatonin secretion entrains the circadian rhythms — "
            "sleepiness and wakefulness, and with them appetite "
            "and body temperature (S7). The source is explicit "
            "that the gland's functions are not entirely "
            "understood (S7); nothing further is asserted here.",
        "regulation":
            "Secretion varies with environmental light: photons "
            "striking the retina signal the suprachiasmatic "
            "nucleus of the hypothalamus, which relays through "
            "the spinal cord to the pineal and inhibits melatonin "
            "production — levels fall and wakefulness follows; in "
            "darkness production rises and drowsiness follows "
            "(S7).",
    })
    r["sources"] = OrderedDict([
        ("position", ["S7"]),
        ("products", ["S7"]),
        ("function", ["S7"]),
        ("regulation", ["S7"]),
    ])
    r["verify"] = [
        HELD,
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("Cross-module record: geometry in the nervous "
                 "module (brain.pineal-body), function here — the "
                 "release's filing split, kept, with each side "
                 "pointing at the other.")
    records.append(finish(r,
                          core=["position", "products", "function"],
                          soft=["regulation"]))

    # ---------------- the pancreatic islets ----------------
    r = base("gland.pancreatic-islets", "Pancreatic islets",
             "gland", "Pancreatic islets")
    typed(r, {
        "definition":
            "Clusters of endocrine cells scattered through the "
            "pancreas — formerly called the islets of Langerhans "
            "— which secrete glucagon, insulin, somatostatin and "
            "pancreatic polypeptide into the blood (S8). The "
            "pancreas that hosts them is primarily an exocrine "
            "gland (S8).",
        "cell_types":
            "Four cell varieties, in the proportions the "
            "consulted source gives: alpha cells about 20% of the "
            "islet, beta cells about 75%, delta cells about 4%, "
            "and PP cells about 1% (S8).",
        "products":
            "Alpha cells secrete glucagon, which raises blood "
            "glucose and is released when glucose is low; beta "
            "cells secrete insulin, which reduces blood glucose; "
            "delta cells secrete somatostatin, which inhibits the "
            "release of both glucagon and insulin; PP cells "
            "secrete pancreatic polypeptide (S8).",
        "host_organ":
            "The host organ is the pancreas — a long, slender "
            "organ lying mostly posterior to the bottom half of "
            "the stomach (S8) — which is the digestive module's "
            "inventory record pancreas and clinical record "
            "organ.pancreas (Milestone 11); the islets are "
            "censused there as this module's cross-reference "
            "boundary in reverse. No islet, and no part of the "
            "endocrine pancreas, has a concept in the release.",
    })
    r["sources"] = OrderedDict([
        ("definition", ["S8"]),
        ("cell_types", ["S8"]),
        ("products", ["S8"]),
        ("host_organ", ["S8"]),
    ])
    r["verify"] = [
        ABSENCE + " — 'islet' and 'langerhans' score zero hits "
        "in both parts lists and in all six release tables",
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("Sourced-text record on another module's organ: "
                 "the endocrine pancreas exists in the clinical "
                 "layer only, exactly as far as the consulted "
                 "source describes it.")
    records.append(finish(r,
                          core=["definition", "cell_types",
                                "products"],
                          soft=["host_organ"]))

    tiers = {}
    for rec in records:
        tiers[rec["sourcing_tier"]] = tiers.get(rec["sourcing_tier"],
                                                0) + 1
    doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA endocrine system clinical records "
                      "— Milestone 13"),
            ("generated_by", "tools/build_endo_records.py"),
            ("sources", SOURCES),
            ("record_count", len(records)),
            ("tiers", tiers),
            ("groups", list(OrderedDict.fromkeys(
                r["group"] for r in records))),
            ("sourcing_rule",
             "every field value is drawn only from the sources "
             "listed, consulted in this session, and cites them "
             "per field in the record's sources map; a field no "
             "consulted source supports is null and carries a "
             "verify entry naming it. TA names are not asserted "
             "anywhere in this tranche (no TA2 list consulted). "
             "Three records link geometry the release carries "
             "(pituitary, both adrenals); the thyroid, "
             "parathyroid and islet records are sourced text with "
             "the dataset absence recorded, and the pineal record "
             "points at the nervous module's geometry rather "
             "than duplicating it. Hormone names are asserted "
             "only where a consulted source lists them."),
        ])),
        ("records", records),
    ])
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: {len(records)} records, tiers {tiers}")
    for rec in records:
        print(" ", rec["id"], rec["sourcing_tier"],
              "links:", rec["geometry_record_ids"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
