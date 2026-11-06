#!/usr/bin/env python3
"""ANATOMICA Milestone 15 — integumentary system clinical
tranche.

Field-sourcing rule (set in Milestone 4, binding since): every
field value comes only from the sources actually consulted in
this session, and the record cites the source(s) it used for
that field in its `sources` map. A field the consulted sources
do not support is null and carries a `verify` entry instead.

Sources consulted in-session, 2026-11-06:
  S1  OpenStax Anatomy and Physiology 2e, §5.1 "Layers of
      the Skin" (openstax.org): the skin as an organ of two
      main layers — epidermis (keratinized stratified
      squamous epithelium, avascular; thin skin four strata,
      thick skin five with the stratum lucidum; strata from
      deep to superficial: basale, spinosum, granulosum,
      lucidum, corneum) over dermis (papillary layer of loose
      areolar tissue with dermal papillae, Meissner
      corpuscles and capillaries; reticular layer of dense
      irregular connective tissue, well vascularised, with a
      rich sensory and sympathetic supply) over the
      hypodermis (subcutaneous layer / superficial fascia —
      not strictly part of the skin; loose areolar and
      adipose tissue storing fat, insulating and cushioning);
      keratinocytes made in the stratum basale, melanocytes
      and melanin, Merkel cells as touch receptors,
      Langerhans cells as macrophages of the spinosum; the
      dermis housing vessels, follicles and sweat glands.
  S2  OpenStax Anatomy and Physiology 2e, §5.2 "Accessory
      Structures of the Skin" (openstax.org): hair as a
      keratinous filament from the follicle — shaft, root,
      bulb, matrix, papilla; medulla, cortex and cuticle;
      arrector pili and the hair root plexus; hair functions
      (protection, sensory input, thermoregulation,
      communication), head hair protecting the skull from
      the sun, eyebrow hair preventing sweat and particles
      from dripping into the eyes, eyelashes trapping dust;
      the growth cycle (anagen 2-7 years, catagen 2-3 weeks,
      telogen 2-4 months, ~0.3 mm/day, ~50 hairs lost per
      day) and melanin colour from the papilla; nails — nail
      bed, body, root, matrix, lateral fold, eponychium
      (cuticle), lunula, hyponychium — protecting the digits
      and back-supporting the fingers; eccrine glands (all
      over the surface, abundant on palms, soles and
      forehead; hypotonic sweat, merocrine; primary
      thermoregulation) and apocrine glands (axillary and
      genital regions, ducts into follicles, nervous and
      hormonal control); sebaceous glands (associated with
      follicles, sebum lubricating and waterproofing,
      antibacterial fatty acids, hormone-stimulated from
      puberty).
  S3  OpenStax Anatomy and Physiology 2e, §5.3 "Functions
      of the Integumentary System" (openstax.org): protection
      against microorganisms, chemicals, abrasion, water
      loss and UV; sensory function (Meissner corpuscles for
      light touch, Pacinian corpuscles for vibration, Merkel
      cells, pain and temperature receptors, motor nerves to
      the arrector pili and glands); thermoregulation
      (sympathetic monitoring, ~500 mL/day insensible
      perspiration, up to 0.7-1.5 L/hour of sweat in activity,
      dermal arteriole dilation and constriction); vitamin D
      synthesis in the epidermis; the hypodermis storing fat
      and cushioning.
  S4  TeachMeAnatomy — "The Breasts" (teachmeanatomy.info):
      paired structures of the anterior thoracic wall,
      present in both sexes and prominent in females after
      puberty, containing the mammary glands — "an accessory
      gland of the female reproductive system" in the
      article's own framing, and, in its structure section,
      "modified sweat glands": 15-20 lobules of alveoli,
      each drained by a lactiferous duct converging at the
      nipple; the circular body and axillary tail; nipple
      and areola (with its sebaceous glands); fibrous and
      fatty stroma, the suspensory ligaments of Cooper
      attaching to dermis and pectoral fascia; the
      retromammary space; extent from the lateral sternal
      border to the mid-axillary line and the 2nd to 6th
      costal cartilages, superficial to pectoralis major
      and serratus anterior; medial supply from the internal
      thoracic artery, lateral supply from lateral thoracic,
      thoracoacromial, lateral mammary (posterior
      intercostal) and anterior intercostal mammary
      branches; veins to the axillary and internal thoracic
      veins; lymphatics to axillary nodes (75%), parasternal
      (20%) and posterior intercostal (5%), the nipple and
      areola to the subareolar plexus; innervation by the
      anterior and lateral cutaneous branches of the 4th to
      6th intercostal nerves, which do not control milk
      production — prolactin and oxytocin from the pituitary
      do.
  S5  The ANATOMICA project datasets themselves, consulted
      in-session: this milestone's BP3D 4.0 census
      (tools/integ_map.py — the twelve-concept universe, the
      four mesh files, the probe counts), the reproductive
      module (Milestone 14 — its inventory and tranche carry
      no mammary or breast record; the mons pubis is its
      only female record and the pubic hair's PART-OF
      parent), and the TotalSegmentator label index
      (Milestone 3 — the 'face' region mask adjudication).
      Used only for dataset facts and cross-module pointers,
      never for anatomy the other sources state.

The tranche's shape follows the dataset's, which here means
it mostly follows the dataset's absences. The skin the
release carries is one undifferentiated shell, so the
layered anatomy — epidermis with its five strata, dermis
with its two layers, hypodermis — is carried as fully
sourced records over a total layer absence, each with the
absence on the record (the Milestone 9/14 pattern). Hair is
the one appendage with geometry: the class record and the
eyebrow and head-hair records are sourced; the trunk and
pubic records are tier C, the consulted sources treating
hair in general and the head and brows in particular but
never the trunk or pubic hair separately — recorded thin,
not padded. Nails and both cutaneous glands are sourced
records over absences. The mammary gland closes the
tranche and the module: absent from the release under every
name and filed by it under neither candidate system, it is
owned here by adjudication — the consulted source defines
the mammary glands as modified sweat glands, which makes
them cutaneous glands by kind and of a piece with this
module's gland records, while the reproductive module
completed its census without claiming them. The
counter-consideration is recorded on the record itself:
the same source calls the gland an accessory gland of the
female reproductive system, and lactation is reproductive
function. The decision is a stated convention, not a
dataset fact, and the checker gates its terms: absence
recorded, no geometry, no mammary record in the
reproductive module.

Tiers: A = every field valued and cited; B = a soft field is
null; C = a core field is null. Tier discipline is enforced
by finish() and re-derived independently by
tools/integ_check.py.
"""
import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "data", "integumentary",
                   "integumentary-inventory.json")
