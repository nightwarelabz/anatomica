# ANATOMICA

![The cardiovascular system — a still from ANATOMICA's surgical simulation film](assets/anatomica-hero.jpg)

*The cardiovascular system — a still from ANATOMICA's surgical simulation film.*

An open medical surgical and anatomy system: a 3D anatomical atlas, a physiology
simulation engine, an imaging suite, a surgical procedure simulator, and a clinical
case and hypothesis workbench — all reading one verified model of the human body.

ANATOMICA is an educational and simulation system. It is not a clinical device, it
carries no real patient data, and it is not for diagnosis or treatment of real persons.

## Principles

- **One body, one truth.** Every module derives from the same Body Model; modules
  never keep private copies of anatomy or physiology.
- **Data before rendering.** A structure exists because its record is verified —
  nomenclature, counts, and relations traceable to named sources. Uncertain items
  carry a visible *verify* flag instead of a silently chosen answer.
- **Derived, never invented.** Geometry comes from segmented human anatomy adopted
  under compatible licenses, tracked per file in a provenance ledger.
- **Computed, not scripted.** Vitals and labs are outputs of a running physiological
  state; complications in the operating theatre are computed by the engine.
- **Open forever.** The whole system is licensed AGPL-3.0.

## Layout

| Path | Contents |
|---|---|
| `design/` | Buildable design documents for every area of the system |
| `data/` | Body Model data modules, one folder per body system; `data/sources/` holds adopted source datasets with their provenance |
| `tools/` | Verification tooling: provenance ledger builder, censuses, checkers |
| `native/` | The native application (flagship) |
| `web/` | The browser application (universal-access companion) |
| `research/` | The research library the design rests on (3 rounds, 31 fronts) |

## Status

Milestones 1–8 are complete and recorded in `MILESTONE-1.md` through
`MILESTONE-8.md`: verified Body Model data modules for the skeletal, muscular,
and cardiovascular systems (a nervous system module is in progress), the
assembled real-geometry skeleton, web and native shells rendering that
geometry, and a deterministic physiology engine whose resting cardiovascular
outputs validate against published normal ranges.

## License

AGPL-3.0. See `LICENSE`. Adopted datasets keep their own licenses, recorded
per file in the provenance ledger under `data/sources/`.
