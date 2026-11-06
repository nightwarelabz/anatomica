# 09 — Web Shell (Browser Companion)

## Purpose

The universal-access build: any student, anywhere, opens a URL (or a local
file) and gets the atlas, imaging, physiology views, and the case workbench.
It is a companion to the native flagship — same Body Model, same content,
honest about the one thing it does not do (physical tissue simulation).

## Lineage

Evolves the Phase-1 application (single-file, zero-dependency, hand-written
software renderer, verified 206-bone skeletal module with live integrity
census) into a modular TypeScript application. The Phase-1 app remains the
reference for the data-integrity UX: counts computed live from loaded data,
verify flags visible, nothing asserted that the data does not contain.

## Stack

- TypeScript, no framework lock-in for the core (framework permitted in view
  layers only); rendering: WebGPU where available → WebGL2 → the Phase-1
  software renderer as the guaranteed floor.
- Imaging views follow the OHIF + Cornerstone3D (MIT) architecture patterns;
  Cornerstone3D may be adopted directly for DICOM viewports (license-clean),
  OHIF itself is a reference, not a dependency, unless a later decision says
  otherwise.
- The physiology engine reaches the web shell as the shared Rust core compiled
  to wasm (OD-01.2) — one engine, two shells; a TypeScript re-implementation
  of physiology is explicitly rejected (divergence risk).
- Static hosting only: no server, no accounts, no telemetry. Runs from
  `file://` for the atlas tier, as Phase 1 proved.

## Scope per module

| Module | Web scope |
|---|---|
| Atlas | Full: orbit/zoom/pan, layers, dissection peeling (mesh-level), labels, search (English/Latin/synonyms), isolate/dim, "ask the body" over the relations graph |
| Physiology | Full views: monitor, labs, perturbation library, what-if branching (engine via wasm) |
| Imaging | Full 2D/MPR suite; volume rendering per OD-06.1 (WebGPU-gated) |
| Theatre | Guided mode full; practice mode with step/instrument decisions and engine consequences — **without** tissue deformation: interactions are discrete (choose/disect-by-step), clearly labelled as the companion's model. Assessment available, labelled with its validity limits |
| Cases | Full workbench including calibration tracking (local storage only) |

## Honesty rules (enforced in UX copy review)

- The web Theatre never presents itself as hands-on tissue training; its
  practice mode is decision training, and says so.
- Every module shows the same Messick validity labels as the native shell.
- Synthetic imaging watermarked identically (export paths included).

## Data loading

Per-system data modules loaded on demand; geometry registry LODs selected by
device capability; total initial payload budget is a release metric (target:
atlas interactive before the full registry downloads — progressive loading by
system, skeleton first, as Phase 1 established the pattern).

## Verification gates

- The Phase-1 census discipline generalised: every data module's integrity
  panel recomputes counts live in the shipped app; a module whose panel
  disagrees with `tools/census.py` output fails release.
- Renderer fallback test: the app must reach full atlas function on the
  software-renderer path (no WebGL) — the floor is tested, not assumed.
- Offline test: full function with the network disabled after first load.

## Open decisions

- **OD-09.1** Whether the web shell ships as installable PWA in addition to
  plain static files. Leaning yes at P6; Phase-1's file:// capability must
  not regress either way.
- **OD-09.2** Search index: build-time static index (simple, offline) vs
  client-side index generation. Leaning build-time; decide with the P3
  "ask the body" work, when the relations graph is complete.
