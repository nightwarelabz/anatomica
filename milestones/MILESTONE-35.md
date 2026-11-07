# Milestone 35 — TA2 name pass over the FMA nerve records; innervation links re-pointed

Two linked pieces of work, both under the standing precision law
(nothing invented; every outcome evidenced or flagged with a
dated, specific reason):

1. the Milestone 23 TA2 name pass, extended over the 286
   FMA-sourced nervous inventory records intaken at Milestone 33
   — the last record set in the Body Model still carrying no TA2
   names;
2. the innervation re-pointing Milestone 33 §4 deferred: the
   muscle module's 45 innervation phrases, which at Milestone 33
   still resolved under Milestone 9's recorded-absence semantics
   (11 phrases to clinical records, 2 to inventory records, by
   full-phrase string equality), are now decomposed into
   named-nerve components and linked to the FMA inventory
   records that now exist — by exact correspondence only.

State: built and verified locally; not yet landed on the repo.

---

## 1. TA2 pass over the 286 FMA nerve records

Method mirrors Milestone 23 exactly, with sibling tools:
`tools/ta2_match_fma.py` (worksheet) →
`tools/ta2_decide_fma.py` (mechanical rules + hand overrides,
each with its reason) → `tools/ta2_pass_fma.py` (applying tool of
record, idempotent — two consecutive runs produce byte-identical
files). One worksheet input is new: each record's FMA class also
contributes its own FMA-listed non-English (Latin) equivalents as
match keys, because TA2 serves several nerves under a Latin term
with no English equivalent at all (e.g. 6499 *nervus
ilioinguinalis*), and the FMA's Latin name is the bridge TA2's
apparatus itself recognises.

### Census

| outcome | records | |
|---|---|---|
| resolved | **194** | preferred 170 · synonym 14 · collective-term 5 · latin-term 4 · latin-synonym 1 |
| ambiguous | **92** | each carrying a dated `ta_name` verify entry with its reason |
| not found | **0** | every FMA class made some contact with TA2's apparatus; the gaps are structural (§5), not absences of contact |

The 92 ambiguous records fall in five families, every one the
Milestone 23 pattern "the candidate's denotation strictly
contains the record's":

| family | records | candidate(s) | why not a resolution |
|---|---|---|---|
| per-level spinal nerves (C1–C8, T1–T12, L1–L5, S1–S5) | 60 | 6143 *nervus spinalis* | TA2 names the spinal nerve only generically and under regional plural headings (6363/6467/6489/6507, under 6362 *nervi spinales*); no per-level term exists in the served table |
| per-level intercostal nerves (1st–11th) | 22 | 6472 *nervus intercostalis* | TA2 names the intercostal nerve only generically (under 6470 *rami anteriores nervorum thoracicorum*); no per-level term |
| per-level lumbar splanchnic nerves (1st–4th) | 8 | 6635 *nervi splanchnici lumbales* | TA2 names them only as the collective set term |
| aortic plexus | 1 | 6658 *plexus aorticus thoracicus*, 6695 *plexus aorticus abdominalis* | TA2 names the plexus only as its two regional parts; the FMA class is the undivided plexus |
| posterior cutaneous nerve (FMA77561) | 1 | 6566 *nervus cutaneus posterior femoris* | name collision, not identity: 6566 is the posterior cutaneous nerve of thigh (a sacral-plexus branch); the FMA class is a branch of the lateral branch of the posterior ramus of a spinal nerve (its IS-A path). TA2 names such branches only regionally and plurally (6369, 6370, 6469) |

### Curation calls worth naming

- **Collective-term resolutions (5 records).** Where the FMA
  class *is* the generic of the set TA2 names only plurally, the
  record resolves to the set term, as at Milestone 23:
  supraclavicular nerve → 6391 *nervi supraclaviculares* (its
  children 6392–6394 are the medial/intermediate/lateral
  subsets); sacral splanchnic nerve → 6636; pelvic splanchnic
  nerve → 6685; celiac ganglion → 6639 *ganglia coeliaca* (the
  plural pair term; no English served).
- **Brachial plexus divisions (6 records).** TA2 names them in
  its own word order — *divisio anterior trunci superioris
  plexus brachialis* (6399) for FMA's "Superior anterior
  division of brachial plexus" — and the parent trunk terms
  (6398/6401/6404) corroborate; resolved, basis *preferred*.
