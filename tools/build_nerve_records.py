#!/usr/bin/env python3
"""ANATOMICA Milestone 9, step 2: nervous system clinical tranche.

Builds data/nervous/nervous.json from the inventory
(data/nervous/nervous-inventory.json, produced by tools/nerve_map.py).

FIELD-SOURCING RULE (precision law, same discipline as Milestones 4
and 5): a clinical value is entered only when it comes from a source
actually consulted during this build session, and the record cites
that source per field in its `sources` map. Anything not sourced is
null plus an explicit `verify` entry. TA names were not given by the
consulted sources and are null + verify-flagged throughout.

Sources (consulted in-session; TeachMeAnatomy abbreviated TMA):
  S1  TMA, "Summary of the Cranial Nerves" (summary table: number,
      name, exit foramen, modality, function per nerve)
  S2  TMA, "The Brachial Plexus" (formation C5-T1; the five terminal
      branches with roots, motor and sensory functions; minor branch
      table by plexus part)
  S3  TMA, "The Lumbar Plexus" (formation L1-L4 + T12; six branches
      with roots, motor and sensory functions)
  S4  TMA, "The Sacral Plexus" (formation S1-S4 + lumbosacral trunk
      L4/L5; five major branches with roots and functions)
  S5  TMA, "The Tibial Nerve" (roots L4-S3; motor/sensory; plantar
      and calcaneal branches)
  S6  TMA, "The Common Fibular Nerve" (roots L4-S2; superficial and
      deep fibular branches and their functions)
  S7  TMA, "The Cerebrum" (the four lobes and their cortical
      association-area functions)
  S8  OpenStax, Anatomy and Physiology — brain region functional
      summaries (cerebellum, brain stem, medulla cardiovascular
      centre, basal nuclei) via the Pearson OpenStax study guide and
      the OpenStax coordination-exam course text
  S9  TMA, "The Spinal Cord" (course, conus medullaris at L2, cauda
      equina, cervical enlargement C4-T1, lumbar enlargement T11-L1,
      meninges, filum terminale, spinal nerve formation)
  S10 Lecture notes, "Neuroanatomy Lecture 2: Spinal Cord" (31 cord
      segments: 8 cervical, 12 thoracic, 5 lumbar, 5 sacral,
      1 coccygeal)
  S11 "Parts of the Brain" class summary (McKee & Murphy) —
      hypothalamus homeostasis functions; medulla/pons/midbrain
      summaries (corroboration)

Record types and fields:
  nerve (peripheral nerves and plexuses): root_values, branches,
    motor_territory, sensory_territory (design/02 nerve kind).
    Tiers: A = all four fields sourced; B = root values and both
    territories sourced, branches verify-flagged; C = root values or
    a territory verify-flagged.
  cranial (the 12 cranial nerves): modality, function, exit_foramen
    (from the S1 summary table), plus branches.
    Tiers: A = all four sourced; B = modality/function/exit sourced,
    branches flagged; C = a core field (modality/function/exit)
    flagged.
  central (brain structures): function, connections.
    Tiers: A = both sourced; B = function sourced only; C = function
    flagged.
  organ (brain, spinal cord): hand-built records with per-field
    sources, as the heart record of Milestone 5.

Geometry linkage: clinical records link inventory records by exact
record name. Most peripheral-nerve and cranial-nerve records link
NOTHING, because the BP3D release carries no concepts for them (the
module's central gap, quantified in the inventory); those records
carry the absence in their note and verify list instead.
"""

import json
import os
import sys

PROJECT = "/home/hatch/workspace/anatomica-project"
INV_PATH = os.path.join(PROJECT, "data/nervous/nervous-inventory.json")
OUT_PATH = os.path.join(PROJECT, "data/nervous/nervous.json")

inv = json.load(open(INV_PATH, encoding="utf-8"))
inv_by_name = {}
for r in inv["records"]:
    inv_by_name.setdefault(r["name"], []).append(r["record_id"])

SOURCES = {
    "S1": "TeachMeAnatomy, 'Summary of the Cranial Nerves' (teachmeanatomy.info)",
    "S2": "TeachMeAnatomy, 'The Brachial Plexus' (teachmeanatomy.info)",
    "S3": "TeachMeAnatomy, 'The Lumbar Plexus' (teachmeanatomy.info)",
    "S4": "TeachMeAnatomy, 'The Sacral Plexus' (teachmeanatomy.info)",
    "S5": "TeachMeAnatomy, 'The Tibial Nerve' (teachmeanatomy.info)",
    "S6": "TeachMeAnatomy, 'The Common Fibular Nerve' (teachmeanatomy.info)",
    "S7": "TeachMeAnatomy, 'The Cerebrum' (teachmeanatomy.info)",
    "S8": "OpenStax, Anatomy and Physiology (brain-region functional summaries, via Pearson OpenStax study guide and OpenStax course text)",
    "S9": "TeachMeAnatomy, 'The Spinal Cord' (teachmeanatomy.info)",
    "S10": "Lecture notes, 'Neuroanatomy Lecture 2: Spinal Cord' (humsc.net)",
    "S11": "'Parts of the Brain' class summary (McKee & Murphy, nh-chs-anatomy.pbworks.com)",
}

records = []
link_failures = []


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
    """Apply the sourcing discipline: values need citations, nulls
    need verify flags, tier from which fields are flagged."""
    src = rec["sources"]
    ver = rec["verify"]
    if not any(v.startswith("ta_name:") for v in ver):
        ver.append("ta_name: not given by consulted sources - verify")
    for f in fields:
        if rec[f] is None and not any(v.startswith(f + ":") for v in ver):
            ver.append(f"{f}: not sourced from consulted sources - verify")
        if rec[f] is not None and f not in src:
            raise SystemExit(f"{rec_id}: field {f} has a value but no source")
    if any(rec[f] is None for f in core):
        rec["sourcing_tier"] = "C"
    elif any(rec[f] is None for f in soft):
        rec["sourcing_tier"] = "B"
    else:
        rec["sourcing_tier"] = "A"
    records.append(rec)


