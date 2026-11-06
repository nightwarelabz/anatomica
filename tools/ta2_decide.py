#!/usr/bin/env python3
"""ANATOMICA Milestone 23: TA2 decision curation.

Turns the match worksheet (tools/ta2_match.py) into an explicit,
reviewable decision for every one of the 361 clinical records:
work/ta2/decisions.json. Every decision in this file was reviewed
against the TA2 2.07 table (data/sources/ta2-2.07/ta2-terms.json)
during the Milestone 23 session; the hand-curated overrides below
ARE the review record for the records the mechanical classes could
not settle alone.

Mechanical classes and how they were decided:
  unique-strong  one candidate, matched on a TA2 preferred term.
                 Reviewed in the printed digest (all 103). Resolved.
  unique-weak    one candidate via synonym / related / core key.
                 Reviewed individually (all 111). Resolved, except
                 central.basal-ganglia (override below): its only
                 bridge is a TA2 *related* term and the structures
                 differ.
  multi          the CORE-key noise pattern: vessels/nerves/nodes
                 sharing an epithet. Resolved to the unique STRONG
                 candidate whose Latin carries the record's own
                 structure class (arteria/carotis/aorta for arteries,
                 vena/venae/sinus for veins, nervus for nerves,
                 musculus for muscles, glandula for glands), EXCEPT
                 the overrides below. The general-adjective entries
                 in Terminologia's general-terms chapter (radialis,
                 ulnaris, medianus, tibialis, plantaris) are not
                 structures and never win.
  none           no mechanical candidate. Every record decided by
                 hand from targeted TA2 table probes (overrides).

Resolution rule applied throughout (stated in MILESTONE-23.md):
a record resolves to a TA2 term only when TA2's own naming
apparatus (preferred term, listed synonym, or listed related term)
names that term for a structure identical to the record's —
identity corroborated by the record's type, its FMA class names,
and the TA2 chapter — and no other TA2 term denotes the record
with an equal claim. Anything else is ambiguous (candidates listed)
or not found (probe evidence recorded).
"""

import json
import os
import sys

PROJECT = "/home/hatch/workspace/anatomica-project"
WS = os.path.join(PROJECT, "work/ta2/worksheet.json")
OUT = os.path.join(PROJECT, "work/ta2/decisions.json")

CLASS_PREFIX = (
    ("artery.", ("arteria", "carotis", "aorta", "truncus")),
    ("vein.", ("vena", "venae", "sinus")),
    ("nerve.", ("nervus", "nervi")),
    ("plexus.", ("plexus",)),
    ("muscle.", ("musculus", "musculi")),
    ("gland.", ("glandula",)),
)

