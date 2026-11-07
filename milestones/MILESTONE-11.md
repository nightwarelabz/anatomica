# Milestone 11 — Digestive system module v1

Status: built and checked locally. Not uploaded; presented for
approval as a unit, as with Milestones 2–10.

Method follows Milestones 4, 5, 9 and 10: inventory from the release
tables → geometry mapping by exact lookup and streamed counting → a
clinical tranche whose values come only from sources consulted
during the build, cited per field → an independent checker that
shares no code with the builders.

## Deliverables

| File | Content |
|---|---|
| `tools/dig_map.py` | Census + geometry builder (rerunnable) |
| `data/digestive/digestive-inventory.json` | Concept census and the 93 derived records |
| `data/digestive/digestive-geometry.json` | Per-record mesh lists with measured vertex/face counts and bounding boxes |
| `tools/build_dig_records.py` | Clinical tranche builder (sources S1–S16 in its header) |
| `data/digestive/digestive.json` | 31 clinical records |
| `tools/dig_check.py` | Independent checker (fresh census, re-measured geometry incl. bounding boxes, probe re-runs, disposition accounting, cross-module resolution, citation/flag/tier validation) |

## Inventory (from the BodyParts3D 4.0 tables)

Universe: **220 concepts** — 104 named in the IS-A tables, 142 in
the PART-OF tables, 26 in both. There is no IS-A digestive tree at
all: the IS-A table files each digestive organ as a leaf under
generic organ classes, so the census hangs on the PART-OF root
FMA7152 "alimentary system", completed by three IS-A-only lines
(salivary glands, teeth, hepatovenous segments and biliary ducts)
and two sweep admissions. Counting convention (stated in the
inventory file): one record per lateralised instance where the
tables lateralise; one record for an un-sided class modelled
jointly; the nine subtree organs are records keyed on their PART-OF
concepts; canal divisions, liver apparatus, biliary trees, mouth
parts and peritoneal structures are records keyed on PART-OF
concepts; the extrahepatic ducts, salivary gland instances,
hepatovenous segment ix, the mesentery of the large intestine and
the 28 teeth are records keyed on IS-A concepts.

| Source set | Concepts |
|---|---|
| PART-OF alimentary system (root FMA7152) | 141 |
| — of which the gastrointestinal tract subtree (root FMA71132) | 121 |
| IS-A tooth line (root FMA12516) | 56 |
| IS-A biliary tree line (root FMA71856) | 15 |
| IS-A hepatovenous segment line (root FMA15737) | 12 |
| IS-A salivary gland line (root FMA9597) | 8 |
| IS-A bile duct line (root FMA9706) | 6 |
| IS-A gingiva line (root FMA59762) | 3 |
| IS-A segment of liver (root FMA14495) | 2 |
| Sweep: external anal sphincter (FMA21930, both tables; muscular cross-reference) | 1 |
| Sweep: mesentery of large intestine (FMA14645, IS-A only) | 1 |

Cross-references censused inside the universe, by design not
digestive records: **cardiovascular 40** (the portal-vein branches,
segmental hepatic arteries and hepatic-vein tributaries inside the
liver subtree; measured by the checker, **30 of the 40 resolve to
concepts in the cardiovascular module's census — the 10 unresolved
are the intrahepatic branch concepts**: the segmental hepatic
arteries, the lobar portal-vein branches and the right/left hepatic
artery as filed in this subtree, which the cardiovascular census
does not carry), **muscular 6** (levator and tensor veli palatini
L/R, uvular muscle, external anal sphincter — the sphincter record
itself is `muscle.external-anal-sphincter` in the muscular module,
referenced, never duplicated), **skeletal 2** (upper and lower jaw
— the skeletal records `maxilla_left`, `maxilla_right`, `mandible`).

A name sweep over both tables for digestive terms outside the
universe rejected **122 names** — the named gut and liver arteries
and veins (cardiovascular neighbours, including the marginal artery
of colon and the pancreaticoduodenal arcades), the tongue and
palate muscle classes, digastric/gastrocnemius/puborectalis hits,
the spleen and splenic vessels (lymphatic/cardiovascular), and
generic region classes ("segment of colon", "zone of ileum",
"region of peritoneum") — none admitted.

**Records: 93** — 9 partof-organ, 45 partof-concept, 39
whole-concept:

- Organs 9: mouth, tongue, esophagus, stomach, small intestine,
  large intestine, liver, gallbladder, pancreas.
- Alimentary canal divisions 10: duodenum, jejunum, ileum, cecum,
  appendix, ascending/transverse/descending colon, rectum,
  ileocecal junction; plus the three taeniae coli.
- Liver morphological apparatus 9: right/left/caudate lobes, right/
  left hemilivers, four sectors.