def nerve(rec_id, name, group, names, root_values=None, branches=None,
          motor=None, sensory=None, sources=None, verify=None, note=None):
    rec = {
        "id": rec_id, "name": name, "type": "nerve", "group": group,
        "ta_name": None,
        "root_values": root_values, "branches": branches,
        "motor_territory": motor, "sensory_territory": sensory,
        "sources": dict(sources or {}), "verify": list(verify or []),
        "note": note,
        "geometry_record_ids": link(rec_id, names),
    }
    finish(rec, ["root_values", "branches", "motor_territory",
                 "sensory_territory"],
           core=["root_values", "motor_territory", "sensory_territory"],
           soft=["branches"], rec_id=rec_id)


def cranial(rec_id, name, group, names, modality=None, function=None,
            exit_foramen=None, branches=None, sources=None, verify=None,
            note=None):
    rec = {
        "id": rec_id, "name": name, "type": "cranial_nerve",
        "group": group, "ta_name": None,
        "modality": modality, "function": function,
        "exit_foramen": exit_foramen, "branches": branches,
        "sources": dict(sources or {}), "verify": list(verify or []),
        "note": note,
        "geometry_record_ids": link(rec_id, names),
    }
    finish(rec, ["modality", "function", "exit_foramen", "branches"],
           core=["modality", "function", "exit_foramen"],
           soft=["branches"], rec_id=rec_id)


def central(rec_id, name, group, names, function=None, connections=None,
            sources=None, verify=None, note=None):
    rec = {
        "id": rec_id, "name": name, "type": "central_structure",
        "group": group, "ta_name": None,
        "function": function, "connections": connections,
        "sources": dict(sources or {}), "verify": list(verify or []),
        "note": note,
        "geometry_record_ids": link(rec_id, names),
    }
    finish(rec, ["function", "connections"], core=["function"],
           soft=["connections"], rec_id=rec_id)


NO_GEO = ("no BP3D concept: this structure has no concept in the "
          "BodyParts3D 4.0 release (see the inventory gap analysis); "
          "the record is text-only in v1 - verify")


# ------------------------------------------------------------ cranial nerves
# All values transcribed from the S1 summary table (number, exit,
# modality, function). Branches were not enumerated by S1 except for
# the three trigeminal divisions, and are flagged elsewhere.
CN = "Cranial nerves"
cranial("nerve.cn-01-olfactory", "Olfactory nerve (CN I)", CN, [],
        modality="Sensory (SVS)",
        function="Smell.",
        exit_foramen="Cribriform plate (cribriform foramina of the ethmoid bone)",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        verify=[NO_GEO],
        note="Arises from the cerebrum (S1). " + NO_GEO)
cranial("nerve.cn-02-optic", "Optic nerve (CN II)", CN,
        ["right optic nerve", "left optic nerve", "optic chiasm",
         "right optic tract", "left optic tract"],
        modality="Sensory (SSS)",
        function="Vision.",
        exit_foramen="Optic canal",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        note="Arises from the cerebrum (S1). The only cranial nerve "
             "whose trunk, chiasm and tracts all have BP3D concepts; "
             "geometry links the inventory optic records.")
cranial("nerve.cn-03-oculomotor", "Oculomotor nerve (CN III)", CN,
        ["superior branch of right oculomotor nerve",
         "superior branch of left oculomotor nerve",
         "inferior branch of right oculomotor nerve",
         "inferior branch of left oculomotor nerve"],
        modality="Motor (GSM & GVM)",
        function=("GSM: four extrinsic eye muscles and levator "
                  "palpebrae superioris. GVM: pupillary sphincter."),
        exit_foramen="Superior orbital fissure",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        note="Arises at the midbrain-pontine junction (S1). The "
             "release carries no oculomotor trunk concept; geometry "
             "links its superior and inferior branch records only.")
cranial("nerve.cn-04-trochlear", "Trochlear nerve (CN IV)", CN,
        ["right trochlear nerve", "left trochlear nerve"],
        modality="Motor (GSM)",
        function="Superior oblique muscle.",
        exit_foramen="Superior orbital fissure",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        note="Arises from the posterior side of the midbrain; the "
             "longest intracranial length of all the cranial nerves "
             "(S1). Geometry links the lateralised inventory records.")
cranial("nerve.cn-05-trigeminal", "Trigeminal nerve (CN V)", CN,
        ["right ophthalmic nerve", "left ophthalmic nerve",
         "right frontal nerve", "left frontal nerve",
         "right lacrimal nerve", "left lacrimal nerve",
         "right nasociliary nerve", "left nasociliary nerve",
         "right supra-orbital nerve", "left supra-orbital nerve",
         "right supratrochlear nerve", "left supratrochlear nerve",
         "right infratrochlear nerve", "left infratrochlear nerve",
         "right anterior ethmoidal nerve",
         "left anterior ethmoidal nerve",
         "right posterior ethmoidal nerve",
         "left posterior ethmoidal nerve",
         "right long ciliary nerve", "left long ciliary nerve",
         "short ciliary nerve",
         "right ciliary ganglion", "left ciliary ganglion"],
        modality=("Mixed: ophthalmic GSS; maxillary GSS; mandibular "
                  "GSS & SVM"),
        function=("Ophthalmic division (GSS): scalp, forehead and "
                  "nose. Maxillary division (GSS): cheeks, lower "
                  "eyelid, nasal mucosa, upper lip, upper teeth and "
                  "palate. Mandibular division (GSS): anterior two "
                  "thirds of tongue, skin over mandible and lower "
                  "teeth; (SVM): muscles of mastication."),
        exit_foramen=("Ophthalmic: superior orbital fissure. "
                      "Maxillary: foramen rotundum. Mandibular: "
                      "foramen ovale."),
        branches=["Ophthalmic nerve (V1)", "Maxillary nerve (V2)",
                  "Mandibular nerve (V3)"],
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"], "branches": ["S1"]},
        note="Arises from the pons (S1). The release carries concepts "
             "only for the ophthalmic division and its branches (and "
             "the ciliary ganglion); the trigeminal trunk, ganglion "
             "and the maxillary and mandibular divisions have no "
             "concepts — geometry links the V1 records only.")