OUT = os.path.join(ROOT, "data", "integumentary",
                   "integumentary.json")

SOURCES = OrderedDict([
    ("S1", "OpenStax Anatomy and Physiology 2e, §5.1 Layers "
           "of the Skin (openstax.org): skin of two main "
           "layers; epidermis keratinized stratified squamous "
           "and avascular, thin skin four strata and thick "
           "skin five (stratum lucidum between granulosum "
           "and corneum), strata deep to superficial basale, "
           "spinosum, granulosum, lucidum, corneum; "
           "keratinocytes from the stratum basale, "
           "melanocytes making melanin against UV, Merkel "
           "cells as touch receptors, Langerhans cells as "
           "macrophages; dermis of papillary (loose areolar, "
           "dermal papillae, Meissner corpuscles) and "
           "reticular (dense irregular, well vascularised, "
           "rich sensory and sympathetic supply) layers "
           "housing vessels, follicles and sweat glands; "
           "hypodermis (subcutaneous layer, superficial "
           "fascia) of loose areolar and adipose tissue, not "
           "strictly part of the skin, storing fat and "
           "providing insulation and cushioning"),
    ("S2", "OpenStax Anatomy and Physiology 2e, §5.2 "
           "Accessory Structures of the Skin (openstax.org): "
           "accessory structures (hair, nails, sweat and "
           "sebaceous glands) originating from the epidermis; "
           "hair a keratinous filament — follicle, shaft, "
           "root, bulb, matrix, papilla, medulla/cortex/"
           "cuticle, arrector pili, root plexus; head hair "
           "protecting the skull from the sun, eyebrows "
           "keeping sweat and particles from the eyes, "
           "eyelashes trapping dust; growth cycle anagen "
           "2-7 years, catagen 2-3 weeks, telogen 2-4 "
           "months, ~0.3 mm/day, ~50 hairs shed per day; "
           "nails — bed, body, root, matrix, lateral fold, "
           "eponychium, lunula, hyponychium — protecting the "
           "digits; eccrine glands over the whole surface "
           "(palms, soles, forehead), hypotonic sweat by "
           "exocytosis, primary thermoregulation; apocrine "
           "glands of armpits and genital regions emptying "
           "into follicles under nervous and hormonal "
           "control; sebaceous glands with follicles, sebum "
           "lubricating and waterproofing, antibacterial "
           "fatty acids, hormone-driven from puberty"),
    ("S3", "OpenStax Anatomy and Physiology 2e, §5.3 "
           "Functions of the Integumentary System "
           "(openstax.org): protection against "
           "microorganisms, chemicals, abrasion, dehydration "
           "and UV; sensation via Meissner and Pacinian "
           "corpuscles, Merkel cells and pain/temperature "
           "receptors, densest at the fingertips; "
           "thermoregulation under sympathetic monitoring — "
           "~500 mL/day insensible perspiration, 0.7-1.5 "
           "L/hour of sweat in activity, dermal arteriole "
           "dilation and constriction; epidermal vitamin D "
           "synthesis; the hypodermis storing fat, "
           "cushioning and insulating"),
    ("S4", "TeachMeAnatomy — The Breasts "
           "(teachmeanatomy.info): paired anterior thoracic "
           "structures in both sexes, prominent in females "
           "after puberty; mammary glands called an "
           "accessory gland of the female reproductive "
           "system and defined structurally as modified "
           "sweat glands — 15-20 lobules of alveoli, each "
           "lobule drained by a lactiferous duct converging "
           "at the nipple; circular body and axillary tail; "
           "nipple and areola with sebaceous glands; "
           "suspensory ligaments of Cooper; retromammary "
           "space; extent lateral sternum to mid-axillary "
           "line, 2nd-6th costal cartilages, on pectoralis "
           "major and serratus anterior; internal thoracic "
           "artery medially, lateral thoracic, "
           "thoracoacromial, lateral mammary and anterior "
           "intercostal mammary branches laterally; veins "
           "to axillary and internal thoracic; lymphatics "
           "axillary 75%, parasternal 20%, posterior "
           "intercostal 5%, nipple/areola to the subareolar "
           "plexus; innervation by cutaneous branches of "
           "the 4th-6th intercostal nerves, milk production "
           "under prolactin and oxytocin, not the nerves"),
    ("S5", "ANATOMICA project datasets consulted "
           "in-session: this milestone's BP3D 4.0 census "
           "(tools/integ_map.py), the reproductive module "
           "inventory and tranche (Milestone 14 — no "
           "mammary or breast record there; the mons pubis "
           "as the pubic hair's PART-OF parent) and the "
           "TotalSegmentator label index (Milestone 3 — "
           "'face' adjudicated a region mask) — dataset "
           "facts and cross-module pointers only"),
])

