#!/usr/bin/env python3
"""ANATOMICA Milestone 13 — lymphatic system clinical tranche.

Field-sourcing rule (set in Milestone 4, binding since): every
field value comes only from the sources actually consulted in
this session, and the record cites the source(s) it used for
that field in its `sources` map. A field the consulted sources
do not support is null and carries a `verify` entry instead.

Sources consulted in-session, 2026-11-06:
  S1  TeachMeAnatomy — "The Spleen" (teachmeanatomy.info):
      position, ligaments, capsule and surfaces, splenic
      arterial tree (five terminal branches, no anastomoses,
      vascular segments), portal venous confluence, coeliac
      plexus innervation, pancreaticosplenic-node lymphatic
      drainage. Its relations table did not render in the fetch,
      so the relations field is null with a verify flag.
  S2  OpenStax Anatomy and Physiology 2e, §21.1 "Anatomy of the
      Lymphatic and Immune Systems" (openstax.org): the drainage
      pathway in order (capillaries -> vessels -> trunks ->
      ducts -> the jugular-subclavian venous junction), the
      right lymphatic and thoracic duct territories and the
      cisterna chyli, lymph node structure and count, tonsils,
      MALT and Peyer's patches, thymus structure and involution,
      spleen size, red and white pulp.
  S3  StatPearls — "Anatomy, Head and Neck, Thymus" (NCBI
      Bookshelf NBK539748; search-excerpt level — the full page
      was blocked by a robot check): thymus position detail —
      superior and retrosternal mediastinum, lobes converging at
      the manubrium, cervical extensions toward the thyroid.

The tranche is deliberately small because the dataset is: the
release carries two lymphatic organs (spleen, thymus) and
nothing else of the system, so beside the two organ records the
tranche carries the drainage pathway and the lymphoid tissue as
sourced text records with the dataset absence recorded on each —
the conducting and filtering apparatus exists in the clinical
layer exactly as far as the consulted sources describe it, and
nowhere in the geometry layer. Splenic supply cross-references
the cardiovascular module's records (artery.splenic-artery,
vein.splenic-vein), which the checker resolves.

Tiers: A = every field valued and cited; B = a soft field is
null; C = a core field is null. Tier discipline is enforced by
finish() and re-derived independently by tools/lymph_check.py.
"""
import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "data", "lymphatic", "lymphatic-inventory.json")
OUT = os.path.join(ROOT, "data", "lymphatic", "lymphatic.json")

SOURCES = OrderedDict([
    ("S1", "TeachMeAnatomy — The Spleen (teachmeanatomy.info): "
           "position, ligaments, capsule and surfaces, blood "
           "filtration function, splenic artery (coeliac trunk, "
           "five terminal branches, vascular segments), splenic "
           "vein and the portal confluence, coeliac plexus "
           "innervation, lymphatic drainage to pancreaticosplenic "
           "and coeliac nodes"),
    ("S2", "OpenStax Anatomy and Physiology 2e, §21.1 Anatomy of "
           "the Lymphatic and Immune Systems (openstax.org): the "
           "drainage pathway in order, duct territories and the "
           "cisterna chyli, lymph node structure and number, "
           "tonsils, MALT and Peyer's patches, thymus structure "
           "and involution rates, spleen red and white pulp"),
    ("S3", "StatPearls — Anatomy, Head and Neck, Thymus (NCBI "
           "Bookshelf NBK539748; consulted at search-excerpt "
           "level, full page blocked by a robot check): thymus "
           "position in the superior and retrosternal "
           "mediastinum, lobes converging at the manubrium, "
           "cervical extensions toward the thyroid"),
])