cranial("nerve.cn-06-abducens", "Abducens nerve (CN VI)", CN, [],
        modality="Motor (GSM)",
        function="Lateral rectus muscle.",
        exit_foramen="Superior orbital fissure",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        verify=[NO_GEO],
        note="Arises at the pontine-medulla junction (S1). " + NO_GEO)
cranial("nerve.cn-07-facial", "Facial nerve (CN VII)", CN, [],
        modality="Both (GSS, SVS, SVM, GVM)",
        function=("GSS: sensation to part of the external ear. SVS: "
                  "taste from anterior two thirds of tongue, hard and "
                  "soft palate. SVM: muscles of facial expression. "
                  "GVM: lacrimal, submandibular and sublingual glands "
                  "and mucous glands of mouth and nose."),
        exit_foramen=("Internal acoustic meatus, then stylomastoid "
                      "foramen"),
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        verify=[NO_GEO],
        note="Arises at the pontine-medulla junction (S1). " + NO_GEO)
cranial("nerve.cn-08-vestibulocochlear",
        "Vestibulocochlear nerve (CN VIII)", CN, [],
        modality="Sensory (SSS)",
        function="Hearing and balance.",
        exit_foramen="Internal acoustic meatus",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        verify=[NO_GEO],
        note="Arises at the pontine-medulla junction (S1). " + NO_GEO)
cranial("nerve.cn-09-glossopharyngeal",
        "Glossopharyngeal nerve (CN IX)", CN, [],
        modality="Both (GSS, GVS, SVS, GVM, SVM)",
        function=("GSS: posterior third of tongue, external ear and "
                  "middle ear cavity. GVS: carotid body and sinus. "
                  "SVS: taste from posterior third of tongue. GVM: "
                  "parotid gland. SVM: stylopharyngeus."),
        exit_foramen="Jugular foramen",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        verify=[NO_GEO],
        note="Arises from the medulla, posterior to the olive (S1). "
             + NO_GEO)
cranial("nerve.cn-10-vagus", "Vagus nerve (CN X)", CN, [],
        modality="Both (GSS, GVS, SVS, GVM, SVM)",
        function=("GSS: external ear, larynx and pharynx. GVS: "
                  "larynx, pharynx and thoracic and abdominal viscera. "
                  "SVS: taste from epiglottis region of tongue. GVM: "
                  "smooth muscles of pharynx, larynx and most of the "
                  "gastrointestinal tract. SVM: most muscles of "
                  "pharynx and larynx."),
        exit_foramen="Jugular foramen",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        verify=[NO_GEO],
        note="Arises from the medulla, posterior to the olive (S1). "
             + NO_GEO)
cranial("nerve.cn-11-accessory", "Accessory nerve (CN XI)", CN, [],
        modality="Motor (GSM & SVM)",
        function=("GSM: trapezius and sternocleidomastoid. SVM: a few "
                  "fibres run with CN X to viscera."),
        exit_foramen="Jugular foramen",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        verify=[NO_GEO],
        note="Listed by S1 as the spinal accessory nerve; arises from "
             "the medulla, posterior to the olive. " + NO_GEO)
cranial("nerve.cn-12-hypoglossal", "Hypoglossal nerve (CN XII)", CN, [],
        modality="Motor (GSM)",
        function=("Intrinsic and extrinsic tongue muscles (except the "
                  "palatoglossus)."),
        exit_foramen="Hypoglossal canal",
        sources={"modality": ["S1"], "function": ["S1"],
                 "exit_foramen": ["S1"]},
        verify=[NO_GEO],
        note="Arises from the medulla, anterior to the olive (S1). "
             + NO_GEO)


# ------------------------------------------------- plexuses and spinal nerves
PX = "Spinal cord and plexuses"
nerve("plexus.brachial", "Brachial plexus", PX, [],
      root_values="C5, C6, C7, C8, T1 (anterior rami of spinal nerves)",
      branches=["Dorsal scapular nerve (from C5 root)",
                "Long thoracic nerve (from C5-C7 roots)",
                "Suprascapular nerve (from superior trunk)",
                "Nerve to subclavius (from superior trunk)",
                "Lateral pectoral nerve (from lateral cord)",
                "Musculocutaneous nerve (from lateral cord)",
                "Median nerve (from lateral and medial cords)",
                "Medial pectoral nerve (from medial cord)",
                "Medial cutaneous nerve of arm (from medial cord)",
                "Medial cutaneous nerve of forearm (from medial cord)",
                "Ulnar nerve (from medial cord)",
                "Superior subscapular nerve (from posterior cord)",
                "Thoracodorsal nerve (from posterior cord)",
                "Inferior subscapular nerve (from posterior cord)",
                "Axillary nerve (from posterior cord)",
                "Radial nerve (from posterior cord)"],
      motor=("Supplies the musculature of the upper limb, via its "
             "branches (see the terminal-branch records)."),
      sensory=("Supplies the skin of the upper limb, via its "
               "branches."),
      sources={"root_values": ["S2"], "branches": ["S2"],
               "motor_territory": ["S2"], "sensory_territory": ["S2"]},
      verify=[NO_GEO],
      note="Formed by the anterior rami of C5-T1; organised as five "
           "roots, three trunks (superior C5-C6, middle C7, inferior "
           "C8-T1), anterior and posterior divisions, and three cords "
           "(lateral, posterior, medial) named relative to the "
           "axillary artery (S2). " + NO_GEO)