- Hepatovenous segments 8: ii–viii keyed on PART-OF concepts,
  segment ix keyed on its IS-A-only concept (see the numbering
  anomaly in the gap analysis).
- Biliary apparatus 11: five tree records (biliary, hepatic,
  intrahepatic, right and left hepatic biliary trees), the right/
  left/common hepatic ducts, cystic duct, left duct of caudate
  lobe, and the pancreatic duct (whose record also carries the
  pancreatic duct tree concept).
- Mouth parts 4: soft palate, uvula, gingiva of upper and lower
  jaw.
- Salivary glands 4: submandibular L/R and sublingual L/R, keyed on
  their instances with the side-stripped classes carried.
- Teeth 28: the lateralised permanent-tooth instances (seven tooth
  types per quadrant), keyed on the instances with their classes
  carried.
- Peritoneum and mesenteries 7: peritoneum, visceral peritoneum,
  peritoneal sac, mesentery of small intestine, mesentery of large
  intestine, transverse mesocolon, mesoappendix.

Disposition accounting for the 220 universe concepts, verified
exactly by the checker: **94 concepts carried by the 93 records**
(the pancreatic duct record carries two concepts), **16
class-carried** (the submandibular/sublingual classes and the 14
per-type tooth classes), **48 cross-references** (40 cardiovascular
+ 6 muscular + 2 skeletal), **34 grouping classes** (system and
tract roots, the tooth/gland/liver/biliary intermediate classes and
the three in-vivo liver region classes), **28 subtree internals**
(6 zonal parts of jejunum/ileum, 5 wall concepts, pancreatic
parenchyma, 3 mouth region parts, 13 named biliary tributaries).
Nothing in the universe is unaccounted.

## Geometry

Coverage **93/93 records** in both tables combined. The independent
checker re-measured all **434 mesh entries** by streaming — vertex
counts, face counts AND bounding boxes — and verified the FJ-file
attribution of every record against the element-parts tables:
**0 mismatches**.

Distinct mesh files: IS-A 69 files (225,911 vertices / 305,652
faces); PART-OF 147 files (280,503 vertices / 395,980 faces).

## TotalSegmentator overlap

Of the 104 TotalSegmentator v1 labels, **exactly 8 are digestive**:
`esophagus`, `stomach`, `duodenum`, `small_bowel`, `colon`,
`liver`, `gallbladder`, `pancreas`, each present in all 1,204
subjects of the M3 census. All eight map to inventory records. The
`spleen` label is filed under lymphatic in that census and is a
cross-reference here, not a digestive label. TS adds nothing below
the organ level: `small_bowel` is one undivided label for jejunum
and ileum together, `colon` is one undivided label (it cannot
resolve the sigmoid gap below), and there is no segment, duct,
gland, tooth or peritoneum label in v1.

## Clinical tranche

