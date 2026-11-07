# ANATOMICA — Milestone 38

**FMA concept intake #4 (final): the integumentary layers and
appendages, and the male reproductive remainder — plus the
oculomotor name-provenance correction. This milestone closes
the FMA concept-intake line (Milestones 33–38).**

Local only. Nothing uploaded.

Tools: `tools/fma_oculomotor_correct.py` (the correction),
`tools/fma_integ_male_map.py` (builder),
`tools/fma_integ_male_check.py` (independent checker),
`tools/ta2_match_fma38.py` / `tools/ta2_decide_fma38.py` /
`tools/ta2_pass_fma38.py` (the TA2 pass). Accounting artifact:
`data/fma-intake-38.json` (the correction's evidence in
§oculomotor_correction, the intake accounting in §systems).

## 1. The oculomotor correction, and the whole-intake sweep

Milestone 37 §5 recorded, and deliberately did not correct,
an adjacent observation: the two oculomotor records
(`nerve.left-oculomotor-nerve`, `nerve.right-oculomotor-nerve`)
carry the same naive-parser artifact the plexus correction
had just removed from six records — `class_concept_id` null
and one null group-path slot, where their parent class
FMA50864 *does* carry a preferred name.

The correction applies the Milestone 37 pattern exactly.
Under both the depth-aware regex parse and an independent
ElementTree XML parse, FMA50864 "Oculomotor nerve" carries
`fma:preferred_name` identical to its `rdfs:label`, as do the
sided classes (FMA50879 right, FMA50880 left — the FMA
numbers the right class first). Both records now carry
`class_concept_id` **FMA50864** and the preferred name in the
single null path slot; every other field is untouched, and
the records' identity — names, concept FMAIDs, TA2 outcome
(6187 *nervus oculomotorius*) — is re-verified unchanged
(checker O1–O3; the evidence is written into
`data/fma-intake-38.json` §oculomotor_correction).

**The sweep.** The corrector first enumerated every
FMA-sourced record in the frozen pre-Milestone-38 snapshots
of all eleven inventories — all **555** records intaken at
Milestones 33/36/37 — for a null `class_concept_id` or a null
group-path entry anywhere. Exactly **2** carriers exist: the
oculomotor pair. (The M36/M37 inventories hold none by
construction — those builders filled the class id from the
frozen target table — and the sweep proves it rather than
assuming it.) After the correction, the same enumeration
over the current inventories finds **zero** survivors across
all 684 FMA records (checker S1, which re-enumerates both
states itself). The Milestone 37 plexus corrections are
re-verified intact (checker O4), and `fma_uri_repro_check`'s
P4 — which at Milestone 37 asserted the oculomotor pair as
the only survivors — is updated to assert the corrected
state, as Milestone 37's own text anticipated a ruling.

## 2. What was absent

**Integumentary (Milestone 15).** The module carried 6 BP3D
records — the skin shell and the hair class with its regional
kinds — and its census had proved the rest absent from BP3D:
no epidermis, dermis or hypodermis as concepts; no layer of
any of them; no sweat or sebaceous gland; no follicle
apparatus; no nail apparatus; no mammary structures (the
clinical mammary record is deliberately geometry-less,
Milestone 15's ownership adjudication). 22 absence probes
were re-run for this intake against the FMA's preferred
names; all returned zero (`data/fma-intake-38.json`
§systems.integumentary.absence_probes) — the structures are
absent from the Body Model, present in the FMA.

**Male reproductive remainder (Milestones 14/37).** After
Milestone 37 the reproductive inventory held the 13 BP3D
records and the 57-record female intake; the male side still
lacked everything below its organ wholes: the deferent
duct's course segments and parts, the epididymis's parts and
duct, the testis's interior (tubules, rete, septa, tunics),
the prostate's zones and parts, the spermatic cord and its
fasciae, the scrotal wall, the penis's parts, the bulbourethral
glands. 15 absence probes re-run; all zero (§systems.
reproductive.absence_probes).

These were the last two concept gaps on the standing blocker
list closable from the source already cleared for intake
(FMA 5.1.0, CC BY 4.0, hash-pinned at Milestone 33).

## 3. Resolution discipline (as Milestones 33/36/37)

Absence census → frozen target list → mechanical resolution
against `fma.owl` under the **depth-aware** parser → records
carrying FMAID, the verbatim preferred name, the IS-A group
path to *Anatomical entity*, source `fma-5.1.0`, geometry
`absent` and dated verify flags → an independent checker that
re-parses the OWL as XML and shares no code with the builder
→ the TA2 pass through the parameterized pipeline → a
per-target accounting file.

Sided targets resolve to a left/right record pair only when
**both** sided classes exist and each is an IS-A child of the
un-sided class (parent-verified mechanically). One parsing
note: the OWL writes apostrophes as XML entities
(`Meissner&apos;s corpuscle`); the builder entity-decodes
names so the record carries the name the XML checker reads
("Meissner's corpuscle").

**Integumentary: 53 targets frozen; 50 resolved, 3 excluded,
0 not in FMA → +53 records (6 → 59).** The skin layers whole
and divided (epidermis, dermis, hypodermis, the five
epidermal strata, the two dermal layers, superficial fascia),
skin of scalp, the five epidermal cell classes, the two
cutaneous corpuscles, the hair follicle apparatus (12
classes), the cutaneous glands (sebaceous; sweat generic,
eccrine, apocrine), the nail apparatus (11 classes), and the
mammary structures (gland, nipple, areola — all sided — and
the lactiferous duct).

**Reproductive (male): 54 targets frozen; 48 resolved,
5 excluded, 1 not in FMA → +76 records (70 → 146).** The
deferent duct (the FMA's preferred name for the ductus
deferens — "ductus deferens" and "vas deferens" exist only
as its synonyms) with its proper part, ampulla and four
course segments; the ejaculatory duct; the epididymal duct,
efferent ductules and head/body/tail; the testis interior
(seminiferous and straight tubules, rete, lobules, septa,
mediastinum, both tunics and the vaginalis layers); the
prostate's apex, base, lobe and three zones plus its
anterior fibromuscular stroma; the seminal vesicle's duct;
the spermatic cord with its three fasciae, cremaster and
dartos; the scrotum; the pampiniform plexus; and the penis
with root, body, bulb, fascia, prepuce, frenulum, corona and
neck of glans.

**Exclusions (mechanical, checker-verified B2).** Eight
frozen targets named classes already owned by BP3D records
and were excluded rather than duplicated: Skin FMA7163,
Hair FMA53667, Eyebrow FMA54237 (integumentary); Testis
FMA7210/7211/7212, Epididymis FMA18255/18256/18257, Seminal
vesicle FMA19386/19387/19388, Prostate FMA9600, Glans penis
FMA18247 (reproductive). Boundary calls are recorded on the
records that carry them: the cremasteric and dartos muscles
sit in this inventory as spermatic-cord and scrotal-wall
contents (neither is in the muscular inventory — verified
before the intake), and the pampiniform plexus as a cord
content (not in the cardiovascular inventory — verified).

**Not in FMA (1): the bulbourethral gland.** The FMA carries
no class for the gland itself — only its duct classes
(FMA20091 and sided children). The duct alone is not
intaken (the Milestone 37 paraurethral pattern: a duct
without its gland is not the structure the census named),
and the gland is recorded concept-blocked inside
...[truncated 11049 chars]