nerve("plexus.lumbar", "Lumbar plexus", PX, [],
      root_values="L1, L2, L3, L4 (anterior rami), with a contribution from T12",
      branches=["Iliohypogastric nerve", "Ilioinguinal nerve",
                "Genitofemoral nerve",
                "Lateral cutaneous nerve of thigh",
                "Obturator nerve", "Femoral nerve"],
      motor=("Supplies the musculature of the lower limb and lower "
             "abdominal wall, via its branches."),
      sensory=("Supplies the skin of the lower limb, groin and lower "
               "abdomen, via its branches."),
      sources={"root_values": ["S3"], "branches": ["S3"],
               "motor_territory": ["S3"], "sensory_territory": ["S3"]},
      verify=[NO_GEO],
      note="Lies within the substance of psoas major, anterior to "
           "the lumbar transverse processes (S3). " + NO_GEO)
nerve("plexus.sacral", "Sacral plexus", PX, [],
      root_values=("S1, S2, S3, S4 (anterior rami), joined by the "
                   "lumbosacral trunk formed from L4 and L5"),
      branches=["Superior gluteal nerve", "Inferior gluteal nerve",
                "Sciatic nerve", "Posterior cutaneous nerve of thigh",
                "Pudendal nerve", "Nerve to piriformis",
                "Nerve to obturator internus",
                "Nerve to quadratus femoris",
                "Perforating cutaneous nerve",
                "Pelvic splanchnic nerves"],
      motor=("Supplies the muscles of the pelvis and lower limb, via "
             "its branches."),
      sensory=("Supplies the skin of the pelvis and lower limb, via "
               "its branches."),
      sources={"root_values": ["S4"], "branches": ["S4"],
               "motor_territory": ["S4"], "sensory_territory": ["S4"]},
      verify=[NO_GEO],
      note="Lies on the posterior pelvic wall, anterior to "
           "piriformis (S4). " + NO_GEO)

UL = "Peripheral nerves — upper limb"
nerve("nerve.musculocutaneous", "Musculocutaneous nerve", UL, [],
      root_values="C5, C6, C7",
      motor=("Brachialis, biceps brachii and coracobrachialis "
             "(anterior compartment of the arm)."),
      sensory=("Lateral half of the anterior forearm and a small "
               "lateral portion of the posterior forearm, via the "
               "lateral cutaneous branch of the forearm."),
      sources={"root_values": ["S2"], "motor_territory": ["S2"],
               "sensory_territory": ["S2"]},
      verify=[NO_GEO],
      note="Continuation of the lateral cord of the brachial plexus "
           "(S2). " + NO_GEO)
nerve("nerve.axillary", "Axillary nerve", UL, [],
      root_values="C5, C6",
      motor="Deltoid and teres minor.",
      sensory=("Inferior region of the deltoid (the 'regimental "
               "badge area'), via the superior lateral cutaneous "
               "nerve of arm."),
      sources={"root_values": ["S2"], "motor_territory": ["S2"],
               "sensory_territory": ["S2"]},
      verify=[NO_GEO],
      note="Arises from the posterior cord of the brachial plexus "
           "(S2). " + NO_GEO)
nerve("nerve.median", "Median nerve", UL, [],
      root_values="C6, C7, C8, T1 (with fibres from C5 in some individuals)",
      motor=("Most of the flexor muscles in the forearm, the thenar "
             "muscles, and the two lateral lumbricals (index and "
             "middle fingers)."),
      sensory=("Lateral part of the palm (via the palmar cutaneous "
               "branch) and the lateral three and a half fingers on "
               "the palmar surface of the hand (via the digital "
               "cutaneous branch)."),
      sources={"root_values": ["S2"], "motor_territory": ["S2"],
               "sensory_territory": ["S2"]},
      verify=[NO_GEO],
      note="Formed by the union of a lateral root from the lateral "
           "cord and a medial root from the medial cord (S2). "
           + NO_GEO)
nerve("nerve.radial", "Radial nerve", UL, [],
      root_values="C5, C6, C7, C8, T1",
      motor=("Triceps brachii and the muscles of the posterior "
             "compartment of the forearm (primarily extensors of the "
             "wrist and fingers)."),
      sensory=("Posterior aspect of the arm and forearm, and the "
               "posterolateral aspect of the hand."),
      sources={"root_values": ["S2"], "motor_territory": ["S2"],
               "sensory_territory": ["S2"]},
      verify=[NO_GEO],
      note="Continuation of the posterior cord of the brachial "
           "plexus (S2). " + NO_GEO)
nerve("nerve.ulnar", "Ulnar nerve", UL, [],
      root_values="C8, T1",
      motor=("The intrinsic muscles of the hand (apart from the "
             "thenar muscles and the two lateral lumbricals), flexor "
             "carpi ulnaris and the medial half of flexor digitorum "
             "profundus."),
      sensory=("Anterior and posterior surfaces of the medial one "
               "and a half fingers, and the associated palm area."),
      sources={"root_values": ["S2"], "motor_territory": ["S2"],
               "sensory_territory": ["S2"]},
      verify=[NO_GEO],
      note="Continuation of the medial cord of the brachial plexus "
           "(S2). " + NO_GEO)