ABSENCE = ("no BP3D 4.0 concept exists for this structure "
           "(probe-verified over all six release tables by "
           "tools/integ_map.py); the record is sourced text "
           "only and links no geometry")
TA_VERIFY = ("ta_name: not asserted — no TA2 term list was "
             "consulted in this session")


def base(rid, name, typ, group):
    return OrderedDict([
        ("id", rid), ("name", name), ("type", typ),
        ("group", group),
        ("ta_name", None), ("sources", OrderedDict()),
        ("verify", []), ("note", None),
        ("geometry_record_ids", []),
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
    entry records the dataset absence (ABSENCE).
    """
    problems = []
    for fname in core + soft:
        val = rec.get(fname)
        if val is None:
            if not any(fname in v for v in rec["verify"]):
                problems.append(
                    f"{rec['id']}: null field {fname} has no "
                    "verify entry naming it")
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

    # ============ the skin and its layers ============
    r = base("organ.skin", "Skin", "organ", "Skin and its layers")
    link(r, inv_by_name, ["skin"])
    typed(r, {
        "description":
            "The body's protective organ: multiple layers of "
            "cells and tissues held to underlying structures "
            "by connective tissue, made of two main layers — "
            "the epidermis of closely packed epithelial cells "
            "and the dermis of dense, irregular connective "
            "tissue housing blood vessels, hair follicles, "
            "sweat glands and other structures — with the "
            "hypodermis of loose connective and fatty tissue "
            "closely associated beneath it. The skin and its "
            "accessory structures make up the integumentary "
            "system, which provides the body with overall "
            "protection (S1). In the release the skin is one "
            "concept and one whole-body mesh shell: no "
            "regional skin and no layer of it has a concept "
            "(S5).",
        "layers": [
            "epidermis",
            "dermis",
            "hypodermis (subcutaneous layer — closely "
            "associated, not strictly part of the skin)"],
        "function":
            "Protection first: against invasion by "
            "microorganisms, chemicals and other "
            "environmental factors, against dehydration, and "
            "against UV sunlight; the skin also acts as a "
            "sensory organ, modulates body temperature and "
            "electrolyte balance, and synthesizes vitamin D "
            "— its epidermal layer produces cholecalciferol "
            "from a cholesterol derivative under UV "
            "radiation (S3).",
        "cells":
            "The epidermis is populated from the stratum "
            "basale: keratinocytes, manufactured there and "
            "pushed superficially, make and store keratin — "
            "the fibrous protein that gives skin, hair and "
            "nails their hardness and water resistance; "
            "melanocytes dispersed among the basal cells "
            "produce melanin, colouring skin and hair and "
            "shielding living epidermal cells from UV "
            "damage; Merkel cells of the basale act as touch "
            "receptors; Langerhans cells of the stratum "
            "spinosum act as macrophages (S1).",
        "vascularisation":
            "The epidermis is avascular — it has no blood "
            "vessels within it. The dermis is well "
            "vascularised, the reticular layer especially; "
            "its arterioles dilate to dissipate heat through "
            "the skin and constrict to conserve it, the skin "
            "reddening with exercise and paling in the cold "
            "(S1, S3). No consulted source names the skin's "
            "arteries individually, so no named supply is "
            "asserted.",
        "innervation":
            "The dermis carries numerous sensory, autonomic "
            "and sympathetic nerve fibres ensuring "
            "communication to and from the brain: Meissner "
            "corpuscles answering light touch and Pacinian "
            "corpuscles vibration, Merkel cells, and pain "
            "and temperature receptors scattered throughout, "
            "most concentrated at the fingertips; motor "
            "nerves supply the arrector pili muscles and the "
            "glands (S1, S3). No named cutaneous nerve is "
            "asserted — none is named by the consulted "
            "sources for the skin in general.",
    })
    r["sources"] = OrderedDict([
        ("description", ["S1", "S5"]),
        ("layers", ["S1"]),
        ("function", ["S3"]),
        ("cells", ["S1"]),
        ("vascularisation", ["S1", "S3"]),
        ("innervation", ["S1", "S3"]),
    ])
    r["verify"] = [TA_VERIFY]
    r["note"] = ("The release's skin record is the shell this "
                 "clinical record describes; the layers it "
                 "names are the next three records, each "
                 "carried over a total concept absence.")
    records.append(finish(
        r, core=["description", "layers", "function"],
        soft=["cells", "vascularisation", "innervation"]))

    r = base("structure.epidermis", "Epidermis", "structure",
             "Skin and its layers")
    typed(r, {
        "description":
            "The superficial layer of the skin: keratinized, "
            "stratified squamous epithelium, avascular, made "
            "of four or five layers of epithelial cells "
            "depending on location — four in the thin skin "
            "that covers most of the body, five in the thick "
            "skin of the palms and soles, which adds the "
            "stratum lucidum (S1). The release has no "
            "epidermis concept: its only layer-named concept "
            "is a 'subdivision of epidermis' class under "
            "which the appendages are filed (S5).",
        "strata": [
            "stratum basale", "stratum spinosum",
            "stratum granulosum",
            "stratum lucidum (thick skin only)",
            "stratum corneum"],
        "function":
            "The barrier layer: its keratin and the "
            "water-repelling glycolipids released from the "
            "stratum spinosum upward make the skin relatively "
            "waterproof; the dry, dead stratum corneum — 15 "
            "to 30 cell layers, replaced over about four "
            "weeks — resists microbial penetration, "
            "dehydration and abrasion; and the epidermis "
            "synthesizes vitamin D under UV (S1, S3).",
        "cells":
            "All its cells but the basal layer's are "
            "keratinocytes, produced by mitosis in the "
            "stratum basale and pushed superficially as new "
            "cells form, flattening and dying through the "
            "granulosum until only keratin, keratohyalin and "
            "cell membranes remain at the surface (S1).",
        "forms":
            "Thin skin (four strata) covers most of the "
            "body; thick skin (five, with the stratum "
            "lucidum of dead, eleidin-packed keratinocytes) "
            "is found only on the palms of the hands and the "
            "soles of the feet (S1).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S1", "S5"]),
        ("strata", ["S1"]),
        ("function", ["S1", "S3"]),
        ("cells", ["S1"]),
        ("forms", ["S1"]),
    ])
    r["verify"] = [ABSENCE, TA_VERIFY]
    r["note"] = ("Sourced text over a total absence: the "
                 "release's 'subdivision of epidermis' "
                 "concept (FMA70593) is a tissue class "
                 "carrying the appendage line's geometry, "
                 "not an epidermis — it is a grouping class "
                 "of the inventory, and this record links no "
                 "geometry.")
    records.append(finish(
        r, core=["description", "strata", "function"],
        soft=["cells", "forms"]))

    r = base("structure.dermis", "Dermis", "structure",
             "Skin and its layers")
    typed(r, {
        "description":
            "The core of the integumentary system beneath "
            "the epidermis: two layers of connective tissue "
            "composing an interconnected mesh of elastin and "
            "collagenous fibres produced by fibroblasts, "
            "containing blood and lymph vessels, nerves, "
            "hair follicles and sweat glands (S1). The "
            "release has no dermis concept (exact-name "
            "probe-verified) (S5).",
        "layers": ["papillary layer", "reticular layer"],
        "function":
            "Support and supply: collagen gives the skin "
            "structure and tensile strength and binds water "
            "to keep it hydrated, elastin gives it the "
            "elasticity that enables movement; the layer "
            "houses and feeds the structures the epidermis "
            "cannot — vessels, nerves, follicles and glands "
            "— and its blood flow is the skin's radiator, "
            "dilating and constricting in thermoregulation "
            "(S1, S3).",
        "contents":
            "The papillary layer (loose areolar tissue) "
            "projects dermal papillae into the stratum "
            "basale, strengthening the epidermal junction — "
            "their meeting with basal cells forms "
            "fingerprints — and holds fibroblasts, a few "
            "adipocytes, small vessels, phagocytes, "
            "lymphatic capillaries, nerve fibres and "
            "Meissner corpuscles; the much thicker reticular "
            "layer (dense irregular tissue) is well "
            "vascularised with a rich sensory and "
            "sympathetic nerve supply (S1).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S1", "S5"]),
        ("layers", ["S1"]),
        ("function", ["S1", "S3"]),
        ("contents", ["S1"]),
    ])
    r["verify"] = [ABSENCE, TA_VERIFY]
    records.append(finish(
        r, core=["description", "layers", "function"],
        soft=["contents"]))

    r = base("structure.hypodermis", "Hypodermis", "structure",
             "Skin and its layers")
    typed(r, {
        "description":
            "The layer directly below the dermis — also "
            "called the subcutaneous layer or superficial "
            "fascia — connecting the skin to the underlying "
            "fascia of the bones and muscles. It is not "
            "strictly a part of the skin, though its border "
            "with the dermis can be difficult to distinguish "
            "(S1). The release has no hypodermis or "
            "subcutaneous concept under any name (S5).",
        "function":
            "Fat storage, insulation and cushioning: its "
            "adipose tissue is an energy reserve, insulates "
            "the body against heat loss and cushions "
            "underlying structures against trauma (S1, S3).",
        "composition":
            "Well-vascularised, loose areolar connective "
            "tissue and adipose tissue of fat-storing "
            "adipocytes; where the fat is deposited depends "
            "on hormones and genetic factors, and its "
            "distribution differs between males and females "
            "(S1).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S1", "S5"]),
        ("function", ["S1", "S3"]),
        ("composition", ["S1"]),
    ])
    r["verify"] = [ABSENCE, TA_VERIFY]
    r["note"] = ("The clinical name 'superficial fascia' for "
                 "this layer is OpenStax's (S1); the "
                 "release's fascial concepts are the deep "
                 "investing fascia of the limbs, a different "
                 "structure, rejected by this module's sweep "
                 "and censused by no module (S5).")
    records.append(finish(
        r, core=["description", "function"],
        soft=["composition"]))

    # ============ the appendages ============
    r = base("structure.hair", "Hair", "structure", "Appendages")
    link(r, inv_by_name, ["hair"])
    typed(r, {
        "description":
            "A keratinous filament growing out of the "
            "epidermis, primarily dead, keratinized cells: "
            "strands originate in an epidermal penetration "
            "of the dermis called the hair follicle, the "
            "exposed part is the shaft, the anchored part "
            "below the surface the root, ending deep in the "
            "dermis at the bulb. Accessory structures like "
            "hair embryologically originate from the "
            "epidermis and can extend down through the "
            "dermis into the hypodermis (S2). The release "
            "carries the hair class and three regional "
            "records — its appendage line's whole geometry "
            "is two mesh files (S5).",
        "parts": [
            "hair follicle", "hair shaft", "hair root",
            "hair bulb", "hair matrix", "hair papilla",
            "medulla", "cortex", "cuticle",
            "arrector pili muscle", "hair root plexus"],
        "function":
            "Protection, sensory input, thermoregulation "
            "and communication: hair on the head protects "
            "the skull from the sun; the sensory innervation "
            "of the hair root plexus makes hair extremely "
            "sensitive to air movement and disturbance; and "
            "each root's arrector pili muscle, contracting "
            "on sympathetic signals, raises the shaft to "
            "trap an insulating layer of air — visible in "
            "humans as goose bumps (S2).",
        "growth_cycle":
            "Growth in three phases: anagen, cells dividing "
            "rapidly at the root, lasting typically 2 to 7 "
            "years; catagen, 2 to 3 weeks of transition; "
            "telogen, 2 to 4 months of rest, after which a "
            "new hair pushes the old out. Hair grows about "
            "0.3 mm per day in anagen, and on average 50 "
            "hairs are lost and replaced per day (S2).",
        "colour":
            "Hair takes its colour from melanin produced by "
            "melanocytes in the hair papilla; the type of "
            "melanin is genetically determined, and as "
            "production decreases with age the hair greys "
            "and whitens (S2).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S5"]),
        ("parts", ["S2"]),
        ("function", ["S2"]),
        ("growth_cycle", ["S2"]),
        ("colour", ["S2"]),
    ])
    r["verify"] = [TA_VERIFY]
    r["note"] = ("The parts list names two structures the "
                 "release does not carry — the follicle and "
                 "the arrector pili are probe-verified "
                 "absences (S5); they are clinical anatomy "
                 "from S2, not dataset concepts.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["growth_cycle", "colour"]))

    r = base("structure.hair-of-head", "Hair of head", "structure",
             "Appendages")
    link(r, inv_by_name, ["hair of head"])
    typed(r, {
        "description":
            "The hair of the scalp — in the release a "
            "regional record of the hair class with its own "
            "mesh file (FJ2813), the head half of the hair "
            "geometry's two-file partition (S5). As hair, it "
            "is the keratinous filament of S2, growing from "
            "follicles of the scalp's epidermis.",
        "function":
            "Hair on the head protects the skull from the "
            "sun (S2).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S5"]),
        ("function", ["S2"]),
    ])
    r["verify"] = [TA_VERIFY]
    records.append(finish(r, core=["description", "function"],
                          soft=[]))

    r = base("structure.hair-of-trunk", "Hair of trunk",
             "structure", "Appendages")
    link(r, inv_by_name, ["hair of trunk"])
    typed(r, {
        "description":
            "The hair of the trunk — in the release a "
            "regional record of the hair class, sharing its "
            "single mesh file (FJ2815) with its child, the "
            "pubic hair (S5). As hair, it is the keratinous "
            "filament of S2.",
        "function": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S5"]),
    ])
    r["verify"] = [
        "function: not asserted — no consulted source "
        "treats trunk hair separately from hair in general; "
        "the general functions are carried on "
        "structure.hair and are not repeated here as if "
        "they were region-specific",
        TA_VERIFY]
    r["note"] = ("Recorded thin by design (the mons pubis "
                 "precedent, Milestone 14): the dataset gives "
                 "the region a record and a mesh; the "
                 "consulted literature gives it no separate "
                 "account.")
    records.append(finish(r, core=["description", "function"],
                          soft=[]))

    r = base("structure.pubic-hair", "Pubic hair", "structure",
             "Appendages")
    link(r, inv_by_name, ["pubic hair"])
    typed(r, {
        "description":
            "The hair of the pubic region — in the release "
            "filed two ways: IS-A under hair of trunk in "
            "this module's line, and PART-OF under the mons "
            "pubis, the reproductive module's only female "
            "record; it shares the trunk hair's mesh file "
            "(FJ2815) in both tables (S5). As hair, it is "
            "the keratinous filament of S2.",
        "function": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S5"]),
    ])
    r["verify"] = [
        "function: not asserted — no consulted source "
        "treats pubic hair separately from hair in "
        "general; the general functions are carried on "
        "structure.hair",
        TA_VERIFY]
    r["note"] = ("The one clinical record of this tranche "
                 "whose dataset concept sits in two modules' "
                 "filings; the concept is owned by this "
                 "module's inventory and cross-filed under "
                 "the reproductive module's mons pubis (S5).")
    records.append(finish(r, core=["description", "function"],
                          soft=[]))

    r = base("structure.eyebrow", "Eyebrow", "structure",
             "Appendages")
    link(r, inv_by_name, ["eyebrow"])
    typed(r, {
        "description":
            "The hair of the brow — in the release a single "
            "concept under 'set of facial hairs', resolving "
            "with both of its set classes to one mesh file "
            "(FJ2812); the only named facial hair the "
            "release carries, there being no eyelash concept "
            "in it (S5).",
        "function":
            "Hair of the eyebrows prevents sweat and other "
            "particles from dripping into and bothering the "
            "eyes (S2).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S5"]),
        ("function", ["S2"]),
    ])
    r["verify"] = [TA_VERIFY]
    records.append(finish(r, core=["description", "function"],
                          soft=[]))

    r = base("structure.nail", "Nail", "structure", "Appendages")
    typed(r, {
        "description":
            "An accessory structure formed on a specialized "
            "structure of the epidermis at the tips of the "
            "fingers and toes: the nail body, composed of "
            "densely packed dead keratinocytes, is formed on "
            "the nail bed and grows continuously from a "
            "matrix of proliferating cells of the stratum "
            "basale at the nail root (S2). The release has "
            "no nail concept in any form — 'nail' and "
            "'unguis' are zero-hit in all six tables (S5).",
        "parts": [
            "nail bed", "nail root", "nail matrix",
            "nail body", "lateral nail fold",
            "eponychium (nail cuticle)", "lunula",
            "hyponychium"],
        "function":
            "The nail body protects the tips of the fingers "
            "and toes — the farthest extremities, under the "
            "maximum mechanical stress — and forms a "
            "back-support for picking up small objects with "
            "the fingers (S2).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S5"]),
        ("parts", ["S2"]),
        ("function", ["S2"]),
    ])
    r["verify"] = [ABSENCE, TA_VERIFY]
    records.append(finish(
        r, core=["description", "parts", "function"], soft=[]))

    r = base("gland.sebaceous-glands", "Sebaceous glands",
             "gland", "Appendages")
    typed(r, {
        "description":
            "Oil glands found all over the body, most of "
            "them associated with hair follicles, generating "
            "and excreting sebum onto the skin surface (S2). "
            "The release has no sebaceous concept — "
            "'sebaceous' is zero-hit in all six tables (S5).",
        "secretion":
            "Sebum, a mixture of lipids, excreted onto the "
            "skin surface and into the follicle (S2).",
        "function":
            "To lubricate and waterproof the skin and hair: "
            "sebum keeps the dry, dead keratinized layer of "
            "the stratum corneum pliable, its fatty acids "
            "are antibacterial, and it prevents water loss "
            "from the skin in low-humidity environments "
            "(S2).",
        "activation":
            "Sebum secretion is stimulated by hormones, "
            "many of which do not become active until "
            "puberty, so the glands are relatively inactive "
            "during childhood (S2). The areola's sebaceous "
            "glands enlarge during pregnancy, secreting an "
            "oily lubricant for the nipple (S4).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S5"]),
        ("secretion", ["S2"]),
        ("function", ["S2"]),
        ("activation", ["S2", "S4"]),
    ])
    r["verify"] = [ABSENCE, TA_VERIFY]
    records.append(finish(
        r, core=["description", "secretion", "function"],
        soft=["activation"]))

    r = base("gland.sweat-glands", "Sweat glands", "gland",
             "Appendages")
    typed(r, {
        "description":
            "Sudoriferous glands that develop from epidermal "
            "projections into the dermis, classified as "
            "merocrine glands — their secretions are "
            "excreted by exocytosis through a duct without "
            "affecting the gland's cells. There are two "
            "types, eccrine and apocrine, each secreting a "
            "slightly different product (S2). The release "
            "has no sweat-gland concept — 'sweat' and "
            "'sudoriferous' are zero-hit in all six tables "
            "(S5).",
        "types": [
            "eccrine sweat gland — a coiled gland lying "
            "deep in the dermis, its duct rising to a pore "
            "on the surface; found all over the skin but "
            "especially abundant on the palms, soles and "
            "forehead; produces a hypotonic sweat of mostly "
            "water with some salt, antibodies, traces of "
            "metabolic waste and the antimicrobial peptide "
            "dermcidin",
            "apocrine sweat gland — larger and deeper, "
            "usually associated with hair follicles in "
            "densely hairy areas such as the armpits and "
            "genital regions, its duct normally emptying "
            "into the follicle; its sweat adds organic "
            "compounds that thicken it and subject it to "
            "bacterial decomposition and smell; release is "
            "under both nervous and hormonal control"],
        "function":
            "Thermoregulation: when the body becomes warm "
            "the glands produce sweat to cool it — a primary "
            "component of temperature homeostasis, under "
            "sympathetic control, from about 500 mL a day "
            "of insensible perspiration to 0.7-1.5 litres "
            "per hour in an active person; the sweat's "
            "dermcidin also deters microbes from "
            "over-colonizing the skin surface (S2, S3).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S5"]),
        ("types", ["S2"]),
        ("function", ["S2", "S3"]),
    ])
    r["verify"] = [ABSENCE, TA_VERIFY]
    r["note"] = ("The mammary gland record that follows is "
                 "this gland family's other member by kind: "
                 "the consulted source defines the mammary "
                 "glands as modified sweat glands (S4).")
    records.append(finish(
        r, core=["description", "types", "function"], soft=[]))

    # ============ the mammary gland (ownership adjudicated) ====
    r = base("organ.mammary-gland", "Mammary gland and breast",
             "organ", "The mammary gland")
    typed(r, {
        "description":
            "The breasts are paired structures on the "
            "anterior thoracic wall in the pectoral region, "
            "present in both males and females and more "
            "prominent in females following puberty; in "
            "females they contain the mammary glands, the "
            "key structures involved in lactation. The "
            "mammary glands are modified sweat glands: a "
            "series of ducts and secretory lobules (15-20) "
            "surrounded by a connective tissue stroma (S4). "
            "The release carries no mammary, breast, nipple "
            "or areola concept under any name — the gland "
            "exists in this module as this record alone "
            "(S5).",
        "parts": [
            "circular body", "axillary tail", "nipple",
            "areola", "secretory lobules (15-20)",
            "alveoli", "lactiferous ducts",
            "suspensory ligaments of Cooper",
            "fibrous stroma", "fatty stroma",
            "retromammary space"],
        "function":
            "Lactation: the gland produces and secretes "
            "milk, each lobule's alveoli draining by a "
            "single lactiferous duct, the ducts converging "
            "at the nipple like spokes of a wheel. "
            "Production and secretion are regulated by the "
            "hormones prolactin and oxytocin from the "
            "pituitary gland — not by the breast's own "
            "nerves (S4).",
        "relations":
            "The breast extends horizontally from the "
            "lateral border of the sternum to the "
            "mid-axillary line and vertically between the "
            "2nd and 6th costal cartilages, lying "
            "superficially to the pectoralis major and "
            "serratus anterior; its base lies on the "
            "pectoral fascia, with the loose connective "
            "tissue of the retromammary space between, and "
            "the suspensory ligaments attach it to the "
            "dermis and the pectoral fascia and separate "
            "its lobules (S4).",
        "arterial_supply":
            "The medial aspect is supplied by the internal "
            "thoracic artery, a branch of the subclavian; "
            "the lateral part by four vessels — the lateral "
            "thoracic and thoracoacromial branches of the "
            "axillary artery, the lateral mammary branches "
            "of the posterior intercostal arteries in the "
            "2nd, 3rd and 4th spaces, and the mammary branch "
            "of the anterior intercostal artery (S4). The "
            "vessels are named here as the source names "
            "them; no cardiovascular record ids are asserted "
            "for them.",
        "venous_drainage":
            "The veins correspond with the arteries, "
            "draining into the axillary and internal "
            "thoracic veins (S4).",
        "lymphatic_drainage":
            "Of great clinical importance for the metastasis "
            "of breast cancer: three node groups receive the "
            "breast's lymph — the axillary nodes (75%), the "
            "parasternal nodes (20%) and the posterior "
            "intercostal nodes (5%). The skin of the breast "
            "drains to the axillary, inferior deep cervical "
            "and infraclavicular nodes, and the nipple and "
            "areola to the subareolar lymphatic plexus (S4).",
        "innervation":
            "The anterior and lateral cutaneous branches of "
            "the 4th to 6th intercostal nerves, carrying "
            "sensory and autonomic fibres — the autonomic "
            "fibres regulating smooth muscle and blood "
            "vessel tone. These nerves do not control the "
            "production and secretion of milk (S4).",
        "ownership":
            "Ownership adjudication, recorded as this "
            "module's decision: the dataset cannot decide "
            "the question — the release files the mammary "
            "gland under neither the integumentary nor the "
            "reproductive system, having no concept for it "
            "under any name (S5) — so the record is placed "
            "by classification. It is owned HERE, in the "
            "integumentary module, because the consulted "
            "clinical source defines the mammary glands as "
            "modified sweat glands (S4): cutaneous glands "
            "by kind, of a piece with this module's "
            "sebaceous and sweat gland records, and "
            "developmentally an appendage of the skin. The "
            "counter-consideration is recorded, not "
            "suppressed: the same source introduces the "
            "glands as 'an accessory gland of the female "
            "reproductive system', and lactation is "
            "reproductive function. The reproductive module "
            "(Milestone 14) completed its census of the "
            "release without claiming any mammary name, so "
            "no module boundary is crossed by placing the "
            "record here; the placement is a stated "
            "convention of this project, not a fact of the "
            "dataset, and the reproductive module's records "
            "cross-reference it by this id.",
    })
    r["sources"] = OrderedDict([
        ("description", ["S4", "S5"]),
        ("parts", ["S4"]),
        ("function", ["S4"]),
        ("relations", ["S4"]),
        ("arterial_supply", ["S4"]),
        ("venous_drainage", ["S4"]),
        ("lymphatic_drainage", ["S4"]),
        ("innervation", ["S4"]),
        ("ownership", ["S4", "S5"]),
    ])
    r["verify"] = [ABSENCE, TA_VERIFY]
    r["note"] = ("The tranche's closing record and the "
                 "module's argument, as the ovary was "
                 "Milestone 14's: complete sourced clinical "
                 "anatomy for a structure the dataset does "
                 "not contain, with the absence recorded on "
                 "the record and its ownership decided in "
                 "the open, on a stated basis.")
    records.append(finish(
        r, core=["description", "parts", "function",
                 "ownership"],
        soft=["relations", "arterial_supply",
              "venous_drainage", "lymphatic_drainage",
              "innervation"]))

    tiers = {}
    tiers_by_group = {}
    for rec in records:
        tiers[rec["sourcing_tier"]] = tiers.get(
            rec["sourcing_tier"], 0) + 1
        tiers_by_group.setdefault(rec["group"], {}).setdefault(
            rec["sourcing_tier"], 0)
        tiers_by_group[rec["group"]][rec["sourcing_tier"]] += 1
    doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA integumentary system clinical "
                      "records — Milestone 15"),
            ("generated_by", "tools/build_integ_records.py"),
            ("sources", SOURCES),
            ("record_count", len(records)),
            ("tiers", tiers),
            ("tiers_by_group", tiers_by_group),
            ("groups", list(OrderedDict.fromkeys(
                r["group"] for r in records))),
            ("sourcing_rule",
             "every field value is drawn only from the sources "
             "listed, consulted in this session, and cites them "
             "per field in the record's sources map; a field no "
             "consulted source supports is null and carries a "
             "verify entry naming it. TA names are not asserted "
             "anywhere in this tranche (no TA2 list consulted). "
             "Six records link geometry the release carries "
             "(the skin shell, the hair class and its three "
             "regional records, the eyebrow); seven link none, "
             "each with the dataset absence recorded — the "
             "epidermis, dermis and hypodermis, the nail, both "
             "cutaneous glands and the mammary gland. Two of "
             "the linked records (trunk hair, pubic hair) are "
             "tier C by design: the consulted sources give "
             "their regions no separate account, and the "
             "records say so rather than padding. The mammary "
             "record's ownership is an adjudicated convention "
             "stated on the record itself: the release files "
             "the gland under neither candidate system, the "
             "reproductive module claimed no mammary name, "
             "and this module owns it on the "
             "modified-sweat-gland basis."),
        ])),
        ("records", records),
    ])
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: {len(records)} records, tiers {tiers}")
    print("tiers by group:", tiers_by_group)
    for rec in records:
        print(" ", rec["id"], rec["sourcing_tier"],
              "links:", rec["geometry_record_ids"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
