# ANATOMICA — Milestone 7 fix: web viewer pick-layer bug

Date: 2026-11-06. Status: **fixed and verified locally; not
uploaded.** Scope: `web/viewer.js` (the fix) and
`tools/verify_web.js` (a new regression check, W6). No other files
touched — `native/`, `data/`, `physiology/` untouched.

## 1. The defect (MILESTONE-7.md §1.4, restated against the code)

The pick id is `(layer_bit << 24) | slot`, with
`LAYER_BIT = { skeleton: 1, muscle: 2 }`. Two halves of the web
codec disagreed about byte 3:

- **Encoder** (`FS_PICK` in `web/viewer.js`): the shader computed
  the full 32-bit id but wrote only its low three bytes into RGB
  and fixed the output alpha at `1.0`. Byte 3 — the layer bit —
  never reached the framebuffer; every drawn fragment landed in
  the pick target with alpha byte 255 regardless of layer.
- **Decoder** (`pick()` in `web/viewer.js`): reconstructed only
  24 bits, `id = px[0] | (px[1] << 8) | (px[2] << 16)`, then
  computed `bit = id >>> 24`, which is therefore always 0.
  `bit === LAYER_BIT.skeleton` (1) could never hold, so the
  ternary's else branch resolved **every** pick against the
  muscle ranges — clicking any bone selected the muscle record
  whose slot number happened to match the bone's slot (skeleton
  slots run 0..198, muscle slots 0..358, so a wrong record was
  always found; the failure was silent, never a miss). The hit
  test `px[3] === 0` kept working only because the clear alpha is
  0 and the constant drawn alpha was non-zero.

The native shell (§1.4 of MILESTONE-7.md) did not reproduce the
bug: it writes byte 3 into the alpha channel — alpha was already
the hit flag (0 = miss), and layer bits are 1/2, so alpha ≠ 0
still means hit and now also carries the layer — and its decoder
returns no-hit for any layer bit it does not recognise
(`LayerKind::from_pick_bit` → `None`).

## 2. The fix (web/viewer.js, two hunks, nothing else changed)

Encoder — alpha now carries byte 3, mirroring
`native/src/model.rs`:

```diff
   uint id = (uLayerBit << 24) | vSlot;
+  // byte 3 (the layer bit) rides in alpha: 0 = miss (the clear value),
+  // 1/2 = hit — the native shell's pick codec (native/src/model.rs)
   o = vec4(float(id & 255u) / 255.0, float((id >> 8) & 255u) / 255.0,
-           float((id >> 16) & 255u) / 255.0, 1.0);
+           float((id >> 16) & 255u) / 255.0, float((id >> 24) & 255u) / 255.0);
```