LL = "Peripheral nerves — lower limb"
nerve("nerve.iliohypogastric", "Iliohypogastric nerve", LL, [],
      root_values="L1 (with contributions from T12)",
      motor="Internal oblique and transversus abdominis.",
      sensory="Skin of the posterolateral gluteal and pubic regions.",
      sources={"root_values": ["S3"], "motor_territory": ["S3"],
               "sensory_territory": ["S3"]},
      verify=[NO_GEO],
      note="First major branch of the lumbar plexus (S3). " + NO_GEO)
nerve("nerve.ilioinguinal", "Ilioinguinal nerve", LL, [],
      root_values="L1",
      motor="Internal oblique and transversus abdominis.",
      sensory=("Skin of the superior anteromedial thigh; in males "
               "also the root of the penis and anterior scrotum, in "
               "females the mons pubis and labia majora."),
      sources={"root_values": ["S3"], "motor_territory": ["S3"],
               "sensory_territory": ["S3"]},
      verify=[NO_GEO],
      note="Follows the course of the iliohypogastric nerve and "
           "passes through the superficial inguinal ring (S3). "
           + NO_GEO)
nerve("nerve.genitofemoral", "Genitofemoral nerve", LL, [],
      root_values="L1, L2",
      branches=["Genital branch", "Femoral branch"],
      motor="Cremasteric muscle (via the genital branch).",
      sensory=("Genital branch: skin of the anterior scrotum in "
               "males, or mons pubis and labia majora in females. "
               "Femoral branch: skin of the upper anterior thigh."),
      sources={"root_values": ["S3"], "branches": ["S3"],
               "motor_territory": ["S3"], "sensory_territory": ["S3"]},
      verify=[NO_GEO],
      note="Divides into genital and femoral branches after leaving "
           "psoas major (S3). " + NO_GEO)
nerve("nerve.lateral-cutaneous-thigh",
      "Lateral cutaneous nerve of thigh", LL, [],
      root_values="L2, L3",
      motor="None — purely sensory nerve (S3).",
      sensory=("Anterior and lateral thigh down to the level of the "
               "knee."),
      sources={"root_values": ["S3"], "motor_territory": ["S3"],
               "sensory_territory": ["S3"]},
      verify=[NO_GEO], note=NO_GEO)
nerve("nerve.obturator", "Obturator nerve", LL, [],
      root_values="L2, L3, L4",
      motor=("Muscles of the medial thigh: obturator externus, "
             "adductor longus, adductor brevis, adductor magnus and "
             "gracilis."),
      sensory="Skin over the medial thigh.",
      sources={"root_values": ["S3"], "motor_territory": ["S3"],
               "sensory_territory": ["S3"]},
      verify=[NO_GEO],
      note="From the lumbar plexus (S3). " + NO_GEO)
nerve("nerve.femoral", "Femoral nerve", LL, [],
      root_values="L2, L3, L4",
      motor=("Muscles of the anterior thigh: iliacus, pectineus, "
             "sartorius and quadriceps femoris."),
      sensory="Skin on the anterior thigh and the medial leg.",
      sources={"root_values": ["S3"], "motor_territory": ["S3"],
               "sensory_territory": ["S3"]},
      verify=[NO_GEO],
      note="Largest branch of the lumbar plexus (S3). " + NO_GEO)
nerve("nerve.superior-gluteal", "Superior gluteal nerve", LL, [],
      root_values="L4, L5, S1",
      motor="Gluteus medius, gluteus minimus and tensor fascia lata.",
      sensory="None (S4).",
      sources={"root_values": ["S4"], "motor_territory": ["S4"],
               "sensory_territory": ["S4"]},
      verify=[NO_GEO],
      note="Leaves the pelvis via the greater sciatic foramen above "
           "piriformis (S4). " + NO_GEO)
nerve("nerve.inferior-gluteal", "Inferior gluteal nerve", LL, [],
      root_values="L5, S1, S2",
      motor="Gluteus maximus.",
      sensory="None (S4).",
      sources={"root_values": ["S4"], "motor_territory": ["S4"],
               "sensory_territory": ["S4"]},
      verify=[NO_GEO],
      note="Leaves the pelvis via the greater sciatic foramen below "
           "piriformis (S4). " + NO_GEO)
nerve("nerve.sciatic", "Sciatic nerve", LL, [],
      root_values="L4, L5, S1, S2, S3",
      branches=["Tibial nerve (tibial division)",
                "Common fibular nerve (common fibular division)"],
      motor=("Tibial portion: muscles of the posterior compartment "
             "of the thigh (apart from the short head of biceps "
             "femoris) and the hamstring component of adductor "
             "magnus; all muscles of the posterior compartment of "
             "the leg and sole of the foot. Common fibular portion: "
             "short head of biceps femoris; all muscles of the "
             "anterior and lateral compartments of the leg and "
             "extensor digitorum brevis."),
      sensory=("Tibial portion: skin of the posterolateral leg, "
               "lateral foot and sole of the foot. Common fibular "
               "portion: skin of the lateral leg and dorsum of the "
               "foot."),
      sources={"root_values": ["S4"], "branches": ["S5", "S6"],
               "motor_territory": ["S4"], "sensory_territory": ["S4"]},
      verify=[NO_GEO],
      note="Largest branch of the sacral plexus; its two divisions "
           "separate at the apex of the popliteal fossa (S4, S5). "
           + NO_GEO)
nerve("nerve.posterior-cutaneous-thigh",
      "Posterior cutaneous nerve of thigh", LL, [],
      root_values="S1, S2, S3",
      motor="None (S4).",
      sensory=("Skin on the posterior surface of the thigh and leg, "
               "and skin of the perineum."),
      sources={"root_values": ["S4"], "motor_territory": ["S4"],
               "sensory_territory": ["S4"]},
      verify=[NO_GEO], note=NO_GEO)
