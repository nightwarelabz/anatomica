# ANATOMICA — Surgical Simulation Film Engine

The 3D engine behind the ANATOMICA surgical simulation film. It renders
a full layered human patient — skin, skeleton, cartilage, muscle,
arteries, veins, heart, nerves, brain, lungs and organs — from verified
anatomical datasets as multi-pass render plates, composites the plates
into finished frames (layer fades, sweeps, pulses, camera moves are all
post operations on the plates), and stamps every frame with the
NIGHTWARE LABZ mark.

## Requirements

- Blender 4.2.3 LTS (standalone). On the build machine it lives at
  `~/workspace/blender423/blender`.
- Headless rendering on Linux uses Xvfb + Mesa EGL:
  `xvfb-run -a -s "-screen 0 1280x720x24" <blender> -b --python ...`
  If the host loses its EGL libraries (VM images do), restore them with
  `restore_render_env.sh` (installs the kept .deb packages).
- Python 3 with numpy, scipy, Pillow for the analysis and compositing
  tools.
- ffmpeg for act encoding, concatenation and the audio mux.

## Patient scene (patient.blend.xz)

The built patient — twelve joined per-system meshes in one registered
space with finished materials, built by `patient.py` from the source
datasets below — is 626,296,988 bytes uncompressed, over GitHub's
100 MB per-file repository limit. It is therefore stored in this
directory compressed:

- The scene is one XZ (-6, multithreaded) archive of 99,927,280
  bytes — under both the 100 MB decimal and the 100 MiB (104,857,600)
  per-file limits. Web upload tooling caps individual files lower
  than that, so the archive is stored here split into four transport
  parts, `patient.blend.xz.part-aa` … `patient.blend.xz.part-ad`
  (25,165,824 bytes each; the last is 24,429,808). The parts are the
  single archive, byte for byte, in order.
- Restore with `./restore_patient.sh`: it reassembles the parts,
  decompresses the archive, and verifies the result byte-for-byte —
  the SHA-256 of the restored `patient.blend` must equal
  `10fd128418624492e00773621eefa4da069658198594a4c3ed8674618793fe0a`,
  and the script fails loudly if it does not.

Place the restored `patient.blend` beside these scripts (the
directory `patient.py` writes and `plates.py` opens) before rendering
plates.

## Pipeline

Run the stages in order:

1. **Patient build** — `patient.py` imports the per-system GLB models,
   classifies mesh nodes into anatomy groups by name, joins each group,
   bakes transforms, assigns materials, and saves `patient.blend`:

   ```
   blender -b --python patient.py -- patient.blend
   ```

   The trailing `-- patient.blend` argument is required; without it
   the build runs but nothing is saved.
   The replacement skin is a voxel-remeshed duplicate of the muscle
   layer (`make_skin2.py`), so every layer is the same body in the
   same pose; `fix_clip.py`, `fix_skin.py`, `fix_mats.py`, `fix_lung*.py`
   are the repair passes that were applied, and `probe*.py` /
   `islands*.py` / `dump_groups.py` / `diag.py` are the verification
   tools behind them (mesh dumps land in `work/`, see Geometry inputs).

2. **Scene** — `scene.py` is imported by `plates.py`: it parents the
   patient to a rig, poses it supine on the examination table, builds
   the room (floor, table, pad, procedural surgical drape) and the
   lighting rig (key / fill / rim / surgical spot), AgX colour
   management.

3. **Plates** — `plates.py` renders one transparent-background plate
   per anatomy group per camera:

   ```
   blender -b --python plates.py -- <camera> <group> <out.png> [width] [samples]
   ```

   Cameras: `main` (full-body hero) and `surg` (surgical field, with
   its own light levels and exposure). Groups: `base` (room + drape,
   opaque), `skin`, `bone` (+ cartilage), `muscle`, `vessels`
   (arteries + veins), `heart`, `nerve`, `brain`, `lung`, `organliver`
   (organs + liver), `drapeonly` (drape alone, composited last so the
   pelvis stays covered over every layer combination).
   Production plates: 2560x1440, 64 TAA samples, 1024 shadow maps.
   Test plates: 1280x720, 8 samples.

4. **Composite + mark** — `compose_still.py` composites plates with a
   named recipe and stamps the mark (all caps, letter-spaced, bottom
   right, clean white):

   ```
   python3 compose_still.py --plates <plate_dir> --recipe surgery --out still.png
   ```

5. **Acts** — the film is assembled per act from the production
   plates: camera moves are eased crop windows over the 2560-wide
   plates, the x-ray sweep is a wipe between skin and bone plates,
   layer analysis crossfades the groups, the arterial pulse wave and
   nerve signal pulses are masked travelling highlights on the vessel
   and nerve plates, the heart beats by scaling the heart plate about
   its centroid on the same ECG curve the HUD and the sound design
   follow, and the drape plate is composited last in every frame.
   Acts are encoded at high bitrate (H.264, CRF ~15), verified from
   the encoded files (frame count, duration, boundary stills), then
   concatenated.

6. **Sound** — a procedural soundscape built to the picture: a low
   drone bed and room pressure as the constant, the monitor and
   ventilator locked to the patient's scripted vitals, procedure
   sounds (cautery, suction, instrument contacts) placed on their
   action frames. Verification before the mux: band-energy profile,
   spectrogram inspection, onset-sync audit against the action
   frames, loudness / true-peak metering.

7. **Mux** — act video + verified sound, final verification from the
   encoded file.

## Geometry inputs (geometry/)

`geometry/*.npz` are per-system mesh dumps of the built patient
(vertex arrays, face-index runs per source part, and the per-face
keep masks produced by the connected-component island analysis in
`islands*.py`). They are the working geometry the verification tools
and the compositing masks are computed from:

| file(s) | system |
|---|---|
| `artery`, `vein` (+ `_keep`) | cardiovascular tree |
| `bone`, `cartilage` (+ `_keep`) | skeletal system |
| `brain` (+ `_keep`) | brain |
| `heart` (+ `_keep`) | heart |
| `liver`, `organ` (+ `_keep`) | abdominal organs |
| `lung` (+ `_keep`) | lungs |
| `muscle` (+ `_keep`) | muscular system |
| `nerve` (+ `_keep`) | nervous system |
| `skin` (+ `_keep`) | original skin mesh (superseded in the scene by the remeshed muscle duplicate; kept for reference) |

## Data sources and attribution

- **Z-Anatomy** — the master model (all systems in one registered
  space), CC BY-SA 4.0, derived from BodyParts3D.
  <https://www.z-anatomy.com/>
- **BodyParts3D** — © The Database Center for Life Science (DBCLS),
  CC BY 4.0. <https://dbarchive.biosciencedb.jp/en/bodyparts3d/>

Anatomical content is presented as a simulation for visualisation;
no real person is depicted.
