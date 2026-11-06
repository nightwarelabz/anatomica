#!/usr/bin/env python3
"""ANATOMICA Milestone 10, step 2: respiratory system clinical tranche.

Builds data/respiratory/respiratory.json from the inventory
(data/respiratory/respiratory-inventory.json, produced by
tools/resp_map.py).

FIELD-SOURCING RULE (precision law, same discipline as Milestones 4,
5 and 9): a clinical value is entered only when it comes from a
source actually consulted during this build session, and the record
cites that source per field in its `sources` map. Anything not
sourced is null plus an explicit `verify` entry. TA names were not
given by the consulted sources and are null + verify-flagged
throughout. The mechanics values carry their source's own caveat
that they are approximates which vary between sources.

Sources (consulted in-session; TeachMeAnatomy abbreviated TMA):
  S1  TMA, "The Lungs" (lobes, fissures, surfaces, borders, root and
      hilum, vasculature, nerve supply, lymphatics)
  S2  TMA, "The Tracheobronchial Tree" (trachea position/structure/
      carina, main and lobar and segmental bronchi, bronchioles,
      alveoli ~300 million)
  S3  TMA, "The Pleurae" (visceral/parietal parts, pleural cavity,
      recesses, neurovascular supply)
  S4  Wikipedia, "Bronchopulmonary segment" (definition and the
      Jackson & Huber segment list: 10 right; left apico-posterior
      and anteromedial basal mergers giving 8 named units)
  S5  TMA, "The Nasal Cavity" (divisions, functions, conchae and
      meatuses, openings, vasculature, innervation)
  S6  TMA, "The Larynx" (position C3-C6, cavity divisions,
      vasculature, innervation)
  S7  TMA, "The Pharynx" (extent, three parts and their borders,
      circular and longitudinal muscles, innervation, vasculature)
  S8  ETSU (Currie), "The Lung Volumes and Capacities Page"
      (spirometric table: TV 500, IRV 3000, ERV 1300, RV 1200,
      FRC 2500, VC 5000, TLC 6000 mL; anatomical dead space ~150 mL;
      respiratory rate 12-15/min; minute volume 6000-7500 mL/min;
      alveolar ventilation 5250 mL/min at rest; FEV1 ~80% of VC)
  S9  LibreTexts BIO 50 (Zingg), "Functional Anatomy of the
      Respiratory Tract" (conducting vs respiratory zone membership,
      tracheal rings 16-20, bronchiole <1 mm, alveolar ducts/sacs)
  S10 OpenStax, Anatomy and Physiology 2e, section 22.2 "The Lungs"
      (segment definition corroboration, pleura corroboration)
  S11 TMA, "Laryngeal Cartilages" (nine cartilages: unpaired
      epiglottis/thyroid/cricoid; paired arytenoid/corniculate/
      cuneiform)

Record types and fields:
  pathway (the airway in order): pathway_order, zone, extent,
    structure, function. Tiers: A = all sourced; B = extent and
    function sourced, structure flagged; C = extent or function
    flagged.
  organ (lungs, larynx): type-specific fields (below).
    Lung tiers: core = lobes, fissures; soft = root_hilum,
    relations, blood_supply, nerve_supply.
    Larynx tiers: core = position, functions, cartilages; soft =
    cavity_divisions, innervation, blood_supply.
  region (nasal cavity, pharynx): nasal cavity core = divisions,
    functions; soft = conchae_meatuses, openings, blood_supply,
    innervation. Pharynx core = extent, parts; soft = muscles,
    innervation, blood_supply.
  segment (the 18 clinical bronchopulmonary segments of S4):
    lobe, definition, surgical_note. Core = lobe, definition;
    soft = surgical_note.
  membrane (pleura): layers, parietal_parts, cavity_and_fluid,
    recesses, innervation_supply. Core = layers, cavity_and_fluid;
    soft = the rest.
  values (respiratory mechanics): a `values` map; every value
    sourced (S8) or the record is not written. Tier A by
    construction; the checker re-validates.

Geometry linkage: clinical records link inventory records by exact
record name. Records for structures the release does not contain
(nasal cavity as a space, the pharyngeal parts, the lobar bronchi,
the bronchioles and the whole respiratory zone, the pleura) link
nothing and carry the absence in their verify list instead —
checker-gated, as in Milestone 9.
"""

import json
import os

PROJECT = "/home/hatch/workspace/anatomica-project"
INV_PATH = os.path.join(PROJECT, "data/respiratory/respiratory-inventory.json")
OUT_PATH = os.path.join(PROJECT, "data/respiratory/respiratory.json")

inv = json.load(open(INV_PATH, encoding="utf-8"))
inv_by_name = {}
for r in inv["records"]:
    inv_by_name.setdefault(r["name"], []).append(r["record_id"])