Decoder — reconstruct all 32 bits, and map the layer bit strictly
(unknown bit → no hit, the native decoder's guard):

```diff
   if (px[3] === 0) return null;
-  const id = px[0] | (px[1] << 8) | (px[2] << 16);
+  const id = px[0] | (px[1] << 8) | (px[2] << 16) | (px[3] << 24);
   const bit = id >>> 24, slot = id & 0xffffff;
-  const layerName = bit === LAYER_BIT.skeleton ? "skeleton" : "muscles";
+  const layerName = bit === LAYER_BIT.skeleton ? "skeleton" : bit === LAYER_BIT.muscle ? "muscles" : null;
+  if (!layerName) return null;
```

Semantics now match the native codec exactly: bytes are
`[slot b0, slot b1, slot b2, layer_bit]`; alpha 0 = miss;
alpha 1/2 = hit on skeleton/muscles; any other alpha is a
no-hit, not a silent muscle resolution. The pre-fix decoder's
fallback mapped *any* unexpected bit to muscles — that
silent-misresolution class is gone.

Why this is exact on the web target: the pick pass renders into
an `RGBA8` framebuffer texture; the viewer never enables
blending and the FBO has no MSAA, so fragment alpha is stored
verbatim, and bytes 1/2 round-trip through `byte/255.0` exactly —
the same assumption the pre-existing RGB channels already relied
on. Slot capacity is unchanged (max slot 358, far under the
24-bit field).

## 3. The new check — W6 in tools/verify_web.js, and how it binds

W6 does **not** restate the codec. At run time it extracts the
codec from the viewer source under test and evaluates that:

- `LAYER_BIT` is parsed out of the shipped `const LAYER_BIT =
  { skeleton: …, muscle: … };` declaration.
- The encoder is parsed out of the shipped `FS_PICK` shader: the
  `uint id = …;` expression and all four channel expressions of
  the `o = vec4(…);` statement are extracted, mechanically
  translated from GLSL to JS (`Nu` → `N`, `float(` → `(`), and
  evaluated. The shift amounts, masks, channel order, and —
  critically — whether alpha is an id-derived expression or a
  constant all come from the file. Framebuffer storage is
  simulated as `round(clamp(v,0,1) × 255)` per channel.
- The decoder is the shipped code itself: the statements of
  `pick()` from the `if (px[3] === 0)` hit test through the
  range-resolution `return` are sliced out of the source and
  executed verbatim via `new Function`, given the real manifest
  range tables and the real records from `web/data/`.
- The roundtrip then runs **every slot of both layers** — 199
  skeleton (slots 0 and 198 included) + 359 muscle (slots 0 and
  358 included) = 558 encode→decode cases — plus the miss pixel
  `[0,0,0,0]`, which must decode to null. A case passes only if
  the decoder returns the exact record object that the encoded
  (layer, slot) names.
- If the shipped code's shape changes so any extraction no
  longer matches, W6 fails loudly ("could not bind to shipped
  code: …") rather than silently testing a private copy.
  `VIEWER_JS` may point the binding at another viewer.js copy
  (used for the counter-demonstration in §4); the data files
  still come from `web/`.

## 4. Verification

`node --check` passes on both edited files. Full output of
`node tools/verify_web.js` against the fixed viewer (exit 0):

```
[PASS] W1 manifest record counts — skeleton 199, muscles 359
[PASS] W1 records.json counts — bones 206 (199 with geometry), muscles 360 (359 with geometry)
[PASS] W2 skeleton.bin header/size — v2, 283091 vertices, 1535904 indices, 1596168 edge indices, 18190236 bytes
[PASS] W3 skeleton.bin content vs records.json — worst bbox diff 7.57e-6 cm (tol 0.01), slot mismatches 0, out-of-range indices 0
[PASS] W2 muscles.bin header/size — v2, 1704260 vertices, 7096476 indices, 8028654 edge indices, 94585848 bytes
[PASS] W3 muscles.bin content vs records.json — worst bbox diff 7.57e-6 cm (tol 0.01), slot mismatches 0, out-of-range indices 0
[PASS] W4 skeletal OBJ recount — 201 distinct files re-counted from disk, 0 mismatches vs assembled + geometry JSONs; distinct-file totals 283091 v / 511968 f
[PASS] W4 muscular OBJ recount — 417 distinct files re-counted from disk, 0 mismatches vs assembled + geometry JSONs; distinct-file totals 1704260 v / 2365492 f
[PASS] W5 no-geometry bones == Milestone 3 set — coccyx, incus_left, incus_right, malleus_left, malleus_right, stapes_left, stapes_right
[PASS] W5 clinical links — 127 clinical records; clinical-only entries 1 (multifidus)
[PASS] W6 pick codec roundtrip (bound to shipped viewer.js) — 558 encode->decode cases (every slot, both layers) + miss case; failures 0

ALL CHECKS PASS
```

Counter-demonstration — that W6 would have caught the defect:
both fix hunks were reversed in a scratch copy of the viewer
(`/tmp/viewer-prefix-buggy.js`, reconstructing the pre-fix code)
and the verifier was run with `VIEWER_JS` pointed at it. W1–W5
still pass (the data never changed); W6 fails on exactly the
skeleton layer — 199 failures, one per skeleton slot, each
resolving to the muscle record at the same slot number, which
is precisely the reported symptom:

```
[FAIL] W6 pick codec roundtrip (bound to shipped viewer.js) — 558 encode->decode cases (every slot, both layers) + miss case; failures 199; e.g. skeleton slot 0 (bytes 0/0/0/255) -> muscle:muscle.left-pectoralis-minor | skeleton slot 1 (bytes 1/0/0/255) -> muscle:muscle.right-pectoralis-minor | skeleton slot 2 (bytes 2/0/0/255) -> muscle:muscle.diaphragm | skeleton slot 3 (bytes 3/0/0/255) -> muscle:muscle.left-external-oblique | skeleton slot 4 (bytes 4/0/0/255) -> muscle:muscle.right-external-oblique | skeleton slot 5 (bytes 5/0/0/255) -> muscle:muscle.left-sternohyoid

1 FAILURE(S)
```

(exit 1). Note the encoded bytes in the failures: alpha 255 in
every case — the constant `1.0` — direct evidence the layer byte
never left the shader.

## 5. Anything else noticed

- The hover path (the render loop's `pick()` call on mouse move)
  shares this decoder, so hover highlighting and the hover
  cursor/name were wrong in exactly the same way and are fixed
  by the same two hunks; no separate hover code exists.
- `pick()` is the only decoder of pick ids in the viewer (one
  `>>> 24` site); the shade shader compares slots only and is
  unaffected.
- Not verified, stated plainly: no in-browser run was made (this
  VM still has no drivable browser — the open item carried since
  Milestone 6). The codec is proven at the code level by W6's
  extraction-and-execution and by the native shell's identical
  codec passing its own roundtrip unit test on rendered pixels
  (MILESTONE-7.md §3–§4); the web viewer's rendered-pixel pick
  remains unexercised until a browser is available.
