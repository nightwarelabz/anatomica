# 01 — Architecture

## Purpose

Define the system-wide shape every other design conforms to: one Body Model,
two shells (native flagship, browser companion), and strict module boundaries so
that anatomy, physiology, imaging, the Theatre, and cases can never disagree.

## System shape

```
                 ┌────────────────────────────────────────────┐
                 │              BODY MODEL (data)             │
                 │  records · relations graph · variants      │
                 │  geometry registry · provenance ledger     │
                 └───────▲───────────────────────▲────────────┘
                         │ read-only             │ read-only
        ┌────────────────┴───────┐     ┌─────────┴──────────────┐
        │   PHYSIOLOGY ENGINE    │     │     CONTENT PACKS      │
        │  deterministic core    │     │  procedures (CTA)      │
        │  state ⇄ Body Model    │     │  cases · formulary     │
        └───────▲────────────────┘     └─────────▲──────────────┘
                │ state ticks                    │ content refs
   ┌────────────┴────────────────────────────────┴─────────────┐
   │                        SHELLS                             │
   │  native/  Rust + wgpu (Vulkan/Metal/D3D12), VTK volumes,  │
   │           OpenXR, SOFA/XPBD tissue, haptics via plugins   │
   │  web/     TypeScript, WebGPU→WebGL2 fallback, OHIF-       │
   │           pattern imaging, software-renderer fallback     │
   └───────────────────────────────────────────────────────────┘
```

## Rules

1. **The Body Model is data, not code.** It ships as versioned data modules
   (see `02-body-model-schema.md`). Shells and engine load it; nothing embeds
   anatomical facts in source code.
2. **The engine owns state; the model owns structure.** Physiology state
   (volumes, pressures, drug concentrations) lives in the engine and refers to
   Body Model structures by stable ID. The model itself is stateless.
3. **Content refers, never copies.** A procedure step or a case names structure
   IDs, drug IDs, and engine perturbations. If a name or a number is needed in
   two modules, it lives once, in the model or the formulary.
4. **Both shells render the same registry.** Geometry is registered onto records
   once, by the geometry pipeline (`03-geometry-pipeline.md`); each shell is a
   view. A shell may degrade fidelity (LOD, fallback renderer) but never content:
   the same structure is selectable, by the same name, in both.
5. **Plugins sit outside the core.** Haptics SDKs and any proprietary component
   load through the plugin boundary of the native shell only. The AGPL core must
   build and run with zero plugins present.
6. **Offline-first.** A fresh clone builds and runs with no network. All data,
   including adopted datasets, is in-tree or fetched by an explicit, recorded
   setup step.

## Interfaces

| Interface | Producer | Consumers | Contract |
|---|---|---|---|
| Body Model package | `data/` modules + build tooling | engine, both shells, content validators | Schema in `02`; versioned by `model_version` semver |
| Geometry registry | `tools/` pipeline | both shells | One entry per structure ID: mesh refs, LODs, transform; format in `03` |
| Engine state API | physiology engine | Theatre, Cases, monitor views | Fixed-step tick, perturbation application, causal-chain query; `04` |
| Content pack format | Theatre / Cases authors | shells, validators | CTA graph format in `05`; case format in `07` |
| Provenance ledger | `tools/provenance.py` | build gate, release process | JSON ledger + summary; `03` |

## Repository layout

`data/<system>/` one folder per body system (skeletal, muscular, cardiovascular,
nervous, respiratory, digestive, urinary, reproductive, endocrine, lymphatic,
integumentary); `data/sources/` adopted raw datasets, untouched, each with its
own `SOURCE.md`; `tools/` checkers and pipeline; `design/` these documents;
`research/` the research library; `native/`, `web/` the shells.

## Verification gates

- Model package passes schema validation + per-system census checkers before
  any shell or engine change is accepted against it.
- Provenance gate: no geometry file is referenced by the registry unless it
  appears in the ledger with source, license, and SHA-256.
- Determinism gate: engine replay of a recorded input stream reproduces state
  hashes bit-exactly (native shell CI; web shell where the platform allows).

## Open decisions (flagged, not silently resolved)

- **OD-01.1 Model package distribution format:** single compiled package
  (binary, mmap-friendly) vs per-system files loaded on demand. Leaning:
  per-system source files + a build step emitting one package per shell.
  Decide before the geometry pipeline emits its first registry.
- **OD-01.2 Engine implementation language boundary:** engine core in Rust
  shared by both shells (wasm for web) vs a TypeScript port for web. Leaning:
  one Rust core, wasm-compiled for the web shell — two implementations of
  physiology is exactly the divergence this architecture exists to prevent.
  Decide at the physiology phase (P4) with the Pulse embed-vs-build decision.
- **OD-01.3 Plugin ABI:** stable C ABI vs versioned Rust trait objects.
  Decide when the first haptics plugin is scheduled (P8); not on the critical path.