- **The six sided plexus records** (brachial/lumbar/lumbosacral)
  whose class Milestone 33 left unrecorded: their OWL IS-A
  parent classes (FMA5906/5908/5907) carry an `rdfs:label` but
  no `fma:preferred_name`, which is why the importer missed
  them. The classes are identified from the OWL, and per the
  Milestone 23 sidedness rule the sided records take their
  class's un-sided terms (6395/6517/6516).
- **Pharyngeal nerve plexus (2 records).** The mechanical
  candidate was 6223 *nervus pharyngeus* — the pharyngeal
  *nerve*, a different structure. TA2 names the plexus at 6338
  *plexus pharyngeus*; resolved there.
- **Myenteric nerve plexus (1 record).** FMA63252's own
  non-English equivalent list carries both *Plexus myentericus*
  and *Plexus submucosus* (an FMA data quirk; the two enteric
  classes share a parent). Resolved to 6727 on the class's
  preferred Latin equivalent and its English name. The
  submucosal record separately resolves to 6728 (FMA inserts
  "nerve" in that class name; TA2's *plexus submucosus* is the
  same plexus).
- **Filum terminale (1 record)** resolves to 5414 *filum
  terminale internum* by Latin synonym, with the anomaly noted
  on the artifact entry: TA2 splits the filum into internum
  (pial part) and externum (5384, dural part), and the bare name
  "filum terminale" appears in 5414's related terms and in no
  other term's apparatus.
- **Latin-only terms (4 records).** Ilioinguinal nerve (×2) →
  6499, celiac plexus → 6696, esophageal plexus → 6690: TA2
  serves no English equivalent for these terms; the resolutions
  rest on the terms' Latin preferred forms via the FMA classes'
  own Latin equivalents (basis *latin-term*).

### Combined coverage

`tools/ta2_discipline.py` gains `run_fma_inventory` (assertions
F1–F5, the T1–T4 analogues plus a scope assertion that the 133
BP3D-sourced records in the same file carry no `ta_name`/
`ta_code` at all), wired into `tools/nerve_check.py`. The
discipline now spans **647 records**: 361 clinical (Milestone
23: 340 resolved, 9 ambiguous, 12 not found) + 286 inventory
(194 resolved, 92 ambiguous, 0 not found) = **534 resolved, 101
ambiguous, 12 not found**. The pass artifact
`data/ta2-name-pass.json` gains a separate `fma_inventory`
section; its clinical sections are byte-for-byte unchanged in
parsed content (verified against the pre-pass snapshot).

### Diff proof

Against the pre-pass snapshot of `nervous-inventory.json`:
exactly the fields `ta_name`, `ta_code`, `sources` and the
appended `ta_name` verify entries differ on FMA records; every
FMA field (FMAIDs, verbatim name, IS-A `group_path`, source,
geometry, note) is identical, and the 133 BP3D records are
wholly unchanged. Meta gains only the `ta2_pass` block.

---

## 2. Innervation re-pointing

Pipeline: `tools/innervation_match.py` (worksheet) →
`tools/innervation_decide.py` (decisions) →
`tools/innervation_pass.py` (applying tool of record,
idempotent). The full rule text ships in the artifact
`data/innervation-link-pass.json`. In brief: a phrase decomposes
into named-nerve components by stated mechanical rules (`;`
separates; `territory:` prefixes and parentheticals are
qualifiers, except the two contributory patterns — "may also
receive a branch from the X", "with contributions from the X";
"A component of the B" names B; "A and B \<stem\> nerves"
expands to the two nerves). A component links only on exact
correspondence with an FMA-sourced inventory record:

- **R1** the name equals an un-sided record's name;
- **R2** it equals the preferred name of an FMA class with
  records (targets: all the class's records);
- **R3** it equals an FMA-listed synonym of such a class;
- **R4** it is the class name pluralised under the closed
  mapping {nerve→nerves, ramus→rami} (targets: the class's
  records, or its level-specialisation child classes' records —
  "First intercostal nerve" qualifies under "Intercostal
  nerve"; "Subcostal nerve" does not and is never swept in).

A name that restricts a generic class to a region/level subset
(the anterior rami of the *cervical* spinal nerves, of *L1–L3*,
of the *upper/lower thoracic* nerves; the posterior rami of the
*lower cervical* nerves) does **not** link to the generic
class's record: the subset has no record, and the absence
stands with the near-miss named in the reason. No fuzzy
matching anywhere: every bridge is a string equality against a
name one of the two sources itself lists.

### Census: before → after

| | before (M9/M33 semantics) | after (M35) |
|---|---|---|
| phrases resolving to inventory records | 2 of 45 (full-phrase equality) | **29 fully + 2 partially** of 45 |
| phrases resolving to clinical records | 11 of 45 | 11 of 45 (unchanged; gated in C8d) |
| named-nerve components | — (not decomposed) | 53: **37 linked** (R1 ×2, R2 ×29, R3 ×4, R4 ×2), 5 restricted, 11 absent |
| distinct inventory records linked | 2 | **69** |
| muscle records carrying links | — | 115 carry `innervation.nerve_record_ids`; 78 non-empty |

The 2 partially resolved phrases are "medial half: ulnar nerve;
lateral half: anterior interosseous branch of the median nerve"
(ulnar links; the anterior interosseous branch does not) and
"median nerve (lateral two lumbricals); deep branch of the
ulnar nerve (medial two lumbricals)" (median links; the deep
branch does not).

### The 45 phrases

Before = resolution under full-phrase equality (Milestone 9/33).
After = Milestone 35 status and linked-record count. Evidence
names the rule, the FMA class, and the target count per
component; full per-component record ids and the verbatim
reasons for every non-resolution ship in
`data/innervation-link-pass.json`.

| # | phrase | before | after | evidence |
|---|---|---|---|---|
| 1 | accessory nerve | clinical | resolved (2 records) | accessory nerve: R3 → FMA6720 Spinal accessory nerve (2) |
| 2 | anterior interosseous branch of the median nerve | — | unresolved | anterior interosseous branch of median nerve: absent — no intaken record |
| 3 | anterior rami of cervical spinal nerves | — | unresolved | anterior rami of cervical spinal nerves: restricted — no link (generic-class subset) |
| 4 | anterior rami of spinal nerves L1-L3 | — | unresolved | anterior rami of spinal nerves l1-l3: restricted — no link (generic-class subset) |
| 5 | anterior rami of the lower thoracic spinal nerves | — | unresolved | anterior rami of lower thoracic spinal nerves: restricted — no link (generic-class subset) |
| 6 | anterior rami of the upper thoracic spinal nerves | — | unresolved | anterior rami of upper thoracic spinal nerves: restricted — no link (generic-class subset) |
| 7 | axillary nerve | clinical | resolved (2 records) | axillary nerve: R2 → FMA37072 Axillary nerve (2) |
| 8 | deep branch of the radial nerve | — | unresolved | deep branch of radial nerve: absent — no intaken record |
| 9 | deep branch of the ulnar nerve | — | unresolved | deep branch of ulnar nerve: absent — no intaken record |
| 10 | deep fibular (peroneal) nerve | — | resolved (2 records) | deep fibular nerve: R2 → FMA44771 Deep fibular nerve (2) |
| 11 | dorsal scapular nerve | — | unresolved | dorsal scapular nerve: absent — no intaken record |
| 12 | femoral nerve | clinical | resolved (2 records) | femoral nerve: R2 → FMA16486 Femoral nerve (2) |
| 13 | femoral nerve (may also receive a branch from the obturator nerve) | — | resolved (4 records) | obturator nerve: R2 → FMA16487 Obturator nerve (2); femoral nerve: R2 → FMA16486 Femoral nerve (2) |
| 14 | inferior gluteal nerve | clinical | resolved (2 records) | inferior gluteal nerve: R2 → FMA16511 Inferior gluteal nerve (2) |
| 15 | intercostal nerves | — | resolved (22 records) | intercostal nerves: R4 → FMA6028 Intercostal nerve (22) |
| 16 | lateral and medial pectoral nerves | — | resolved (4 records) | lateral pectoral nerve: R2 → FMA65296 Lateral pectoral nerve (2); medial pectoral nerve: R2 → FMA65293 Medial pectoral nerve (2) |
| 17 | long thoracic nerve | — | resolved (2 records) | long thoracic nerve: R2 → FMA65275 Long thoracic nerve (2) |
| 18 | lower subscapular nerve | — | resolved (2 records) | lower subscapular nerve: R3 → FMA65307 Inferior subscapular nerve (2) |
| 19 | medial half: ulnar nerve; lateral half: anterior interosseous branch of the median nerve | — | partial (2 records) | ulnar nerve: R2 → FMA37319 Ulnar nerve (2); anterior interosseous branch of median nerve: absent — no intaken record |
| 20 | medial pectoral nerve | — | resolved (2 records) | medial pectoral nerve: R2 → FMA65293 Medial pectoral nerve (2) |
| 21 | median nerve | clinical | resolved (2 records) | median nerve: R2 → FMA14385 Median nerve (2) |
| 22 | median nerve (lateral two lumbricals); deep branch of the ulnar nerve (medial two lumbricals) | — | partial (2 records) | median nerve: R2 → FMA14385 Median nerve (2); deep branch of ulnar nerve: absent — no intaken record |
| 23 | musculocutaneous nerve | clinical | resolved (2 records) | musculocutaneous nerve: R2 → FMA37064 Musculocutaneous nerve (2) |
| 24 | musculocutaneous nerve, with contributions from the radial nerve | — | resolved (4 records) | radial nerve: R2 → FMA37069 Radial nerve (2); musculocutaneous nerve: R2 → FMA37064 Musculocutaneous nerve (2) |
| 25 | nerve to obturator internus | — | unresolved | nerve to obturator internus: absent — no intaken record |
| 26 | nerve to piriformis | inventory | resolved (1 records) | nerve to piriformis: R1 → record Nerve to piriformis (1) |
| 27 | nerve to quadratus femoris | inventory | resolved (1 records) | nerve to quadratus femoris: R1 → record Nerve to quadratus femoris (1) |
| 28 | nerve to subclavius | — | unresolved | nerve to subclavius: absent — no intaken record |
| 29 | obturator nerve | clinical | resolved (2 records) | obturator nerve: R2 → FMA16487 Obturator nerve (2) |
| 30 | obturator nerve (adductor part); tibial component of the sciatic nerve (hamstring part) | — | resolved (4 records) | obturator nerve: R2 → FMA16487 Obturator nerve (2); sciatic nerve: R2 → FMA19034 Sciatic nerve (2) |
| 31 | phrenic nerve | — | resolved (2 records) | phrenic nerve: R2 → FMA6191 Phrenic nerve (2) |
| 32 | posterior interosseous nerve | — | unresolved | posterior interosseous nerve: absent — no intaken record |
| 33 | posterior rami of the lower cervical spinal nerves | — | unresolved | posterior rami of lower cervical spinal nerves: restricted — no link (generic-class subset) |
| 34 | posterior rami of the spinal nerves | — | resolved (1 records) | posterior rami of spinal nerves: R4 → FMA5983 Posterior ramus of spinal nerve (1) |
| 35 | radial nerve | clinical | resolved (2 records) | radial nerve: R2 → FMA37069 Radial nerve (2) |
| 36 | recurrent branch of the median nerve | — | unresolved | recurrent branch of median nerve: absent — no intaken record |
| 37 | spinal accessory nerve (CN XI) | — | resolved (2 records) | spinal accessory nerve: R2 → FMA6720 Spinal accessory nerve (2) |
| 38 | suboccipital nerve (posterior ramus of C1) | — | unresolved | suboccipital nerve: absent — no intaken record |
| 39 | superficial fibular (peroneal) nerve | — | resolved (2 records) | superficial fibular nerve: R2 → FMA44699 Superficial fibular nerve (2) |
| 40 | superior gluteal nerve | clinical | resolved (2 records) | superior gluteal nerve: R2 → FMA16510 Superior gluteal nerve (2) |
| 41 | suprascapular nerve | — | resolved (2 records) | suprascapular nerve: R2 → FMA37025 Suprascapular nerve (2) |
| 42 | tibial nerve | clinical | resolved (2 records) | tibial nerve: R2 → FMA19035 Tibial nerve (2) |
| 43 | tibial nerve (long head); common fibular nerve (short head) | — | resolved (4 records) | tibial nerve: R2 → FMA19035 Tibial nerve (2); common fibular nerve: R2 → FMA19039 Common fibular nerve (2) |
| 44 | ulnar nerve | clinical | resolved (2 records) | ulnar nerve: R2 → FMA37319 Ulnar nerve (2) |
| 45 | upper and lower subscapular nerves | — | resolved (4 records) | upper subscapular nerve: R3 → FMA65304 Superior subscapular nerve (2); lower subscapular nerve: R3 → FMA65307 Inferior subscapular nerve (2) |

Notes on individual links:

- **Accessory nerve (phrase 1)** links by R3: "Accessory nerve"
  is an FMA-listed synonym of FMA6720 *Spinal accessory nerve* —
  the same class phrase 37 names directly (R2). Both phrases
  link the same two records, and phrase 1 also remains one of
  the 11 clinical resolutions (to *Accessory nerve (CN XI)*).
- **Upper/lower subscapular nerves (phrases 18, 45)** link by
  R3: FMA lists "Upper subscapular nerve" as a synonym of
  FMA65304 *Superior subscapular nerve* and "Lower subscapular
  nerve" of FMA65307 *Inferior subscapular nerve*.
- **Intercostal nerves (phrase 15)** link by R4 to the 22
  records of the eleven level classes — and not to the
  subcostal records (the subcostal nerve is FMA's child of the
  intercostal class too, but its name is not a level
  specialisation of "Intercostal nerve", and it is not an
  intercostal nerve).
- **Posterior rami of the spinal nerves (phrase 34)** link by
  R4 to the single generic-class record; the restricted rami
  phrases (3–6, 33) do not link, per the subset rule above.

### Checker semantics

The recorded-absence semantics are gone where they are now
false. `tools/nerve_check.py` C8 is no longer a report: C8a
gates that every muscle record's shipped `nerve_record_ids`
equals an **independent re-derivation** (the checker re-parses
the OWL, re-implements decomposition and R1–R4 from the
artifact's stated rules, and shares no code with the pass
tools); C8b gates the artifact's accounting against that
re-derivation; C8c gates that every restricted/absent component
carries a specific reason; C8d gates that the 11 clinical
resolutions are unchanged. `tools/fma_nerve_check.py` C2 now
prints this same census from the artifact instead of running a
second, naive count. `tools/muscle_check.py` is unchanged (its
C3 counts phrase components against the BP3D tables, where the
statement "peripheral nerves are not concepts in BodyParts3D
4.0" remains literally true).

### Diff proof

Against the pre-pass snapshot of `muscles.json`: no field of
any record differs except the added
`innervation.nerve_record_ids`; meta gains only the
`innervation_link_pass` block. The clinical nervous tranche
(`data/nervous/nervous.json`) is written by no Milestone 35
tool and its checker assertions (C1–C7, TA2 discipline) pass
unchanged. Note: `tools/build_muscle_records.py` predates the
link pass and would drop `nerve_record_ids` if re-run;
`innervation_pass.py` is the applying tool of record for the
field (the same relationship `ta2_pass.py` has to the tranche
builders).

---

## 3. Checker matrix (all run after both passes)

- Tranche checkers — cardiovascular, digestive, endocrine,
  integumentary, lymphatic, muscular, nervous, reproductive,
  respiratory, urinary, skeletal: **all pass** (each includes
  its TA2 discipline assertions; the nervous checker also runs
  the new F1–F5 inventory discipline and C8a–C8d).
- `fma_nerve_check.py`: **all checks pass**.
- `assembly_check_all.py`: **ALL GATED CHECKS PASS**.
- `node tools/verify_web.js`: **ALL CHECKS PASS**.
- `theatre_check.py`: **245 checks, 0 failures**.
- `case_check.py`: **5,145 passed, 0 failed**.
- Physiology `cargo test --release`: **25 passed, 0 failed**.
- Native `anatomica verify`: **99/99 data assertions PASS**;
  the GPU render stage cannot initialise on this machine (no
  wgpu adapter) — the standing disclosed limitation, unchanged.
- Geometry packs and served data: the 26 pre-pass hashes
  (every `web/data/*.bin`/`*.gz`, `delivery.json`,
  `records.json`, `nervous-geometry.json`,
  `nervous-assembled.json`) are **byte-identical** after both
  passes. (`web/data/records.json` carries no `ta_name` field,
  so the TA2 pass does not move it; the link field lives in the
  muscle module data.)

---

## 4. Honest limits

**TA2's own nerve coverage is the binding constraint.** The
served TA2 2.07 table names the peripheral apparatus generously
for named nerves but structurally for the segmental ones:

- no per-level spinal nerve terms at all (generic 6143 and
  regional plural headings only) — 60 records cannot resolve;
- no per-level intercostal terms (generic 6472 only) — 22
  records;
- lumbar splanchnics collective-only (6635) — 8 records;
- the aortic plexus split into thoracic/abdominal parts with
  no undivided term;
- several terms served Latin-only, with no English equivalent
  (6499, 6696, 6690, 6639) — resolutions there rest on the
  Latin apparatus alone;
- the posterior cutaneous collision: TA2's only "posterior
  cutaneous" nerve term (6566) names a different structure
  than the FMA class that bears the name.

An ambiguous outcome here is a property of the terminology,
recorded on the record — not a gap in the pass. 0 records are
"not found": every FMA class touches TA2's apparatus somewhere,
which is itself a finding about how the two terminologies
overlap.

**Sixteen components still have no record to link.** Five are
region/level subsets of the generic rami classes (they would
need per-level ramus records, which neither source currently
supplies as records). The other eleven are plain absences:

- six FMA classes that exist in FMA 5.1.0 but were outside
  Milestone 33's frozen intake list cover eight of them —
  deep branch of the ulnar nerve (FMA44877, two components),
  dorsal scapular nerve (FMA65279), nerve to obturator
  internus (FMA78711), posterior interosseous nerve
  (FMA77559; the "deep branch of the radial nerve" is its
  listed synonym, so phrases 8 and 32 are the same absence),
  nerve to subclavius (a listed synonym of FMA65280
  *Subclavian nerve*), suboccipital nerve (FMA7054);
- the anterior interosseous branch (two components) matches
  neither the preferred name nor any listed synonym of its
  evidently intended class (FMA44822 *Anterior interosseous
  nerve*) — an exact-correspondence link is not available even
  if the class is intaken, without a curation ruling on the
  name;
- the recurrent branch of the median nerve has no FMA class
  under that name at all (preferred-name and synonym probes
  over the full OWL are empty).

**Geometry is untouched by this milestone.** The 286 FMA
records remain geometry-absent; the Milestone 34 audit's
blockers on nerve geometry (per-object provenance separability
in Z-Anatomy and the absence of a derived registration
transform) stand exactly as recorded there.

---

## 5. Next steps

1. A small FMA intake of the six existing-but-unintaken classes
   named in §4 (deep branch of ulnar, dorsal scapular, nerve
   to obturator internus, posterior interosseous, subclavian,
   suboccipital) would resolve eight more components and leave
   only the rami subsets, the anterior interosseous name
   question, and the recurrent branch unlinked. It is an
   intake decision, not a matching change.
2. The anterior interosseous name correspondence
   ("branch of the median nerve" vs FMA44822's preferred name)
   needs an explicit curation ruling before any link; the
   evidence is recorded in the artifact either way.
3. The remaining Body Model TA2 frontier is now zero record
   sets: every clinical tranche and the full inventory carry
   TA2 names or dated flags. Attention returns to the standing
   dataset blockers (lymphatics depth, thyroid/parathyroids,
   kidney/urinary interior, female reproductive tract, skin
   layers) and to nerve geometry, which remains blocked on the
   Milestone 34 findings.

---

## Batch contents

New files:

- `MILESTONE-35.md` (this document)
- `data/innervation-link-pass.json` (re-pointing artifact:
  rules, before/after census, all 45 phrases with per-component
  evidence and reasons)
- `tools/ta2_match_fma.py`, `tools/ta2_decide_fma.py`,
  `tools/ta2_pass_fma.py` (TA2-over-FMA pipeline)
- `tools/innervation_match.py`, `tools/innervation_decide.py`,
  `tools/innervation_pass.py` (innervation pipeline)

Modified files:

- `data/nervous/nervous-inventory.json` — `ta_name`/`ta_code`/
  `sources` or dated `ta_name` flags on the 286 FMA records;
  meta `ta2_pass` block. Nothing else.
- `data/ta2-name-pass.json` — `fma_inventory` section added;
  meta extension note. Clinical sections unchanged.
- `data/muscular/muscles.json` — `innervation.nerve_record_ids`
  on the 115 records carrying a nerve phrase; meta
  `innervation_link_pass` block. Nothing else.
- `tools/ta2_discipline.py` — `run_fma_inventory` added (F1–F5).
- `tools/nerve_check.py` — C8 rewritten as gated assertions
  C8a–C8d with an independent re-derivation; TA2 discipline
  call for the FMA inventory added; docstring updated.
- `tools/fma_nerve_check.py` — C2 report now prints the
  Milestone 35 census from the artifact; docstring updated.
