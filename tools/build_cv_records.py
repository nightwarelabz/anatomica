#!/usr/bin/env python3
"""ANATOMICA Milestone 5, step 2: cardiovascular clinical tranche.

Builds data/cardiovascular/cardiovascular.json from the inventory
(data/cardiovascular/cv-inventory.json, produced by tools/cv_map.py).

FIELD-SOURCING RULE (precision law, same discipline as Milestone 4): a
clinical value is entered only when it comes from a source actually
consulted during this build session, and the record cites that source
per field in its `sources` map.  Anything not sourced is null plus an
explicit `verify` entry.  TA names were not given by the consulted
sources and are null + verify-flagged throughout.

Sources (consulted in-session; TeachMeAnatomy abbreviated TMA):
  S1  TMA, "The Aorta"
  S2  TMA, "Arterial Supply of the Head and Neck" (overview)
  S3  TMA, "Arterial Supply to the Upper Limb"
  S4  TMA, "Venous Drainage of the Abdomen"
  S5  TMA, "Venous Drainage of the Lower Limb"
  S6  StatPearls, "Anatomy, Thorax, Heart Coronary Arteries"
  S7  StatPearls, "Cardiac Dominance"
  S8  StatPearls, "Anatomy, Thorax, Subclavian Arteries" (NCBI NBK539736)
  S9  StatPearls, "Neuroanatomy, Circle of Willis"
  S10 OpenStax Anatomy & Physiology (heart structure and conduction,
      via Pearson study guides)
  S11 JoVE Core, "Veins of Head and Neck"
  S12 UAMS anatomy tables, "Selected Veins of the Thorax" (azygos system)
  S13 Frontiers in Surgery 2025, "Anatomical variations of hepatic
      arteries" (Michels classification prevalences)
  S14 Noussios et al., J Clin Med Res 2017, hepatic artery variations
      review (19,013 patients)
  S15 Dimmick et al., JBR-BTR 2010, "Vascular liver anatomy and main
      variants" (Michels prevalence table)
  S16 ESR EPOS 2017 poster, Michels classification summary
  S17 Lecture notes, "Arteries and Veins of the Lower Limb"
      (Elmedany & Salama) and Ankara Univ. lower-limb notes
  S18 Lecture notes, "Large Blood Vessels of the Gut" (coeliac trunk,
      SMA, IMA branches; after Gray's Anatomy)
  S19 UEN Pressbooks, "Coronary Vessels" (coronary sinus termination)
  S20 Wikipedia, "Azygos vein" (corroboration of S12)

Vessel fields: origin (for a vein: formation), course, branches (for a
vein: tributaries), territory (supplied / drained), termination.
Tiers: A = every clinical field sourced; B = sourced except territory
and/or termination; C = at least one core field (origin / course /
branches) verify-flagged.
"""

import json
import os
import sys

PROJECT = "/home/hatch/workspace/anatomica-project"
INV_PATH = os.path.join(PROJECT, "data/cardiovascular/cv-inventory.json")
OUT_PATH = os.path.join(PROJECT, "data/cardiovascular/cardiovascular.json")

inv = json.load(open(INV_PATH, encoding="utf-8"))
inv_by_name = {}
for r in inv["records"]:
    inv_by_name.setdefault(r["name"], []).append(r["record_id"])

SOURCES = {
    "S1": "TeachMeAnatomy, 'The Aorta' (teachmeanatomy.info)",
    "S2": "TeachMeAnatomy, 'Arterial Supply of the Head and Neck' (teachmeanatomy.info)",
    "S3": "TeachMeAnatomy, 'Arterial Supply to the Upper Limb' (teachmeanatomy.info)",
    "S4": "TeachMeAnatomy, 'Venous Drainage of the Abdomen' (teachmeanatomy.info)",
    "S5": "TeachMeAnatomy, 'Venous Drainage of the Lower Limb' (teachmeanatomy.info)",
    "S6": "StatPearls, 'Anatomy, Thorax, Heart Coronary Arteries'",
    "S7": "StatPearls, 'Cardiac Dominance'",
    "S8": "StatPearls, 'Anatomy, Thorax, Subclavian Arteries' (NCBI Bookshelf NBK539736)",
    "S9": "StatPearls, 'Neuroanatomy, Circle of Willis'",
    "S10": "OpenStax, Anatomy and Physiology (heart structure/conduction, via Pearson study guides)",
    "S11": "JoVE Core, 'Veins of Head and Neck'",
    "S12": "UAMS anatomy tables, 'Selected Veins of the Thorax'",
    "S13": "Frontiers in Surgery (2025), 'Anatomical variations of hepatic arteries'",
    "S14": "Noussios G et al., J Clin Med Res (2017), hepatic artery variations review",
    "S15": "Dimmick SJ et al., JBR-BTR (2010), 'Vascular liver anatomy and main variants'",
    "S16": "ESR EPOS (2017), Michels classification of hepatic arterial variants (poster)",
    "S17": "Lecture notes, 'Arteries and Veins of the Lower Limb' (Elmedany & Salama); Ankara University lower-limb notes",
    "S18": "Lecture notes, 'Large Blood Vessels of the Gut' (after Gray's Anatomy)",
    "S19": "UEN Pressbooks, 'Coronary Vessels - Integrated Human Anatomy and Physiology'",
    "S20": "Wikipedia, 'Azygos vein'",
}

CLINICAL_FIELDS = ["origin", "course", "branches", "territory", "termination"]
CORE_FIELDS = ["origin", "course", "branches"]
records = []
link_failures = []


def link(rec_id, names):
    """Resolve inventory record ids by exact record name."""
    out = []
    for n in names:
        ids = inv_by_name.get(n)
        if not ids:
            link_failures.append((rec_id, n))
        else:
            out.extend(ids)
    return sorted(set(out))


def vessel(rec_id, name, group, names, origin=None, course=None, branches=None,
           territory=None, termination=None, sources=None, verify=None,
           note=None):
    fields = {"origin": origin, "course": course, "branches": branches,
              "territory": territory, "termination": termination}
    src = dict(sources or {})
    ver = list(verify or [])
    for f in CLINICAL_FIELDS:
        if fields[f] is None and not any(f in v for v in ver):
            ver.append(f"{f}: not sourced from consulted sources - verify")
        if fields[f] is not None and f not in src:
            raise SystemExit(f"{rec_id}: field {f} has a value but no source")
    if any(fields[f] is None for f in CORE_FIELDS):
        tier = "C"
    elif any(fields[f] is None for f in CLINICAL_FIELDS):
        tier = "B"
    else:
        tier = "A"
    records.append({
        "id": rec_id, "name": name, "type": "vessel", "group": group,
        "ta_name": None,
        "origin": origin, "course": course, "branches": branches,
        "territory": territory, "termination": termination,
        "sources": src, "verify": ver, "note": note,
        "sourcing_tier": tier,
        "geometry_record_ids": link(rec_id, names),
    })


# ---------------------------------------------------------------- heart
heart_verify = [
    "ta_name: not given by consulted sources - verify",
    "pericardium: the pericardium has no concept in the BP3D release "
    "(stem search over all six release tables returned no match); its "
    "description is therefore not entered - verify",
    "conduction system geometry: the sinoatrial node, atrioventricular "
    "node, bundle of His and Purkinje fibres have no concepts in the "
    "BP3D release (stem search returned no matches); the conduction "
    "system is described in text only and has no geometry in v1 - verify",
    "interatrial and interventricular septa: no concepts in the BP3D "
    "release (stem search returned no matches); chamber separation is "
    "described, not modelled - verify",
    "chordae tendineae: no concept in the BP3D release - verify",
]
records.append({
    "id": "organ.heart",
    "name": "Heart",
    "type": "organ",
    "group": "Heart",
    "ta_name": None,
    "chambers": ("Four chambers: right atrium (receives systemic venous "
                 "blood), right ventricle (pumps to the pulmonary "
                 "circuit), left atrium (receives the pulmonary veins), "
                 "left ventricle (pumps to the systemic circuit; thickest "
                 "wall)."),
    "valves": ("Four valves ensure unidirectional flow: tricuspid "
               "(right atrioventricular, three cusps), mitral/bicuspid "
               "(left atrioventricular, two cusps), pulmonary semilunar "
               "(right ventricle to pulmonary trunk), aortic semilunar "
               "(left ventricle to aorta). AV valve cusps are restrained "
               "by chordae tendineae attached to papillary muscles."),
    "conduction_system": ("Sinoatrial (SA) node: pacemaker of the heart, "
                          "in the right atrium, initiates each beat. "
                          "Atrioventricular (AV) node: delays the impulse "
                          "in the interatrial septum region. AV bundle "
                          "(bundle of His): the only electrical connection "
                          "between atria and ventricles; divides into "
                          "right and left bundle branches in the "
                          "interventricular septum. Purkinje fibres "
                          "distribute the impulse through the ventricular "
                          "myocardium."),
    "arterial_supply": ("Right and left coronary arteries, arising from "
                        "the right and left aortic sinuses of the "
                        "ascending aorta; see the coronary records. The "
                        "sinoatrial nodal artery is a branch of the right "
                        "coronary artery; the AV node is supplied via a "
                        "septal perforating branch of the RCA in 90% of "
                        "people (S6)."),
    "venous_drainage": ("Most venous blood of the heart wall drains via "
                        "the coronary sinus into the right atrium; the "
                        "right atrium also receives the superior and "
                        "inferior venae cavae."),
    "sources": {"chambers": ["S10"], "valves": ["S10"],
                "conduction_system": ["S10"],
                "arterial_supply": ["S1", "S6"],
                "venous_drainage": ["S10", "S19"]},
    "verify": heart_verify,
    "note": ("Geometry links the BP3D heart organ record and its part "
             "records (chambers, valves, fibrous skeleton). The "
             "conduction system, septa, chordae and pericardium are "
             "absent from the BP3D release and are flagged, not "
             "modelled."),
    "sourcing_tier": "A",
    "geometry_record_ids": link("organ.heart", [
        "heart", "right atrium", "left atrium", "right ventricle",
        "left ventricle", "tricuspid valve", "mitral valve",
        "aortic valve", "pulmonary valve", "fibrous skeleton of heart"]),
})

