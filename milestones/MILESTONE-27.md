# ANATOMICA — Milestone 27: Web tier delivery — pack compression + progressive per-layer loading

**State: built and verified locally. Not uploaded (per-item approval stands).**

Milestone 16 §6 defect 3 recorded the access tier's weight problem
verbatim: "the access tier now downloads 290.3 MiB of packs + 2.1 MB
of JSON. No compression or streaming exists yet; on a slow connection
the layer-by-layer load (with progress) is the only mitigation. Pack
compression / level-of-detail is future work, not attempted here."
This milestone does the compression and the progressive loading.
Level-of-detail remains future work and out of scope (§6): it is a
lossy question, and everything here is byte-exactly lossless.

Two changes, both in the delivery layer only:

1. **A compressed delivery encoding of the packs** — one gzip file
   per layer next to the canonical pack, plus a `delivery.json`
   describing it. The canonical ANW1 v2 packs are untouched and
   remain the artifacts of record (the native shell reads them
   exactly as before; §5).
2. **Progressive loading in the web shell** — the render loop now
   starts after the manifest and records arrive; layers stream in
   behind it in a stated priority order and become drawable and
   pickable as each lands, instead of the previous all-or-nothing
   wait for all eleven.

The web shell remains zero-dependency: decoding uses the platform
`DecompressionStream('gzip')`, no library was added (§1).

## 1. Codec choice — measured, not assumed

Candidates were the formats the browser-native `DecompressionStream`
exposes (`gzip`, `deflate`, `deflate-raw`; Brotli is not exposed by
that API and was never a candidate under the zero-dependency rule).
Measured on this VM with Python zlib (streaming, 4 MiB chunks) on
the three most representative packs, before any code was written:

| pack | canonical B | gzip-6 | gzip-9 | deflate-9 |
|---|---|---|---|---|
| muscular | 94,585,848 | 39,061,425 (0.4130×) | 39,048,149 (0.4128×) | 39,048,137 |
| skeletal | 18,190,236 | 7,439,450 (0.4090×) | 7,410,865 (0.4074×) | 7,410,853 |
| urinary | 350,920 | 145,839 (0.4156×) | 145,264 (0.4140×) | 145,252 |

- **Format: gzip.** It differs from raw deflate only by the ~12 B
  header/trailer per file, and wins on everything around the bytes:
  universal tooling, `Content-Encoding` semantics if a host ever
  serves it that way, and a two-byte magic (`1f 8b`) a reader can
  corroborate. Ratios land at 0.34–0.42× per layer (§2) — the pack
  sections (float32 positions, uint32 indices/ids/edges) compress
  uniformly well.
- **Level: 6.** Level 9 buys ≤ 0.4% (13 KB on the 39 MB muscular
  pack, 29 KB on skeletal) at ~3× the one-off encode time. Level 6
  is zlib's default for a reason; the evidence here gives no cause
  to pay more.
- The full compress + self-verify pass over all eleven layers took
  ~62 s wall on this VM — a build-time cost, paid once per pack
  rebuild.

**How a decoder knows which encoding a file is:** authoritatively,
`web/data/delivery.json` names each layer's `compressed_file`; the
viewer never sniffs. Corroboration, in order: the `.gz` begins with
the gzip magic `1f 8b` (the canonical pack begins with `ANW1`);
after decoding, the viewer's `fetchPack()` asserts the decoded byte
length equals the canonical byte count recorded in delivery.json
and that the buffer begins with `ANW1`, before `uploadLayer()`
applies its own header checks. Any failure at any step falls back
to fetching the canonical pack (§3).

## 2. The delivery encoding — sizes and byte-identity proof

Produced by `python3 tools/pack_geometry.py --compress` (a new mode;
the canonical pack path, `--check`, the manifest and the packs
themselves are unmodified). It writes `web/data/<system>.bin.gz`
× 11 and `web/data/delivery.json` (4,856 B), which records, per
layer: canonical file name/size/SHA-256, compressed file
name/size/SHA-256, the codec, and the load order (§3).

| layer | canonical B | gzip B | ratio | SHA-256 (canonical, first 16) |
|---|---|---|---|---|
| skeletal | 18,190,236 | 7,439,450 | 0.4090 | e4ef4cf8cc63f1b8 |
| muscular | 94,585,848 | 39,061,425 | 0.4130 | 7d04536b807ab460 |
| cardiovascular | 74,688,188 | 29,378,946 | 0.3934 | c5b74eb92a12eb5c |
| nervous | 40,059,000 | 16,520,336 | 0.4124 | c8ff8916a617da9b |
| respiratory | 19,199,216 | 7,526,001 | 0.3920 | 7aff696280007a12 |
| digestive | 46,780,860 | 18,883,522 | 0.4037 | a420327b1798e52a |
| urinary | 350,920 | 145,839 | 0.4156 | 9f37ae6c997b3fbf |
| lymphatic | 197,044 | 66,586 | 0.3379 | 63fa1a29f2d69550 |
| endocrine | 254,368 | 103,460 | 0.4067 | e01d5e3066f66867 |
| reproductive | 511,644 | 184,609 | 0.3608 | 1b873af7467b7148 |
| integumentary | 9,550,572 | 4,042,227 | 0.4232 | f4e5c585038e55f8 |
| **total** | **304,367,896 (290.3 MiB)** | **123,352,401 (117.6 MiB)** | **0.4053** | |

