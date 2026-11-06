#!/usr/bin/env python3
"""ANATOMICA Milestone 11, step 2: digestive system clinical tranche.

Builds data/digestive/digestive.json from the inventory
(data/digestive/digestive-inventory.json, produced by
tools/dig_map.py).

FIELD-SOURCING RULE (precision law, same discipline as Milestones 4,
5, 9 and 10): a clinical value is entered only when it comes from a
source actually consulted during this build session, and the record
cites that source per field in its `sources` map. Anything not
sourced is null plus an explicit `verify` entry. TA names were not
given by the consulted sources and are null + verify-flagged
throughout. The hepatic arterial, portal venous and hepatic venous
records themselves live in the cardiovascular module (Milestone 5);
this tranche cites them in notes and cross-references rather than
duplicating them.

Sources (consulted in-session; TeachMeAnatomy abbreviated TMA):
  S1  TMA, "The Oesophagus" (~25 cm, C6-T11, wall layers, upper
      sphincter anatomical / lower sphincter physiological, four
      constrictions, segmental supply)
  S2  TMA, "The Stomach" (four divisions, curvatures and their
      supply, sphincters, coeliac supply, vagal innervation)
  S3  TMA, "The Small Intestine" (~6.5 m, digestion and absorption;
      duodenum four parts and the major duodenal papilla; jejunum /
      ileum distinguishing table; ileocaecal valve)
  S4  TMA, "The Colon" (large intestine) (~150 cm, four parts,
      teniae / haustra / omental appendices, midgut-hindgut split,
      marginal artery, sigmoid ~40 cm to S3)
  S5  TMA, "The Liver" (surfaces, lobes incl. caudate and quadrate,
      ligaments, porta hepatis, dual supply 25/75, innervation)
  S6  TMA, "The Gallbladder" (parts, 30-50 mL capacity, CCK; the
      biliary tree sequence from canaliculi to the major duodenal
      papilla and the sphincter of Oddi)
  S7  TMA, "The Pancreas" (five parts, main duct to the ampulla,
      splenic and pancreaticoduodenal supply)
  S8  TMA, "The Peritoneum" (parietal/visceral layers and their
      sensation, mesentery, omenta, intraperitoneal vs
      retroperitoneal relations)
  S9  TMA, "The Rectum" (S3 origin, flexures, ampulla, peritoneal
      coverings, rectal supply)
  S10 TMA, "The Anal Canal" (~4 cm, internal/external sphincters,
      anorectal ring, pectinate line and the above/below table)
  S11 TMA, "The Submandibular Gland" and "The Parotid Gland"
      (submandibular triangle, Wharton duct ~5 cm, submental supply;
      parotid serous secretion, lobes divided by the facial nerve)
  S12 OpenStax, Anatomy and Physiology 2e, section 23.3 "The Mouth,
      Pharynx, and Esophagus" (oral cavity framing, vestibule and
      cavity proper, palate, tongue, saliva 1-1.5 L/day and pH
      6.35-6.85, two dentitions: 20 deciduous, 32 permanent =
      8 incisors / 4 canines / 8 premolars / 12 molars)
  S13 Sibulesky, "Normal liver anatomy", Clinical Liver Disease
      2013 (PMC6448666): the Couinaud classification — eight
      independent functional segments, each with its own portal
      pedicle and hepatic venous outflow; sector groupings;
      resection nomenclature table
  S14 Last's Anatomy (Regional and Applied), "Liver and biliary
      tract" (chapter text consulted in-session): segment I
      autonomous supply and drainage; II posterior / III anterior in
      the left lateral sector; IV recognised on the visceral surface
      as the quadrate lobe; V and VI the inferior segments, VII and
      VIII the superior segments of the right sectors
  S15 TMA, "The Peritoneal Cavity" (greater sac compartments and
      paracolic gutters, lesser sac and the epiploic foramen,
      pelvic pouches)
  S16 anatomy.app, "Salivary glands (overview)" (three pairs of
      major glands each with one central duct; parotid largest,
      duct opens opposite the maxillary second molar; submandibular
      second largest, duct opens near the frenulum; sublingual
      smallest, below the tongue)

Record types and fields:
  pathway (the alimentary canal in order): pathway_order, extent,
    structure, function. Tiers: A = all sourced; B = extent and
    function sourced, structure flagged; C = extent or function
    flagged.
  organ (stomach, liver, gallbladder, pancreas): type-specific
    fields with per-type core/soft tiers (documented at each call).
  segment (the eight Couinaud segments of S13): sector, position,
    definition, surgical_note. Core = sector, definition;
    soft = position, surgical_note.
  ductpath (the biliary tree): sequence, territory, termination.
    Core = sequence, termination; soft = territory.
  region (oral cavity, peritoneum, peritoneal cavity): per-type
    fields and tiers.
  glands (salivary glands): major_glands, parotid, submandibular,
    sublingual, saliva. Core = major_glands, parotid; soft = rest.
  dentition (values): a `values` map; every value sourced (S12) or
    counted in this module's inventory. Tier A by construction;
    the checker re-validates the arithmetic and the inventory
    count.

Geometry linkage: clinical records link inventory records by exact
record name. Records for structures the release does not contain
(the sigmoid colon, the anal canal) link nothing and carry the
absence in their verify list instead — checker-gated, as in
Milestones 9 and 10. The release's ninth named liver segment
(hepatovenous segment ix) has no Couinaud counterpart and gets no
clinical segment record; see the liver organ record's note.
"""

import json
import os

PROJECT = "/home/hatch/workspace/anatomica-project"
INV_PATH = os.path.join(PROJECT, "data/digestive/digestive-inventory.json")
OUT_PATH = os.path.join(PROJECT, "data/digestive/digestive.json")

inv = json.load(open(INV_PATH, encoding="utf-8"))
inv_by_name = {}
for r in inv["records"]:
    inv_by_name.setdefault(r["name"], []).append(r["record_id"])