**31 records, Tier A 30 / B 1 / C 0** — every field sourced from
the 16 sources consulted during the build (TeachMeAnatomy articles
on the oesophagus, stomach, small intestine, colon, liver,
gallbladder, pancreas, peritoneum, peritoneal cavity, rectum, anal
canal and the submandibular/parotid glands; OpenStax A&P 2e §23.3
for the mouth, tongue, saliva and dentition; Sibulesky's "Normal
liver anatomy" (PMC6448666) and Last's Anatomy for the Couinaud
segments; anatomy.app's salivary overview), cited per field in each
record's `sources` map. The single Tier B is Segment I: the
consulted resection table (S13) names no segment-I resection, so
its `surgical_note` is null and flagged rather than invented. TA
names were not given by the consulted sources and are null +
verify-flagged on all records, as in Milestones 4/5/9/10. The
hepatic and gut vessels are cardiovascular module records (the nine
cited clinical record ids — `artery.hepatic-artery-proper`,
`vein.hepatic-portal-vein`, etc. — are verified by the checker to
resolve in that module) and are cited in notes, never duplicated.

| Group | Records |
|---|---|
| Alimentary canal pathway (mouth → anal canal, orders 1–13) | 13 |
| Organs (stomach structure, liver, gallbladder, pancreas) | 4 |
| Liver segments (Couinaud I–VIII) | 8 |
| Biliary system (the biliary tree pathway) | 1 |
| Oral cavity (structure, salivary glands, dentition) | 3 |
| Peritoneum (peritoneum, peritoneal cavity) | 2 |

Geometry linkage: **29 of 31** clinical records link at least one
inventory record; **77 of 93** inventory records are linked from
the clinical tranche. The 16 unlinked inventory records are the
small/large intestine organ concepts (their divisions carry the
pathway links), the liver lobes/hemilivers/sectors (morphological
records; the clinical segment records key on the segment concepts
and the caudate lobe), the three taeniae, the pancreatic duct and
caudate-duct records, and hepatovenous segment ix (below). Exactly
two clinical records link nothing — the sigmoid colon and the anal
canal — and both carry the recorded absence in their verify lists,
checker-gated.

Notable items:

- **Couinaud segments.** Eight segment records (S13/S14): each an
  independent functional segment with its own portal pedicle and
  hepatic venous outflow; sectors II/III left lateral, IV left
  medial (the quadrate lobe on the visceral surface), V/VIII right
  anterior, VI/VII right posterior, I the caudate — autonomous,
  draining directly to the IVC. Segment I links the inventory's
  caudate lobe record; II–VIII link the hepatovenous segment
  records one-to-one (checker-verified).
- **The segment-ix anomaly.** The release names its liver segments
  ii–ix. Segment i has no concept (Couinaud I corresponds to the
  caudate lobe, which the release carries as a lobe), and segment
  ix has **no Couinaud counterpart** — the classification has
  exactly eight segments. Segment ix is an inventory record (the
  release carries it, with geometry) and deliberately has **no
  clinical segment record**; the checker gates that no clinical
  record links it. It is flagged, not force-mapped.
- **The dentition discrepancy, stated in the record.** The clinical
  permanent dentition is 32 (8 incisors / 4 canines / 8 premolars /
  12 molars, S12); the release carries 28 tooth records. The
  difference is exactly the four third molars (wisdom teeth), which
  have no concepts — the checker re-validates the arithmetic
  (8+4+8+12 = 32; 32 − 28 = 4) against the inventory count.
- **Canal landmarks as sourced.** Sphincters (upper oesophageal —
  anatomical; lower oesophageal and pyloric; the anal sphincters
  and anorectal ring; the sphincter of Oddi in the biliary record),
  the four oesophageal constrictions, the duodenal parts and the
  major papilla, the colic flexures, the ileocecal valve, the
  rectal flexures and the pectinate line are all carried from the
  consulted sources — several of them (ileocecal valve, papilla,
  pectinate line) have no BP3D concepts and are text on records
  whose geometry is the parent structure or a recorded absence.

## Checker results (`tools/dig_check.py`, exit 0)

**84 hard checks PASS, 0 FAIL.** Highlights: the full concept
universe re-derived from the six tables set-by-set (220 concepts,
all 12 set counts exact); cross-reference census re-derived
(40/6/2); rejected-sweep census re-derived (122 names); record
concept sets disjoint and inside the universe; disposition
accounting partitions the universe exactly (94 + 16 + 40 + 6 + 2 +
34 + 28 = 220, re-derived on the IS-A class graph with the
documented grouping constants); cross-module pointers resolve
(muscular `muscle.external-anal-sphincter`, skeletal
`maxilla_left`/`maxilla_right`/`mandible`, the nine cited
cardiovascular clinical records) and cardiovascular concept
resolution measured exactly (30/40, the 10 intrahepatic branches
named); geometry fully re-measured (434 entries, counts + bounding
boxes, FJ attribution exact, 0 mismatches); TS census parsed
independently (104 labels, 8 digestive, all mapped); absence
probes re-run (below); clinical citation/flag/tier discipline
re-validated for all 31 records, including pathway order 1–13, the
eight-segment Couinaud list with per-segment link and sector
checks, the segment-ix non-linking gate, the biliary absence
flags, and the dentition arithmetic.

## Gap analysis — quantified, recorded, never filled

**87 absence probes** were run as occurrence counts over all six
release tables; **69 returned zero hits** (a 70th name,
"hepatovenous segment i", occurs only as a substring of ii/iii and
has no exact concept). The checker re-ran the identical probe set
and reproduced the identical absent list. Probe-verified absences,
by consequence:

- **The canal's last two stations do not exist in this release.**
  No sigmoid colon and no sigmoid mesocolon; no anal canal, no
  anus, no dentate/pectinate line. The clinical sigmoid and anal
  canal records are sourced text with recorded absences where
  their geometry would be. TS cannot fill this: its colon label is
  one undivided label.
- **The biliary tree's final common channel is unnamed.** The tree
  itself is richly present (five tree records, 13 named
  tributaries, the hepatic and cystic ducts), but there is **no
  common bile duct concept** — the release's extrahepatic tree runs
  from the common hepatic duct and the cystic duct with the channel
  below their junction unnamed. Also absent: the hepatopancreatic
  ampulla, the major and minor duodenal papillae, the sphincter of
  the ampulla and the accessory pancreatic duct. The biliary
  clinical record carries these absences in its verify list; the
  surgically load-bearing last centimetre of the tree is text-only.
- **No organ parts for stomach or pancreas.** No cardia, fundus,
  body or pyloric part of stomach, no greater/lesser curvature, no
  pylorus or pyloric sphincter concept; no head, neck, body, tail
  or uncinate process of pancreas. The divisions in the clinical
  records are sourced text on whole-organ geometry (the pancreas
  record carries the absence explicitly in its verify list).
- **Liver surface anatomy is absent while its segments exist.**
  No quadrate lobe concept (clinical segment IV is recognised on
  the visceral surface as the quadrate lobe — text only), no porta
  hepatis, no bare area, no falciform or coronary ligament, no
  ligamentum teres or venosum. Lobes, hemilivers, sectors and
  segments all have geometry; the surface landmarks a surgeon
  orients by do not.
- **The parotid gland does not exist in this release.** The
  salivary census carries the submandibular and sublingual glands
  only: no parotid gland, no parotid duct, no submandibular or
  sublingual duct concepts, no minor salivary glands. The salivary
  clinical record describes the parotid from consulted sources and
  carries its absence in the verify list (the Milestone 10 pleura
  pattern).
- **The peritoneum is thinner than its clinical description.** No
  parietal peritoneum concept (peritoneum and visceral peritoneum
  only), no peritoneal cavity as a space, no lesser sac/omental
  bursa, no greater or lesser omentum, no epiploic (omental)
  foramen, no hepatorenal recess or pelvic pouches, no root of
  mesentery, no sigmoid mesocolon. The clinical peritoneum and
  peritoneal-cavity records are sourced text linked to the seven
  peritoneal records the release does carry.
- **The dentition is incomplete.** 28 tooth records against the
  clinical 32: no third molars, and no primary/deciduous dentition
  at all; no dental pulp, enamel or dentine concepts.
- **Segment numbering anomaly (recorded, not repaired).** The
  release numbers its hepatovenous segments ii–ix: segment i is
  absent as a named concept (its Couinaud territory, the caudate
  lobe, is present as a lobe record), and segment ix is present
  with no clinical counterpart. Any downstream consumer must map
  Couinaud I → caudate lobe record and must not invent a Couinaud
  IX.
- **Canal interior landmarks.** No ileocecal valve (the junction
  exists), no haustra or appendices epiploicae as concepts (the
  taeniae exist), no hepatic/splenic (colic) flexures, no circular
  folds, villi or duodenal glands. All are named in the clinical
  text; none has geometry.
- **Mouth gaps.** No hard palate and no palatine tonsil concepts
  (the palate bones are skeletal records; the soft palate and
  uvula are records here).
- **Cross-module census gap.** 10 of the 40 vessel concepts inside
  the digestive subtree (segmental hepatic arteries, lobar
  portal-vein branches, right/left hepatic artery as filed here)
  are not carried by the cardiovascular module's census at all —
  measured and named by the checker, so the boundary between the
  two modules is exact rather than assumed.
- **TS ceiling:** TotalSegmentator v1 stops at the organs (8
  digestive labels of 104), so CT-derived geometry cannot fill any
  of the above either.

Cross-module continuities confirmed while building: the external
anal sphincter is the muscular module's record and the palate
muscles are muscular cross-references (referenced, not duplicated);
the jaws are the skeletal module's records; the gut and liver
vessels are the cardiovascular module's records (cited per field
and in notes); the spleen belongs to the lymphatic census. The
digestive module invents no record for another module's structure.

