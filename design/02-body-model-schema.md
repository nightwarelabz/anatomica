# 02 — Body Model Schema

## Purpose

The single source of truth for anatomy: record types, the relations graph,
variant records, naming, and standards export. Everything else — engine,
Theatre, imaging, cases — refers to structures defined here, by ID.

## Record format

Data modules are JSON (UTF-8, LF, sorted keys) under `data/<system>/`, one file
per system plus optional per-region splits. JSON is chosen over the Phase-1
JS-module format so both shells and all tooling share one parser; the Phase-1
skeletal module is converted by `tools/` and must reproduce its 206-record
census exactly after conversion.

### Structure record

```json
{
  "id": "artery.hepatic.right",
  "kind": "vessel",
  "name": "Right hepatic artery",
  "ta": {"latin": "Arteria hepatica dextra", "code": null},
  "fma": null,
  "system": "cardiovascular",
  "region": "abdomen",
  "side": "right",
  "classification": null,
  "description": "…",
  "relations": [ {"type": "branch_of", "target": "artery.hepatic.proper"} ],
  "variants": [ … ],
  "sources": [ {"ref": "…", "locator": "…"} ],
  "verify": null
}
```

Field rules:

- `id` — stable, dot-namespaced, lowercase; never reused, never renamed once
  shipped (renames are new IDs + a `supersedes` note).
- `ta.code` — TA2 code where one exists; `null` with a `verify` note otherwise.
  TA2 *terms* are used as-is (public domain per FIPAT); the TA2 publication is
  never reproduced.
- `fma` — FMA ID from the direct OWL release (CC BY 3.0), never the UMLS copy.
- `verify` — `null`, or a string stating exactly what is contested and between
  which sources. A record with `verify` set renders with the flag in both shells.

### Kinds and their extra fields

| Kind | Extra fields |
|---|---|
| `bone` | classification (long/flat/short/irregular/sesamoid), articulations via relations |
| `muscle` | `origin[]`, `insertion[]`, `actions[]`, innervation + arterial supply via relations |
| `vessel` | `origin`, `course`, `branches[]` (ordered), `territory` (structure IDs) |
| `nerve` | `root_values`, `branches[]`, `motor_territory`, `sensory_territory` |
| `organ` | `parts[]`, peritoneal relations, supply/drainage/innervation via relations, `surface_projection` |
| `space` / `region` | `boundaries`, `contents[]` (structure IDs) |
| `gland` | `products[]` (hormone IDs consumed by the physiology engine) |

### Relations graph

Typed, directed edges stored on the source record; inverse edges are derived at
build time and checked for consistency. Relation types (v1 set, extensible only
by schema change): `articulates_with` (symmetric), `attaches_to`, `origin_of`,
`branch_of`, `supplies`, `drains_to`, `innervates`, `pierces`, `lies_within`,
`continuous_with`, `part_of`, `at_risk_in` (target = procedure ID; owned by the
Theatre but stored here so the atlas can answer "what is at risk").

Consistency rules enforced by the checker: referential integrity; symmetry of
`articulates_with`; `branch_of`/`part_of` acyclicity; every `supplies` target
exists; laterality coherence (a `right` structure's relations resolve to the
same side unless the target is midline).

### Variant records

```json
"variants": [{
  "id": "artery.hepatic.right.replaced-from-sma",
  "label": "Replaced right hepatic artery from superior mesenteric artery",
  "prevalence": {"low": 0.10, "high": 0.16, "sources": ["…"]},
  "geometry": "variant mesh ref or null",
  "modeled": true,
  "injury_consequence": "…"
}]
```

Rules (the variant gate): prevalence is always a cited range, never a point
value. Any variant with prevalence ≥1% **and** an injury consequence must have
`modeled: true` or an explicit `unmodeled_note` in the record — the checker
fails the module otherwise.

## Counting conventions & census

Every system module carries a `meta` block: counting convention (as the
Phase-1 skeletal module does — 206 total, sacrum/coccyx as units, ossicles and
hyoid itemised), target census, and source list. `tools/census.py` recomputes
counts from the records and diffs them against `meta`; the in-app integrity
panel reads the same output format, so the check a developer runs is the check
a learner sees.

## Standards export

From P2, the model build emits:

- **CellML** — physiology-facing component descriptions for structures the
  engine models (compartments, vessels as segments).
- **FieldML** — spatial fields for registered geometry (per-region meshes).
- **SED-ML** — stubs describing the standard simulation experiments
  (steady-state, hemorrhage classes) once the engine lands (P4).
- **PMR-style index** — a machine-readable catalogue (`index.json`) of models
  and datasets with source, license, and version, in the spirit of the
  Physiome Model Repository and the SPARC Portal.

Export is generated, never hand-maintained; the JSON records are canonical.

## Verification gates

- Schema validation (JSON Schema per kind) on every commit of a data module.
- Census checker per system; articulation/relation consistency checker globally.
- Dual-source rule: a record whose fields are safety-relevant (supply,
  innervation, danger relations) must carry ≥2 entries in `sources`.

## Open decisions

- **OD-02.1** Whether `at_risk_in` edges live in the model or are derived from
  procedure files at build time. Leaning: derived — procedures are the authority
  on their own risks; the model stores the derived view. Decide at P5 design.
- **OD-02.2** Granularity of vessel branching: named branches only vs named +
  segmental. Affects cardiovascular census targets; decide with the P2
  cardiovascular module design, against TotalSegmentator's 104-structure label
  set as the imaging floor.
