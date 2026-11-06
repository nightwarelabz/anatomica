# Gap analysis — the 7 NOT-FOUND skeletal records (Milestone 3)

Scope: malleus ×2, incus ×2, stapes ×2 (the auditory ossicles) and the
coccyx — the records Milestone 2 proved absent from BodyParts3D 4.0
(stems occur 0 times in all six BP3D release tables). This analysis
checks the TotalSegmentator label set and other candidate sources.
Every coverage claim below was verified against a primary artifact
(the dataset archive index, the publisher's metadata, or the source's
own files) on 2026-11-06. Anything not verified is labelled a lead,
not a source. No geometry is proposed from imagination, and no license
is assumed.

## Sources checked

1. **TotalSegmentator dataset v1.0** (Zenodo record 6802614, CC BY 4.0).
   Label census derived from the archive's own central directory
   (128,830 entries, all 1,204 subjects) by `tools/ts_census.py`: 104
   distinct labels, each present in all 1,204 subjects, in exact
   agreement with the `total_v1` map published in the TotalSegmentator
   code package. **No ossicle label and no coccyx label exists.** The
   nearest labels are `sacrum` (a single class) and — for the ear
   region — nothing at all.
2. **TotalSegmentator v2 label set** (117 labels, `total` map in the
   same package file, fetched 2026-11-06). V2 adds `sternum`, `skull`,
   `costal_cartilages`, `vertebrae_S1`, vessels and others — enumerated
   in full during the check. **No ossicle label and no coccyx label
   exists in v2 either** (string search for ossicle/malleus/incus/
   stapes/coccyx/cochlea over the package's published class maps:
   no hits).
3. **HaN-Seg** (head-and-neck OAR dataset, Zenodo record 7442914) —
   the obvious candidate for ear structures, since it segments the
   cochlea. Its archive index (1,391 entries) was listed: 30 OAR masks
   per case (A_Carotid, Arytenoid, Bone_Mandible, Brainstem,
   BuccalMucosa, Cavity_Oral, Cochlea_L/R, Cricopharyngeus,
   Esophagus_S, Eye_A/P L/R, Glnd_Lacrimal, Glnd_Submand,
   Glnd_Thyroid, Glottis, Larynx_SG, Lips, OpticChiasm, OpticNrv,
   Parotid, Pituitary, SpinalCord). **No ossicle masks.** Independently,
   its license is **CC BY-NC-ND 4.0** (Zenodo metadata) — non-commercial
   and no-derivatives — which fails the design-03 license gate on its
   own. Excluded on both coverage and license grounds.
4. **Zenodo-wide searches** ("ossicles segmentation", "middle ear
   ossicles dataset", 2026-11-06): no human ossicle segmentation
   dataset surfaced — hits were zoology papers and unrelated articles.
   A negative search result is evidence of absence from that index,
   not proof of absence everywhere; it is recorded as such.
5. **VerSe (vertebrae benchmark)** — checked as a coccyx candidate.
   Zenodo holds only the challenge design document (record 3759104,
   CC BY-ND 4.0); the dataset's own distribution terms and label list
   could not be verified from a primary open source in this pass.
   Status: **unverified lead**, not a source.

## Per-bone verdicts

### malleus_left, malleus_right / incus_left, incus_right / stapes_left, stapes_right

- BodyParts3D 4.0: **absent** (Milestone 2, exhaustive).
- TotalSegmentator v1 and v2 label sets: **absent** (verified above).
- HaN-Seg: **absent**, and license-excluded regardless.
- Any other verified clean-license source: **none found**.
- **Verdict: genuinely uncovered by every verified source checked.**
- Intended fallback, in order:
  1. **Z-Anatomy per-object clearance (OD-03.2).** Z-Anatomy models the
     ossicles as individual objects in its per-object source. The
     merged GLBs on this machine are excluded (CC BY-NC-SA as
     distributed, NC parts inseparable — Milestone 1). The route is:
     adopt the per-object source, read the license of the ossicle
     objects specifically, and adopt only if they clear the gate.
     Their license is **not** assumed here — the per-object read is
     the verification step, and it has not happened yet.
  2. If clearance fails: the records keep an **empty, flagged geometry
     slot** (they already exist as records in the Body Model) until a
     clean segmentation source is verified. The ossicles are
     millimetre-scale bones at the edge of what clinical-CT-derived
     datasets segment at all, which is consistent with — though not
     proof of — their absence from every CT label set checked.

### coccyx

- BodyParts3D 4.0: **absent** (Milestone 2, exhaustive — the coccygeus
  muscles exist; the bone does not).
- TotalSegmentator v1/v2: **no coccyx label**; `sacrum` is a single
  class. Whether individual sacrum masks include coccygeal voxels is
  an annotator-convention question that was **not** verified, and
  carving a coccyx out of the sacrum mask would be a modelling
  decision, not an adoption — it is not planned.
- VerSe: **unverified lead** (see above).
- **Verdict: genuinely uncovered by every verified source checked.**
- Intended fallback, in order:
  1. **Z-Anatomy per-object clearance (OD-03.2)** — the coccyx is an
     individual object in the per-object source; same verification
     requirement as the ossicles.
  2. If clearance fails: **empty, flagged geometry slot** on the
     existing record until a clean source is verified.

## Consequence for the pipeline

Skeletal geometry coverage stands at 199/206 records adopted
(BodyParts3D), 0/206 from TotalSegmentator for these seven (TS's role
for the skeleton is the 59-label overlap — vertebrae, ribs, and the
large limb bones — as a second, CT-consistent source; see
`data/sources/totalsegmentator-1.0/labels.md`). The seven gaps are
carried as flagged unknowns into Milestone 3's registry work; the
design-03 P2 exit criterion ("skeletal coverage must reach the full
206-record set") is **not** met by adoption alone and now depends on
the OD-03.2 per-object clearance decision.