SOURCES = {
    "S1": "TeachMeAnatomy, 'The Oesophagus' (teachmeanatomy.info)",
    "S2": "TeachMeAnatomy, 'The Stomach' (teachmeanatomy.info)",
    "S3": "TeachMeAnatomy, 'The Small Intestine' (teachmeanatomy.info)",
    "S4": "TeachMeAnatomy, 'The Colon' (teachmeanatomy.info)",
    "S5": "TeachMeAnatomy, 'The Liver' (teachmeanatomy.info)",
    "S6": "TeachMeAnatomy, 'The Gallbladder' (teachmeanatomy.info)",
    "S7": "TeachMeAnatomy, 'The Pancreas' (teachmeanatomy.info)",
    "S8": "TeachMeAnatomy, 'The Peritoneum' (teachmeanatomy.info)",
    "S9": "TeachMeAnatomy, 'The Rectum' (teachmeanatomy.info)",
    "S10": "TeachMeAnatomy, 'The Anal Canal' (teachmeanatomy.info)",
    "S11": "TeachMeAnatomy, 'The Submandibular Gland' and 'The "
           "Parotid Gland' (teachmeanatomy.info)",
    "S12": "OpenStax, Anatomy and Physiology 2e, section 23.3 "
           "'The Mouth, Pharynx, and Esophagus'",
    "S13": "Sibulesky, 'Normal liver anatomy', Clinical Liver "
           "Disease 2013 (PMC6448666)",
    "S14": "Last's Anatomy (Regional and Applied), 'Liver and "
           "biliary tract' (chapter text consulted in-session)",
    "S15": "TeachMeAnatomy, 'The Peritoneal Cavity' "
           "(teachmeanatomy.info)",
    "S16": "anatomy.app, 'Salivary glands (overview)'",
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


def pathway(rec_id, name, order, names, extent=None, structure=None,
            function=None, sources=None, verify=None, note=None):
    rec = base(rec_id, name, "pathway", "Alimentary canal pathway",
               names, verify, note)
    rec.update({"pathway_order": order,
                "extent": extent, "structure": structure,
                "function": function})
    rec["sources"] = dict(sources or {})
    finish(rec, ["extent", "structure", "function"],
           core=["extent", "function"], soft=["structure"],
           rec_id=rec_id)


def typed(rec_id, name, rtype, group, names, fields, sources, core,
          soft, verify=None, note=None):
    rec = base(rec_id, name, rtype, group, names, verify, note)
    rec.update(fields)
    rec["sources"] = dict(sources or {})
    finish(rec, list(fields), core=core, soft=soft, rec_id=rec_id)


TOOTH_NAMES = [r["name"] for r in inv["records"]
               if r["record_id"].startswith("tooth.")]

# ------------------------------------------------------------------
# Alimentary canal pathway (in order, mouth to anal canal)
# ------------------------------------------------------------------
pathway("dig.oral-cavity", "Oral cavity", 1,
        ["mouth", "tongue", "soft palate", "uvula",
         "gingiva of upper jaw", "gingiva of lower jaw"] + TOOTH_NAMES,
        extent="The mouth (oral or buccal cavity), framed by the "
               "cheeks, tongue and palate; it runs from the lips "
               "back to the fauces, the opening into the oropharynx",
        structure="The lips (covered by the orbicularis oris, the "
                  "inner lip attached to the gum by the labial "
                  "frenulum) and the cheeks (buccinator muscles "
                  "between skin and mucous membrane) form the outer "
                  "walls; the oral vestibule is the pocket framed "
                  "inside by the gums and teeth and outside by the "
                  "cheeks and lips, and the oral cavity proper runs "
                  "from the gums and teeth to the fauces. Its three "
                  "accessory structures are the tongue, the salivary "
                  "glands and the teeth",
        function="Ingestion; mechanical digestion by the teeth and "
                 "tongue, which positions food for chewing, gathers "
                 "it into a bolus and positions it for swallowing; "
                 "chemical digestion begins here (salivary amylase "
                 "and lingual lipase)",
        sources={"extent": ["S12"], "structure": ["S12"],
                 "function": ["S12"]},
        note="the soft palate and uvula records and the gingiva "
             "records are inventory records of this module; the "
             "palate muscles (levator and tensor veli palatini, "
             "uvular muscle) and the jaws are cross-referenced to "
             "the muscular and skeletal modules in the inventory")

pathway("dig.oesophagus", "Oesophagus", 2, ["esophagus"],
        extent="A fibromuscular tube approximately 25 cm long, from "
               "the inferior border of the cricoid cartilage (C6) to "
               "the cardiac orifice of the stomach (T11); it passes "
               "through the oesophageal hiatus of the diaphragm at "
               "T10, and its abdominal portion is approximately "
               "1.25 cm long",
        structure="Wall of four layers: adventitia (serosa only on "
                  "the very distal, intraperitoneal part), muscle "
                  "layer (superior third voluntary striated muscle, "
                  "middle third mixed, inferior third smooth "
                  "muscle), submucosa, and mucosa of non-keratinised "
                  "stratified squamous epithelium. Four "
                  "physiological constrictions: arch of aorta, left "
                  "main bronchus, cricoid cartilage, diaphragmatic "
                  "hiatus",
        function="Conducts the food bolus from the pharynx to the "
                 "stomach. The upper oesophageal sphincter is an "
                 "anatomical sphincter of striated muscle "
                 "(cricopharyngeus), normally constricted to prevent "
                 "air entering; the lower oesophageal sphincter is "
                 "a physiological sphincter at the "
                 "gastro-oesophageal junction (left of T11) that "
                 "prevents reflux of gastric contents",
        sources={"extent": ["S1"], "structure": ["S1"],
                 "function": ["S1"]})

pathway("dig.stomach", "Stomach", 3, ["stomach"],
        extent="An intraperitoneal organ between the oesophagus "
               "and the duodenum, in the epigastric and left "
               "hypochondriac regions; its superior opening (the "
               "cardia) is at T11 and the pylorus demarcates the "
               "transpyloric plane at L1",
        structure="J-shaped, with a long convex greater curvature "
                  "and a short concave lesser curvature; four "
                  "divisions: cardia, fundus, body and pylorus (see "
                  "the Stomach (structure) record)",
        function="Receives the bolus from the oesophagus; the "
                 "pyloric sphincter — an anatomical sphincter of "
                 "smooth muscle, normally contracted — controls "
                 "the exit of chyme into the duodenum",
        sources={"extent": ["S2"], "structure": ["S2"],
                 "function": ["S2"]})

pathway("dig.duodenum", "Duodenum", 4, ["duodenum"],
        extent="The most proximal part of the small intestine, "
               "approximately 25 cm long ('twelve fingers length'), "
               "running in a C-shape around the head of the pancreas "
               "from the pylorus to the duodenojejunal junction",
        structure="Four parts: superior (D1, at L1 — the 'cap'; "
                  "its first 3 cm are covered by peritoneum on both "
                  "sides, the remainder retroperitoneal), descending "
                  "(D2, L1-L3; the major duodenal papilla on its "
                  "internal wall is the opening of the "
                  "hepatopancreatic ampulla), inferior (D3, at L3; "
                  "crosses the IVC and aorta, posterior to the "
                  "superior mesenteric artery and vein) and "
                  "ascending (D4, L3-L2; joins the jejunum at the "
                  "duodenojejunal flexure, whose angle is widened "
                  "by the suspensory muscle of the duodenum)",
        function="Receives chyme from the stomach and, at the "
                 "major duodenal papilla, the bile and pancreatic "
                 "secretions delivered by the hepatopancreatic "
                 "ampulla; the first part is the most common site of "
                 "duodenal ulceration",
        sources={"extent": ["S3"], "structure": ["S3"],
                 "function": ["S3", "S6"]})

pathway("dig.jejunum", "Jejunum", 5, ["jejunum"],
        extent="The middle part of the small intestine, beginning "
               "at the duodenojejunal flexure; there is no clear "
               "external demarcation between the jejunum and the "
               "ileum",
        structure="Intraperitoneal, attached to the posterior "
                  "abdominal wall by the mesentery; located in the "
                  "upper left quadrant, with a thick intestinal "
                  "wall, longer vasa recta, fewer arterial arcades "
                  "and a red colour (the consulted source's "
                  "distinguishing table against the ileum)",
        function="With the rest of the small intestine (about "
                 "6.5 m in the average person), assists in the "
                 "digestion and absorption of ingested food",
        sources={"extent": ["S3"], "structure": ["S3"],
                 "function": ["S3"]})

pathway("dig.ileum", "Ileum", 6, ["ileum", "ileocecal junction"],
        extent="The distal part of the small intestine, ending at "
               "the ileocaecal junction where it meets the large "
               "intestine",
        structure="Intraperitoneal, attached by the mesentery; "
                  "located in the lower right quadrant, with a thin "
                  "intestinal wall, shorter vasa recta, more "
                  "arterial arcades and a pink colour (the consulted "
                  "source's distinguishing table against the "
                  "jejunum)",
        function="Assists in the digestion and absorption of "
                 "ingested food; at the ileocaecal junction the "
                 "ileum invaginates into the cecum to form the "
                 "ileocecal valve, whose main function is to "
                 "prevent reflux of enteric fluid from the colon "
                 "into the small intestine",
        sources={"extent": ["S3"], "structure": ["S3"],
                 "function": ["S3"]},
        note="the ileocecal valve itself has no concept in the "
             "release (probe-verified absence); the ileocecal "
             "junction concept is the linked geometry")

pathway("dig.cecum-appendix", "Cecum and appendix", 7,
        ["cecum", "appendix"],
        extent="The cecum is the first part of the large "
               "intestine, receiving the ileum at the ileocaecal "
               "junction; the appendix is carried with it in the "
               "consulted large-intestine source's division of the "
               "large bowel",
        structure="The cecum is a blind-ended pouch: its blind end "
                  "lies inferiorly and the ascending colon continues "
                  "from it superiorly",
        function="The ileocaecal valve at the junction separates "
                 "the small from the large intestine and prevents "
                 "reflux of enteric fluid from the colon into the "
                 "small intestine",
        sources={"extent": ["S3", "S4"], "structure": ["S3"],
                 "function": ["S3"]},
        note="the consulted sources do not describe the structure "
             "or function of the appendix itself in the passages "
             "used; its inventory record is linked and no unsourced "
             "detail is entered")

pathway("dig.ascending-colon", "Ascending colon", 8,
        ["ascending colon"],
        extent="The first of the four parts of the colon (total "
               "colon length about 150 cm): retroperitoneal, "
               "running superiorly from the cecum on the right side "
               "to the right colic (hepatic) flexure at the right "
               "lobe of the liver, where it turns 90 degrees",
        structure="Carries the colon's distinguishing features: "
                  "omental appendices (small fat-filled peritoneal "
                  "pouches), teniae coli (three longitudinal muscle "
                  "strips — mesocolic, free and omental) and "
                  "haustra (sacculations produced by teniae "
                  "contraction); a paracolic gutter lies laterally",
        function="As the colon as a whole: absorbs water and "
                 "electrolytes from the intestinal contents and "
                 "forms faeces; the ascending colon and proximal "
                 "two-thirds of the transverse colon are midgut in "
                 "embryological origin",
        sources={"extent": ["S4"], "structure": ["S4"],
                 "function": ["S4"]})

pathway("dig.transverse-colon", "Transverse colon", 9,
        ["transverse colon"],
        extent="From the right colic (hepatic) flexure to the "
               "spleen, where the left colic (splenic) flexure turns "
               "90 degrees inferiorly; attached to the diaphragm by "
               "the phrenicocolic ligament; the least fixed part of "
               "the colon",
        structure="Intraperitoneal, enclosed by the transverse "
                  "mesocolon; embryologically the proximal "
                  "two-thirds are midgut and the distal third "
                  "hindgut; carries teniae coli, haustra and "
                  "omental appendices",
        function="Absorbs water and electrolytes and forms faeces "
                 "(the colon's function, per the consulted source)",
        sources={"extent": ["S4"], "structure": ["S4"],
                 "function": ["S4"]})

pathway("dig.descending-colon", "Descending colon", 10,
        ["descending colon"],
        extent="From the left colic (splenic) flexure inferiorly; "
               "retroperitoneal in most people, lying anterior to "
               "the left kidney over its lateral border, then "
               "turning medially to become the sigmoid colon",
        structure="A hindgut part of the colon, carrying teniae "
                  "coli, haustra and omental appendices; a paracolic "
                  "gutter lies laterally",
        function="Absorbs water and electrolytes and forms faeces "
                 "(the colon's function, per the consulted source)",
        sources={"extent": ["S4"], "structure": ["S4"],
                 "function": ["S4"]})

pathway("dig.sigmoid-colon", "Sigmoid colon", 11, [],
        extent="Approximately 40 cm long, in the left lower "
               "quadrant from the left iliac fossa to the third "
               "sacral vertebra (S3), where it becomes the rectum",
        structure="S-shaped and mobile, suspended by the sigmoid "
                  "mesocolon; at the rectosigmoid junction the "
                  "teniae coli broaden out to form a complete "
                  "longitudinal muscle layer in the rectum, and the "
                  "haustra and omental appendices cease",
        function="Absorbs water and electrolytes and forms faeces "
                 "(the colon's function, per the consulted source); "
                 "a hindgut part of the colon",
        sources={"extent": ["S4"], "structure": ["S4"],
                 "function": ["S4"]},
        verify=[ABSENCE],
        note="neither the sigmoid colon nor the sigmoid mesocolon "
             "has a concept in the release (probe-verified "
             "absences); the TotalSegmentator 'colon' label is one "
             "undivided label and does not resolve this gap")

pathway("dig.rectum", "Rectum", 12, ["rectum"],
        extent="The most distal segment of the large intestine: "
               "continuous proximally with the sigmoid colon, "
               "beginning at S3, and terminating into the anal "
               "canal; the most posterior pelvic viscus",
        structure="Macroscopically distinct from the colon by the "
                  "absence of taenia coli, haustra and omental "
                  "appendices. Three flexure groups: the sacral "
                  "flexure (following the sacrum and coccyx), the "
                  "anorectal flexure (formed by puborectalis tone, "
                  "contributing to continence) and three lateral "
                  "flexures formed by transverse folds of the "
                  "internal wall. Peritoneal coverings: superior "
                  "third anterior and lateral surfaces, middle third "
                  "anterior only, lower third none",
        function="A temporary store for faeces; its final segment, "
                 "the ampulla, relaxes to accumulate and store "
                 "faeces before defecation",
        sources={"extent": ["S9"], "structure": ["S9"],
                 "function": ["S9"]})

pathway("dig.anal-canal", "Anal canal", 13, [],
        extent="The final segment of the gastrointestinal tract, "
               "approximately 4 cm long, beginning as the "
               "continuation of the rectum, passing "
               "inferoposteriorly through the pelvic floor to the "
               "anus; it lies within the anal triangle of the "
               "perineum between the right and left ischioanal "
               "fossae",
        structure="Two sphincters keep the canal collapsed: the "
                  "internal anal sphincter (involuntary circular "
                  "smooth muscle surrounding the upper two-thirds) "
                  "and the external anal sphincter (voluntary, "
                  "surrounding the lower two-thirds, blending "
                  "superiorly with puborectalis); their fusion with "
                  "puborectalis forms the anorectal ring. The "
                  "superior mucosa is thrown into anal columns "
                  "joined by anal valves, which collectively form "
                  "the pectinate (dentate) line dividing the "
                  "hindgut-derived upper canal from the "
                  "proctodeum-derived lower canal",
        function="Defecation and the maintenance of faecal "
                 "continence; the canal is collapsed by the anal "
                 "sphincters except during defecation",
        sources={"extent": ["S10"], "structure": ["S10"],
                 "function": ["S10"]},
        verify=[ABSENCE],
        note="the anal canal, the anus and the pectinate line have "
             "no concepts in the release (probe-verified absences); "
             "the external anal sphincter is the muscular module's "
             "record (muscle.external-anal-sphincter), censused in "
             "this module's inventory as a cross-reference")


# ------------------------------------------------------------------
# Organs
# ------------------------------------------------------------------
typed("organ.stomach", "Stomach (structure)", "organ", "Organs",
      ["stomach"],
      fields={
          "parts": "Four divisions: cardia (surrounds the superior "
                   "opening of the stomach, at T11), fundus (the "
                   "rounded, often gas-filled part superior and to "
                   "the left of the cardia), body (the large central "
                   "region, inferior to the fundus) and pylorus "
                   "(pyloric antrum, pyloric canal and pyloric "
                   "sphincter; the sphincter demarcates the "
                   "transpyloric plane at L1)",
          "curvatures": "Greater curvature: the long convex lateral "
                        "border, from the cardiac notch to the "
                        "pyloric antrum, giving attachment to the "
                        "greater omentum; supplied by the short "
                        "gastric and right and left gastro-omental "
                        "arteries. Lesser curvature: the short "
                        "concave medial border, where the angular "
                        "notch marks the junction of body and "
                        "pyloric part and the hepatogastric ligament "
                        "attaches; supplied by the left gastric "
                        "artery and the right gastric branch of the "
                        "hepatic artery",
          "sphincters": "Inferior oesophageal sphincter at the "
                        "cardiac orifice (T11; the oesophagus "
                        "passes the diaphragmatic hiatus at T10) — "
                        "physiological, not under voluntary control. "
                        "Pyloric sphincter — anatomical, of smooth "
                        "muscle, controlling the exit of chyme, "
                        "normally contracted",
          "blood_supply": "All arterial supply derives from the "
                          "coeliac trunk and its branches, with "
                          "anastomoses along both curvatures. The "
                          "veins parallel the arteries and drain "
                          "into the hepatic portal system: right and "
                          "left gastric veins directly to the portal "
                          "vein, short gastric and left "
                          "gastro-omental veins to the splenic vein, "
                          "right gastro-omental vein to the superior "
                          "mesenteric vein",
          "innervation": "Parasympathetic supply from the anterior "
                         "and posterior vagal trunks; sympathetic "
                         "supply from T6-T9 via the greater "
                         "splanchnic nerve to the coeliac plexus, "
                         "which also carries pain fibres",
      },
      sources={"parts": ["S2"], "curvatures": ["S2"],
               "sphincters": ["S2", "S1"], "blood_supply": ["S2"],
               "innervation": ["S2"]},
      core=["parts", "curvatures"],
      soft=["sphincters", "blood_supply", "innervation"],
      note="the cardia, fundus, body and pylorus named here are "
           "sourced text: the release carries no stomach-part "
           "concepts (probe-verified absences in the inventory). "
           "The supplying vessels are cardiovascular module "
           "records (e.g. artery.celiac-artery, "
           "artery.gastroduodenal-artery) and are not duplicated "
           "here")

typed("organ.liver", "Liver", "organ", "Organs", ["liver"],
      fields={
          "position": "A peritoneal organ of the right upper "
                      "quadrant — predominantly the right "
                      "hypochondrium and epigastrium, extending "
                      "into the left hypochondrium; the largest "
                      "visceral structure in the abdominal cavity "
                      "and the largest gland in the body, an "
                      "accessory gland of digestion. About 2% of "
                      "adult body weight (approximately 1400 g in "
                      "females and 1800 g in males, S13)",
          "surfaces": "Diaphragmatic surface (anterosuperior): "
                      "smooth and convex, fitting beneath the "
                      "diaphragm; its posterior aspect is not "
                      "covered by visceral peritoneum and contacts "
                      "the diaphragm directly — the bare area. "
                      "Visceral surface (posteroinferior): covered "
                      "by peritoneum except at the gallbladder "
                      "fossa and the porta hepatis, and moulded by "
                      "the right kidney, right adrenal gland, right "
                      "colic flexure, transverse colon, first part "
                      "of the duodenum, gallbladder, oesophagus and "
                      "stomach",
          "lobes": "Externally a large right lobe and a smaller "
                   "left lobe, divided by the falciform ligament. "
                   "Caudate lobe: on the upper visceral surface, "
                   "between the IVC and the fossa for the "
                   "ligamentum venosum. Quadrate lobe: on the lower "
                   "visceral surface, between the gallbladder and "
                   "the fossa for the ligamentum teres. The "
                   "functional (Couinaud) division into eight "
                   "segments is carried in this module's segment "
                   "records",
          "ligaments": "Falciform ligament: anterior surface to "
                       "the anterior abdominal wall, its free edge "
                       "containing the ligamentum teres (remnant of "
                       "the umbilical vein). Coronary ligament: "
                       "superior surface to the diaphragm, "
                       "demarcating the bare area. Right and left "
                       "triangular ligaments: the unions of the "
                       "coronary folds at each lobe. Lesser "
                       "omentum: to the lesser curvature of the "
                       "stomach and the first part of the duodenum; "
                       "its hepatoduodenal ligament surrounds the "
                       "portal triad",
          "blood_supply": "Dual supply: the hepatic artery proper "
                          "contributes approximately 25% of the "
                          "liver's blood (oxygenated, from the "
                          "coeliac trunk) and the hepatic portal "
                          "vein approximately 75% (nutrient-rich "
                          "blood from the gut; the portal vein is "
                          "formed by the union of the splenic and "
                          "superior mesenteric veins, S13). Drainage "
                          "is by the hepatic veins into the IVC",
          "nerve_supply": "The hepatic plexus (sympathetic fibres "
                          "from the coeliac plexus and "
                          "parasympathetic fibres from the vagus) "
                          "enters at the porta hepatis and follows "
                          "the hepatic artery and portal vein "
                          "branches; Glisson's capsule is supplied "
                          "by the lower intercostal nerves, so "
                          "capsular distension gives sharp, "
                          "localised pain",
      },
      sources={"position": ["S5", "S13"], "surfaces": ["S5"],
               "lobes": ["S5", "S13"], "ligaments": ["S5"],
               "blood_supply": ["S5", "S13"],
               "nerve_supply": ["S5"]},
      core=["lobes", "surfaces"],
      soft=["position", "ligaments", "blood_supply", "nerve_supply"],
      note="the quadrate lobe, porta hepatis, bare area and the "
           "named ligaments are sourced text: the release carries "
           "no concepts for them (probe-verified absences). The "
           "supplying vessels are cardiovascular module records "
           "(artery.hepatic-artery-proper, artery.common-hepatic-"
           "artery, vein.hepatic-portal-vein, vein.hepatic-vein) "
           "and are cited, not duplicated. The release also "
           "carries a 'hepatovenous segment ix' concept (IS-A "
           "only) with no counterpart in the eight-segment "
           "Couinaud classification (S13); it is an inventory "
           "record and deliberately has no clinical segment record "
           "here")

typed("organ.gallbladder", "Gallbladder", "organ", "Organs",
      ["gallbladder"],
      fields={
          "position_relations": "An intraperitoneal, pear-shaped "
                                "sac in the right hypochondrium, "
                                "lying in a fossa between the "
                                "inferior aspects of the right and "
                                "quadrate lobes of the liver, "
                                "anterior to the first part of the "
                                "duodenum; posterior relations are "
                                "the transverse colon and proximal "
                                "duodenum",
          "parts": "Fundus: the rounded distal end, projecting at "
                   "the inferior border of the liver in the "
                   "mid-clavicular line. Body: the largest part. "
                   "Neck: tapers into the cystic duct and contains "
                   "a mucosal fold (Hartmann's pouch), a common "
                   "site for gallstones to lodge",
          "function": "Concentrates and stores the bile produced "
                      "by the liver (capacity 30-50 mL); bile is "
                      "released into the biliary tree in response "
                      "to cholecystokinin",
          "blood_supply": "The cystic artery, a branch of the "
                          "right hepatic artery (from the common "
                          "hepatic artery, from the coeliac trunk). "
                          "Venous drainage: the neck via cystic "
                          "veins directly into the portal vein; the "
                          "fundus and body into the hepatic "
                          "sinusoids",
          "innervation": "Coeliac plexus (sympathetic and sensory "
                         "fibres) and the vagus nerve "
                         "(parasympathetic; gallbladder "
                         "contraction and relaxation of the "
                         "sphincter of Oddi), although most "
                         "post-prandial emptying is driven by "
                         "cholecystokinin",
      },
      sources={"position_relations": ["S6"], "parts": ["S6"],
               "function": ["S6"], "blood_supply": ["S6"],
               "innervation": ["S6"]},
      core=["parts", "function"],
      soft=["position_relations", "blood_supply", "innervation"])

typed("organ.pancreas", "Pancreas", "organ", "Organs", ["pancreas"],
      fields={
          "position": "In the upper abdomen at the transpyloric "
                      "plane (L1), deep in the epigastric and left "
                      "hypochondriac regions; retroperitoneal except "
                      "for the tail",
          "parts": "Five parts: head (the widest part, sitting in "
                   "the C-curve of the duodenum), uncinate process "
                   "(a hook from the lower head extending medially "
                   "beneath the body, posterior to the superior "
                   "mesenteric vessels), neck (between head and "
                   "body, overlying the superior mesenteric vessels "
                   "and the formation of the portal vein), body "
                   "(crossing the midline posterior to the stomach) "
                   "and tail (the left-most part, the only "
                   "intraperitoneal part, reaching the splenic "
                   "hilum within the splenorenal ligament with the "
                   "splenic vessels)",
          "duct_system": "The main pancreatic duct runs the length "
                         "of the gland (collecting from intercalated "
                         "and intralobular ducts draining about one "
                         "million acini) and unites with the common "
                         "bile duct at the hepatopancreatic ampulla "
                         "of Vater, opening into the second part of "
                         "the duodenum at the major duodenal papilla; "
                         "the sphincter of Oddi surrounds the "
                         "ampulla. The consulted source does not "
                         "describe an accessory pancreatic duct",
          "blood_supply": "Pancreatic branches of the splenic "
                          "artery; the head is additionally "
                          "supplied by the superior "
                          "pancreaticoduodenal artery "
                          "(gastroduodenal, from the coeliac trunk) "
                          "and the inferior pancreaticoduodenal "
                          "artery (superior mesenteric artery). "
                          "Venous drainage: head to superior "
                          "mesenteric branches of the hepatic portal "
                          "vein, the remainder to the splenic vein",
      },
      sources={"position": ["S7"], "parts": ["S7"],
               "duct_system": ["S7", "S6"], "blood_supply": ["S7"]},
      core=["parts", "duct_system"],
      soft=["position", "blood_supply"],
      verify=["no BP3D concept: the head, neck, body, tail and "
              "uncinate process named in the parts field have no "
              "concepts in the BodyParts3D 4.0 release "
              "(probe-verified absences); the parts are sourced "
              "text and the record's geometry is the whole-organ "
              "pancreas record"],
      note="the supplying vessels are cardiovascular module "
           "records (artery.splenic-artery, "
           "artery.gastroduodenal-artery, "
           "artery.superior-mesenteric-artery, vein.splenic-vein) "
           "and are cited, not duplicated")

# ------------------------------------------------------------------
# Couinaud segments (S13/S14): eight records, keyed to the
# inventory's hepatovenous segment records ii-viii and, for
# segment I, to the caudate lobe record
# ------------------------------------------------------------------
SEGDEF = ("One of the eight independent functional segments of the "
          "Couinaud classification: each segment has its own portal "
          "pedicle — a hepatic arterial branch, a portal branch "
          "and a bile duct — with a separate hepatic venous branch "
          "providing outflow (S13). The middle hepatic vein divides "
          "the functional right and left lobes, the right hepatic "
          "vein divides the right lobe into anterior and posterior "
          "sectors, the left hepatic vein divides the left lobe "
          "into medial and lateral sectors, and the portal vein "
          "plane divides upper from lower segments")


def segment(rec_id, name, links, sector, position, surgical,
            sector_src, position_src):
    srcs = {"sector": sector_src, "definition": ["S13"]}
    if position is not None:
        srcs["position"] = position_src
    if surgical is not None:
        srcs["surgical_note"] = ["S13"]
    typed(rec_id, name, "segment", "Liver segments (Couinaud)",
          links,
          fields={"sector": sector, "position": position,
                  "definition": SEGDEF, "surgical_note": surgical},
          sources=srcs, core=["sector", "definition"],
          soft=["position", "surgical_note"])


segment("seg.couinaud-i", "Segment I (caudate)",
        ["caudate lobe of liver"],
        sector="The caudate lobe: outside the functional right / "
               "left division of the liver (the functional left "
               "lobe is segments II-IV and the functional right "
               "lobe segments V-VIII)",
        position="Located posteriorly (S13). Autonomous: it "
                 "receives blood from both the right and left "
                 "hepatic artery and portal branches, drains bile "
                 "into both the right and left hepatic ducts, and "
                 "has independent venous drainage directly into "
                 "the IVC (S14)",
        surgical=None,
        sector_src=["S13"], position_src=["S13", "S14"])

segment("seg.couinaud-ii", "Segment II", ["hepatovenous segment ii"],
        sector="Left lateral sector (with segment III, the left "
               "lateral segment, i.e. the topographic left lobe); "
               "part of the functional left lobe (II-IV)",
        position="The posterior segment of the left lateral sector "
                 "(S14)",
        surgical="Segments II and III are resected together as a "
                 "left lateral segmentectomy",
        sector_src=["S13"], position_src=["S14"])

segment("seg.couinaud-iii", "Segment III",
        ["hepatovenous segment iii"],
        sector="Left lateral sector (with segment II, the left "
               "lateral segment, i.e. the topographic left lobe); "
               "part of the functional left lobe (II-IV)",
        position="The anterior segment of the left lateral sector "
                 "(S14)",
        surgical="Segments II and III are resected together as a "
                 "left lateral segmentectomy",
        sector_src=["S13"], position_src=["S14"])

segment("seg.couinaud-iv", "Segment IV", ["hepatovenous segment iv"],
        sector="Left medial sector: segment IV is the medial "
               "segment of the left lobe; part of the functional "
               "left lobe (II-IV)",
        position="Recognised on the visceral surface of the liver "
                 "as the quadrate lobe (S14)",
        surgical="Resection of segment IV is a left medial "
                 "segmentectomy; resection of segments II, III and "
                 "IV is a left hepatectomy",
        sector_src=["S13"], position_src=["S14"])

segment("seg.couinaud-v", "Segment V", ["hepatovenous segment v"],
        sector="Right anterior sector (with segment VIII); part "
               "of the functional right lobe (V-VIII)",
        position="The inferior segment of the right anterior "
                 "sector (S14)",
        surgical="Segments V and VIII are resected together as a "
                 "right anterior segmentectomy",
        sector_src=["S13"], position_src=["S14"])

segment("seg.couinaud-vi", "Segment VI", ["hepatovenous segment vi"],
        sector="Right posterior sector (with segment VII); part "
               "of the functional right lobe (V-VIII)",
        position="The inferior segment of the right posterior "
                 "sector (S14)",
        surgical="Segments VI and VII are resected together as a "
                 "right posterior segmentectomy",
        sector_src=["S13"], position_src=["S14"])

segment("seg.couinaud-vii", "Segment VII",
        ["hepatovenous segment vii"],
        sector="Right posterior sector (with segment VI); part of "
               "the functional right lobe (V-VIII)",
        position="The superior segment of the right posterior "
                 "sector (S14)",
        surgical="Segments VI and VII are resected together as a "
                 "right posterior segmentectomy",
        sector_src=["S13"], position_src=["S14"])

segment("seg.couinaud-viii", "Segment VIII",
        ["hepatovenous segment viii"],
        sector="Right anterior sector (with segment V); part of "
               "the functional right lobe (V-VIII)",
        position="The superior segment of the right anterior "
                 "sector (S14)",
        surgical="Segments V and VIII are resected together as a "
                 "right anterior segmentectomy",
        sector_src=["S13"], position_src=["S14"])

# ------------------------------------------------------------------
# Biliary tree
# ------------------------------------------------------------------
typed("dig.biliary-tree", "Biliary tree", "ductpath",
      "Biliary system",
      ["biliary tree", "hepatic biliary tree",
       "intrahepatic biliary tree", "right hepatic biliary tree",
       "left hepatic biliary tree", "right hepatic duct",
       "left hepatic duct", "common hepatic duct", "cystic duct",
       "gallbladder"],
      fields={
          "sequence": "Bile secreted by the hepatocytes drains "
                      "through canaliculi, intralobular ducts and "
                      "collecting ducts into the left and right "
                      "hepatic ducts, which converge to form the "
                      "common hepatic duct; the cystic duct (the "
                      "duct to and from the gallbladder) joins it "
                      "to form the common bile duct, which descends "
                      "posterior to the first part of the duodenum "
                      "and the head of the pancreas, is joined by "
                      "the main pancreatic duct at the "
                      "hepatopancreatic ampulla (of Vater) and "
                      "empties into the duodenum",
          "territory": "Both lobes of the liver, drained by the "
                       "right and left hepatic ducts and their "
                       "intrahepatic trees; the gallbladder is a "
                       "side reservoir on the cystic duct, "
                       "concentrating and storing bile between "
                       "meals",
          "termination": "The major duodenal papilla, in the "
                         "second part of the duodenum; flow is "
                         "regulated by the sphincter of Oddi, "
                         "which surrounds the hepatopancreatic "
                         "ampulla",
      },
      sources={"sequence": ["S6"], "territory": ["S6"],
               "termination": ["S6"]},
      core=["sequence", "termination"], soft=["territory"],
      verify=["no BP3D concept: the common bile duct named in the "
              "sequence has no concept in the BodyParts3D 4.0 "
              "release (probe-verified absence); the release's "
              "extrahepatic tree runs from the common hepatic duct "
              "and the cystic duct with the final common channel "
              "unnamed",
              "no BP3D concept: the hepatopancreatic ampulla and "
              "the major duodenal papilla named in the sequence "
              "and termination have no concepts in the "
              "BodyParts3D 4.0 release (probe-verified absences)"],
      note="the cystic artery and the hepatic arterial and portal "
           "records relevant to this system are cardiovascular "
           "module records and are cited, not duplicated")

# ------------------------------------------------------------------
# Oral cavity regions, salivary glands, dentition
# ------------------------------------------------------------------
typed("dig.oral-cavity-structure", "Oral cavity (structure)",
      "region", "Oral cavity",
      ["mouth", "tongue", "soft palate", "uvula",
       "gingiva of upper jaw", "gingiva of lower jaw"],
      fields={
          "divisions": "Oral vestibule: the pocket framed inside "
                       "by the gums and teeth and outside by the "
                       "cheeks and lips. Oral cavity proper: from "
                       "the gums and teeth back to the fauces, the "
                       "opening between the oral cavity and the "
                       "oropharynx (throat)",
          "palate": "Hard palate (anterior): formed by the "
                    "maxillary and palatine bones, a wall between "
                    "the oral and nasal cavities and a rigid shelf "
                    "against which the tongue forces food during "
                    "chewing. Soft palate (posterior): mainly "
                    "skeletal muscle, with the uvula dropping from "
                    "the centre of its posterior edge; on "
                    "swallowing the soft palate and uvula move up "
                    "to block the nasal cavity. The palatoglossal "
                    "arch (front) and palatopharyngeal arch "
                    "(behind) extend down from the soft palate, "
                    "with the palatine tonsils between them and "
                    "the lingual tonsils at the base of the tongue",
          "functions": "The tongue facilitates ingestion, "
                       "mechanical digestion, chemical digestion "
                       "(lingual lipase), sensation (including "
                       "taste, via the taste buds of the fungiform "
                       "papillae), swallowing and vocalisation; "
                       "the cavity receives food and begins its "
                       "digestion",
      },
      sources={"divisions": ["S12"], "palate": ["S12"],
               "functions": ["S12"]},
      core=["divisions", "functions"], soft=["palate"],
      note="the hard palate and the palatine tonsil named here "
           "have no concepts in the release (probe-verified "
           "absences); the maxilla and palatine bones are skeletal "
           "module records")

typed("dig.salivary-glands", "Salivary glands", "glands",
      "Oral cavity",
      ["right submandibular gland", "left submandibular gland",
       "right sublingual gland", "left sublingual gland"],
      fields={
          "major_glands": "Three pairs of major glands, lying "
                          "outside the oral mucosa and each "
                          "secreting through one central duct: "
                          "parotid (largest), submandibular (second "
                          "largest) and sublingual (smallest). Many "
                          "minor glands (labial, buccal, palatal "
                          "and lingual) in the mucosa of the mouth "
                          "and tongue secrete constantly, even in "
                          "sleep",
          "parotid": "The largest salivary gland, lying between "
                     "the skin and the masseter near the ear; "
                     "lobulated, its superficial and deep lobes "
                     "separated by the facial nerve. It produces "
                     "serous (watery, enzyme-rich) saliva, "
                     "transported by the parotid (Stensen) duct, "
                     "which opens into the oral cavity opposite "
                     "the maxillary second molar tooth",
          "submandibular": "Bilateral glands in the anterior part "
                           "of the submandibular triangle, of "
                           "elongate flattened hook shape with "
                           "superficial and deep arms; they "
                           "produce mixed serous and mucous "
                           "secretions. The submandibular "
                           "(Wharton) duct, about 5 cm long, "
                           "emerges anteromedially from the deep "
                           "arm between the mylohyoid, hyoglossus "
                           "and genioglossus and opens into the "
                           "floor of the oral cavity near the "
                           "frenulum of the tongue. Supplied by the "
                           "submental artery (branch of the facial "
                           "artery) and the sublingual artery "
                           "(branch of the lingual artery)",
          "sublingual": "The smallest of the major glands, below "
                        "the tongue; it drains into the floor of "
                        "the oral cavity by the lesser sublingual "
                        "ducts and Bartholin's duct. Its secretion "
                        "is mostly mucous — the thickest saliva of "
                        "the three glands, with the least amylase",
          "saliva": "1-1.5 litres of saliva are produced per day; "
                    "saliva is 99.4% water, with salivary amylase "
                    "initiating carbohydrate breakdown (acting "
                    "until inactivated by stomach acid), "
                    "bicarbonate and phosphate buffers keeping pH "
                    "between 6.35 and 6.85, mucus for lubrication, "
                    "and IgA and lysozyme for antimicrobial action",
      },
      sources={"major_glands": ["S12", "S16"],
               "parotid": ["S11", "S12", "S16"],
               "submandibular": ["S11", "S16"],
               "sublingual": ["S12", "S16"], "saliva": ["S12"]},
      core=["major_glands", "parotid"],
      soft=["submandibular", "sublingual", "saliva"],
      verify=["no BP3D concept: the parotid gland and the "
              "parotid duct described in this record have no "
              "concepts in the BodyParts3D 4.0 release "
              "(probe-verified absences); the release's salivary "
              "census carries only the submandibular and "
              "sublingual glands"],
      note="the submandibular duct is the most "
           "calculus-susceptible of the salivary ducts (about 80% "
           "of salivary calculi, S11)")

# Dentition values (S12 for the clinical counts; the release count
# is counted in this module's inventory). Tier A by construction;
# the checker re-validates.
rec = base("dig.dentition", "Dentition", "dentition", "Oral cavity",
           TOOTH_NAMES,
           note="the clinical permanent count of 32 includes the "
                "four third molars (wisdom teeth); the release "
                "carries no third-molar concepts, so its 28 tooth "
                "records are the clinical 32 minus the third "
                "molars. Deciduous (primary) teeth have no "
                "concepts in the release either")
rec["values"] = {
    "permanent_teeth_total": 32,
    "deciduous_teeth_total": 20,
    "incisors": 8,
    "canines": 4,
    "premolars": 8,
    "molars": 12,
    "third_molars_within_molars": 4,
    "release_permanent_tooth_records": 28,
}
rec["value_definitions"] = {
    "permanent_teeth_total": "permanent (secondary) teeth in the "
                             "complete adult dentition (S12)",
    "deciduous_teeth_total": "deciduous teeth of the first "
                             "dentition, appearing from about 6 "
                             "months and replaced between about 6 "
                             "and 12 years (S12)",
    "incisors": "permanent incisors, for biting (S12)",
    "canines": "permanent canines (cuspids), for tearing (S12)",
    "premolars": "permanent premolars (bicuspids), for mashing "
                 "(S12)",
    "molars": "permanent molars, for crushing, including the "
              "four third molars (S12)",
    "third_molars_within_molars": "the third molars (wisdom "
                                  "teeth) within the molar count; "
                                  "eruption is often delayed and "
                                  "they may remain impacted (S12)",
    "release_permanent_tooth_records": "lateralised permanent-"
                                       "tooth records in this "
                                       "module's inventory (counted "
                                       "from digestive-inventory."
                                       "json); the release models "
                                       "seven tooth types per "
                                       "quadrant, without third "
                                       "molars",
}
rec["sources"] = {"values": ["S12"]}
rec["sourcing_tier"] = "A"
records.append(rec)

# ------------------------------------------------------------------
# Peritoneum
# ------------------------------------------------------------------
typed("dig.peritoneum", "Peritoneum", "region", "Peritoneum",
      ["peritoneum", "visceral peritoneum", "peritoneal sac",
       "mesentery of small intestine", "transverse mesocolon",
       "mesoappendix", "mesentery of large intestine"],
      fields={
          "layers": "A continuous membrane of mesothelium (simple "
                    "squamous epithelium) in two layers. Parietal "
                    "peritoneum: lines the abdominopelvic wall, "
                    "derived from somatic mesoderm, with the same "
                    "somatic nerve supply as the wall it lines — "
                    "sensitive to pressure, pain, laceration and "
                    "temperature, with well-localised pain. "
                    "Visceral peritoneum: covers the viscera, "
                    "derived from splanchnic mesoderm, with the "
                    "autonomic supply of the viscus it covers — "
                    "sensitive only to stretch and chemical "
                    "irritation, with poorly localised pain "
                    "referred to the dermatomes of the supplying "
                    "spinal cord segments",
          "cavity": "The peritoneal cavity is the potential space "
                    "between the parietal and visceral layers, "
                    "normally containing only a thin film of "
                    "peritoneal fluid (water, electrolytes, "
                    "leukocytes and antibodies) that lubricates "
                    "the movement of the viscera (see the "
                    "Peritoneal cavity record)",
          "reflections": "A mesentery is a double layer of "
                         "visceral peritoneum connecting an "
                         "intraperitoneal organ to (usually) the "
                         "posterior abdominal wall, providing a "
                         "pathway for nerves, vessels and "
                         "lymphatics; the small-intestine mesentery "
                         "is simply 'the mesentery', the others "
                         "being named (transverse mesocolon, "
                         "sigmoid mesocolon, mesoappendix). The "
                         "greater omentum is four layers of "
                         "visceral peritoneum descending from the "
                         "greater curvature of the stomach and "
                         "proximal duodenum and folding back to the "
                         "transverse colon ('abdominal policeman', "
                         "with an immunity role). The lesser "
                         "omentum is a double layer from the lesser "
                         "curvature and proximal duodenum to the "
                         "liver: the hepatogastric ligament and "
                         "the hepatoduodenal ligament, whose free "
                         "edge contains the portal triad",
          "organ_relations": "Intraperitoneal organs are enveloped "
                             "by visceral peritoneum (stomach, "
                             "liver and spleen among them). "
                             "Retroperitoneal organs are covered "
                             "only on their anterior surface: "
                             "primarily retroperitoneal (oesophagus, "
                             "rectum, kidneys among them) and "
                             "secondarily retroperitoneal, whose "
                             "mesentery has fused to the posterior "
                             "wall (ascending and descending colon; "
                             "also duodenum except its proximal cap "
                             "and pancreas except its tail)",
      },
      sources={"layers": ["S8"], "cavity": ["S8", "S15"],
               "reflections": ["S8"], "organ_relations": ["S8"]},
      core=["layers", "cavity"],
      soft=["reflections", "organ_relations"],
      verify=["no BP3D concept: the parietal peritoneum has no "
              "separate concept in the BodyParts3D 4.0 release "
              "(probe-verified absence); the release carries the "
              "peritoneum and the visceral peritoneum only",
              "no BP3D concept: the greater and lesser omenta and "
              "the sigmoid mesocolon named in the reflections "
              "field have no concepts in the BodyParts3D 4.0 "
              "release (probe-verified absences)"])

typed("dig.peritoneal-cavity", "Peritoneal cavity", "region",
      "Peritoneum", ["peritoneal sac", "peritoneum"],
      fields={
          "greater_sac": "The greater sac comprises the majority "
                         "of the peritoneal cavity and is divided "
                         "by the transverse mesocolon into a "
                         "supracolic compartment (containing the "
                         "stomach, liver and spleen) and an "
                         "infracolic compartment (containing the "
                         "small intestine and the ascending and "
                         "descending colon, itself divided into "
                         "left and right infracolic spaces by the "
                         "mesentery of the small intestine); the "
                         "two compartments are connected by the "
                         "paracolic gutters",
          "lesser_sac": "The lesser sac (omental bursa) lies "
                        "posterior to the stomach and the lesser "
                        "omentum and allows the stomach to move "
                        "freely against the structures posterior "
                        "and inferior to it; it communicates with "
                        "the greater sac through the epiploic "
                        "foramen (of Winslow), situated posterior "
                        "to the free edge of the lesser omentum "
                        "(the hepatoduodenal ligament)",
          "pelvic_pouches": "In males the most distal part of the "
                            "cavity is the rectovesical pouch and "
                            "the cavity is completely closed. In "
                            "females there are the rectouterine "
                            "pouch (of Douglas) and the "
                            "vesicouterine pouch, and the cavity "
                            "is not completely closed: the uterine "
                            "tubes open into it",
      },
      sources={"greater_sac": ["S15"], "lesser_sac": ["S15"],
               "pelvic_pouches": ["S15"]},
      core=["greater_sac", "lesser_sac"], soft=["pelvic_pouches"],
      verify=["no BP3D concept: the peritoneal cavity as a space, "
              "the lesser sac, the epiploic foramen and the pelvic "
              "pouches named here have no concepts in the "
              "BodyParts3D 4.0 release (probe-verified absences); "
              "the linked geometry is the release's peritoneal sac "
              "and peritoneum records"])

# ------------------------------------------------------------------
doc = {
    "meta": {
        "title": "ANATOMICA digestive system clinical records — "
                 "Milestone 11",
        "generated_by": "tools/build_dig_records.py",
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
      sum(1 for r in records if r["geometry_record_ids"]), "/",
      len(records))
print("inventory records linked:", len(linked), "/",
      len(inv["records"]))
print(f"wrote {OUT_PATH}")