ABSENCE = ("no BP3D 4.0 concept exists for this structure "
           "(probe-verified over all six release tables by "
           "tools/lymph_map.py); the record is sourced text only "
           "and links no geometry")


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
    """Assign the sourcing tier and enforce the sourcing rule."""
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
        if not any(ABSENCE in v for v in rec["verify"]):
            problems.append(
                f"{rec['id']}: no geometry links and no absence "
                "verify entry")
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

    # ---------------- the spleen ----------------
    r = base("organ.spleen", "Spleen", "organ", "Spleen")
    link(r, inv_by_name, ["spleen"])
    typed(r, {
        "position":
            "The spleen lies in the upper left quadrant of the "
            "abdomen, under the diaphragm and the ribcage; it is "
            "not normally palpable (S1). It is intraperitoneal "
            "except at its hilum (S1), and is about 12 cm long, "
            "attached to the lateral border of the stomach by the "
            "gastrosplenic ligament (S2, S1).",
        "internal_structure":
            "An oval organ with a weak capsule (S1), a "
            "diaphragmatic surface against the diaphragm and a "
            "visceral surface carrying the hilum, with notches on "
            "its anterior and superior borders (S1). Internally, "
            "the red pulp filters the blood that passes through "
            "it, and the white pulp — lymphoid tissue arranged "
            "around a central arteriole — mounts the adaptive "
            "immune responses (S2). The release carries no "
            "concept for the pulp, the hilum or any other part of "
            "the spleen (probe-verified), so this structure is "
            "sourced text on the whole-organ record.",
        "function":
            "The spleen filters the blood, removing old red blood "
            "cells, and carries cell-mediated and humoral immune "
            "roles (S1); its red pulp is the filtration tissue and "
            "its white pulp the adaptive-response tissue (S2). "
            "It is fragile — it has no strong capsule (S2) — and "
            "its arterial tree divides into vascular segments, "
            "which is what makes subtotal splenectomy possible "
            "(S1).",
        "relations": None,
        "arterial_supply":
            "The splenic artery — the cardiovascular module's "
            "record artery.splenic-artery — arises from the "
            "coeliac trunk, runs along the superior border of the "
            "pancreas within the splenorenal ligament, and divides "
            "into five terminal branches with no anastomoses "
            "between them, defining the spleen's vascular segments "
            "(S1).",
        "venous_drainage":
            "The splenic vein — the cardiovascular module's record "
            "vein.splenic-vein — leaves the hilum and joins the "
            "superior mesenteric vein to form the hepatic portal "
            "vein (S1).",
        "lymphatic_drainage":
            "Lymph follows the splenic vessels to the "
            "pancreaticosplenic lymph nodes and onward to the "
            "coeliac nodes (S1). Neither node group exists as a "
            "concept in the release (probe-verified), so this "
            "drainage is sourced text only.",
        "innervation":
            "Sympathetic supply reaches the spleen from the "
            "coeliac plexus (S1).",
    })
    r["sources"] = OrderedDict([
        ("position", ["S1", "S2"]),
        ("internal_structure", ["S1", "S2"]),
        ("function", ["S1", "S2"]),
        ("arterial_supply", ["S1"]),
        ("venous_drainage", ["S1"]),
        ("lymphatic_drainage", ["S1"]),
        ("innervation", ["S1"]),
    ])
    r["verify"] = [
        "relations: no value asserted — the consulted "
        "TeachMeAnatomy page's relations table did not render in "
        "the fetched text, and no other consulted source states "
        "the spleen's relations; the field stays null rather "
        "than unsourced",
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("The release's only intraperitoneal lymphoid "
                 "organ and, with the thymus, one of only two "
                 "lymphatic organs it carries at all.")
    records.append(finish(r,
                          core=["position", "internal_structure",
                                "function"],
                          soft=["relations", "arterial_supply",
                                "venous_drainage",
                                "lymphatic_drainage", "innervation"]))

    # ---------------- the thymus ----------------
    r = base("organ.thymus", "Thymus", "organ", "Thymus")
    link(r, inv_by_name, ["thymus", "right lobe of thymus",
                          "left lobe of thymus"])
    typed(r, {
        "position":
            "A bilobed organ lying in the anterior mediastinum, "
            "between the sternum and the aorta (S2); more "
            "precisely in the superior and retrosternal "
            "mediastinum, its two lobes converging at the "
            "manubrium, with extensions that can reach the neck "
            "toward the thyroid (S3). It develops from the ventral "
            "third pharyngeal pouch (S3).",
        "structure":
            "The thymus is enclosed in a capsule whose trabeculae "
            "divide it into lobules; each lobule has a cortex "
            "densely packed with thymocytes and a less densely "
            "populated medulla (S2). The release carries the organ "
            "and its two lobes only — no lobule, cortex or medulla "
            "concept exists (probe-verified).",
        "function":
            "A primary lymphoid organ: the thymus is where T "
            "cells (thymocytes) mature, as bone marrow is where B "
            "cells mature (S2).",
        "age_changes":
            "Thymic involution begins after puberty: thymic "
            "tissue is lost at roughly 3% per year until about "
            "age 35–45, then at roughly 1% per year (S2).",
        "arterial_supply": None,
    })
    r["sources"] = OrderedDict([
        ("position", ["S2", "S3"]),
        ("structure", ["S2"]),
        ("function", ["S2"]),
        ("age_changes", ["S2"]),
    ])
    r["verify"] = [
        "arterial_supply: no value asserted — none of the "
        "sources consulted in this session states the thymus's "
        "arterial supply; the field stays null rather than "
        "unsourced",
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("The release carries the thymus as an organ only "
                 "in the PART-OF table, filed under the contents "
                 "of the anterior mediastinum; the IS-A table "
                 "carries only its lobe line.")
    records.append(finish(r,
                          core=["position", "structure", "function"],
                          soft=["age_changes", "arterial_supply"]))

    # ---------------- the drainage pathway ----------------
    r = base("pathway.lymphatic-drainage", "Lymphatic drainage "
             "pathway", "pathway", "Lymphatic pathway")
    typed(r, {
        "sequence": [
            "lymphatic capillaries — blind-ended terminal "
            "lymphatics in the tissues, where lymph forms",
            "lymphatic vessels — valved collecting vessels, "
            "bead-like where their valves constrict them; lymph "
            "passes through lymph nodes along the way",
            "lymphatic trunks — the great collecting trunks of "
            "the body regions",
            "collecting ducts — the right lymphatic duct and the "
            "thoracic duct",
            "the subclavian vein at the junction of the jugular "
            "and subclavian veins, where lymph re-enters the "
            "blood",
        ],
        "function":
            "About 20 litres of plasma are filtered out of the "
            "blood each day; about 17 litres are reabsorbed and "
            "the remaining roughly 3 litres become lymph, which "
            "this pathway returns to the venous blood (S2). The "
            "system has no central pump: lymph is moved by "
            "skeletal muscle action and breathing, and one-way "
            "valves prevent backflow (S2). Superficial lymphatics "
            "follow the veins and deep lymphatics follow the "
            "arteries (S2).",
        "ducts_and_territories":
            "The right lymphatic duct drains the right side of "
            "the head, the right thorax and the right upper limb "
            "into the right subclavian vein. The thoracic duct "
            "drains everything else into the left subclavian vein; "
            "it begins just beneath the diaphragm in the cisterna "
            "chyli, which receives the right and left lumbar "
            "trunks and the intestinal trunk (S2). In the small "
            "intestine, specialised lymphatics — the lacteals — "
            "carry the milky fat-laden lymph called chyle (S2).",
    })
    r["sources"] = OrderedDict([
        ("sequence", ["S2"]),
        ("function", ["S2"]),
        ("ducts_and_territories", ["S2"]),
    ])
    r["verify"] = [
        ABSENCE + " — this holds for every station of the "
        "pathway: no capillary, vessel, trunk or duct of the "
        "lymphatic system exists in the release, and the "
        "thoracic duct's absence was already probe-verified by "
        "Milestone 5 against the same tables",
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("The pathway is the system the dataset does not "
                 "carry: it exists here as sourced clinical text "
                 "only, in the order the consulted source gives.")
    records.append(finish(r,
                          core=["sequence", "function"],
                          soft=["ducts_and_territories"]))

    # ---------------- lymph nodes and lymphoid tissue ----------------
    r = base("structure.lymph-nodes", "Lymph nodes and lymphoid "
             "tissue", "structure", "Lymphoid tissue")
    typed(r, {
        "nodes":
            "The body carries roughly 500–600 lymph nodes — "
            "small, bean-shaped organs that act as filters of the "
            "lymph, clustered near the groin, the armpits, the "
            "neck, the chest and the abdomen (S2). Within a node, "
            "lymph enters by afferent vessels, passes through the "
            "subcapsular sinus, the cortex — which holds follicles "
            "with germinal centres — and the medulla with its "
            "cords and sinuses, and leaves by efferent vessels "
            "(S2).",
        "tonsils":
            "The tonsils are lymphoid nodules arranged along the "
            "inner surface of the pharynx: the pharyngeal tonsil "
            "at the roof of the posterior wall of the superior "
            "nasopharynx — called the adenoid when swollen — and "
            "the palatine tonsils on either side; they carry an "
            "incomplete capsule and tonsillar crypts (S2).",
        "malt":
            "Beyond the nodes, lymphoid follicles aggregate "
            "under mucous membranes as mucosa-associated lymphoid "
            "tissue (MALT) across the gastrointestinal tract, "
            "breast, lungs and eyes (S2). In the small intestine "
            "these aggregates are Peyer's patches, whose M "
            "(microfold) cells sample the gut lumen; the appendix "
            "also carries MALT, and bronchus-associated lymphoid "
            "tissue (BALT) sits along the bifurcations of the "
            "bronchi (S2). The appendix itself is the digestive "
            "module's record (Milestone 11); no MALT structure "
            "has a concept in the release.",
    })
    r["sources"] = OrderedDict([
        ("nodes", ["S2"]),
        ("tonsils", ["S2"]),
        ("malt", ["S2"]),
    ])
    r["verify"] = [
        ABSENCE + " — no lymph node, tonsil or MALT concept of "
        "any kind exists in the release",
        "ta_name: not asserted — no TA2 term list was consulted "
        "in this session",
    ]
    r["note"] = ("The filtering tissue of the system, carried as "
                 "sourced text; the geometry layer has none of it.")
    records.append(finish(r,
                          core=["nodes", "tonsils"],
                          soft=["malt"]))

    tiers = {}
    for rec in records:
        tiers[rec["sourcing_tier"]] = tiers.get(rec["sourcing_tier"],
                                                0) + 1
    doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA lymphatic system clinical records "
                      "— Milestone 13"),
            ("generated_by", "tools/build_lymph_records.py"),
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
             "The tranche is two organ records plus two sourced-"
             "text records for the parts of the system the "
             "dataset does not carry at all — the drainage "
             "pathway and the lymphoid tissue; no geometry is "
             "invented for them and their absence from the "
             "dataset is recorded on each."),
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