nerve("nerve.pudendal", "Pudendal nerve", LL, [],
      root_values="S2, S3, S4",
      motor=("Skeletal muscles of the perineum, the external "
             "urethral sphincter, the external anal sphincter and "
             "levator ani."),
      sensory="Penis and clitoris and most of the skin of the perineum.",
      sources={"root_values": ["S4"], "motor_territory": ["S4"],
               "sensory_territory": ["S4"]},
      verify=[NO_GEO],
      note="Leaves the pelvis via the greater sciatic foramen and "
           "re-enters via the lesser sciatic foramen (S4). " + NO_GEO)
nerve("nerve.tibial", "Tibial nerve", LL, [],
      root_values="L4, L5, S1, S2, S3",
      branches=["Medial calcaneal branches", "Medial plantar nerve",
                "Lateral plantar nerve",
                "Cutaneous contribution to the sural nerve"],
      motor=("All muscles of the posterior compartment of the leg "
             "(superficial and deep) and, via the medial and lateral "
             "plantar branches, the majority of the intrinsic "
             "muscles of the foot (except extensor digitorum brevis "
             "and extensor hallucis brevis, supplied by the deep "
             "fibular nerve)."),
      sensory=("Skin of the posterolateral leg, lateral foot and the "
               "sole of the foot: heel via the medial calcaneal "
               "branches, medial three and a half digits and "
               "associated sole via the medial plantar nerve, lateral "
               "one and a half digits and associated sole via the "
               "lateral plantar nerve."),
      sources={"root_values": ["S5"], "branches": ["S5"],
               "motor_territory": ["S5"], "sensory_territory": ["S5"]},
      verify=[NO_GEO],
      note="Terminal branch of the sciatic nerve, arising at the "
           "apex of the popliteal fossa; passes through the tarsal "
           "tunnel posterior to the medial malleolus (S5). " + NO_GEO)
nerve("nerve.common-fibular", "Common fibular nerve", LL, [],
      root_values="L4, L5, S1, S2",
      branches=["Superficial fibular nerve", "Deep fibular nerve",
                "Lateral sural cutaneous nerve",
                "Sural communicating nerve"],
      motor=("Short head of biceps femoris directly; via the "
             "superficial fibular nerve, fibularis longus and brevis "
             "(lateral compartment of the leg, eversion); via the "
             "deep fibular nerve, tibialis anterior, extensor "
             "digitorum longus and extensor hallucis longus "
             "(anterior compartment of the leg, dorsiflexion and "
             "digit extension) and some intrinsic muscles of the "
             "foot."),
      sensory=("Skin of the lateral leg and the dorsum of the foot: "
               "anterolateral leg and dorsum except the first web "
               "space via the superficial fibular nerve; first web "
               "space via the deep fibular nerve."),
      sources={"root_values": ["S6"], "branches": ["S6"],
               "motor_territory": ["S6"], "sensory_territory": ["S6"]},
      verify=[NO_GEO],
      note="Terminal branch of the sciatic nerve; wraps around the "
           "neck of the fibula and divides into superficial and deep "
           "fibular nerves (S6). " + NO_GEO)


# ------------------------------------------------------- central structures
BR = "Brain regions"
central("central.cerebrum", "Cerebrum", BR,
        ["left cerebral hemisphere", "right cerebral hemisphere"],
        function=("Its cortical association areas collate "
                  "information from different modalities for "
                  "processing, giving a meaningful perceptual "
                  "interpretation and experience of the surrounding "
                  "environment (S7)."),
        sources={"function": ["S7"]},
        note="The largest part of the brain, divided into two "
             "cerebral hemispheres and four lobes per hemisphere "
             "(S7). Geometry links the PART-OF hemisphere records.")
central("central.frontal-lobe", "Frontal lobe", BR,
        ["left frontal lobe", "right frontal lobe"],
        function=("Association areas responsible for higher "
                  "intellect, personality, mood, social conduct and "
                  "language (dominant hemisphere side only) (S7)."),
        sources={"function": ["S7"]},
        note="Separated from the parietal lobe by the central "
             "sulcus and from the temporal lobe by the lateral "
             "sulcus (S7).")	
central("central.parietal-lobe", "Parietal lobe", BR,
        ["left parietal lobe", "right parietal lobe"],
        function=("Cortical association areas contribute to language "
                  "and calculation on the dominant hemisphere side, "
                  "and to visuospatial functions (e.g. two-point "
                  "discrimination) on the non-dominant side (S7)."),
        sources={"function": ["S7"]}, note=None)
central("central.temporal-lobe", "Temporal lobe", BR,
        ["left temporal lobe", "right temporal lobe"],
        function=("Cortical association areas accountable for memory "
                  "and language; contains the primary auditory "
                  "cortex, so it is also the location of hearing "
                  "(S7)."),
        sources={"function": ["S7"]}, note=None)
central("central.occipital-lobe", "Occipital lobe", BR,
        ["left occipital lobe", "right occipital lobe"],
        function=("Contains the primary visual cortex (V1); its "
                  "cortical association area is responsible for "
                  "vision (S7)."),
        sources={"function": ["S7"]},
        note="Geometry links the IS-A occipital lobe records; the "
             "occipital lobe has no PART-OF-tree concept in the "
             "release's nervous-system subtree.")
central("central.insula", "Insula", BR,
        ["left insula", "right insula"],
        sources={}, verify=[],
        note="Inventory geometry exists (lateralised IS-A records); "
             "no consulted source stated insular function in this "
             "session, so function is flagged, not entered.")
central("central.limbic-lobe", "Limbic lobe", BR,
        ["left limbic lobe", "right limbic lobe"],
        sources={}, verify=[],
        note="Inventory geometry exists (PART-OF records); limbic "
             "function was not stated by a consulted source in this "
             "session, so function is flagged, not entered.")