**Byte-identity, proven three independent ways:**

1. At production time, `--compress` decompresses every `.gz` it
   wrote and hash-compares against the canonical pack; a mismatch
   aborts the mode. All 11 passed.
2. In the standing gate, `tools/verify_web.js` **W9** recomputes
   both files' sizes and SHA-256 from disk, gunzips each `.gz`
   (Node zlib), and asserts the decoded bytes hash identically to
   the canonical pack — per layer, every run. All 11 pass.
3. W9 additionally decodes the largest layer (muscular) through
   `DecompressionStream('gzip')` itself — the exact API and code
   path shape the viewer uses — and hash-compares. Pass.

The full SHA-256 pairs live in `delivery.json`; the table above
truncates for print only.

## 3. Progressive loading — order, mechanics, pick behaviour

**Order** (`LOAD_ORDER` in the viewer, `load_order` in
delivery.json; W9 asserts the two are equal and that the list is a
permutation of the 11 systems with the stated ends):

skeletal → muscular → cardiovascular → nervous → respiratory →
digestive → urinary → lymphatic → endocrine → reproductive →
integumentary

Rationale: **skeletal first** — it is default-visible and the
framing/reference layer every other system registers against, and
at 7.4 MB delivered it is the cheapest complete layer that makes
the shell a body viewer rather than a spinner. **Muscular second**
— it completes the default view (the écorché). The remaining
systems then follow **manifest order** (the shells' canonical
innermost → outermost order), which puts the default-off,
occluding **integumentary shell last** — it is the layer a first
paint least needs.

**Mechanics** (`web/viewer.js`; boot restructured, nothing else in
the shell's behaviour changed):

- Boot still fetches `manifest.json` + `records.json` first (the
  record list, panels, toggles and region filter are all live from
  that moment), then tries `delivery.json` — optional by design;
  its absence, a missing entry, a failed `.gz` fetch, a decode
  error, or a browser without `DecompressionStream` all fall back
  to the canonical pack per layer, so older data directories and
  older browsers behave exactly as the pre-Milestone-27 shell did.
- The render loop starts immediately after controls are wired.
  `loadLayersProgressive()` runs un-awaited behind it: for each
  layer in LOAD_ORDER it fetches (progress callbacks drive the
  layer's own count span: `queued` → `loading… NN%` → the M16
  counts line; the footer strip reports `layers loaded n/11`,
  first-layer time, and full-load time), decodes if compressed,
  uploads to the GPU, and marks the layer ready.
- **Toggles for in-flight layers are intent, recorded in the
  checkbox.** `layerVisible()` reads the checkbox as before; the
  draw path already skipped layers with no GPU buffers, so a layer
  checked while absent simply appears when it lands, and one
  unchecked stays dark. Drawn-stats and label projection now also
  skip unloaded layers, so the strip never claims geometry that
  has not arrived.
- **Picking degrades gracefully, then is unchanged.** The id pass
  renders only loaded layers (its standing `if (!lay || …)
  continue;` guard — asserted present by W9), so a click while
  layers are in flight resolves against what is actually on
  screen; a record whose layer has not arrived cannot be hit yet,
  and can be the moment it lands. Once a layer is loaded, pick
  semantics are bit-for-bit the Milestone-7-FIX codec: **W6 still
  roundtrips all 1,545 slots**, and neither `pick()` nor `FS_PICK`
  was modified by this milestone (the W8 opacity-blindness
  assertion on `pick()` also still passes).

## 4. Measurements — transfer model and decode cost

All transfer figures below are **arithmetic, labelled as such**:
measured byte counts (this section's tables) divided by a stated
constant bandwidth, plus measured decode time. No network was
involved and none is claimed; latency, TCP slow-start, server
behaviour and GPU upload time are excluded (GPU upload is real but
was measured only for the native shell's stack — 1,642 ms for all
11 layers in this session's verify run — and is not transferable
to a browser number, so it is reported, not folded in).

Setup bytes fetched before any layer in both shells, old and new:
manifest.json 396,195 B + records.json 1,727,037 B (+ delivery.json
4,856 B in the new shell) = 2,128,088 B. The old shell's first
render required **all** packs: 306,491,128 B on the wire. The new
shell's first render requires setup + skeletal.gz = 9,567,538 B.

| at constant | old: first render (= full) | new: first render (skeletal) | new: default view (+ muscular) | new: full body |
|---|---|---|---|---|
| 10 Mbit/s | 245.2 s | 7.7 s + 0.84 s decode = **8.5 s** | 38.9 s + 3.90 s = **42.8 s** | 100.4 s + 7.78 s = **108.2 s** |
| 50 Mbit/s | 49.0 s | 1.5 s + 0.84 s = **2.4 s** | 7.8 s + 3.90 s = **11.7 s** | 20.1 s + 7.78 s = **27.9 s** |
| 200 Mbit/s | 12.3 s | 0.4 s + 0.84 s = **1.2 s** | 1.9 s + 
...[truncated 6151 chars]