# ---- hand-curated overrides: key "system:record_id" ----
OVERRIDES = {
    # unique-weak exception
    "nervous:central.basal-ganglia": {
        "decision": "ambiguous", "candidates": [5559],
        "reason": "TA2 lists 'basal ganglia' only as a related term of "
                  "5559 corpus striatum, whose structure differs from "
                  "this record (corpus striatum = caudate + lentiform "
                  "nuclei; the record covers the basal nuclei group); "
                  "no TA2 preferred or synonym term denotes the basal "
                  "ganglia."},
    # multi exceptions
    "cardiovascular:vein.renal-vein": {
        "decision": "ambiguous", "candidates": [5000, 5006],
        "reason": "TA2 lists the renal vein only as sided terms "
                  "(5000 vena renalis dextra, 5006 vena renalis "
                  "sinistra); no unpaired term denotes this unsided "
                  "record."},
    "cardiovascular:artery.pulmonary-artery": {
        "decision": "resolved", "ta_id": 4074, "basis": "collective-term",
        "note": "the record spans the pulmonary trunk and both "
                "pulmonary arteries (its own geometry ids and note); "
                "TA2's collective term for that set is 4074 arteriae "
                "pulmonales, parent of 4075/4077/4091."},
    "cardiovascular:vein.pulmonary-vein": {
        "decision": "resolved", "ta_id": 4107, "basis": "collective-term",
        "note": "the record is the pulmonary veins collectively "
                "(four veins, one undivided family concept per its "
                "note); TA2's term is the plural collective."},
    "cardiovascular:vein.hepatic-vein": {
        "decision": "resolved", "ta_id": 4994, "basis": "collective-term",
        "note": "the record is the hepatic venous outflow "
                "collectively; TA2's term is the plural collective "
                "venae hepaticae."},
    "cardiovascular:artery.brachiocephalic-artery": {
        "decision": "resolved", "ta_id": 4179, "basis": "related-term",
        "note": "TA2's term for this vessel is truncus "
                "brachiocephalicus ('brachiocephalic trunk'; listed "
                "synonym 'innominate artery', related term 'arteria "
                "anonyma'); it is the sole TA2 term for the structure "
                "and the record's FMA class identity agrees."},
    # ---- none class, resolved by targeted probe ----
    "cardiovascular:artery.celiac-artery": {
        "decision": "resolved", "ta_id": 4211, "basis": "related-term",
        "note": "TA2's term is truncus coeliacus (English equivalent "
                "not given in the served table); TA2 lists 'arteria "
                "celiaca' as its related term. Sole TA2 term for the "
                "structure; the record denotes that trunk."},
    "cardiovascular:vein.accessory-hemiazygos-vein": {
        "decision": "resolved", "ta_id": 4758, "basis": "latin-synonym",
        "note": "TA2 lists the Latin synonym 'vena hemiazygos "
                "accessoria' for vena hemiazyga accessoria."},
    "endocrine:gland.adrenal-gland": {
        "decision": "resolved", "ta_id": 3874, "basis": "synonym",
        "note": "TA2 lists the English synonym 'adrenal gland' for "
                "glandula suprarenalis; the record is the class "
                "record for both glands, TA2's term is singular."},
    "digestive:seg.couinaud-i": {
        "decision": "resolved", "ta_id": 3073, "basis": "synonym",
        "note": "TA2 synonym 'segment I of liver'; its related term "
                "is 'caudate lobe', matching the record's own name."},
    "digestive:seg.couinaud-ii": {
        "decision": "resolved", "ta_id": 3068, "basis": "synonym",
        "note": "TA2 synonym 'segment II of liver'."},
    "digestive:seg.couinaud-iii": {
        "decision": "resolved", "ta_id": 3069, "basis": "synonym",
        "note": "TA2 synonym 'segment III of liver'."},
    "digestive:seg.couinaud-iv": {
        "decision": "resolved", "ta_id": 3071, "basis": "synonym",
        "note": "TA2 synonym 'segment IV of liver'."},
    "digestive:seg.couinaud-v": {
        "decision": "resolved", "ta_id": 3076, "basis": "synonym",
        "note": "TA2 synonym 'segment V of liver'."},
    "digestive:seg.couinaud-vi": {
        "decision": "resolved", "ta_id": 3079, "basis": "synonym",
        "note": "TA2 synonym 'segment VI of liver'."},
    "digestive:seg.couinaud-vii": {
        "decision": "resolved", "ta_id": 3080, "basis": "synonym",
        "note": "TA2 synonym 'segment VII of liver'."},
    "digestive:seg.couinaud-viii": {
        "decision": "resolved", "ta_id": 3077, "basis": "synonym",
        "note": "TA2 synonym 'segment VIII of liver'."},
    "integumentary:structure.hair-of-head": {
        "decision": "resolved", "ta_id": 7055, "basis": "preferred",
        "note": "TA2 'capilli', English 'hairs of head' (record name "
                "is the singular collective form)."},
    "integumentary:structure.pubic-hair": {
        "decision": "resolved", "ta_id": 7062, "basis": "preferred",
        "note": "TA2 'pubes', English 'pubic hairs'."},
    "integumentary:gland.sebaceous-glands": {
        "decision": "resolved", "ta_id": 7082, "basis": "preferred",
        "note": "TA2 class term is singular (glandula sebacea); the "
                "record is the class record for the glands."},
    "muscular:muscle.cervical-rotator": {
        "decision": "resolved", "ta_id": 2289, "basis": "synonym",
        "note": "TA2 lists 'rotatores cervicis' among the English "
                "synonyms of rotatores colli."},
    "muscular:muscle.thoracic-rotator": {
        "decision": "resolved", "ta_id": 2286, "basis": "preferred",
        "note": "TA2 'rotatores thoracis'."},
    "muscular:muscle.lumbar-rotator": {
        "decision": "resolved", "ta_id": 2285, "basis": "preferred",
        "note": "TA2 'rotatores lumborum'."},
    "muscular:muscle.interspinalis-thoracis": {
        "decision": "resolved", "ta_id": 2292, "basis": "preferred",
        "note": "TA2 'musculi interspinales thoracis'."},
    "muscular:muscle.set-of-interspinales-cervicis": {
        "decision": "resolved", "ta_id": 2293, "basis": "latin-synonym",
        "note": "TA2 lists the Latin synonym 'musculi interspinales "
                "cervicis' for musculi interspinales colli."},
    "muscular:muscle.set-of-interspinales-lumborum": {
        "decision": "resolved", "ta_id": 2291, "basis": "preferred",
        "note": "TA2 'musculi interspinales lumborum'."},
    "muscular:muscle.lateral-lumbar-intertransversarius": {
        "decision": "resolved", "ta_id": 2239, "basis": "synonym",
        "note": "TA2 English synonym 'lateral lumbar "
                "intertransversarii muscles'."},
    "muscular:muscle.medial-lumbar-intertransversarius": {
        "decision": "resolved", "ta_id": 2295, "basis": "synonym",
        "note": "TA2 English synonym 'medial lumbar "
                "intertransversarii muscles'."},
    "muscular:muscle.set-of-anterior-cervical-intertransversarii": {
        "decision": "resolved", "ta_id": 2237, "basis": "synonym",
        "note": "TA2 English synonym 'anterior cervical "
                "intertransversarii muscles'; Latin synonym carries "
                "the record's own 'cervicis' form."},
    "muscular:muscle.set-of-levatores-costarum-breves": {
        "decision": "resolved", "ta_id": 2310, "basis": "synonym",
        "note": "TA2 English synonym 'levatores costarum breves "
                "muscles'."},
    "muscular:muscle.set-of-levatores-costarum-longi": {
        "decision": "resolved", "ta_id": 2309, "basis": "synonym",
        "note": "TA2 English synonym 'levatores costarum longi "
                "muscles'."},
    "muscular:muscle.flexor-digiti-minimi-brevis-of-hand": {
        "decision": "resolved", "ta_id": 2530, "basis": "synonym",
        "note": "TA2 English synonym 'flexor digiti minimi brevis "
                "muscle of hand' for flexor digiti minimi manus."},
    "muscular:muscle.opponens-digiti-minimi-of-hand": {
        "decision": "resolved", "ta_id": 2531, "basis": "preferred",
        "note": "TA2 'musculus opponens digiti minimi manus', "
                "English 'opponens digiti minimi muscle of hand'."},
    "muscular:muscle.set-of-dorsal-interossei-of-hand": {
        "decision": "resolved", "ta_id": 2533, "basis": "preferred",
        "note": "TA2 'musculi interossei dorsales manus'."},
    "muscular:muscle.set-of-palmar-interossei-of-hand": {
        "decision": "resolved", "ta_id": 2534, "basis": "preferred",
        "note": "TA2 'musculi interossei palmares' (hand chapter "
                "position; its Latin synonym set is I-III)."},
    "muscular:muscle.set-of-lumbricals-of-hand": {
        "decision": "resolved", "ta_id": 2532, "basis": "synonym",
        "note": "TA2 English synonym 'lumbricals of hand' for "
                "musculi lumbricales manus."},
    "nervous:nerve.ilioinguinal": {
        "decision": "resolved", "ta_id": 6499, "basis": "latin-term",
        "note": "TA2 carries no English equivalent for 6499; its "
                "Latin 'nervus ilioinguinalis' is the unique "
                "ilioinguinal nerve entry in the table."},
    "reproductive:gland.seminal-vesicles": {
        "decision": "resolved", "ta_id": 3631, "basis": "synonym",
        "note": "TA2 lists 'seminal vesicle' as the English synonym "
                "and 'vesicula seminalis' as the Latin synonym of "
                "glandula seminalis."},
    "reproductive:gland.bulbourethral-glands": {
        "decision": "resolved", "ta_id": 3659, "basis": "latin-term",
        "note": "TA2 carries no English equivalent for 3659; its "
                "related terms include 'Cowper's gland', the record's "
                "own parenthetical name."},
    "respiratory:resp.main-bronchi": {
        "decision": "resolved", "ta_id": 3227, "basis": "preferred",
        "note": "TA2 class term 'bronchus principalis' (English "
                "'main bronchus'); the sided bronchi are its "
                "children 3237/3252."},
    "respiratory:resp.lobar-bronchi": {
        "decision": "resolved", "ta_id": 3229, "basis": "preferred",
        "note": "TA2 class term 'bronchus lobaris' (English 'lobar "
                "bronchus', synonym 'secondary bronchus')."},
    "respiratory:resp.bronchioles": {
        "decision": "resolved", "ta_id": 3282, "basis": "preferred",
        "note": "TA2 class term 'bronchiolus' (English "
                "'bronchiole')."},
    "respiratory:segment.right-apical": {
        "decision": "resolved", "ta_id": 3285, "basis": "preferred",
        "note": "TA2 synonyms 'segment 1 of right lung', 's1'."},
    "respiratory:segment.right-posterior": {
        "decision": "resolved", "ta_id": 3286, "basis": "preferred",
        "note": "TA2 synonyms 'segment 2 of right lung', 's2'."},
    "respiratory:segment.right-anterior": {
        "decision": "resolved", "ta_id": 3287, "basis": "preferred",
        "note": "TA2 synonyms 'segment 3 of right lung', 's3'."},
    "respiratory:segment.right-lateral": {
        "decision": "resolved", "ta_id": 3290, "basis": "preferred",
        "note": "TA2 synonyms 'segment 4 of right lung', 's4'."},
    "respiratory:segment.right-medial": {
        "decision": "resolved", "ta_id": 3291, "basis": "preferred",
        "note": "TA2 synonyms 'segment 5 of right lung', 's5'."},
    "respiratory:segment.right-superior": {
        "decision": "resolved", "ta_id": 3294, "basis": "preferred",
        "note": "TA2 synonyms 'segment 6 of right lung', 's6'."},
    "respiratory:segment.right-medial-basal": {
        "decision": "resolved", "ta_id": 3295, "basis": "preferred",
        "note": "TA2 synonyms 'segment 7 of right lung', 's7'."},
    "respiratory:segment.right-anterior-basal": {
        "decision": "resolved", "ta_id": 3296, "basis": "preferred",
        "note": "TA2 synonyms 'segment 8 of right lung', 's8'."},
    "respiratory:segment.right-lateral-basal": {
        "decision": "resolved", "ta_id": 3297, "basis": "preferred",
        "note": "TA2 synonyms 'segment 9 of right lung', 's9'."},
    "respiratory:segment.right-posterior-basal": {
        "decision": "resolved", "ta_id": 3298, "basis": "preferred",
        "note": "TA2 synonyms 'segment 10 of right lung', 's10'."},
    "respiratory:segment.left-apicoposterior": {
        "decision": "resolved", "ta_id": 3301, "basis": "preferred",
        "note": "TA2 synonyms 'segment 1+2 of left lung', 's1+2'."},
    "respiratory:segment.left-anterior": {
        "decision": "resolved", "ta_id": 3302, "basis": "preferred",
        "note": "TA2 synonyms 'segment 3 of left lung', 's3'."},
    "respiratory:segment.left-superior-lingular": {
        "decision": "resolved", "ta_id": 3305, "basis": "preferred",
        "note": "TA2 synonyms 'segment 4 of left lung', 's4'."},
    "respiratory:segment.left-inferior-lingular": {
        "decision": "resolved", "ta_id": 3306, "basis": "preferred",
        "note": "TA2 synonyms 'segment 5 of left lung', 's5'."},
    "respiratory:segment.left-superior": {
        "decision": "resolved", "ta_id": 3309, "basis": "preferred",
        "note": "TA2 synonyms 'segment 6 of left lung', 's6'."},
    "respiratory:segment.left-anteromedial-basal": {
        "decision": "resolved", "ta_id": 3311, "basis": "preferred",
        "note": "TA2 synonyms 'segment 7+8', 's7+8' — the combined "
                "left segment, as the record defines it."},
    "respiratory:segment.left-lateral-basal": {
        "decision": "resolved", "ta_id": 3313, "basis": "preferred",
        "note": "TA2 synonyms 'segment 9 of left lung', 's9'."},
    "respiratory:segment.left-posterior-basal": {
        "decision": "resolved", "ta_id": 3314, "basis": "preferred",
        "note": "TA2 synonyms 'segment 10 of left lung', 's10'."},
    # ---- none class, ambiguous ----
    "digestive:dig.cecum-appendix": {
        "decision": "ambiguous", "candidates": [2970, 2976],
        "reason": "compound record (two organs in one record): TA2 "
                  "terms exist separately — 2970 caecum, 2976 "
                  "appendix vermiformis; no single TA2 term denotes "
                  "the pair."},
    "digestive:dig.dentition": {
        "decision": "ambiguous", "candidates": [901, 2818],
        "reason": "TA2 repeats 'dentes' (teeth) under two ids — 901 "
                  "(skeletal chapter) and 2818 (digestive chapter) — "
                  "and carries no term 'dentition' for the dental "
                  "set as such, which is what this record denotes."},
    "digestive:dig.biliary-tree": {
        "decision": "ambiguous",
        "candidates": [3064, 3091, 3092, 3101, 3103],
        "reason": "collective record: TA2 names the parts separately "
                  "(3064 ductus biliferi interlobulares, 3091 ductus "
                  "biliares extrahepatici, 3092 ductus hepaticus "
                  "communis, 3101 ductus cysticus, 3103 ductus "
                  "biliaris) and has no single term for the whole "
                  "biliary tree."},
    "integumentary:organ.mammary-gland": {
        "decision": "ambiguous", "candidates": [7097, 7099],
        "reason": "compound record ('mammary gland and breast'): "
                  "TA2 terms 7097 mamma (breast) and 7099 glandula "
                  "mammaria (mammary gland) each denote part of what "
                  "this single record covers; neither denotes the "
                  "whole."},
    "respiratory:resp.pleura": {
        "decision": "ambiguous", "candidates": [3322, 3316],
        "reason": "compound record ('pleurae and pleural cavities'): "
                  "TA2 terms 3322 pleura and 3316 cavitas pleuralis "
                  "denote its two parts separately."},
    "lymphatic:structure.lymph-nodes": {
        "decision": "ambiguous", "candidates": [5191],
        "reason": "the record covers lymph nodes AND lymphoid tissue "
                  "generally; TA2 5191 nodi lymphoidei denotes the "
                  "nodes only, and lymphoid tissue as such is TA2's "
                  "chapter grouping (5149 organa lymphoidea), not a "
                  "term denoting this record."},
    "muscular:muscle.set-of-posterior-cervical-intertransversarii": {
        "decision": "ambiguous", "candidates": [2238, 2297],
        "reason": "TA2 splits the posterior cervical "
                  "intertransversarii into 2238 (laterales) and 2297 "
                  "(mediales), with no single term for the posterior "
                  "set as a whole."},
    # ---- none class, not found ----
    "integumentary:structure.hair": {
        "decision": "not_found",
        "reason": "TA2 names hairs only by region (7055 capilli, "
                  "7062 pubes, 7059 pili tragi); no generic hair term "
                  "('pilus') exists in the consulted table.",
        "probes": ["pilus"]},
    "integumentary:structure.hair-of-trunk": {
        "decision": "not_found",
        "reason": "no TA2 term for hair of the trunk in the "
                  "consulted table; TA2's regional hair terms cover "
                  "head, pubis and tragus only.",
        "probes": ["trunci", "of trunk"]},
    "lymphatic:pathway.lymphatic-drainage": {
        "decision": "not_found",
        "reason": "project pathway construct (a drainage route, not "
                  "a structure); no TA2 term denotes it.",
        "probes": ["drainage"]},
    "reproductive:pathway.male-reproductive-pathway": {
        "decision": "not_found",
        "reason": "project pathway construct (the sperm pathway as "
                  "a route, not a structure); no TA2 term denotes "
                  "it.",
        "probes": ["pathway"]},
    "reproductive:pathway.female-reproductive-pathway": {
        "decision": "not_found",
        "reason": "project pathway construct (a route, not a "
                  "structure); no TA2 term denotes it.",
        "probes": ["pathway"]},
    "urinary:pathway.urinary-pathway": {
        "decision": "not_found",
        "reason": "project pathway construct (the urine pathway as "
                  "a route, not a structure); TA2 names its organs "
                  "individually.",
        "probes": ["pathway"]},
    "respiratory:resp.segmental-bronchi": {
        "decision": "not_found",
        "reason": "TA2 names the segmental bronchi only individually "
                  "(20 terms); no collective or class term exists "
                  "for them — unlike bronchus principalis (3227) "
                  "and bronchus lobaris (3229), which TA2 does carry "
                  "as class terms.",
        "probes": ["bronchi segmentales", "bronchus segmentalis"]},
    "respiratory:resp.respiratory-bronchioles": {
        "decision": "not_found",
        "reason": "no respiratory-bronchiole term in the consulted "
                  "TA2 table; the served respiratory tree ends at "
                  "3282 bronchiolus.",
        "probes": ["respiratorius", "bronchiolus respiratorius"]},
    "respiratory:resp.alveolar-ducts-and-sacs": {
        "decision": "not_found",
        "reason": "no alveolar duct or alveolar sac term in the "
                  "consulted TA2 table; the served respiratory tree "
                  "ends at 3282 bronchiolus.",
        "probes": ["ductus alveolaris", "sacculus alveolaris",
                   "sacculi alveolares"]},
    "respiratory:resp.alveoli": {
        "decision": "not_found",
        "reason": "no pulmonary alveoli term in the consulted TA2 "
                  "table; in TA2 'alveoli' denotes the dental "
                  "alveoli (793, 853).",
        "probes": ["alveoli pulmonis", "alveolus pulmonis"]},
    "respiratory:resp.mechanics": {
        "decision": "not_found",
        "reason": "measurements (respiratory volumes and "
                  "capacities), not an anatomical structure; no TA2 "
                  "term applies.",
        "probes": ["capacitas", "volumen"]},
    "urinary:structure.nephron": {
        "decision": "not_found",
        "reason": "the string 'nephron' occurs in no TA2 term, "
                  "synonym or related term in the consulted table; "
                  "TA2 2.07 carries no nephron term.",
        "probes": ["nephron"]},
}