central("central.cerebellum", "Cerebellum", BR, ["cerebellum"],
        function=("Processes input from the premotor cortex, brain "
                  "stem and sensory receptors to provide feedback "
                  "for precise, coordinated movements of skeletal "
                  "muscles; plays a major role in balance (S8)."),
        connections=("Connected to the brain stem by three paired "
                     "peduncles: inferior (to the medulla, conveying "
                     "sensory/proprioceptive input), middle (the "
                     "ventral pons, conveying a copy of cortical "
                     "motor commands) and superior (to the midbrain "
                     "and thalamus, its major output) (S8)."),
        sources={"function": ["S8"], "connections": ["S8"]},
        note="Comprises about 10-11% of brain mass and lies dorsal "
             "to the pons and medulla (S8). The release names no "
             "cerebellar nucleus, vermis or flocculus (probe-verified "
             "absences); the record's geometry is the whole-organ "
             "composition only.")
central("central.brainstem", "Brainstem", BR, ["brainstem"],
        function=("Controls automatic behaviours necessary for "
                  "survival and serves as a conduit for fibre tracts "
                  "connecting higher and lower neural centres (S8). "
                  "Cranial nerves III-XII arise from the brainstem "
                  "(S1)."),
        connections=("Continuous cranially with the diencephalon "
                     "and caudally, via the medulla, with the spinal "
                     "cord at the foramen magnum (S8)."),
        sources={"function": ["S8", "S1"], "connections": ["S8"]},
        note="Consists of the midbrain, pons and medulla oblongata "
             "(S8). In the release the brainstem concept hangs in "
             "the PART-OF tree under head proper, not under the "
             "nervous system (see inventory).")
central("central.midbrain", "Midbrain", BR, ["midbrain"],
        function=("Contains the corpora quadrigemina (superior and "
                  "inferior colliculi), the visual and auditory "
                  "reflex centres, and the cerebral aqueduct "
                  "connecting the third and fourth ventricles (S8). "
                  "Cranial nerves III and IV arise from it (S1)."),
        sources={"function": ["S8", "S1"]}, note=None)
central("central.pons", "Pons", BR, ["pons"],
        function=("Chiefly composed of conduction tracts between "
                  "higher brain centres and the spinal cord, and of "
                  "tracts connecting the pons to the cerebellum "
                  "(S8). The trigeminal nerve (CN V) arises from it "
                  "(S1)."),
        connections=("Relays cortical motor commands to the "
                     "cerebellum via the middle cerebellar peduncle "
                     "(S8)."),
        sources={"function": ["S8", "S1"], "connections": ["S8"]},
        note=None)
central("central.medulla", "Medulla oblongata", BR,
        ["medulla oblongata"],
        function=("Contains the cardiovascular centre, which "
                  "adjusts the force and rate of heart contraction "
                  "and regulates blood vessel diameter (S8); "
                  "controls vital involuntary functions including "
                  "breathing, heart rate, blood pressure and "
                  "digestion, and relays nerve signals between brain "
                  "and body (S11). Cranial nerves IX-XII arise from "
                  "it (S1)."),
        sources={"function": ["S8", "S11", "S1"]},
        note="Blends into the spinal cord at the foramen magnum "
             "(S8). The release's medulla record carries no named "
             "nuclei or olives (probe-verified absences).")
central("central.thalamus", "Thalamus", BR,
        ["left thalamus", "right thalamus"],
        sources={}, verify=[],
        note="Inventory geometry exists (lateralised IS-A records); "
             "no consulted source stated thalamic function in this "
             "session, so function is flagged, not entered.")
central("central.hypothalamus", "Hypothalamus", BR, ["hypothalamus"],
        function=("Maintains the body's internal balance "
                  "(homeostasis), controlling body temperature, "
                  "hunger, thirst, sleep cycles, emotions and stress "
                  "responses (S11)."),
        sources={"function": ["S11"]},
        note="Lies below the thalamus, above the pituitary gland "
             "(S11).")
central("central.basal-ganglia", "Basal ganglia (basal nuclei)", BR,
        ["left caudate nucleus", "right caudate nucleus",
         "left putamen", "right putamen",
         "left globus pallidus", "right globus pallidus"],
        function=("Subcortical motor centres that help control "
                  "skeletal muscle movements (S8)."),
        sources={"function": ["S8"]},
        note="The release has no 'basal ganglia' concept: only the "
             "generic class 'basal ganglion of telencephalon' and "
             "the individual nuclei. 'Striatum' and 'lentiform "
             "nucleus' are probe-verified absent, and the substantia "
             "nigra — a basal-ganglia component in the functional "
             "literature — has no concept either; geometry links "
             "the caudate, putamen and globus pallidus records "
             "only.")
central("central.hippocampus", "Hippocampus", BR,
        ["left hippocampus", "right hippocampus"],
        sources={}, verify=[],
        note="Inventory geometry exists (IS-A records and PART-OF "
             "hippocampal formations); hippocampal function was not "
             "stated by a consulted source in this session (the "
             "temporal-lobe account in S7 assigns memory to the "
             "lobe's association areas generally), so function is "
             "flagged, not entered.")
central("central.corpus-callosum", "Corpus callosum", BR,
        ["corpus callosum"],
        sources={}, verify=[],
        note="Inventory geometry exists (single un-sided IS-A "
             "record); its commissural function was not stated by a "
             "consulted source in this session, so function is "
             "flagged, not entered.")