## Next steps

1. A TA2 pass for `ta_name` across the digestive records (owed
   jointly with the muscular/nervous/respiratory TA debt since
   Milestone 4).
2. The dataset-shaped gaps — common bile duct and ampulla/papilla,
   sigmoid colon, anal canal, parotid gland, third molars, stomach
   and pancreas parts, omenta — need a source beyond BP3D 4.0 +
   TS v1: same class of blocker as Milestone 9's peripheral-nerve
   gap and Milestone 10's pleura gap. Recorded, not filled.
3. Cardiovascular census extension candidate: the 10 intrahepatic
   branch concepts measured above are the exact, bounded list a
   future CV tranche would need to absorb for the two modules'
   boundary to close.
4. Theatre follow-on: the eight Couinaud segment records with their
   one-to-one inventory links, and the biliary tree pathway with
   its flagged missing final channel, are the unit list a hepatic
   or biliary procedure would be authored against — the ampulla
   gap must be closed (step 2) before a sphincterotomy-class
   procedure can be staged honestly.
5. Physiology follow-on: the liver's dual-supply split (≈25%
   arterial / ≈75% portal, S5) and the portal formation are the
   natural parameters where the Milestone 8 engine's hepatic
   compartment would attach.
6. Remaining systems queue per the Master Plan: urinary,
   lymphatic, endocrine, reproductive, integumentary.