def via_basis(via):
    return {"STRONG": "preferred", "SYN": "synonym",
            "REL": "related-term", "CORE": "class-word-form"}[via]


def main():
    ws = json.load(open(WS))
    decisions = {}
    unresolved = []
    for w in ws:
        key = f"{w['system']}:{w['record_id']}"
        if key in OVERRIDES:
            decisions[key] = dict(OVERRIDES[key], name=w["name"],
                                  system=w["system"],
                                  record_id=w["record_id"])
            continue
        auto = w["auto"]
        if auto == "unique-strong":
            c = w["candidates"][0]
            decisions[key] = {
                "decision": "resolved", "ta_id": c["ta_id"],
                "basis": "preferred", "name": w["name"],
                "system": w["system"], "record_id": w["record_id"]}
        elif auto == "unique-weak":
            c = w["candidates"][0]
            decisions[key] = {
                "decision": "resolved", "ta_id": c["ta_id"],
                "basis": via_basis(c["via"]), "name": w["name"],
                "system": w["system"], "record_id": w["record_id"]}
        elif auto == "multi":
            prefixes = ()
            for pre, prefs in CLASS_PREFIX:
                if w["record_id"].startswith(pre):
                    prefixes = prefs
                    break
            strong = [c for c in w["candidates"]
                      if c["via"] == "STRONG"
                      and (c["latin"] or "").strip().lower()
                      .startswith(prefixes)]
            if len(strong) == 1:
                decisions[key] = {
                    "decision": "resolved", "ta_id": strong[0]["ta_id"],
                    "basis": "preferred",
                    "note": "unique STRONG candidate in the record's "
                            "own structure class; remaining candidates "
                            "matched only the bare epithet (CORE keys) "
                            "and denote other structures.",
                    "name": w["name"], "system": w["system"],
                    "record_id": w["record_id"]}
            else:
                unresolved.append((key, w["name"], strong,
                                   w["candidates"]))
        else:
            unresolved.append((key, w["name"], None, w["candidates"]))
    if unresolved:
        print("UNRESOLVED (need overrides):")
        for key, name, strong, cands in unresolved:
            print(" ", key, "|", name, "| strong-in-class:", strong,
                  "| ncand:", len(cands))
        return 1
    from collections import Counter
    print(Counter(d["decision"] for d in decisions.values()))
    print("total decisions:", len(decisions))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(decisions, f, ensure_ascii=False, indent=1)
    print("->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