SOURCES = {
    "S1": "TeachMeAnatomy, 'The Lungs' (teachmeanatomy.info)",
    "S2": "TeachMeAnatomy, 'The Tracheobronchial Tree' (teachmeanatomy.info)",
    "S3": "TeachMeAnatomy, 'The Pleurae' (teachmeanatomy.info)",
    "S4": "Wikipedia, 'Bronchopulmonary segment' (Jackson & Huber nomenclature)",
    "S5": "TeachMeAnatomy, 'The Nasal Cavity' (teachmeanatomy.info)",
    "S6": "TeachMeAnatomy, 'The Larynx' (teachmeanatomy.info)",
    "S7": "TeachMeAnatomy, 'The Pharynx' (teachmeanatomy.info)",
    "S8": "ETSU (Currie), 'The Lung Volumes and Capacities Page' (faculty.etsu.edu)",
    "S9": "LibreTexts BIO 50 (Zingg), 'Functional Anatomy of the Respiratory Tract'",
    "S10": "OpenStax, Anatomy and Physiology 2e, section 22.2 'The Lungs'",
    "S11": "TeachMeAnatomy, 'Laryngeal Cartilages' (teachmeanatomy.info)",
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


def pathway(rec_id, name, order, zone, names, extent=None, structure=None,
            function=None, sources=None, verify=None, note=None):
    rec = base(rec_id, name, "pathway", "Airway pathway", names,
               verify, note)
    rec.update({"pathway_order": order, "zone": zone,
                "extent": extent, "structure": structure,
                "function": function})
    rec["sources"] = dict(sources or {})
    finish(rec, ["extent", "structure", "function"],
           core=["extent", "function"], soft=["structure"],
           rec_id=rec_id)


def organ(rec_id, name, group, names, fields, sources, core, soft,
          verify=None, note=None, extra=None):
    rec = base(rec_id, name, "organ", group, names, verify, note)
    rec.update(fields)
    if extra:
        rec.update(extra)
    rec["sources"] = dict(sources or {})
    finish(rec, list(fields), core=core, soft=soft, rec_id=rec_id)


# ------------------------------------------------------------------
# Airway pathway (in order, nares to alveoli)
# ------------------------------------------------------------------
pathway("resp.nasal-cavity", "Nasal cavity", 1, "conducting",
        ["nose", "external nose", "internal nose", "nasal septum",
         "septal nasal cartilage", "left lateral nasal cartilage",
         "right lateral nasal cartilage", "left major alar cartilage",
         "right major alar cartilage"],
        extent="The most superior part of the respiratory tract; "
               "extends from the vestibule of the nose to the "
               "nasopharynx",
        structure="Three divisions: vestibule (around the anterior "
                  "external opening), respiratory region (ciliated "
                  "pseudostratified epithelium with mucus-secreting "
                  "goblet cells) and olfactory region at the apex, "
                  "lined by olfactory cells with olfactory receptors",
        function="Warms and humidifies inspired air; removes and "
                 "traps pathogens and particulate matter; sense of "
                 "smell; drains and clears the paranasal sinuses "
                 "and lacrimal ducts",
        sources={"extent": ["S5"], "structure": ["S5"],
                 "function": ["S5"]},
        note="the nasal cavity as a space has no concept in the "
             "release; geometry links are the nose organ record and "
             "its named parts and cartilages")

pathway("resp.nasopharynx", "Nasopharynx", 2, "conducting", [],
        extent="Between the base of the skull and the soft palate; "
               "continuous with the nasal cavity",
        structure="Lined with respiratory epithelium (ciliated "
                  "pseudostratified columnar epithelium with goblet "
                  "cells); the posterosuperior wall contains the "
                  "adenoid (pharyngeal) tonsils, which enlarge "
                  "between 3-8 years of age and then regress",
        function="Respiratory part of the pharynx: conditions "
                 "inspired air and propagates it towards the larynx",
        sources={"extent": ["S7"], "structure": ["S7"],
                 "function": ["S7"]},
        verify=[ABSENCE])

pathway("resp.oropharynx", "Oropharynx", 3, "conducting", [],
        extent="The middle part of the pharynx, between the soft "
               "palate and the superior border of the epiglottis",
        structure="Contains the posterior one-third of the tongue, "
                  "the lingual tonsils, the palatine tonsils (in the "
                  "tonsillar fossa) and the superior constrictor "
                  "muscle; with the palatine, adenoid and lingual "
                  "tonsils it forms part of Waldeyer's ring",
        function="A passageway shared by air and food; involved in "
                 "the voluntary and involuntary phases of swallowing",
        sources={"extent": ["S7"], "structure": ["S7"],
                 "function": ["S7"]},
        verify=[ABSENCE])

pathway("resp.laryngopharynx", "Laryngopharynx", 4, "conducting", [],
        extent="The most distal part of the pharynx, between the "
               "superior border of the epiglottis and the inferior "
               "border of the cricoid cartilage (C6); continuous "
               "inferiorly with the oesophagus",
        structure="Lies posterior to the larynx and communicates "
                  "with it via the laryngeal inlet, lateral to which "
                  "lie the piriform fossae; contains the middle and "
                  "inferior pharyngeal constrictors",
        function="Directs air into the larynx and swallowed "
                 "material into the oesophagus",
        sources={"extent": ["S7"], "structure": ["S7"],
                 "function": ["S7", "S9"]},
        verify=[ABSENCE])

organ("resp.larynx", "Larynx", "Airway pathway",
      ["thyroid cartilage", "cricoid cartilage",
       "left arytenoid cartilage", "right arytenoid cartilage",
       "left corniculate cartilage", "right corniculate cartilage",
       "left cuneiform cartilage", "right cuneiform cartilage",
       "epiglottis", "hyo-epiglottic ligament",
       "thyro-epiglottic ligament", "median cricothyroid ligament",
       "left vocal ligament", "right vocal ligament",
       "left conus elasticus", "right conus elasticus",
       "left thyrohyoid membrane", "right thyrohyoid membrane",
       "median thyrohyoid ligament",
       "left lateral thyrohyoid ligament",
       "right lateral thyrohyoid ligament"],
      fields={
          "position": "Anterior compartment of the neck, suspended "
                      "from the hyoid bone, spanning C3 to C6; "
                      "continuous inferiorly with the trachea and "
                      "opening superiorly into the laryngeal part of "
                      "the pharynx; oesophagus lies posteriorly",
          "functions": "Phonation, the cough reflex, and protection "
                       "of the lower respiratory tract",
          "cartilages": "Nine cartilages forming the laryngeal "
                        "skeleton: three unpaired (epiglottis, "
                        "thyroid, cricoid) and three paired "
                        "(arytenoid, corniculate, cuneiform)",
          "cavity_divisions": "Supraglottis (inferior surface of "
                              "epiglottis to the vestibular folds), "
                              "glottis (the vocal cords and 1 cm "
                              "below; the opening between the cords "
                              "is the rima glottidis) and subglottis "
                              "(to the inferior border of the cricoid "
                              "cartilage); lined by pseudostratified "
                              "ciliated columnar epithelium except "
                              "the true vocal cords (stratified "
                              "squamous)",
          "innervation": "Via the vagus nerve: the recurrent "
                         "laryngeal nerve gives sensory supply to "
                         "the infraglottis and motor supply to all "
                         "internal laryngeal muscles except the "
                         "cricothyroid; the superior laryngeal "
                         "nerve's internal branch is sensory to the "
                         "supraglottis and its external branch is "
                         "motor to the cricothyroid",
          "blood_supply": "Superior laryngeal artery (branch of the "
                          "superior thyroid artery, from the "
                          "external carotid) and inferior laryngeal "
                          "artery (branch of the inferior thyroid "
                          "artery, from the thyrocervical trunk); "
                          "the superior laryngeal vein drains via "
                          "the superior thyroid vein to the internal "
                          "jugular vein, the inferior via the "
                          "inferior thyroid vein to the left "
                          "brachiocephalic vein",
      },
      sources={"position": ["S6"], "functions": ["S6"],
               "cartilages": ["S11"],
               "cavity_divisions": ["S6"], "innervation": ["S6"],
               "blood_supply": ["S6"]},
      core=["position", "functions", "cartilages"],
      soft=["cavity_divisions", "innervation", "blood_supply"],
      extra={"pathway_order": 5, "zone": "conducting"},
      note="the larynx as an organ has no concept in the release; "
           "geometry links are its nine cartilages and its ligament/"
           "membrane records as released")

pathway("resp.trachea", "Trachea", 6, "conducting", ["trachea"],
        extent="Arises at the lower border of the cricoid cartilage "
               "in the neck as a continuation of the larynx; travels "
               "inferiorly into the superior mediastinum, anterior "
               "to the oesophagus, and bifurcates at the level of "
               "the sternal angle",
        structure="Held open by C-shaped cartilage rings (16-20 "
                  "rings of hyaline cartilage) whose free ends are "
                  "supported by the trachealis muscle; lined by "
                  "ciliated pseudostratified columnar epithelium "
                  "with goblet cells, forming the mucociliary "
                  "escalator; at the bifurcation the carina, a ridge "
                  "of cartilage between the bronchial openings, is "
                  "the most sensitive area for triggering the cough "
                  "reflex",
        function="Conducts air between the larynx and the main "
                 "bronchi; the mucociliary escalator traps inhaled "
                 "particles and pathogens and moves them up out of "
                 "the airways",
        sources={"extent": ["S2"], "structure": ["S2", "S9"],
                 "function": ["S2"]})

pathway("resp.main-bronchi", "Main bronchi", 7, "conducting",
        ["left main bronchus", "right main bronchus proper"],
        extent="From the tracheal bifurcation at the sternal angle, "
               "each bronchus enters the root of its lung through "
               "the hilum",
        structure="The right main bronchus is wider, shorter and "
                  "more vertical than the left (hence a higher "
                  "incidence of foreign-body inhalation); the left "
                  "main bronchus passes inferior to the arch of the "
                  "aorta and anterior to the thoracic aorta and "
                  "oesophagus; in the main bronchi, cartilage rings "
                  "completely encircle the lumen",
        function="Deliver air from the trachea to each lung; with "
                 "branches of the pulmonary artery and veins, the "
                 "main bronchi make up the roots of the lungs",
        sources={"extent": ["S2"], "structure": ["S2"],
                 "function": ["S2"]})

pathway("resp.lobar-bronchi", "Lobar bronchi", 8, "conducting", [],
        extent="Within the lungs, branching from the main bronchi "
               "and dividing into the segmental bronchi",
        structure="Secondary bronchi; their cartilage is found "
                  "only in crescent shapes (unlike the complete "
                  "rings of the main bronchi)",
        function="One lobar (secondary) bronchus supplies each "
                 "lobe of the lung: three on the right, two on "
                 "the left",
        sources={"extent": ["S2"], "structure": ["S2"],
                 "function": ["S2"]},
        verify=[ABSENCE],
        note="the release contains no lobar bronchus concept: its "
             "bronchial tree jumps from the main bronchi to the "
             "segmental bronchial trees")

pathway("resp.segmental-bronchi", "Segmental bronchi", 9,
        "conducting",
        ["left apical segmental bronchial tree",
         "right apical segmental bronchial tree",
         "left posterior segmental bronchial tree",
         "right posterior segmental bronchial tree",
         "left anterior segmental bronchial tree",
         "right anterior segmental bronchial tree",
         "lateral segmental bronchial tree",
         "medial segmental bronchial tree",
         "left superior segmental bronchial tree",
         "right superior segmental bronchial tree",
         "superior lingular bronchial tree",
         "inferior lingular bronchial tree",
         "basal segmental bronchial tree",
         "left medial basal segmental bronchial tree",
         "right medial basal segmental bronchial tree",
         "left anterior basal segmental bronchial tree",
         "right anterior basal segmental bronchial tree",
         "left lateral basal segmental bronchial tree",
         "right lateral basal segmental bronchial tree",
         "left posterior basal segmental bronchial tree",
         "right posterior basal segmental bronchial tree"],
        extent="Branch from the lobar bronchi within each lobe",
        structure="Tertiary bronchi; cartilage only in crescent "
                  "shapes",
        function="Each segmental bronchus provides air to a "
                 "bronchopulmonary segment — the functional units "
                 "of the lungs",
        sources={"extent": ["S2"], "structure": ["S2"],
                 "function": ["S2", "S1"]},
        note="geometry links are the release's 21 segmental "
             "bronchial tree records (16 lateralised instances and "
             "the un-sided lateral, medial, basal and two lingular "
             "trees)")

pathway("resp.bronchioles", "Bronchioles", 10, "conducting", [],
        extent="The segmental bronchi branch repeatedly into "
               "numerous smaller bronchioles, ending as terminal "
               "bronchioles",
        structure="The smallest airways: no cartilage and no "
                  "mucus-secreting goblet cells; club cells produce "
                  "a surfactant lipoprotein that stops the small "
                  "airway walls sticking together during "
                  "expiration; bronchioles are less than 1 mm wide",
        function="Conducting bronchioles transport air but are "
                 "not involved in gas exchange; the terminal "
                 "bronchioles are the last part of the conducting "
                 "zone",
        sources={"extent": ["S2"], "structure": ["S2", "S9"],
                 "function": ["S2", "S9"]},
        verify=[ABSENCE])

pathway("resp.respiratory-bronchioles", "Respiratory bronchioles",
        11, "respiratory", [],
        extent="Branch from the terminal bronchioles; the first "
               "structures of the respiratory zone",
        structure="Distinguishable by thin-walled alveoli "
                  "extending as outpocketings from their lumens; "
                  "simple cuboidal epithelium, thinner than the "
                  "simple columnar epithelium of the terminal "
                  "bronchioles",
        function="The first airways at which gas exchange occurs, "
                 "through their alveolar outpocketings",
        sources={"extent": ["S2", "S9"], "structure": ["S2", "S9"],
                 "function": ["S2", "S9"]},
        verify=[ABSENCE])

pathway("resp.alveolar-ducts-and-sacs", "Alveolar ducts and sacs",
        12, "respiratory", [],
        extent="Respiratory bronchioles branch into alveolar "
               "ducts, which open into clusters of alveolar sacs",
        structure="Ducts opening into clustered sacs of alveoli",
        function="Conduct air into the alveolar sacs, where "
                 "oxygen and carbon dioxide are exchanged",
        sources={"extent": ["S9"], "structure": ["S9"],
                 "function": ["S9"]},
        verify=[ABSENCE])

pathway("resp.alveoli", "Alveoli", 13, "respiratory", [],
        extent="At the ends of the respiratory zone throughout "
               "the lung parenchyma, extending from the lumens of "
               "the respiratory bronchioles and forming the "
               "alveolar sacs",
        structure="Tiny air-filled pockets with thin walls of "
                  "simple squamous epithelium; altogether around "
                  "300 million alveoli in the adult lungs",
        function="The sites of gaseous exchange in the lungs, "
                 "providing a large surface area for exchange",
        sources={"extent": ["S2", "S9"], "structure": ["S2"],
                 "function": ["S2"]},
        verify=[ABSENCE])

# ------------------------------------------------------------------
# Lungs
# ------------------------------------------------------------------
LUNG_ROOT = ("Each lung root contains a bronchus, a pulmonary "
             "artery, two pulmonary veins, bronchial vessels, the "
             "pulmonary plexus of nerves and lymphatic vessels; all "
             "enter or leave the lung via the hilum, a wedge-shaped "
             "area on the mediastinal surface")
LUNG_NERVES = ("Derived from the pulmonary plexuses: "
               "parasympathetic fibres (vagus) stimulate secretion "
               "from the bronchial glands, contraction of bronchial "
               "smooth muscle and vasodilation of the pulmonary "
               "vessels; sympathetic fibres (sympathetic trunks) "
               "stimulate relaxation of bronchial smooth muscle and "
               "vasoconstriction of the pulmonary vessels; visceral "
               "afferent fibres conduct pain impulses to the sensory "
               "ganglion of the vagus nerve")

organ("resp.right-lung", "Right lung", "Lungs",
      ["right lung", "upper lobe of right lung", "middle lobe of lung",
       "lower lobe of right lung"],
      fields={
          "lobes": "Three lobes: superior, middle and inferior",
          "fissures": "Two fissures: the oblique fissure, running "
                      "from the inferior border superoposteriorly "
                      "to the posterior border, separating the "
                      "inferior lobe from the middle and superior "
                      "lobes; and the horizontal fissure, running "
                      "horizontally from the sternum at the level "
                      "of the 4th rib to meet the oblique fissure",
          "root_hilum": LUNG_ROOT,
          "relations": "Cone shaped, with apex projecting above "
                       "the 1st rib into the floor of the neck and "
                       "base sitting on the diaphragm (the "
                       "diaphragmatic concavity is deeper on the "
                       "right, due to the higher right dome over "
                       "the liver); medial surface related to the "
                       "oesophagus, heart, inferior vena cava, "
                       "superior vena cava and azygos vein",
          "blood_supply": "Deoxygenated blood by the pulmonary "
                          "arteries; oxygenated blood leaves via "
                          "the pulmonary veins (two per lung); an "
                          "extra nutritive supply to the bronchi, "
                          "lung roots, visceral pleura and lung "
                          "tissue comes from the bronchial arteries "
                          "(from the descending aorta); the right "
                          "bronchial vein drains into the azygos "
                          "vein",
          "nerve_supply": LUNG_NERVES,
      },
      sources={"lobes": ["S1"], "fissures": ["S1"],
               "root_hilum": ["S1"], "relations": ["S1"],
               "blood_supply": ["S1"], "nerve_supply": ["S1"]},
      core=["lobes", "fissures"],
      soft=["root_hilum", "relations", "blood_supply", "nerve_supply"])

organ("resp.left-lung", "Left lung", "Lungs",
      ["left lung", "upper lobe of left lung",
       "lower lobe of left lung"],
      fields={
          "lobes": "Two lobes: superior and inferior",
          "fissures": "One fissure: the oblique fissure, similar "
                      "to that of the right lung, separating the "
                      "superior and inferior lobes",
          "root_hilum": LUNG_ROOT,
          "relations": "Slightly smaller than the right lung "
                       "because of the heart; its anterior border "
                       "is marked by the cardiac notch, a deep "
                       "notch created by the apex of the heart; "
                       "medial surface related to the heart, arch "
                       "of aorta, thoracic aorta and oesophagus; "
                       "base sits on the diaphragm",
          "blood_supply": "Deoxygenated blood by the pulmonary "
                          "arteries; oxygenated blood leaves via "
                          "the pulmonary veins (two per lung); "
                          "nutritive supply from the bronchial "
                          "arteries (from the descending aorta); "
                          "the left bronchial vein drains into the "
                          "accessory hemiazygos vein",
          "nerve_supply": LUNG_NERVES,
      },
      sources={"lobes": ["S1"], "fissures": ["S1"],
               "root_hilum": ["S1"], "relations": ["S1"],
               "blood_supply": ["S1"], "nerve_supply": ["S1"]},
      core=["lobes", "fissures"],
      soft=["root_hilum", "relations", "blood_supply", "nerve_supply"])

# ------------------------------------------------------------------
# Upper airway summary records
# ------------------------------------------------------------------
rec = base("resp.nasal-cavity-organ", "Nasal cavity (structure)",
           "region", "Upper airway",
           ["nose", "external nose", "internal nose", "nasal septum",
            "septal nasal cartilage", "left lateral nasal cartilage",
            "right lateral nasal cartilage",
            "left major alar cartilage", "right major alar cartilage"],
           note="companion to the pathway record of the same name: "
                "the cavity's own sourced structure; the release "
                "carries no nasal cavity concept")
rec.update({
    "divisions": "Vestibule, respiratory region and olfactory "
                 "region",
    "functions": "Warms and humidifies inspired air; removes and "
                 "traps pathogens and particulate matter; sense of "
                 "smell; drains and clears the paranasal sinuses "
                 "and lacrimal ducts",
    "conchae_meatuses": "Three conchae (inferior, middle, "
                        "superior) project from the lateral walls, "
                        "creating four pathways: the inferior "
                        "meatus (below the inferior concha), middle "
                        "meatus (between inferior and middle "
                        "conchae), superior meatus (between middle "
                        "and superior conchae) and the "
                        "spheno-ethmoidal recess (above and behind "
                        "the superior concha); the conchae increase "
                        "surface area and make airflow slow and "
                        "turbulent, so air spends longer in contact "
                        "with the cavity walls",
    "openings": "Frontal, maxillary and anterior ethmoidal "
                "sinuses open into the middle meatus at the "
                "semilunar hiatus; the middle ethmoidal sinuses "
                "empty onto the ethmoidal bulla; the posterior "
                "ethmoidal sinuses open at the level of the "
                "superior meatus; the sphenoid sinus drains onto "
                "the posterior roof; the nasolacrimal duct opens "
                "into the inferior meatus; the auditory (Eustachian) "
                "tube opens into the nasopharynx at the level of "
                "the inferior meatus",
    "blood_supply": "From both carotids: internal carotid via "
                    "the anterior and posterior ethmoidal arteries "
                    "(branches of the ophthalmic artery, descending "
                    "through the cribriform plate); external "
                    "carotid via the sphenopalatine, greater "
                    "palatine, superior labial and lateral nasal "
                    "arteries; the branches anastomose, "
                    "particularly in the anterior nose (Kiesselbach "
                    "area); veins drain to the pterygoid plexus, "
                    "facial vein or cavernous sinus",
    "innervation": "Special sensory (smell) by the olfactory "
                   "nerves, whose fibres pass through the "
                   "cribriform plate from the olfactory bulb; "
                   "general sensory supply to septum and lateral "
                   "walls by the nasopalatine nerve (maxillary) and "
                   "nasociliary nerve (ophthalmic); the skin of "
                   "the external nose by the trigeminal nerve",
})
rec["sources"] = {"divisions": ["S5"], "functions": ["S5"],
                  "conchae_meatuses": ["S5"], "openings": ["S5"],
                  "blood_supply": ["S5"], "innervation": ["S5"]}
finish(rec, ["divisions", "functions", "conchae_meatuses",
             "openings", "blood_supply", "innervation"],
       core=["divisions", "functions"],
       soft=["conchae_meatuses", "openings", "blood_supply",
             "innervation"],
       rec_id="resp.nasal-cavity-organ")

rec = base("resp.pharynx", "Pharynx", "region", "Upper airway", [],
           verify=[ABSENCE],
           note="the pharynx has no concept in the release (only "
                "its subdivision classes, its raphe and its "
                "muscles); its muscle records live in the muscular "
                "module (superior/middle/inferior constrictors, "
                "stylopharyngeus, salpingopharyngeus, "
                "palatopharyngeus)")
rec.update({
    "extent": "A muscular tube connecting the oral and nasal "
              "cavities to the larynx and oesophagus; it begins at "
              "the base of the skull and ends at the inferior "
              "border of the cricoid cartilage (C6)",
    "parts": "Three parts, superior to inferior: nasopharynx "
             "(base of skull to soft palate), oropharynx (soft "
             "palate to superior border of the epiglottis) and "
             "laryngopharynx (superior border of the epiglottis to "
             "the inferior border of the cricoid cartilage, C6)",
    "muscles": "Two groups: circular muscles — the superior, "
               "middle and inferior pharyngeal constrictors, "
               "arranged like stacked glasses, contracting "
               "sequentially from superior to inferior to propel "
               "the bolus into the oesophagus (the inferior "
               "constrictor has thyropharyngeal and cricopharyngeal "
               "parts); longitudinal muscles — stylopharyngeus, "
               "palatopharyngeus and salpingopharyngeus, which "
               "shorten and widen the pharynx and elevate the "
               "larynx during swallowing",
    "innervation": "Motor and sensory supply mainly via the "
                   "pharyngeal plexus (pharyngeal branches of the "
                   "glossopharyngeal and vagus nerves, branches of "
                   "the external laryngeal nerve and sympathetic "
                   "fibres from the superior cervical ganglion); "
                   "all pharyngeal muscles are supplied by the "
                   "vagus except the stylopharyngeus "
                   "(glossopharyngeal); sensory supply is mainly "
                   "glossopharyngeal, with the maxillary nerve to "
                   "the anterior/superior nasopharynx",
    "blood_supply": "Arterial supply from branches of the "
                    "external carotid artery: the ascending "
                    "pharyngeal artery and branches of the facial, "
                    "lingual and maxillary arteries; venous "
                    "drainage by the pharyngeal venous plexus into "
                    "the internal jugular vein",
})
rec["sources"] = {"extent": ["S7"], "parts": ["S7"],
                  "muscles": ["S7"], "innervation": ["S7"],
                  "blood_supply": ["S7"]}
finish(rec, ["extent", "parts", "muscles", "innervation",
             "blood_supply"],
       core=["extent", "parts"],
       soft=["muscles", "innervation", "blood_supply"],
       rec_id="resp.pharynx")

# ------------------------------------------------------------------
# Bronchopulmonary segments (S4: Jackson & Huber list)
# ------------------------------------------------------------------
SEG_DEF = ("A portion of lung supplied by a specific segmental "
           "bronchus and its vessels; the arteries branch from the "
           "pulmonary and bronchial arteries and run together "
           "through the centre of the segment, while veins and "
           "lymphatic vessels drain along the edges of the segment")
SEG_SURG = ("Separated from the other segments by layers of "
            "connective tissue into a discrete anatomical and "
            "functional unit, so a bronchopulmonary segment can "
            "be surgically removed without affecting the function "
            "of the others")


def segment(rec_id, name, lobe, names, merger=None):
    rec = base(rec_id, name, "segment", "Bronchopulmonary segments",
               names)
    definition = SEG_DEF
    if merger:
        definition = merger + ". " + definition
    rec.update({"lobe": lobe, "definition": definition,
                "surgical_note": SEG_SURG})
    rec["sources"] = {"lobe": ["S4"], "definition": ["S4"],
                      "surgical_note": ["S4"]}
    finish(rec, ["lobe", "definition", "surgical_note"],
           core=["lobe", "definition"], soft=["surgical_note"],
           rec_id=rec_id)


RUL = "Superior (upper) lobe of the right lung"
RML = "Middle lobe of the right lung"
RLL = "Inferior (lower) lobe of the right lung"
LUL = "Superior (upper) lobe of the left lung"
LLL = "Inferior (lower) lobe of the left lung"

segment("segment.right-apical", "Apical segment (S1)", RUL,
        ["right apical bronchopulmonary segment",
         "right apical segmental bronchial tree"])
segment("segment.right-posterior", "Posterior segment (S2)", RUL,
        ["right posterior bronchopulmonary segment",
         "right posterior segmental bronchial tree"])
segment("segment.right-anterior", "Anterior segment (S3)", RUL,
        ["right anterior bronchopulmonary segment",
         "right anterior segmental bronchial tree"])
segment("segment.right-lateral", "Lateral segment (S4)", RML,
        ["lateral bronchopulmonary segment",
         "lateral segmental bronchial tree"])
segment("segment.right-medial", "Medial segment (S5)", RML,
        ["medial bronchopulmonary segment",
         "medial segmental bronchial tree"])
segment("segment.right-superior", "Superior segment (S6)", RLL,
        ["right superior bronchopulmonary segment",
         "right superior segmental bronchial tree"])
segment("segment.right-medial-basal", "Medial basal segment (S7)",
        RLL, ["right medial basal bronchopulmonary segment",
              "right medial basal segmental bronchial tree"])
segment("segment.right-anterior-basal", "Anterior basal segment (S8)",
        RLL, ["right anterior basal bronchopulmonary segment",
              "right anterior basal segmental bronchial tree"])
segment("segment.right-lateral-basal", "Lateral basal segment (S9)",
        RLL, ["right lateral basal bronchopulmonary segment",
              "right lateral basal segmental bronchial tree"])
segment("segment.right-posterior-basal",
        "Posterior basal segment (S10)", RLL,
        ["right posterior basal bronchopulmonary segment",
         "right posterior basal segmental bronchial tree"])
segment("segment.left-apicoposterior",
        "Apico-posterior segment (S1+2)", LUL,
        ["apicoposterior bronchopulmonary segment",
         "left apical bronchopulmonary segment",
         "left posterior bronchopulmonary segment",
         "left apical segmental bronchial tree",
         "left posterior segmental bronchial tree"],
        merger="Merger of the apical and posterior segments")
segment("segment.left-anterior", "Anterior segment (S3)", LUL,
        ["left anterior bronchopulmonary segment",
         "left anterior segmental bronchial tree"])
segment("segment.left-superior-lingular",
        "Superior lingular segment (S4)",
        "Lingula of the superior (upper) lobe of the left lung",
        ["superior lingular bronchopulmonary segment",
         "superior lingular bronchial tree"])
segment("segment.left-inferior-lingular",
        "Inferior lingular segment (S5)",
        "Lingula of the superior (upper) lobe of the left lung",
        ["inferior lingular bronchopulmonary segment",
         "inferior lingular bronchial tree"])
segment("segment.left-superior", "Superior segment (S6)", LLL,
        ["left superior bronchopulmonary segment",
         "left superior segmental bronchial tree"])
segment("segment.left-anteromedial-basal",
        "Anteromedial basal segment (S7+8)", LLL,
        ["left medial basal bronchopulmonary segment",
         "left anterior basal bronchopulmonary segment",
         "left medial basal segmental bronchial tree",
         "left anterior basal segmental bronchial tree"],
        merger="Merger of the anterior basal and medial basal "
               "segments")
segment("segment.left-lateral-basal", "Lateral basal segment (S9)",
        LLL, ["left lateral basal bronchopulmonary segment",
              "left lateral basal segmental bronchial tree"])
segment("segment.left-posterior-basal",
        "Posterior basal segment (S10)", LLL,
        ["left posterior basal bronchopulmonary segment",
         "left posterior basal segmental bronchial tree"])

# ------------------------------------------------------------------
# Pleura
# ------------------------------------------------------------------
rec = base("resp.pleura", "Pleurae and pleural cavities", "membrane",
           "Pleura", [],
           verify=[ABSENCE],
           note="no pleura concept of any kind exists in the "
                "release; the only pleura-adjacent concepts are "
                "the two pulmopleural compartments, censused in "
                "the inventory as compartment concepts, not "
                "records")
rec.update({
    "layers": "Two pleurae, one associated with each lung; each "
              "is a serous membrane (a layer of simple squamous "
              "cells — mesothelium — on connective tissue) divided "
              "into the visceral pleura, which covers the lungs, "
              "and the parietal pleura, which covers the internal "
              "surface of the thoracic cavity; the two are "
              "continuous with each other at the hilum of the lung",
    "parietal_parts": "The parietal pleura is subdivided by the "
                      "surface it covers: mediastinal pleura "
                      "(lateral aspect of the mediastinum), "
                      "cervical pleura (the extension into the "
                      "neck), costal pleura (inner aspect of the "
                      "ribs, costal cartilages and intercostal "
                      "muscles) and diaphragmatic pleura (superior "
                      "surface of the diaphragm)",
    "cavity_and_fluid": "The pleural cavity is a potential space "
                        "between the visceral and parietal pleura "
                        "containing a small volume of serous fluid; "
                        "the fluid lubricates the pleural surfaces "
                        "so they slide over each other, and its "
                        "surface tension pulls the two layers "
                        "together, ensuring the lung expands when "
                        "the thorax expands",
    "recesses": "Two recesses in each pleural cavity where "
                "opposing parietal surfaces touch and fluid can "
                "collect: the costodiaphragmatic recess (between "
                "the costal and diaphragmatic pleurae) and the "
                "costomediastinal recess (between the costal and "
                "mediastinal pleurae, behind the sternum)",
    "innervation_supply": "The parietal pleura is sensitive to "
                          "pressure, pain and temperature, "
                          "producing well-localised pain; it is "
                          "innervated by the phrenic and "
                          "intercostal nerves and supplied by the "
                          "intercostal arteries. The visceral "
                          "pleura is not sensitive to pain, "
                          "temperature or touch (its sensory fibres "
                          "detect stretch only), receives autonomic "
                          "innervation from the pulmonary plexus, "
                          "and is supplied by the bronchial "
                          "arteries",
})
rec["sources"] = {"layers": ["S3"], "parietal_parts": ["S3"],
                  "cavity_and_fluid": ["S3"], "recesses": ["S3"],
                  "innervation_supply": ["S3"]}
finish(rec, ["layers", "parietal_parts", "cavity_and_fluid",
             "recesses", "innervation_supply"],
       core=["layers", "cavity_and_fluid"],
       soft=["parietal_parts", "recesses", "innervation_supply"],
       rec_id="resp.pleura")

# ------------------------------------------------------------------
# Respiratory mechanics values (S8 only; approximates per the source)
# ------------------------------------------------------------------
rec = base("resp.mechanics", "Respiratory volumes and capacities",
           "values", "Respiratory mechanics", [],
           verify=["no BP3D concept: spirometric values are "
                   "measurements, not anatomical structures; no "
                   "geometry is linked by design"],
           note="all values are the consulted source's stated "
                "approximates, which the source itself notes will "
                "vary somewhat between sources; resting adult "
                "values. Related structure record: the diaphragm "
                "(muscular module, muscle.diaphragm), the "
                "dome-shaped muscle at the base of the lungs "
                "(S10)")
rec["values"] = {
    "tidal_volume_ml": 500,
    "inspiratory_reserve_volume_ml": 3000,
    "expiratory_reserve_volume_ml": 1300,
    "residual_volume_ml": 1200,
    "functional_residual_capacity_ml": 2500,
    "vital_capacity_ml": 5000,
    "total_lung_capacity_ml": 6000,
    "minimal_volume_ml": 500,
    "anatomical_dead_space_ml": 150,
    "respiratory_rate_breaths_per_min": "12-15",
    "minute_respiratory_volume_ml_per_min": "6000-7500",
    "alveolar_ventilation_ml_per_min": 5250,
    "fev1_percent_of_vital_capacity": "about 80",
}
rec["value_definitions"] = {
    "tidal_volume_ml": "volume of air taken into the lungs in a "
                       "resting breath",
    "inspiratory_reserve_volume_ml": "reserve that can be inspired "
                                     "beyond a normal inspiration",
    "expiratory_reserve_volume_ml": "difference between the lung "
                                    "volume at the end of normal "
                                    "and of maximal expiration",
    "residual_volume_ml": "air left in the lungs at the end of "
                          "maximal expiration, which cannot be "
                          "voluntarily exhaled",
    "functional_residual_capacity_ml": "air left at the end of "
                                       "normal resting expiration "
                                       "(ERV + RV)",
    "vital_capacity_ml": "the total usable volume of the lungs "
                         "under voluntary control",
    "total_lung_capacity_ml": "residual volume + vital capacity",
    "minimal_volume_ml": "volume below which the lungs will "
                         "collapse",
    "anatomical_dead_space_ml": "volume of the air-conducting "
                                "pathways in which no gas exchange "
                                "occurs (approximately 150 mL in the "
                                "average adult)",
    "respiratory_rate_breaths_per_min": "resting respiratory "
                                        "frequency",
    "minute_respiratory_volume_ml_per_min": "air exchanged in one "
                                            "minute (rate x tidal "
                                            "volume); the source "
                                            "notes the average is "
                                            "closer to 6000",
    "alveolar_ventilation_ml_per_min": "(tidal volume - anatomical "
                                       "dead space) x rate, as "
                                       "computed by the source at "
                                       "rest",
    "fev1_percent_of_vital_capacity": "volume expired in the "
                                      "first second of a vital "
                                      "capacity determination "
                                      "(FEV1), as a percentage of "
                                      "VC",
}
rec["sources"] = {"values": ["S8"]}
rec["sourcing_tier"] = "A"
records.append(rec)

# ------------------------------------------------------------------
doc = {
    "meta": {
        "title": "ANATOMICA respiratory system clinical records — "
                 "Milestone 10",
        "generated_by": "tools/build_resp_records.py",
        "sourcing_rule": "every non-null clinical field cites a "
                         "source consulted during the build session "
                         "in the record's sources map; every null "
                         "field carries an explicit verify entry; "
                         "TA names were not given by the consulted "
                         "sources and are null + flagged throughout",
        "sources": SOURCES,
        "record_count": len(records),
        "tiers": dict(sorted(
            __import__("collections").Counter(
                r["sourcing_tier"] for r in records).items())),
        "groups": dict(sorted(
            __import__("collections").Counter(
                r["group"] for r in records).items())),
        "link_failures": [list(x) for x in link_failures],
    },
    "records": records,
}
with open(OUT_PATH, "w") as f:
    json.dump(doc, f, indent=1, sort_keys=False)
print(f"records: {len(records)}")
print("tiers:", doc["meta"]["tiers"])
print("groups:", doc["meta"]["groups"])
print("link failures:", link_failures)
linked = set()
for r in records:
    linked.update(r["geometry_record_ids"])
print("clinical records linking >=1 inventory record:",
      sum(1 for r in records if r["geometry_record_ids"]), "/", len(records))
print("inventory records linked:", len(linked), "/", len(inv["records"]))
print(f"wrote {OUT_PATH}")