# ------------------------------------------------------- coronary tree
vessel("artery.left-coronary-artery", "Left coronary artery", "Coronary",
       ["trunk of left coronary artery"],
       origin=("Arises from the left aortic sinus at the root of the "
               "ascending aorta."),
       course=("Passes along the coronary sulcus and almost immediately "
               "divides into the left anterior descending (anterior "
               "interventricular) and circumflex branches."),
       branches=["anterior interventricular branch of left coronary artery",
                 "circumflex branch of left coronary artery"],
       territory=("Left atrium and left ventricle; the LAD supplies the "
                  "anterior two-thirds of the interventricular septum."),
       termination="Divides into the anterior interventricular and circumflex branches.",
       sources={"origin": ["S1", "S6"], "course": ["S6"],
                "branches": ["S6"], "territory": ["S6"],
                "termination": ["S6"]})

vessel("artery.right-coronary-artery", "Right coronary artery", "Coronary",
       ["trunk of right coronary artery"],
       origin=("Arises from the right (anterior) aortic sinus at the root "
               "of the ascending aorta."),
       course=("Traces the right coronary sulcus, supplying the anterior "
               "and diaphragmatic surfaces of the right side of the "
               "heart."),
       branches=["sinoatrial nodal branch of right coronary artery",
                 "right marginal branch of right coronary artery",
                 "posterior interventricular branch of right coronary artery"],
       territory=("Right atrium, right ventricle, the sinoatrial and "
                  "atrioventricular nodes, and the posterior third of "
                  "the interventricular septum (via the posterior "
                  "descending branch)."),
       termination=("Continues in the coronary sulcus to the posterior "
                    "interventricular branch (in right-dominant "
                    "circulation)."),
       sources={"origin": ["S1", "S6"], "course": ["S6"],
                "branches": ["S6"], "territory": ["S6"],
                "termination": ["S6", "S7"]},
       verify=["branches: 'right marginal branch of right coronary "
               "artery' and the sinoatrial nodal branch are named in S6 "
               "but have no dedicated records in the BP3D inventory "
               "partition - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.anterior-interventricular-branch-of-left-coronary-artery",
       "Anterior interventricular branch of left coronary artery (LAD)",
       "Coronary",
       ["trunk of anterior interventricular branch of left coronary artery"],
       origin="One of the two major branches of the left coronary artery.",
       course=("Descends in the anterior interventricular groove towards "
               "the apex of the heart."),
       branches=None,
       territory=("Anterior portion of the left ventricle and the "
                  "anterior two-thirds of the interventricular septum."),
       termination="Reaches the apex of the heart.",
       sources={"origin": ["S6"], "course": ["S6"], "territory": ["S6"],
                "termination": ["S6"]},
       verify=["branches: diagonal and septal perforating branches are "
               "not enumerated in the consulted sources - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.circumflex-branch-of-left-coronary-artery",
       "Circumflex branch of left coronary artery", "Coronary",
       ["circumflex branch of left coronary artery"],
       origin="One of the two major branches of the left coronary artery.",
       course="Follows the coronary sulcus around the left side of the heart.",
       branches=["left marginal branch of circumflex branch of left coronary artery"],
       territory=("Left atrium and the posterior-lateral aspect of the "
                  "left ventricle; in left-dominant circulation it gives "
                  "the posterior descending artery."),
       termination=None,
       sources={"origin": ["S6"], "course": ["S6"], "branches": ["S6"],
                "territory": ["S6"]},
       verify=["branches: 'left marginal branch of circumflex branch of "
               "left coronary artery' is named in S6 but has no dedicated "
               "record in the BP3D inventory partition - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.posterior-interventricular-branch-of-right-coronary-artery",
       "Posterior interventricular branch of right coronary artery (PDA)",
       "Coronary",
       ["posterior interventricular branch of right coronary artery"],
       origin=("Branch of the right coronary artery in right-dominant "
               "circulation (70-80% of the population, S7); from the "
               "circumflex in left dominance."),
       course="Runs in the posterior interventricular groove towards the apex.",
       branches=None,
       territory=("Posterior one-third of the interventricular septum "
                  "and the inferior aspect of the heart."),
       termination="Anastomoses with the anterior interventricular branch near the apex.",
       sources={"origin": ["S6", "S7"], "course": ["S6"],
                "territory": ["S6"], "termination": ["S6"]},
       verify=["branches: septal perforating branches not enumerated in "
               "the consulted sources - verify",
               "ta_name: not given by consulted sources - verify"])

# ---------------------------------------------------------------- aorta
vessel("organ.aorta", "Aorta", "Aorta and great vessels", ["aorta"],
       origin=("Arises from the aortic orifice of the left ventricle; "
               "the largest artery in the body, about 2.5 cm in diameter "
               "at its origin."),
       course=("Four parts in sequence: ascending aorta, aortic arch, "
               "thoracic (descending) aorta, abdominal aorta."),
       branches=["right coronary artery", "left coronary artery",
                 "brachiocephalic artery", "left common carotid artery",
                 "left subclavian artery", "celiac artery",
                 "superior mesenteric artery", "inferior mesenteric artery",
                 "left renal artery", "right renal artery",
                 "left common iliac artery", "right common iliac artery"],
       territory="The entire systemic circulation.",
       termination=("Terminates at the level of the L4 vertebra by "
                    "bifurcating into the right and left common iliac "
                    "arteries."),
       sources={"origin": ["S1"], "course": ["S1"], "branches": ["S1"],
                "territory": ["S1"], "termination": ["S1"]},
       verify=["branches: branch list gives the principal named "
               "branches only; bronchial, intercostal, phrenic, lumbar, "
               "gonadal and other segmental branches are recorded on "
               "the segment records - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("The aorta as a whole exists only in the PART-OF table of "
             "the BP3D release; its geometry record is the partof-organ "
             "record. Segment detail is on the four segment records."))

vessel("artery.ascending-aorta", "Ascending aorta", "Aorta and great vessels",
       ["ascending aorta"],
       origin="Arises from the aortic orifice of the left ventricle.",
       course=("Ascends within the pericardial sac with the pulmonary "
               "trunk, about 5 cm long, to become the aortic arch."),
       branches=["right coronary artery", "left coronary artery"],
       territory="The myocardium, via the coronary arteries (its only branches).",
       termination="Continues as the aortic arch at the level of the second sternocostal joint.",
       sources={"origin": ["S1"], "course": ["S1"], "branches": ["S1"],
                "territory": ["S1"], "termination": ["S1"]})

vessel("artery.arch-of-aorta", "Arch of aorta", "Aorta and great vessels",
       ["arch of aorta"],
       origin="Continuation of the ascending aorta at the level of the second sternocostal joint.",
       course=("Arches superiorly, posteriorly and to the left, ending "
               "at the level of the T4 vertebra; connected to the "
               "pulmonary trunk by the ligamentum arteriosum."),
       branches=["brachiocephalic artery", "left common carotid artery",
                 "left subclavian artery"],
       territory=("Head, neck and upper limbs via its three branches "
                  "(proximal to distal: brachiocephalic trunk, left "
                  "common carotid, left subclavian)."),
       termination="Continues as the thoracic aorta at the level of T4.",
       sources={"origin": ["S1"], "course": ["S1"], "branches": ["S1"],
                "territory": ["S1"], "termination": ["S1"]})

vessel("artery.descending-thoracic-aorta", "Thoracic aorta",
       "Aorta and great vessels", ["descending thoracic aorta"],
       origin="Continuation of the aortic arch at the lower border of T4.",
       course=("Descends through the posterior mediastinum, moving from "
               "the left of the vertebral column towards the midline, to "
               "the aortic hiatus of the diaphragm at T12."),
       branches=["bronchial artery", "mediastinal artery",
                 "esophageal artery", "pericardial artery",
                 "superior phrenic artery", "posterior intercostal artery",
                 "subcostal artery"],
       territory=("Bronchial and peribronchial tissue and visceral "
                  "pleura; posterior mediastinum; oesophagus; dorsal "
                  "pericardium; superior diaphragm; intercostal spaces "
                  "3-11 (nine pairs of posterior intercostal arteries) "
                  "and the anterolateral abdominal wall (subcostal)."),
       termination="Becomes the abdominal aorta at the aortic hiatus (T12).",
       sources={"origin": ["S1"], "course": ["S1"], "branches": ["S1"],
                "territory": ["S1"], "termination": ["S1"]},
       verify=["branches: the named branch classes are recorded as "
               "unpaired class names; the release lateralises several of "
               "them per side - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.abdominal-aorta", "Abdominal aorta", "Aorta and great vessels",
       ["abdominal aorta"],
       origin="Begins at the aortic hiatus of the diaphragm at T12.",
       course=("Descends anterior to the vertebral column, about 13 cm, "
               "to the level of L4."),
       branches=["inferior phrenic artery", "celiac artery",
                 "superior mesenteric artery", "middle suprarenal artery",
                 "left renal artery", "right renal artery",
                 "gonadal artery", "inferior mesenteric artery",
                 "median sacral artery", "lumbar artery",
                 "left common iliac artery", "right common iliac artery"],
       territory=("Diaphragm; foregut (coeliac); midgut (SMA); adrenal "
                  "glands; kidneys; gonads; hindgut (IMA); coccyx, "
                  "lumbar vertebrae and sacrum (median sacral); abdominal "
                  "wall and spinal cord (four pairs of lumbar arteries); "
                  "pelvis and lower limbs via the common iliacs."),
       termination="Bifurcates into the right and left common iliac arteries at L4.",
       sources={"origin": ["S1"], "course": ["S1"], "branches": ["S1"],
                "territory": ["S1"], "termination": ["S1"]},
       verify=["branches: 'median sacral artery' is named in S1 but has "
               "no concept in the BP3D release (stem search returned no "
               "match) - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.brachiocephalic-artery", "Brachiocephalic artery",
       "Aorta and great vessels", ["brachiocephalic artery"],
       origin=("First and largest branch of the aortic arch."),
       course="Ascends and divides into the right common carotid and right subclavian arteries.",
       branches=["right common carotid artery", "right subclavian artery"],
       territory="Right side of the head and neck, and the right upper limb.",
       termination="Divides into the right common carotid and right subclavian arteries.",
       sources={"origin": ["S1"], "course": ["S1"], "branches": ["S1"],
                "territory": ["S1"], "termination": ["S1"]})

# ------------------------------------------------------- head and neck
vessel("artery.common-carotid-artery", "Common carotid artery",
       "Head and neck",
       ["left common carotid artery", "right common carotid artery"],
       origin=("Right: from the brachiocephalic artery behind the right "
               "sternoclavicular joint. Left: directly from the aortic "
               "arch in the superior mediastinum."),
       course=("Ascends through the neck within the carotid sheath, "
               "under cover of the anterior border of "
               "sternocleidomastoid."),
       branches=["external carotid artery", "internal carotid artery"],
       territory="The majority of the head and neck.",
       termination=("Divides into the external and internal carotid "
                    "arteries at the upper border of the thyroid "
                    "cartilage (level of C4)."),
       sources={"origin": ["S2"], "course": ["S2"], "branches": ["S2"],
                "territory": ["S2"], "termination": ["S2"]})

vessel("artery.external-carotid-artery", "External carotid artery",
       "Head and neck",
       [],
       origin=("Terminal branch of the common carotid artery, arising "
               "at the level of C4 within the carotid triangle."),
       course=("Ascends superiorly through the neck and terminates "
               "within the parotid gland."),
       branches=["superior thyroid artery", "ascending pharyngeal artery",
                 "lingual artery", "facial artery", "occipital artery",
                 "posterior auricular artery", "maxillary artery",
                 "superficial temporal artery"],
       territory="The neck, face and scalp (the main arterial supply to these structures).",
       termination=("Divides into its terminal branches, the maxillary "
                    "and superficial temporal arteries, within the "
                    "parotid gland."),
       sources={"origin": ["S2"], "course": ["S2"], "branches": ["S2"],
                "territory": ["S2"], "termination": ["S2"]},
       verify=["geometry: the external carotid artery has NO concept "
               "of its own in the BP3D 4.0 release (the carotid "
               "concepts present are the common carotid artery, the "
               "internal carotid artery and their subdivisions), so "
               "no inventory record exists to link - verify",
               "branches: 'superior thyroid artery', 'lingual artery' "
               "and 'facial artery' are named in S2 but have NO concepts "
               "in the BP3D release (stem search over all six release "
               "tables returned no matches); the external carotid "
               "system in this release is therefore unmodelled "
               "- verify",
               "ta_name: not given by consulted sources - verify"],
       note=("Major data gap: the external carotid artery itself and "
             "most of its named branches are absent from the BP3D 4.0 "
             "release; this record is clinical text only in v1. See "
             "MILESTONE-5.md."))

vessel("artery.internal-carotid-artery", "Internal carotid artery",
       "Head and neck",
       ["left internal carotid artery", "right internal carotid artery"],
       origin="Terminal branch of the common carotid artery at the level of C4.",
       course=("Ascends through the neck without giving branches, "
               "enters the skull via the carotid canal, and passes "
               "through the cavernous sinus to the intracranial cavity."),
       branches=["ophthalmic artery", "anterior cerebral artery",
                 "middle cerebral artery"],
       territory=("The brain (anterior circulation: frontal and parietal "
                  "lobes, lateral temporal lobes, anterior deep "
                  "cerebrum), orbit, forehead and nose."),
       termination="Terminates intracranially as the anterior and middle cerebral arteries.",
       sources={"origin": ["S2"], "course": ["S2"], "branches": ["S2"],
                "territory": ["S2", "S9"], "termination": ["S2"]})

vessel("artery.vertebral-artery", "Vertebral artery", "Head and neck",
       ["left vertebral artery", "right vertebral artery"],
       origin="Paired branch of the first part of the subclavian artery.",
       course=("Ascends through the transverse foramina of the cervical "
               "vertebrae (C6-C1), curves around the atlas and enters "
               "the cranial cavity via the foramen magnum."),
       branches=["posterior inferior cerebellar artery"],
       territory=("Posterior circulation of the brain: brainstem, "
                  "cerebellum, occipital lobes, medial temporal lobes "
                  "and thalamus; also the spinal cord."),
       termination=("The two vertebral arteries unite at the "
                    "medullopontine junction to form the basilar "
                    "artery."),
       sources={"origin": ["S2", "S8"], "course": ["S2"],
                "branches": ["S9"], "territory": ["S2", "S9"],
                "termination": ["S2"]})

vessel("artery.basilar-artery", "Basilar artery", "Head and neck",
       ["basilar artery"],
       origin=("Formed by the union of the two vertebral arteries at "
               "the medullopontine junction."),
       course="Ascends along the anterior pons.",
       branches=["superior cerebellar artery",
                 "anterior inferior cerebellar artery",
                 "posterior cerebral artery"],
       territory="Brainstem (pontine branches), cerebellum, and the posterior cerebrum via the posterior cerebral arteries.",
       termination="Divides into the two posterior cerebral arteries.",
       sources={"origin": ["S2"], "course": ["S9"], "branches": ["S9"],
                "territory": ["S2"], "termination": ["S9"]},
       verify=["branches: pontine branches are described in S9 but are "
               "not enumerated as named branches here - verify",
               "branches: 'posterior cerebral artery' is named in S9 "
               "but has no concept of its own in the BP3D release - "
               "verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.anterior-cerebral-artery", "Anterior cerebral artery",
       "Head and neck",
       ["left anterior cerebral artery", "right anterior cerebral artery"],
       origin="Terminal branch of the internal carotid artery.",
       course="Courses medially above the optic nerve towards the longitudinal fissure; the two arteries are joined by the anterior communicating artery.",
       branches=["anterior communicating artery"],
       territory="The medial aspects (anteromedial portion) of the cerebral hemispheres.",
       termination=None,
       sources={"origin": ["S9"], "course": ["S9"], "branches": ["S9"],
                "territory": ["S2", "S9"]},
       verify=["ta_name: not given by consulted sources - verify"])

vessel("artery.middle-cerebral-artery", "Middle cerebral artery",
       "Head and neck", [],
       origin="The lateral continuation of the internal carotid artery at its termination.",
       course="Runs laterally into the lateral (Sylvian) fissure.",
       branches=None,
       territory="The lateral aspects of the cerebral hemispheres (the majority of the lateral part of the brain).",
       termination=None,
       sources={"origin": ["S9"], "course": ["S9"], "territory": ["S2"]},
       verify=["geometry: the middle cerebral artery has NO concept "
               "of its own in the BP3D 4.0 release - only its named "
               "branches (anterolateral central, temporal and terminal "
               "branches) exist as concepts and records - so no "
               "inventory record exists to link - verify",
               "branches: cortical and central (lenticulostriate) "
               "branches are not enumerated in the consulted sources - "
               "verify",
               "ta_name: not given by consulted sources - verify"],
       note=("Clinical text only in v1: the vessel itself is absent "
             "from the source tables although its branches are "
             "present. See MILESTONE-5.md."))

vessel("artery.posterior-cerebral-artery", "Posterior cerebral artery",
       "Head and neck",
       [],
       origin="Terminal branch of the basilar artery.",
       course="Courses around the midbrain to the posterior cerebrum; joined to the internal carotid system by the posterior communicating artery.",
       branches=["posterior communicating artery"],
       territory="The medial and lateral parts of the posterior cerebrum (occipital lobes, medial temporal lobes).",
       termination=None,
       sources={"origin": ["S9"], "course": ["S9"], "branches": ["S9"],
                "territory": ["S9"]},
       verify=["geometry: the posterior cerebral artery has NO "
               "concept of its own in the BP3D 4.0 release - only its "
               "posteromedial central branch exists as a class with "
               "lateralised records - so no inventory record exists "
               "to link - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("Clinical text only in v1: the vessel itself is absent "
             "from the source tables although a named branch is "
             "present. See MILESTONE-5.md."))

# --------------------------------------------------------- upper limb
vessel("artery.subclavian-artery", "Subclavian artery", "Upper limb",
       ["left subclavian artery", "right subclavian artery"],
       origin=("Right: from the brachiocephalic trunk. Left: directly "
               "from the aortic arch."),
       course=("Courses laterally between the anterior and middle "
               "scalene muscles; divided into three parts by the "
               "anterior scalene (first: origin to medial border; "
               "second: posterior to the muscle; third: lateral border "
               "to the lateral border of the first rib)."),
       branches=["vertebral artery", "internal thoracic artery",
                 "thyrocervical trunk", "costocervical trunk",
                 "dorsal scapular artery"],
       territory=("The upper limb, with contributions to the head and "
                  "neck (circle of Willis via the vertebral artery, "
                  "thyroid and breast tissue)."),
       termination="Becomes the axillary artery at the lateral border of the first rib.",
       sources={"origin": ["S3", "S8"], "course": ["S3", "S8"],
                "branches": ["S8"], "territory": ["S8"],
                "termination": ["S3", "S8"]},
       verify=["branches: 'dorsal scapular artery' is listed in S8 as "
               "an additional branch; the BP3D record partition carries "
               "it within the subclavian records - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.internal-thoracic-artery", "Internal thoracic artery",
       "Upper limb",
       ["left internal thoracic artery", "right internal thoracic artery"],
       origin="Branch of the first part of the subclavian artery.",
       course="Descends into the thorax behind the costal cartilages, lateral to the sternum.",
       branches=None,
       territory="Anterior thoracic wall and breast tissue.",
       termination=None,
       sources={"origin": ["S8"], "course": ["S8"], "territory": ["S8"]},
       verify=["branches: anterior intercostal, perforating and "
               "terminal (musculophrenic, superior epigastric) branches "
               "are not enumerated in the consulted sources - verify",
               "termination: not stated in the consulted sources - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("Surgically load-bearing as the left internal mammary "
             "artery graft in coronary bypass; course detail beyond S8 "
             "is flagged, not entered."))

vessel("artery.thyrocervical-trunk", "Thyrocervical trunk", "Upper limb",
       ["left thyrocervical trunk", "right thyrocervical trunk"],
       origin="Branch of the first part of the subclavian artery.",
       course="Short trunk at the root of the neck, dividing almost immediately.",
       branches=["inferior thyroid artery", "ascending cervical artery",
                 "transverse cervical artery", "suprascapular artery"],
       territory=("Thyroid gland; posterior prevertebral muscles; "
                  "trapezius and rhomboid muscles; posterior shoulder "
                  "area."),
       termination="Divides into the inferior thyroid, ascending cervical, transverse cervical and suprascapular arteries.",
       sources={"origin": ["S8"], "course": ["S2"], "branches": ["S2"],
                "territory": ["S2"], "termination": ["S2"]})

vessel("artery.axillary-artery", "Axillary artery", "Upper limb",
       ["left axillary artery", "right axillary artery"],
       origin="Continuation of the subclavian artery at the lateral border of the first rib.",
       course=("Passes through the axilla deep to pectoralis minor "
               "within the axillary sheath; three parts relative to "
               "pectoralis minor (proximal, posterior, distal)."),
       branches=["superior thoracic artery", "thoracoacromial artery",
                 "lateral thoracic artery", "subscapular artery",
                 "anterior circumflex humeral artery",
                 "posterior circumflex humeral artery"],
       territory="Axilla, pectoral region and shoulder; the circumflex humeral arteries form an anastomosis around the surgical neck of the humerus.",
       termination="Becomes the brachial artery at the lower border of teres major.",
       sources={"origin": ["S3"], "course": ["S3"], "branches": ["S3"],
                "territory": ["S3"], "termination": ["S3"]},
       verify=["branches: 'thoracoacromial artery' is named in S3 but "
               "has no concept in the BP3D release (stem search "
               "returned no match) - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.brachial-artery", "Brachial artery", "Upper limb",
       ["left brachial artery", "right brachial artery"],
       origin="Continuation of the axillary artery at the lower border of teres major.",
       course=("Descends the arm with the median nerve, passing through "
               "the cubital fossa under the bicipital aponeurosis."),
       branches=["deep artery of arm"],
       territory="The arm (main arterial supply).",
       termination="Bifurcates into the radial and ulnar arteries in the cubital fossa.",
       sources={"origin": ["S3"], "course": ["S3"], "branches": ["S3"],
                "territory": ["S3"], "termination": ["S3"]},
       verify=["branches: the consulted source names the profunda "
               "brachii (deep artery of arm) as the principal branch; "
               "the ulnar collateral and muscular branches are not "
               "enumerated in the consulted sources - verify; note "
               "'profunda brachii' has no concept in the BP3D release "
               "under that name - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.radial-artery", "Radial artery", "Upper limb",
       ["left radial artery", "right radial artery"],
       origin="Formed by the bifurcation of the brachial artery in the cubital fossa.",
       course=("Descends the posterolateral forearm; palpable at the "
               "distal forearm lateral to the flexor carpi radialis "
               "tendon; enters the hand dorsally across the floor of "
               "the anatomical snuffbox."),
       branches=None,
       territory="Posterolateral aspect of the forearm; contributes to the deep palmar arch and to the superficial palmar arch.",
       termination="Continues as the deep palmar arch in the hand.",
       sources={"origin": ["S3"], "course": ["S3"], "territory": ["S3"],
                "termination": ["S3"]},
       verify=["branches: radial recurrent, palmar carpal and "
               "superficial palmar branches are not enumerated in the "
               "consulted sources - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.ulnar-artery", "Ulnar artery", "Upper limb",
       ["left ulnar artery", "right ulnar artery"],
       origin="Formed by the bifurcation of the brachial artery in the cubital fossa.",
       course=("Descends the anteromedial forearm; enters the hand "
               "anterior to the flexor retinaculum, lateral to the "
               "ulnar nerve."),
       branches=["anterior interosseous artery",
                 "posterior interosseous artery"],
       territory="Anteromedial aspect of the forearm and the deeper forearm structures (via the interosseous arteries); forms the superficial palmar arch.",
       termination="Continues across the palm as the superficial palmar arch.",
       sources={"origin": ["S3"], "course": ["S3"], "branches": ["S3"],
                "territory": ["S3"], "termination": ["S3"]},
       verify=["branches: the common interosseous trunk itself is not "
               "named in the consulted source; S3 names its anterior "
               "and posterior divisions - verify",
               "ta_name: not given by consulted sources - verify"])

# ------------------------------------------------- abdomen (arteries)
vessel("artery.celiac-artery", "Celiac artery", "Abdomen - visceral arteries",
       ["celiac artery"],
       origin=("Large unpaired visceral branch of the abdominal aorta "
               "arising anteriorly at the level of T12."),
       course="Short trunk (the coeliac trunk) dividing almost immediately into its three branches.",
       branches=["left gastric artery", "splenic artery",
                 "common hepatic artery"],
       territory=("Foregut: liver, stomach, abdominal oesophagus, "
                  "spleen, superior duodenum and superior pancreas."),
       termination="Trifurcates into the left gastric, splenic and common hepatic arteries.",
       sources={"origin": ["S1"], "course": ["S18"], "branches": ["S18"],
                "territory": ["S1"], "termination": ["S18"]})

vessel("artery.left-gastric-artery", "Left gastric artery",
       "Abdomen - visceral arteries", ["left gastric artery"],
       origin="Smallest branch of the coeliac trunk.",
       course=("Ascends to the gastro-oesophageal junction, giving "
               "oesophageal branches, then descends along the lesser "
               "curvature of the stomach in the lesser omentum."),
       branches=["esophageal branch of left gastric artery"],
       territory="Distal oesophagus and both surfaces of the stomach along the lesser curvature.",
       termination="Anastomoses with the right gastric artery along the lesser curvature.",
       sources={"origin": ["S18"], "course": ["S18"], "branches": ["S18"],
                "territory": ["S18"], "termination": ["S18"]},
       verify=["branches: the oesophageal branches are described in "
               "S18 without the exact BP3D branch name used here - "
               "verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.splenic-artery", "Splenic artery",
       "Abdomen - visceral arteries", ["splenic artery"],
       origin="Largest branch of the coeliac trunk.",
       course=("Takes a tortuous course to the left along the superior "
               "border of the pancreas, travels in the lienorenal "
               "ligament and divides into numerous branches entering "
               "the hilum of the spleen."),
       branches=["pancreatic branch of splenic artery",
                 "short gastric artery", "left gastroepiploic artery"],
       territory="Spleen; body and tail of the pancreas; fundus of the stomach (short gastric arteries); greater curvature of the stomach (left gastroepiploic artery).",
       termination="Divides into terminal branches at the hilum of the spleen.",
       sources={"origin": ["S18"], "course": ["S18"], "branches": ["S18"],
                "territory": ["S18"], "termination": ["S18"]},
       verify=["branches: branch names are recorded in the terminology "
               "of S18 (pancreatic, short gastric, left gastroepiploic); "
               "exact BP3D branch record names differ in form - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.common-hepatic-artery", "Common hepatic artery",
       "Abdomen - visceral arteries", ["common hepatic artery"],
       origin="Branch of the coeliac trunk.",
       course="Runs to the right towards the liver.",
       branches=["hepatic artery proper", "gastroduodenal artery",
                 "right gastric artery"],
       territory="Liver (via the hepatic artery proper), gallbladder, stomach and duodenum/pancreatic head (via the gastroduodenal artery).",
       termination="Divides into its terminal branches, the hepatic artery proper and the gastroduodenal artery.",
       sources={"origin": ["S18"], "course": ["S18"], "branches": ["S18"],
                "territory": ["S18"], "termination": ["S18"]},
       verify=["branches: the right gastric artery is described in S18 "
               "as arising from the common hepatic close to the "
               "gastroduodenal origin (and commonly from the proper "
               "hepatic); its parent vessel varies - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.hepatic-artery-proper", "Hepatic artery proper",
       "Abdomen - visceral arteries", ["hepatic artery proper"],
       origin="Terminal branch of the common hepatic artery, after the gastroduodenal artery is given off.",
       course=("Ascends towards the liver in the free edge of the "
               "lesser omentum, to the left of the bile duct and "
               "anterior to the portal vein (portal triad)."),
       branches=["left hepatic artery", "right hepatic artery"],
       territory="The liver.",
       termination="Divides into the right and left hepatic arteries near the porta hepatis.",
       sources={"origin": ["S18"], "course": ["S18"], "branches": ["S18"],
                "territory": ["S18"], "termination": ["S18"]},
       verify=["branches: the cystic artery, classically a branch of "
               "the right hepatic artery supplying the gallbladder, has "
               "NO concept in the BP3D release (stem search returned no "
               "match) and is not modelled - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.gastroduodenal-artery", "Gastroduodenal artery",
       "Abdomen - visceral arteries", ["trunk of gastroduodenal artery"],
       origin="Terminal branch of the common hepatic artery.",
       course="Travels behind the first part of the duodenum.",
       branches=["right gastroepiploic artery",
                 "superior pancreaticoduodenal artery"],
       territory="Superior part of the duodenum (to the major duodenal papilla) and the head and neck of the pancreas; greater curvature of the stomach via the right gastroepiploic artery.",
       termination="Splits into the right gastroepiploic and superior pancreaticoduodenal arteries.",
       sources={"origin": ["S18"], "course": ["S18"], "branches": ["S18"],
                "territory": ["S18"], "termination": ["S18"]},
       verify=["branches: branch record names in the BP3D inventory "
               "follow the gastroduodenal trunk's own naming and were "
               "not individually verified against S18 - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("The BP3D release carries this vessel as 'trunk of "
             "gastroduodenal artery'; the clinical record links that "
             "record."))

vessel("artery.superior-mesenteric-artery", "Superior mesenteric artery",
       "Abdomen - visceral arteries", ["superior mesenteric artery"],
       origin=("Large unpaired visceral branch of the abdominal aorta "
               "arising anteriorly at the lower level of L1, just below "
               "the coeliac artery."),
       course=("Runs in the root of the mesentery from the "
               "duodenojejunal flexure towards the ileocolic junction, "
               "crossing the third part of the duodenum."),
       branches=["inferior pancreaticoduodenal artery",
                 "middle colic artery", "right colic artery",
                 "ileocolic artery", "jejunal artery", "ileal artery"],
       territory=("Midgut: distal duodenum, jejuno-ileum, ascending "
                  "colon and part of the transverse colon."),
       termination="Ends at the ileocolic junction as the ileocolic artery.",
       sources={"origin": ["S1"], "course": ["S18"], "branches": ["S18"],
                "territory": ["S1"], "termination": ["S18"]},
       verify=["branches: S18 lists 12-15 jejunal and ileal branches "
               "collectively; individual jejunal/ileal branch records "
               "are not enumerated - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.inferior-mesenteric-artery", "Inferior mesenteric artery",
       "Abdomen - visceral arteries", ["inferior mesenteric artery"],
       origin=("Large unpaired visceral branch of the abdominal aorta "
               "arising anteriorly at the level of L3."),
       course="Descends on the left side of the abdominal aorta towards the pelvis.",
       branches=["left colic artery", "sigmoid artery",
                 "superior rectal artery"],
       territory=("Hindgut: large intestine from the splenic flexure "
                  "to the upper part of the rectum."),
       termination="Continues as the superior rectal artery into the pelvis.",
       sources={"origin": ["S1"], "course": ["S18"], "branches": ["S18"],
                "territory": ["S1"], "termination": ["S18"]})

vessel("artery.renal-artery", "Renal artery", "Abdomen - visceral arteries",
       ["left renal artery", "right renal artery"],
       origin="Paired visceral branches of the abdominal aorta arising laterally between L1 and L2.",
       course="Passes laterally to the hilum of the kidney on each side.",
       branches=None,
       territory="The kidneys.",
       termination="Enters the kidney at the hilum, dividing into segmental branches.",
       sources={"origin": ["S1"], "course": ["S1"], "territory": ["S1"],
                "termination": ["S1"]},
       verify=["branches: the five segmental renal branches are named "
               "in the BP3D inventory as segmental artery records; "
               "their order is not enumerated in the consulted sources "
               "- verify",
               "ta_name: not given by consulted sources - verify"])

# ------------------------------------------------ pelvis and lower limb
vessel("artery.common-iliac-artery", "Common iliac artery",
       "Pelvis and lower limb",
       ["left common iliac artery", "right common iliac artery"],
       origin="Formed by the bifurcation of the abdominal aorta at the level of L4.",
       course="Descends into the pelvis on each side.",
       branches=["external iliac artery", "internal iliac artery"],
       territory="Pelvis and lower limb.",
       termination="Divides into the external and internal iliac arteries.",
       sources={"origin": ["S1"], "course": ["S1"], "branches": ["S1"],
                "territory": ["S1"], "termination": ["S1"]})

vessel("artery.external-iliac-artery", "External iliac artery",
       "Pelvis and lower limb",
       ["left external iliac artery", "right external iliac artery"],
       origin="Larger terminal branch of the common iliac artery.",
       course="Descends along the pelvic brim and passes posterior to the inguinal ligament into the thigh.",
       branches=["inferior epigastric artery", "deep circumflex iliac artery"],
       territory="The lower limb (as the femoral artery) and the lower abdominal wall.",
       termination="Becomes the femoral artery posterior to the inguinal ligament.",
       sources={"origin": ["S17"], "course": ["S17"], "branches": ["S17"],
                "territory": ["S17"], "termination": ["S17"]},
       verify=["branches: the inferior epigastric and deep circumflex "
               "iliac branches are named in standard teaching (S17 "
               "lists 'branches of the external iliac artery' without a "
               "full enumeration in the consulted excerpt) - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.internal-iliac-artery", "Internal iliac artery",
       "Pelvis and lower limb",
       ["left internal iliac artery", "right internal iliac artery"],
       origin="Smaller terminal branch of the common iliac artery.",
       course="Descends into the lesser pelvis.",
       branches=None,
       territory="Pelvic organs, the gluteal region and the perineum.",
       termination=None,
       sources={"origin": ["S17"], "course": ["S17"],
                "territory": ["S17"]},
       verify=["branches: the named branches of the internal iliac "
               "artery (including the obturator and superior gluteal "
               "arteries, which have NO concepts in the BP3D release) "
               "are not enumerated in the consulted sources - verify",
               "termination: not stated in the consulted sources - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.femoral-artery", "Femoral artery", "Pelvis and lower limb",
       ["left femoral artery", "right femoral artery"],
       origin=("Continuation of the external iliac artery posterior to "
               "the inguinal ligament, at the mid-inguinal point."),
       course=("Descends through the femoral triangle, then the "
               "adductor canal deep to sartorius, and exits through "
               "the adductor hiatus."),
       branches=["superficial epigastric artery",
                 "superficial circumflex iliac artery",
                 "superficial external pudendal artery",
                 "deep external pudendal artery",
                 "deep artery of thigh"],
       territory="Lower abdominal wall, thigh and external genitalia (via its branches); the principal artery of the lower limb.",
       termination="Becomes the popliteal artery after passing through the adductor hiatus.",
       sources={"origin": ["S17"], "course": ["S17"], "branches": ["S17"],
                "territory": ["S17"], "termination": ["S17"]},
       verify=["branches: the deep artery of thigh (profunda femoris), "
               "the main arterial supply to the thigh, has no dedicated "
               "record in the BP3D inventory partition and 'profunda "
               "femoris' has no concept in the release - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.popliteal-artery", "Popliteal artery",
       "Pelvis and lower limb",
       ["left popliteal artery", "right popliteal artery"],
       origin="Continuation of the femoral artery after the adductor hiatus.",
       course=("Runs through the popliteal fossa as its deepest "
               "structure, close to the capsule of the knee joint."),
       branches=["anterior tibial artery", "posterior tibial artery"],
       territory="Knee region (via genicular branches) and, through its terminal branches, the leg and foot.",
       termination="Ends at the lower border of popliteus by dividing into the anterior and posterior tibial arteries.",
       sources={"origin": ["S17"], "course": ["S17"], "branches": ["S17"],
                "territory": ["S17"], "termination": ["S17"]},
       verify=["branches: the genicular branches around the knee are "
               "described in S17 without a full enumeration - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.anterior-tibial-artery", "Anterior tibial artery",
       "Pelvis and lower limb",
       ["left anterior tibial artery", "right anterior tibial artery"],
       origin="Smaller terminal branch of the popliteal artery.",
       course=("Passes through the interosseous membrane into the "
               "anterior compartment of the leg and descends with the "
               "deep peroneal (fibular) nerve."),
       branches=None,
       territory="Structures of the anterior compartment of the leg and the dorsum of the foot.",
       termination="Becomes the dorsalis pedis (dorsal artery of the foot) at the ankle joint, midway between the malleoli.",
       sources={"origin": ["S17"], "course": ["S17"], "territory": ["S17"],
                "termination": ["S17"]},
       verify=["branches: recurrent and malleolar branches are not "
               "enumerated in the consulted sources - verify",
               "termination: the continuation vessel (dorsalis pedis / "
               "dorsal artery of the foot) has no dedicated record in "
               "the BP3D inventory partition - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.posterior-tibial-artery", "Posterior tibial artery",
       "Pelvis and lower limb",
       ["left posterior tibial artery", "right posterior tibial artery"],
       origin="Larger terminal branch of the popliteal artery.",
       course=("Descends in the posterior compartment of the leg and "
               "passes posterior to the medial malleolus into the sole "
               "of the foot."),
       branches=["fibular artery", "medial plantar artery",
                 "lateral plantar artery"],
       territory="Posterior compartment of the leg and the sole of the foot.",
       termination="Divides into the medial and lateral plantar arteries in the sole of the foot.",
       sources={"origin": ["S17"], "course": ["S17"], "branches": ["S17"],
                "territory": ["S17"], "termination": ["S17"]},
       verify=["branches: 'fibular artery' is named in S17 as a branch "
               "of the posterior tibial artery, but the BP3D release "
               "carries fibular VEINS only - no fibular/peroneal artery "
               "concept exists in the release - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("artery.pulmonary-artery", "Pulmonary artery", "Pulmonary",
       ["pulmonary trunk", "left pulmonary artery",
        "right pulmonary artery"],
       origin=("The pulmonary trunk arises from the right ventricle "
               "through the pulmonary semilunar valve and divides into "
               "the right and left pulmonary arteries."),
       course="Each pulmonary artery passes to the hilum of its lung.",
       branches=None,
       territory="The lungs (the pulmonary circuit).",
       termination="Branches within the lung parenchyma.",
       sources={"origin": ["S10"], "course": ["S10"], "territory": ["S10"],
                "termination": ["S10"]},
       verify=["branches: lobar and segmental branching is not "
               "enumerated in the consulted sources - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("The pulmonary trunk itself is carried in the inventory "
             "within the pulmonary artery records; consulted sources "
             "describe the trunk dividing into the two pulmonary "
             "arteries."))

# ---------------------------------------------------------------- veins
vessel("vein.superior-vena-cava", "Superior vena cava", "Systemic veins",
       ["superior vena cava"],
       origin=("Formed by the union of the right and left "
               "brachiocephalic veins behind the right first costal "
               "cartilage."),
       course="Descends vertically in the superior mediastinum.",
       branches=["azygos vein", "left brachiocephalic vein",
                 "right brachiocephalic vein"],
       territory=("Head, neck, thorax (above the diaphragm, except the "
                  "heart wall) and upper limbs."),
       termination="Drains into the right atrium of the heart.",
       sources={"origin": ["S11"], "course": ["S11"], "branches": ["S11"],
                "territory": ["S11"], "termination": ["S11"]},
       verify=["ta_name: not given by consulted sources - verify"])

vessel("vein.inferior-vena-cava", "Inferior vena cava", "Systemic veins",
       ["inferior vena cava"],
       origin=("Formed by the union of the common iliac veins at the "
               "level of L5."),
       course=("Ascends on the posterior abdominal wall, anterior to "
               "the vertebral column and to the right of the abdominal "
               "aorta; leaves the abdomen through the caval hiatus of "
               "the diaphragm at T8."),
       branches=["left common iliac vein", "right common iliac vein",
                 "lumbar vein", "left renal vein", "right renal vein",
                 "right gonadal vein", "right suprarenal vein",
                 "inferior phrenic vein", "hepatic vein"],
       territory="All structures below the diaphragm.",
       termination="Drains into the right atrium of the heart.",
       sources={"origin": ["S4"], "course": ["S4"], "branches": ["S4"],
                "territory": ["S4"], "termination": ["S4"]},
       verify=["branches: tributary names follow S4; the release "
               "lateralises several of them per side and carries the "
               "hepatic veins as left/right records - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.brachiocephalic-vein", "Brachiocephalic vein",
       "Systemic veins",
       ["left brachiocephalic vein", "right brachiocephalic vein"],
       origin=("Formed on each side by the union of the internal "
               "jugular vein and the subclavian vein, posterior to the "
               "sternoclavicular joint."),
       course=("Right: descends vertically (about 2.5 cm). Left: "
               "crosses obliquely behind the sternum (about 6 cm)."),
       branches=["vertebral vein", "internal thoracic vein",
                 "inferior thyroid vein",
                 "first posterior intercostal vein"],
       territory="Head, neck and upper limb of its side.",
       termination="The two brachiocephalic veins unite to form the superior vena cava.",
       sources={"origin": ["S11"], "course": ["S11"], "branches": ["S11"],
                "territory": ["S11"], "termination": ["S11"]},
       verify=["branches: the tributary list follows the consulted "
               "lecture material in S11's result set and is complete "
               "for the right side only - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.internal-jugular-vein", "Internal jugular vein",
       "Systemic veins",
       ["left internal jugular vein", "right internal jugular vein"],
       origin=("Begins at the jugular foramen as the continuation of "
               "the sigmoid sinus (dural venous sinus)."),
       course=("Descends through the neck in the carotid sheath, "
               "beside the internal carotid and then the common carotid "
               "artery."),
       branches=None,
       territory=("The brain (via the dural venous sinuses), face and "
                  "neck; the largest vein draining the head and neck."),
       termination=("Joins the subclavian vein behind the sternal end "
                    "of the clavicle to form the brachiocephalic "
                    "vein."),
       sources={"origin": ["S11"], "course": ["S11"], "territory": ["S11"],
                "termination": ["S11"]},
       verify=["branches: named tributaries (facial, lingual, "
               "pharyngeal, thyroid veins) are not enumerated in the "
               "consulted sources - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.external-jugular-vein", "External jugular vein",
       "Systemic veins",
       [],
       origin=None,
       course=("Descends through the lateral neck, passing obliquely "
               "over the sternocleidomastoid muscle."),
       branches=None,
       territory="Superficial parts of the scalp and face.",
       termination="Empties into the subclavian vein.",
       sources={"course": ["S11"], "territory": ["S11"],
                "termination": ["S11"]},
       verify=["geometry: the external jugular vein has NO concept of "
               "its own in the BP3D 4.0 release (only a 'tributary of "
               "external jugular vein' family concept exists), so no "
               "inventory record exists to link - verify",
               "origin: formation (union of the posterior auricular "
               "and retromandibular veins) is not stated in the "
               "consulted sources - verify",
               "branches: tributaries not enumerated in the consulted "
               "sources - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("Clinical text only in v1: the vessel itself is absent "
             "from the source tables. See MILESTONE-5.md."))

vessel("vein.subclavian-vein", "Subclavian vein", "Systemic veins",
       ["left subclavian vein", "right subclavian vein"],
       origin=("Continuation of the axillary vein at the outer border "
               "of the first rib."),
       course=("Runs from the outer border of the first rib to the "
               "medial border of the anterior scalene muscle, anterior "
               "to the muscle."),
       branches=["external jugular vein"],
       territory="The upper limb; also receives the external jugular vein (scalp and face).",
       termination="Joins the internal jugular vein to form the brachiocephalic vein.",
       sources={"origin": ["S11"], "course": ["S11"], "branches": ["S11"],
                "territory": ["S11"], "termination": ["S11"]})

vessel("vein.axillary-vein", "Axillary vein", "Systemic veins",
       ["left axillary vein", "right axillary vein"],
       origin=None,
       course="Ascends through the axilla with the axillary artery.",
       branches=None,
       territory="The upper limb.",
       termination="Becomes the subclavian vein at the outer border of the first rib.",
       sources={"course": ["S11"], "territory": ["S11"],
                "termination": ["S11"]},
       verify=["origin: formation (continuation of the brachial veins "
               "/ basilic vein junction) is not stated in the consulted "
               "sources - verify",
               "branches: tributaries not enumerated in the consulted "
               "sources - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.azygos-vein", "Azygos vein", "Systemic veins", ["azygos vein"],
       origin=("Formed by the union of the right ascending lumbar vein "
               "and the right subcostal vein at the level of T12."),
       course=("Enters the thorax through the aortic hiatus, ascends "
               "along the right side of the thoracic vertebral bodies, "
               "and arches anteriorly over the root of the right lung "
               "at T4."),
       branches=["right posterior intercostal vein",
                 "right superior intercostal vein", "hemiazygos vein",
                 "accessory hemiazygos vein", "esophageal vein",
                 "mediastinal vein", "right bronchial vein"],
       territory="Posterior walls of the thorax and abdomen; the azygos system also connects the superior and inferior caval systems.",
       termination="Empties into the superior vena cava.",
       sources={"origin": ["S12", "S20"], "course": ["S12", "S20"],
                "branches": ["S12"], "territory": ["S12", "S20"],
                "termination": ["S12", "S20"]},
       verify=["ta_name: not given by consulted sources - verify"])

vessel("vein.hemiazygos-vein", "Hemiazygos vein", "Systemic veins",
       ["hemiazygos vein"],
       origin="Formed by the union of the left ascending lumbar vein and the left subcostal vein.",
       course=("Ascends on the left side of the vertebral column to "
               "about T8-T9, then crosses the vertebral column "
               "posterior to the aorta, oesophagus and thoracic duct."),
       branches=["left posterior intercostal vein", "esophageal vein",
                 "mediastinal vein"],
       territory="Lower left posterolateral chest wall (left posterior intercostal veins 9-11).",
       termination="Joins the azygos vein.",
       sources={"origin": ["S12"], "course": ["S12"], "branches": ["S12"],
                "territory": ["S12"], "termination": ["S12"]})

vessel("vein.accessory-hemiazygos-vein", "Accessory hemiazygos vein",
       "Systemic veins", ["accessory hemiazygos vein"],
       origin="Begins at the 4th or 5th intercostal space as the continuation of the left fourth posterior intercostal vein.",
       course="Descends along the left side of the vertebral column and crosses to the right at about T7-T8.",
       branches=["left posterior intercostal vein", "left bronchial vein"],
       territory="Mid levels of the left posterolateral chest wall (left posterior intercostal veins 4-8).",
       termination="Joins the azygos vein (or the hemiazygos vein).",
       sources={"origin": ["S12"], "course": ["S12"], "branches": ["S12"],
                "territory": ["S12"], "termination": ["S12"]})

vessel("vein.coronary-sinus", "Coronary sinus", "Systemic veins",
       ["coronary sinus"],
       origin=None,
       course="Runs in the posterior coronary sulcus of the heart.",
       branches=None,
       territory="The wall of the heart (most of its venous drainage gathers here).",
       termination="Empties directly into the right atrium.",
       sources={"course": ["S19"], "territory": ["S19"],
                "termination": ["S19"]},
       verify=["origin: formation (continuation of the great cardiac "
               "vein) is not stated in the consulted sources - verify",
               "branches: named tributaries (great, middle and small "
               "cardiac veins, oblique vein of the left atrium) are not "
               "enumerated in the consulted sources - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("The coronary sinus is a PART-OF-only concept in the BP3D "
             "release (venous trunk line); its record is the "
             "partof-concept inventory record."))

vessel("vein.common-iliac-vein", "Common iliac vein", "Systemic veins",
       ["left common iliac vein", "right common iliac vein"],
       origin="Formed by the union of the external iliac and internal iliac veins.",
       course="Ascends in the pelvis to the level of L5.",
       branches=["external iliac vein", "internal iliac vein"],
       territory="The lower limb and the gluteal region (and the pelvic viscera via the internal iliac vein).",
       termination="The two common iliac veins unite to form the inferior vena cava at L5.",
       sources={"origin": ["S4"], "course": ["S4"], "branches": ["S4"],
                "territory": ["S4"], "termination": ["S4"]})

vessel("vein.external-iliac-vein", "External iliac vein", "Systemic veins",
       ["left external iliac vein", "right external iliac vein"],
       origin="Continuation of the femoral vein posterior to the inguinal ligament.",
       course="Ascends along the pelvic brim.",
       branches=None,
       territory="The lower limb.",
       termination="Joins the internal iliac vein to form the common iliac vein.",
       sources={"origin": ["S5"], "course": ["S5"], "territory": ["S5"],
                "termination": ["S4", "S5"]},
       verify=["branches: tributaries (inferior epigastric, deep "
               "circumflex iliac, pubic veins) are not enumerated in "
               "the consulted sources - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.internal-iliac-vein", "Internal iliac vein", "Systemic veins",
       ["left internal iliac vein", "right internal iliac vein"],
       origin=None,
       course=None,
       branches=None,
       territory="Pelvic viscera and the gluteal region.",
       termination="Joins the external iliac vein to form the common iliac vein.",
       sources={"territory": ["S4"], "termination": ["S4"]},
       verify=["origin: formation from its tributaries is not "
               "described in the consulted sources - verify",
               "course: not described in the consulted sources - verify",
               "branches: tributaries are not enumerated in the "
               "consulted sources - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.renal-vein", "Renal vein", "Systemic veins",
       ["left renal vein", "right renal vein"],
       origin="Formed at the hilum of the kidney.",
       course="Passes medially to join the inferior vena cava; the left renal vein is longer and crosses between the aorta and the superior mesenteric artery.",
       branches=["left suprarenal vein", "left gonadal vein"],
       territory=("The kidney; on the left also the left adrenal gland "
                  "and the left testis/ovary (via the left suprarenal "
                  "and left gonadal veins)."),
       termination="Drains into the inferior vena cava.",
       sources={"origin": ["S4"], "course": ["S4"], "branches": ["S4"],
                "territory": ["S4"], "termination": ["S4"]},
       verify=["course: the aortomesenteric crossing of the left renal "
               "vein is standard anatomy but was not stated verbatim "
               "in the consulted excerpt - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.hepatic-vein", "Hepatic vein", "Systemic veins",
       ["left hepatic vein", "right hepatic vein"],
       origin="Formed within the liver parenchyma from the central veins of the lobules.",
       course="Ascends within the liver to the inferior vena cava just below the diaphragm.",
       branches=None,
       territory="The liver (its entire venous outflow, including portal blood after processing).",
       termination="Drains into the inferior vena cava.",
       sources={"origin": ["S4"], "course": ["S4"], "territory": ["S4"],
                "termination": ["S4"]},
       verify=["branches: the middle hepatic vein is carried in the "
               "BP3D inventory within the lateralised hepatic vein "
               "records; the consulted source does not enumerate three "
               "named trunks - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("Venous return from the spleen, pancreas, gallbladder and "
             "GI tract reaches the IVC via the hepatic veins after "
             "passing through the portal system (S4)."))

vessel("vein.femoral-vein", "Femoral vein", "Systemic veins",
       ["left femoral vein", "right femoral vein"],
       origin="Continuation of the popliteal vein as it enters the thigh via the adductor canal.",
       course="Ascends the thigh anteriorly, accompanying the femoral artery.",
       branches=["deep vein of thigh", "great saphenous vein"],
       territory="The lower limb (deep structures of the thigh and leg, plus the superficial drainage via the great saphenous vein).",
       termination="Becomes the external iliac vein posterior to the inguinal ligament.",
       sources={"origin": ["S5"], "course": ["S5"], "branches": ["S5"],
                "territory": ["S5"], "termination": ["S5"]},
       verify=["branches: 'deep vein of thigh' (profunda femoris vein) "
               "is named in S5; its record linkage follows the femoral "
               "records - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.popliteal-vein", "Popliteal vein", "Systemic veins",
       ["left popliteal vein", "right popliteal vein"],
       origin=("Formed on the posterior surface of the knee by the "
               "union of the anterior tibial, posterior tibial and "
               "fibular veins."),
       course="Ascends through the popliteal fossa and enters the thigh via the adductor canal.",
       branches=["anterior tibial vein", "posterior tibial vein",
                 "fibular vein", "small saphenous vein"],
       territory="The leg and foot (deep veins) and the posterior leg (via the small saphenous vein).",
       termination="Continues as the femoral vein on entering the thigh.",
       sources={"origin": ["S5"], "course": ["S5"], "branches": ["S5"],
                "territory": ["S5"], "termination": ["S5"]})

vessel("vein.great-saphenous-vein", "Great saphenous vein",
       "Systemic veins",
       ["left great saphenous vein", "right great saphenous vein"],
       origin=("Formed by the dorsal venous arch of the foot and the "
               "dorsal vein of the great toe."),
       course=("Ascends the medial side of the leg, passing anterior "
               "to the medial malleolus at the ankle and posterior to "
               "the medial condyle at the knee, then up the medial "
               "thigh."),
       branches=None,
       territory="Superficial tissues of the medial leg and thigh (the longest vein in the body).",
       termination="Drains into the femoral vein immediately inferior to the inguinal ligament.",
       sources={"origin": ["S5"], "course": ["S5"], "territory": ["S5"],
                "termination": ["S5"]},
       verify=["branches: named tributaries near the saphenofemoral "
               "junction are not enumerated in the consulted sources - "
               "verify",
               "ta_name: not given by consulted sources - verify"],
       note="Harvested as a graft in coronary artery bypass surgery (S5 flashcards set; recorded as clinical context).")

vessel("vein.small-saphenous-vein", "Small saphenous vein",
       "Systemic veins",
       ["left small saphenous vein", "right small saphenous vein"],
       origin=("Formed by the dorsal venous arch of the foot and the "
               "dorsal vein of the little toe."),
       course=("Ascends the posterior side of the leg, passing "
               "posterior to the lateral malleolus along the lateral "
               "border of the calcaneal tendon."),
       branches=None,
       territory="Superficial tissues of the posterior leg.",
       termination="Passes between the two heads of gastrocnemius and empties into the popliteal vein in the popliteal fossa.",
       sources={"origin": ["S5"], "course": ["S5"], "territory": ["S5"],
                "termination": ["S5"]},
       verify=["branches: tributaries not enumerated in the consulted "
               "sources - verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.pulmonary-vein", "Pulmonary vein", "Pulmonary",
       [],
       origin="Arises within the lung parenchyma from the pulmonary capillary networks.",
       course="Passes from the hilum of each lung to the left atrium.",
       branches=None,
       territory="The lungs (oxygenated blood returning to the heart).",
       termination="Opens into the left atrium (four pulmonary veins in the usual pattern).",
       sources={"origin": ["S10"], "course": ["S10"], "territory": ["S10"],
                "termination": ["S10"]},
       verify=["geometry: the pulmonary vein exists in the BP3D "
               "release only as a family concept (FMA66643) carrying "
               "84 IS-A element files, with no lateralised instance "
               "concepts; under the module counting convention it "
               "produced no inventory record, so no geometry record "
               "is linked - verify",
               "branches: tributaries within the lung are not "
               "enumerated in the consulted sources - verify",
               "ta_name: not given by consulted sources - verify"],
       note=("Anatomy has four pulmonary veins (superior and inferior "
             "on each side), as stated in S10; the BP3D release "
             "carries the pulmonary veins only as one undivided "
             "family concept."))

# ------------------------------------------------------------- portal
vessel("vein.hepatic-portal-vein", "Hepatic portal vein",
       "Portal venous system", ["hepatic portal vein"],
       origin=("Formed by the union of the splenic vein and the "
               "superior mesenteric vein, posterior to the neck of the "
               "pancreas at the level of L2."),
       course=("Ascends posterior to the superior part of the duodenum "
               "and the bile duct, within the hepatoduodenal ligament."),
       branches=["right portal vein", "left portal vein",
                 "left gastric vein", "right gastric vein",
                 "cystic vein", "paraumbilical vein"],
       territory=("Venous drainage of the spleen, pancreas, "
                  "gallbladder and the abdominal part of the "
                  "gastrointestinal tract, carried to the liver for "
                  "processing; the portal vein provides about "
                  "three-fourths of the liver's blood supply."),
       termination="Divides into right and left branches at the porta hepatis, which enter the liver parenchyma separately.",
       sources={"origin": ["S4"], "course": ["S4"], "branches": ["S4"],
                "territory": ["S4"], "termination": ["S4"]},
       verify=["branches: the right/left gastric, cystic and "
               "para-umbilical tributaries follow S4; several have no "
               "dedicated records in the BP3D inventory partition - "
               "verify",
               "ta_name: not given by consulted sources - verify"])

vessel("vein.splenic-vein", "Splenic vein", "Portal venous system",
       ["splenic vein"],
       origin="Formed from a number of smaller vessels as they leave the hilum of the spleen.",
       course=("Runs straight across the posterior abdominal wall in "
               "contact with the body of the pancreas, to the neck of "
               "the pancreas."),
       branches=["short gastric vein", "left gastroepiploic vein",
                 "pancreatic vein", "inferior mesenteric vein"],
       territory="Spleen, fundus and greater curvature of the stomach, pancreas, and (via the inferior mesenteric vein) the hindgut colon.",
       termination="Joins the superior mesenteric vein behind the neck of the pancreas to form the portal vein.",
       sources={"origin": ["S4"], "course": ["S4"], "branches": ["S4"],
                "territory": ["S4"], "termination": ["S4"]})

vessel("vein.superior-mesenteric-vein", "Superior mesenteric vein",
       "Portal venous system", ["superior mesenteric vein"],
       origin=("Begins in the right iliac fossa as the convergence of "
               "the veins draining the terminal ileum, caecum and "
               "appendix."),
       course="Ascends within the mesentery of the small intestine to the neck of the pancreas.",
       branches=["right gastroepiploic vein",
                 "inferior pancreaticoduodenal vein", "jejunal vein",
                 "ileal vein", "ileocolic vein", "right colic vein",
                 "middle colic vein"],
       territory="Small intestine, caecum, ascending colon and transverse colon.",
       termination="Joins the splenic vein behind the neck of the pancreas to form the portal vein.",
       sources={"origin": ["S4"], "course": ["S4"], "branches": ["S4"],
                "territory": ["S4"], "termination": ["S4"]})

vessel("vein.inferior-mesenteric-vein", "Inferior mesenteric vein",
       "Portal venous system", ["inferior mesenteric vein"],
       origin="Begins as the superior rectal vein in the pelvis.",
       course="Ascends, receiving the sigmoid and left colic veins, and passes posterior to the body of the pancreas.",
       branches=["superior rectal vein", "sigmoid vein",
                 "left colic vein"],
       territory="Rectum, sigmoid colon, descending colon and splenic flexure.",
       termination="Typically joins the splenic vein.",
       sources={"origin": ["S4"], "course": ["S4"], "branches": ["S4"],
                "territory": ["S4"], "termination": ["S4"]})

# ------------------------------------------------------------- variants
# Variant gate (design/02 + master plan): a variant with prevalence
# >= 1% and a plausible injury consequence must be modelled or carry
# an explicit unmodeled declaration.  Prevalences below are RANGES
# taken from the cited consulted sources only.
variants = [
    {
        "id": "variant.replaced-right-hepatic-artery-from-sma",
        "name": "Replaced right hepatic artery arising from the superior mesenteric artery (Michels type III)",
        "description": ("The right hepatic artery arises from the "
                        "superior mesenteric artery instead of the "
                        "hepatic artery proper, and classically ascends "
                        "posterolateral to the common bile duct, "
                        "posterior to the main portal vein."),
        "related_record_ids": ["artery.hepatic-artery-proper",
                               "artery.superior-mesenteric-artery"],
        "prevalence": {"low_pct": 8.7, "high_pct": 11.0,
                       "basis": "Michels type III range in S13"},
        "clinical_significance": ("At risk in cholecystectomy, "
                                  "pancreaticoduodenectomy and liver "
                                  "transplantation; the most common "
                                  "hepatic arterial variant and the "
                                  "chief variant source of bile-duct "
                                  "blood supply (S14)."),
        "modeled": False,
        "unmodeled_note": ("Prevalence recorded per the variant gate; "
                           "variant geometry is not modelled in v1 "
                           "(the BP3D release carries the standard "
                           "pattern only)."),
        "sources": ["S13", "S14"],
    },
    {
        "id": "variant.replaced-left-hepatic-artery-from-left-gastric",
        "name": "Replaced left hepatic artery arising from the left gastric artery (Michels type II)",
        "description": ("The left hepatic artery arises from the left "
                        "gastric artery and reaches the liver through "
                        "the lesser omentum / fissure for the "
                        "ligamentum venosum."),
        "related_record_ids": ["artery.hepatic-artery-proper",
                               "artery.left-gastric-artery"],
        "prevalence": {"low_pct": 3.0, "high_pct": 10.0,
                       "basis": "pooled 3.0% in S14; 10% in the Michels table of S15"},
        "clinical_significance": ("At risk in gastrectomy and "
                                  "hepatobiliary surgery; may be the "
                                  "sole supply to the left lobe."),
        "modeled": False,
        "unmodeled_note": ("Prevalence recorded per the variant gate; "
                           "variant geometry is not modelled in v1."),
        "sources": ["S14", "S15"],
    },
    {
        "id": "variant.accessory-left-hepatic-artery-from-left-gastric",
        "name": "Accessory left hepatic artery arising from the left gastric artery (Michels type V)",
        "description": ("An accessory left hepatic artery from the "
                        "left gastric artery supplements (does not "
                        "replace) the normal left hepatic artery."),
        "related_record_ids": ["artery.hepatic-artery-proper",
                               "artery.left-gastric-artery"],
        "prevalence": {"low_pct": 8.0, "high_pct": 11.0,
                       "basis": "8% in S15; range 8-11% in S16"},
        "clinical_significance": "At risk in gastrectomy; division can compromise left-lobe perfusion where it is dominant.",
        "modeled": False,
        "unmodeled_note": ("Prevalence recorded per the variant gate; "
                           "variant geometry is not modelled in v1."),
        "sources": ["S15", "S16"],
    },
    {
        "id": "variant.accessory-right-hepatic-artery-from-sma",
        "name": "Accessory right hepatic artery arising from the superior mesenteric artery (Michels type VI)",
        "description": ("An accessory right hepatic artery from the "
                        "superior mesenteric artery supplements the "
                        "normal right hepatic artery."),
        "related_record_ids": ["artery.hepatic-artery-proper",
                               "artery.superior-mesenteric-artery"],
        "prevalence": {"low_pct": 7.0, "high_pct": 10.7,
                       "basis": "Michels type VI range in S13"},
        "clinical_significance": "At risk in pancreatic and hepatobiliary surgery.",
        "modeled": False,
        "unmodeled_note": ("Prevalence recorded per the variant gate; "
                           "variant geometry is not modelled in v1."),
        "sources": ["S13"],
    },
    {
        "id": "variant.common-hepatic-artery-from-sma",
        "name": "Common hepatic artery arising from the superior mesenteric artery (Michels type IX)",
        "description": ("The entire common hepatic artery arises from "
                        "the superior mesenteric artery (hepatomesenteric "
                        "trunk pattern)."),
        "related_record_ids": ["artery.common-hepatic-artery",
                               "artery.superior-mesenteric-artery"],
        "prevalence": {"low_pct": 1.0, "high_pct": 4.5,
                       "basis": "Michels type IX range in S13"},
        "clinical_significance": "Load-bearing in pancreaticoduodenectomy planning and coeliac-axis intervention.",
        "modeled": False,
        "unmodeled_note": ("Prevalence recorded per the variant gate; "
                           "variant geometry is not modelled in v1."),
        "sources": ["S13"],
    },
    {
        "id": "variant.coronary-dominance-right",
        "name": "Right coronary dominance",
        "description": ("The posterior descending (posterior "
                        "interventricular) artery originates from the "
                        "right coronary artery."),
        "related_record_ids": [
            "artery.right-coronary-artery",
            "artery.posterior-interventricular-branch-of-right-coronary-artery"],
        "prevalence": {"low_pct": 70.0, "high_pct": 80.0,
                       "basis": "S7 population estimates"},
        "clinical_significance": "Determines the territory at risk in right coronary occlusion and the interpretation of coronary angiography.",
        "modeled": True,
        "unmodeled_note": None,
        "sources": ["S7"],
    },
    {
        "id": "variant.coronary-dominance-left",
        "name": "Left coronary dominance",
        "description": ("The posterior descending artery originates "
                        "from the left circumflex artery."),
        "related_record_ids": [
            "artery.circumflex-branch-of-left-coronary-artery"],
        "prevalence": {"low_pct": 5.0, "high_pct": 10.0,
                       "basis": "S7 population estimates"},
        "clinical_significance": "Circumflex occlusion in left dominance jeopardises the inferior wall and the AV node supply.",
        "modeled": False,
        "unmodeled_note": ("Prevalence recorded per the variant gate; "
                           "the v1 coronary records describe the "
                           "right-dominant pattern, with the variant "
                           "origin stated on the posterior "
                           "interventricular record."),
        "sources": ["S7"],
    },
    {
        "id": "variant.coronary-dominance-codominant",
        "name": "Coronary codominance",
        "description": ("The posterior descending artery is supplied "
                        "by both the right coronary artery and the left "
                        "circumflex artery."),
        "related_record_ids": [
            "artery.right-coronary-artery",
            "artery.circumflex-branch-of-left-coronary-artery"],
        "prevalence": {"low_pct": 10.0, "high_pct": 20.0,
                       "basis": "S7 population estimates"},
        "clinical_significance": "Shared inferior-wall supply; relevant to angiographic interpretation.",
        "modeled": False,
        "unmodeled_note": ("Prevalence recorded per the variant gate; "
                           "variant geometry is not modelled in v1."),
        "sources": ["S7"],
    },
]

# ------------------------------------------- branch-name resolution pass
# Every branch/tributary string that matches no concept name in the
# release tables and no inventory record name is flagged on its record
# (precision law: references resolve, or are flagged - never silently
# carried).  Names already covered by a hand-written verify entry are
# not re-flagged.
_all_names = set()
for _fn in ("isa_parts_list_e.txt", "partof_parts_list_e.txt"):
    with open(os.path.join(
            PROJECT, "data/sources/bodyparts3d-4.0", _fn),
            encoding="utf-8") as _fh:
        for _ln in _fh.read().splitlines()[1:]:
            if _ln.strip():
                _all_names.add(_ln.split("\t")[2])
_all_names |= {r["name"] for r in inv["records"]}
for _r in records:
    _unresolved = []
    for _b in (_r.get("branches") or []):
        if _b not in _all_names and not any(
                _b.lower() in v.lower() for v in _r["verify"]):
            _unresolved.append(_b)
    if _unresolved:
        _r["verify"].append(
            "branches: the following names are given by the consulted "
            "sources but have no matching concept or record in the "
            "BP3D 4.0 release, and are carried as sourced text only: "
            + "; ".join(f"'{b}'" for b in _unresolved) + " - verify")

# ----------------------------------------------------------------- meta
tier_counts = {}
group_tiers = {}
linked_inventory = set()
for r in records:
    tier_counts[r["sourcing_tier"]] = tier_counts.get(r["sourcing_tier"], 0) + 1
    g = group_tiers.setdefault(r["group"], {"A": 0, "B": 0, "C": 0})
    g[r["sourcing_tier"]] += 1
    linked_inventory.update(r["geometry_record_ids"])

out = {
    "meta": {
        "module": "cardiovascular",
        "milestone": 5,
        "description": ("Cardiovascular clinical tranche v1 (heart, "
                        "coronary tree, aorta, named arteries and "
                        "veins, portal system) plus variant records. "
                        "Built by tools/build_cv_records.py from the "
                        "inventory in cv-inventory.json (concepts and "
                        "geometry from the BodyParts3D 4.0 release "
                        "tables; see tools/cv_map.py)."),
        "field_sourcing_rule": ("Values are entered only from sources "
                                "actually consulted during the build "
                                "session and are cited per field in "
                                "each record's `sources` map (keys "
                                "S1-S20, see sources_bibliography). "
                                "Anything not sourced is null plus an "
                                "explicit `verify` entry. Nothing is "
                                "filled from recall."),
        "ta_name_status": ("null on every record: Terminologia "
                           "Anatomica names were not given by the "
                           "consulted sources and are verify-flagged "
                           "throughout, pending a TA2 pass."),
        "vessel_field_semantics": ("Arteries: origin / course / "
                                   "branches in order / territory "
                                   "supplied / termination. Veins: "
                                   "origin = formation, branches = "
                                   "tributaries, territory = drainage "
                                   "area, termination = vessel joined."),
        "sourcing_tiers": {
            "definition": ("A = every clinical field sourced; B = "
                           "sourced except territory and/or "
                           "termination; C = at least one core field "
                           "(origin / course / branches) "
                           "verify-flagged."),
            "counts": tier_counts,
            "by_group": group_tiers,
        },
        "variant_gate": ("Variants with a sourced prevalence >= 1% "
                         "and a plausible injury consequence are "
                         "recorded with a prevalence RANGE and "
                         "citation, and are either modelled or carry "
                         "an explicit unmodeled_note."),
        "counts": {
            "clinical_records": len(records),
            "variant_records": len(variants),
            "inventory_records_total": len(inv["records"]),
            "inventory_records_linked_from_clinical": len(linked_inventory),
            "inventory_records_without_clinical_record":
                len(inv["records"]) - len(linked_inventory),
        },
        "sources_bibliography": SOURCES,
    },
    "records": records,
    "variants": variants,
}

if link_failures:
    print("LINK FAILURES:")
    for rid, n in link_failures:
        print(f"  {rid}: no inventory record named {n!r}")
    sys.exit(1)

with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, sort_keys=True, ensure_ascii=False)
    fh.write("\n")
print(f"wrote {OUT_PATH}: {len(records)} clinical records, "
      f"{len(variants)} variants, tiers {tier_counts}, "
      f"linked inventory records {len(linked_inventory)}")