# ------------------------------------------------------------- organ records
records.append({
    "id": "organ.brain", "name": "Brain", "type": "organ",
    "group": "Brain regions", "ta_name": None,
    "parts": ("Cerebrum (two cerebral hemispheres, each with "
              "frontal, parietal, temporal and occipital lobes), "
              "cerebellum, brainstem (midbrain, pons, medulla "
              "oblongata) and diencephalon (thalamus, hypothalamus "
              "and associated structures)."),
    "function": ("The cerebral hemispheres localise and interpret "
                 "sensory inputs, control voluntary and skilled "
                 "skeletal muscle activity, and function in "
                 "intellectual and emotional processing (S8); the "
                 "remaining parts are covered by their own records."),
    "sources": {"parts": ["S7", "S8"], "function": ["S8"]},
    "verify": ["ta_name: not given by consulted sources - verify",
               "ventricular system: the release models the lateral, "
               "third and fourth ventricles and the cerebral aqueduct "
               "as concepts and records, but the choroid plexus "
               "exists only as the single class 'choroid plexus of "
               "cerebral hemisphere' and there is no ependyma or "
               "septum pellucidum concept — CSF production anatomy "
               "is therefore incomplete in v1 - verify"],
    "note": ("Geometry links the PART-OF brain organ record (its "
             "composition is the whole-brain mesh set). Cranial "
             "nerves I and II arise from the cerebrum and III-XII "
             "from the brainstem (S1)."),
    "sourcing_tier": "A",
    "geometry_record_ids": link("organ.brain", ["brain"]),
})
records.append({
    "id": "organ.spinal-cord", "name": "Spinal cord", "type": "organ",
    "group": "Spinal cord and plexuses", "ta_name": None,
    "segments": ("31 segments: 8 cervical, 12 thoracic, 5 lumbar, "
                 "5 sacral and 1 coccygeal, each giving origin to a "
                 "pair of spinal nerves (S10). Each spinal nerve "
                 "forms from an anterior (motor) and a posterior "
                 "(sensory) root uniting at the intervertebral "
                 "foramen, then divides into posterior and anterior "
                 "rami (S9)."),
    "structure": ("Arises cranially as a continuation of the medulla "
                  "oblongata and travels within the vertebral canal "
                  "surrounded by the spinal meninges (dura mater, "
                  "arachnoid mater, pia mater). At the L2 vertebral "
                  "level it tapers to the conus medullaris; the "
                  "spinal nerves arising beyond it form the cauda "
                  "equina. Two enlargements: cervical (C4-T1, origin "
                  "of the brachial plexus) and lumbar (T11-L1, origin "
                  "of the lumbar and sacral plexi). Distally the "
                  "meninges form the filum terminale, anchoring the "
                  "cord to the coccyx (S9)."),
    "arterial_supply": ("Three longitudinal arteries: the anterior "
                        "spinal artery (from the vertebral arteries) "
                        "and the paired posterior spinal arteries "
                        "(from the vertebral artery or the "
                        "posteroinferior cerebellar artery), "
                        "reinforced by anterior and posterior "
                        "segmental medullary arteries; the largest, "
                        "the artery of Adamkiewicz, supplies the "
                        "inferior two thirds of the cord (S9)."),
    "sources": {"segments": ["S10", "S9"], "structure": ["S9"],
                "arterial_supply": ["S9"]},
    "verify": ["ta_name: not given by consulted sources - verify",
               "cord segments, enlargements, conus medullaris, cauda "
               "equina and filum terminale: none of these has a "
               "concept in the BP3D release (probe-verified over all "
               "six release tables); the anatomy in this record is "
               "sourced text only and has no geometry in v1 - verify",
               "meninges: the release carries no pia mater or "
               "arachnoid mater concept and only class concepts for "
               "the dura (region of dura mater; subdivision of "
               "cranial dura mater) plus the tentorium cerebelli; "
               "the three membranes named by S9 are therefore not "
               "modelled - verify"],
    "note": ("Geometry links the PART-OF spinal cord organ record "
             "and its central canal record is in the inventory; the "
             "cord's own PART-OF subtree in the release is only "
             "those two concepts."),
    "sourcing_tier": "A",
    "geometry_record_ids": link("organ.spinal-cord", ["spinal cord"]),
})

# ------------------------------------------------------------------- output
from collections import Counter, OrderedDict

doc = OrderedDict([
    ("meta", OrderedDict([
        ("title", "ANATOMICA nervous system clinical records — "
                  "Milestone 9"),
        ("generated_by", "tools/build_nerve_records.py"),
        ("sourcing_rule", "every non-null clinical field cites a "
                          "source consulted during the build session "
                          "in the record's sources map; every null "
                          "field carries an explicit verify entry; "
                          "TA names were not given by the consulted "
                          "sources and are null + flagged throughout"),
        ("sources", SOURCES),
        ("record_count", len(records)),
        ("tiers", dict(Counter(r["sourcing_tier"] for r in records))),
        ("groups", dict(Counter(r["group"] for r in records))),
        ("link_failures", [list(x) for x in link_failures]),
    ])),
    ("records", records),
])
with open(OUT_PATH, "w") as f:
    json.dump(doc, f, indent=1, sort_keys=False)

print("records:", len(records))
print("tiers:", dict(Counter(r["sourcing_tier"] for r in records)))
print("by group:")
for g, n in Counter(r["group"] for r in records).items():
    sub = Counter(r["sourcing_tier"] for r in records
                  if r["group"] == g)
    print(f"  {g}: {n}  {dict(sub)}")
linked = sum(1 for r in records if r["geometry_record_ids"])
print("records with geometry links:", linked,
      "| without:", len(records) - linked)
inv_linked = sorted({i for r in records
                     for i in r["geometry_record_ids"]})
print("inventory records linked:", len(inv_linked), "of",
      len(inv["records"]))
print("link failures:", link_failures)
print(f"wrote {OUT_PATH}")
