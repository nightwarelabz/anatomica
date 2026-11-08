#!/usr/bin/env python3
"""ANATOMICA generalized assembly checker — Milestone 16.

Independent of the assemblers (tools/assemble_skeleton.py,
tools/assemble_muscles.py, tools/assemble_systems.py): verifies every
system's assembled JSON against its module geometry file using a
different computation path where possible — bounding boxes are
re-derived by transforming the *stored* per-mesh source boxes
corner-wise (valid because the conversion is an axis permutation
with sign flips) instead of streaming vertices.

Checks (per system unless noted):
  A1  record set: assembled ids == geometry records carrying a
      non-empty chosen composition (IS-A primary, PART-OF fallback);
      assembled and inventory counts equal the Body Model v1 census
      (Milestone 15 closing table, hardcoded below as the
      independent anchor).
  A2  every assembled bbox equals the corner-transformed union of
      the stored per-mesh source boxes of its assembled mesh list
      (worst diff gated at 1e-6 cm).
  A3  layer coherence vs the skeletal assembly: both unions reported
      with per-axis exceedances; gated part — no record's bbox is
      disjoint from the skeletal union expanded by 2.0 cm (a record
      floating entirely outside the body envelope would indicate a
      frame error, not anatomy). Exceedances themselves are
      reported, never gated: soft tissue legitimately reaches
      beyond bone.
  A4  left/right mirror symmetry of paired records, in two parts.
      The GATED part is transform invariance: each pair's mirror
      deviation measured in the canonical frame must equal 0.1x the
      deviation measured in the source frame (same mesh sets, stored
      boxes) to 1e-6 cm — the conversion is an isometry, so any
      sign/permutation error changes deviations and fails here,
      while A2 pins every box exactly. The Milestone-6 distributional
      gate (median <= 0.1 cm, p90 <= 0.5 cm) conflated transform
      correctness with source symmetry; it remains the right test
      for skeletal and muscular (both still pass it — reported) but
      visceral name-pairs are not mirror anatomy (left/right hepatic
      lobes, colic arteries, bronchopulmonary segments are genuinely
      asymmetric in the source model), so for the new systems the
      distribution is REPORTED as source characterization, never
      gated. Every pair >= 1.0 cm is listed individually with its
      measured cross-midline vertex fraction (streamed) so outliers
      carry their mechanism or an explicit "not identified" flag.
  A5  [REPORT, not gated] records whose bbox intersects no bone
      bbox at all — listed in full; bbox intersection is a coarse
      test and a non-zero count is a prompt for anatomical review,
      not proof of error (Milestone 6 K5 precedent).
  A6  no NaN/Inf in any assembled bbox.
  A7  totals: distinct assembled mesh paths == paths of the chosen
      compositions after removing de-duplicated occurrences (an
      occurrence = one (record, fj) entry in a chosen composition;
      the assembled meta's deduped_files list marks the removed
      ones, each verified present in its record's chosen
      composition); grand vertex/face sums over assembled entries ==
      sums over the surviving occurrences; per-record totals equal
      their mesh sums.
  A8  [REPORT] clinical tranche counts per system vs the Milestone
      15 census, and clinical-only counts (clinical records linking
      no inventory record) computed from the tranche files.

Stdlib only. Exit 0 iff all gated checks pass.
"""
import json
import math
import os
import sys
from array import array

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TOL = 1e-6
MIRROR_TOL_CM = 1.0
ENVELOPE_MARGIN_CM = 2.0

# Milestone 15 closing census (the independent anchor):
# system -> (inventory records, with geometry, clinical records)
CENSUS = {
    "skeletal": (206, 199, None),
    "muscular": (359, 359, 127),
    "cardiovascular": (646, 646, 69),
    "nervous": (419, 152, 92),  # Milestone 33: +286 FMA 5.1.0 concept
    # records (geometry-absent); geometry count unchanged.
    # Milestone 39: +40 major-nerve clinical records in a second
    # clinical file (data/nervous/major-nerves.json); inventory and
    # geometry counts unchanged
    # Milestone 63: 19 of the 286 FMA concept records gained derived
    # Z-Anatomy Tier B geometry (2026-11-08 ruling); inventory count
    # unchanged, geometry 133 -> 152
    "respiratory": (83, 83, 37),
    "digestive": (93, 93, 31),
    "urinary": (73, 6, 6),  # Milestone 37: +67 FMA 5.1.0 concept
    # records (geometry-absent); geometry and clinical counts unchanged
    "lymphatic": (135, 4, 4),  # Milestone 36: +131 FMA 5.1.0 concept
    # records (geometry-absent); geometry and clinical counts unchanged
    "endocrine": (17, 3, 6),  # Milestone 36: +14 FMA 5.1.0 concept
    # records (geometry-absent); geometry and clinical counts unchanged
    "reproductive": (146, 15, 16),  # Milestone 37: +57 FMA 5.1.0 concept
    # records (geometry-absent); Milestone 38: +76 more (male);
    # geometry and clinical counts unchanged
    # Milestone 63: the deferent-duct pair claimed its BodyParts3D
    # meshes (FJ3135 / FJ3140; Milestone 40 adjudication, 2026-11-08
    # ruling); inventory count unchanged, geometry 13 -> 15
    "integumentary": (59, 6, 13),  # Milestone 38: +53 FMA 5.1.0 concept
    # records (geometry-absent); geometry and clinical counts unchanged
}

SYSTEMS = {
    "skeletal": ("data/skeletal/skeleton-geometry.json",
                 "data/skeletal/skeleton-assembled.json", None),
    "muscular": ("data/muscular/muscle-geometry.json",
                 "data/muscular/muscles-assembled.json",
                 "data/muscular/muscles.json"),
    "cardiovascular": ("data/cardiovascular/cv-geometry.json",
                       "data/cardiovascular/cv-assembled.json",
                       "data/cardiovascular/cardiovascular.json"),
    "nervous": ("data/nervous/nervous-geometry.json",
                "data/nervous/nervous-assembled.json",
                ("data/nervous/nervous.json",
                 "data/nervous/major-nerves.json")),
    "respiratory": ("data/respiratory/respiratory-geometry.json",
                    "data/respiratory/respiratory-assembled.json",
                    "data/respiratory/respiratory.json"),
    "digestive": ("data/digestive/digestive-geometry.json",
                  "data/digestive/digestive-assembled.json",
                  "data/digestive/digestive.json"),
    "urinary": ("data/urinary/urinary-geometry.json",
                "data/urinary/urinary-assembled.json",
                "data/urinary/urinary.json"),
    "lymphatic": ("data/lymphatic/lymphatic-geometry.json",
                  "data/lymphatic/lymphatic-assembled.json",
                  "data/lymphatic/lymphatic.json"),
    "endocrine": ("data/endocrine/endocrine-geometry.json",
                  "data/endocrine/endocrine-assembled.json",
                  "data/endocrine/endocrine.json"),
    "reproductive": ("data/reproductive/reproductive-geometry.json",
                     "data/reproductive/reproductive-assembled.json",
                     "data/reproductive/reproductive.json"),
    "integumentary": ("data/integumentary/integumentary-geometry.json",
                      "data/integumentary/integumentary-assembled.json",
                      "data/integumentary/integumentary.json"),
}


def conv(x, y, z):
    return (-x * 0.1, z * 0.1, -y * 0.1)


def transform_bbox(bb):
    a = conv(*bb["min"])
    b = conv(*bb["max"])
    return {"min": [min(a[i], b[i]) for i in range(3)],
            "max": [max(a[i], b[i]) for i in range(3)]}


def union(boxes):
    return {"min": [min(b["min"][i] for b in boxes) for i in range(3)],
            "max": [max(b["max"][i] for b in boxes) for i in range(3)]}


def intersects(a, b, margin=0.0):
    return all(a["min"][i] <= b["max"][i] + margin and
               b["min"][i] <= a["max"][i] + margin for i in range(3))


def chosen(rec):
    isa = rec.get("isa_meshes") or []
    if isa:
        return isa
    return rec.get("partof_meshes") or []


def mirror_candidates(rid):
    out = []
    if ".left-" in rid:
        out.append(rid.replace(".left-", ".right-"))
    if rid.endswith("_left"):
        out.append(rid[:-5] + "_right")
    if ".right-" in rid:
        out.append(rid.replace(".right-", ".left-"))
    if rid.endswith("_right"):
        out.append(rid[:-6] + "_left")
    return out


def main():
    fails = []

    def report(ok, label, detail=""):
        print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            fails.append(label)

    def note(label, detail=""):
        print(f"[REPORT] {label}" + (f" — {detail}" if detail else ""))

    data = {}
    for key, (geom_rel, asm_rel, _clin) in SYSTEMS.items():
        geom = json.load(open(os.path.join(ROOT, geom_rel)))
        asm = json.load(open(os.path.join(ROOT, asm_rel)))
        data[key] = (geom, asm)

    skel_asm = data["skeletal"][1]
    skel_union = skel_asm["meta"]["union_bbox_canonical_cm"]
    bone_boxes = [r["bbox_canonical_cm"] for r in skel_asm["records"]]

    for key, (geom, asm) in data.items():
        grec = {r["record_id"]: r for r in geom["records"]}
        arec = {r["record_id"]: r for r in asm["records"]}
        exp_inv, exp_geo, exp_clin = CENSUS[key]

        # A1
        exp_asm = {rid for rid, r in grec.items() if chosen(r)}
        report(set(arec) == exp_asm and len(arec) == exp_geo and len(grec) == exp_inv,
               f"A1 {key} record set",
               f"assembled={len(arec)} (census {exp_geo}), geometry records={len(grec)} (census {exp_inv})")

        # A2 — corner-transform of the stored per-mesh source boxes
        mesh_by_path = {}
        for r in geom["records"]:
            for tree in ("isa_meshes", "partof_meshes"):
                for m in r.get(tree) or []:
                    mesh_by_path[m["path"]] = m
        worst = 0.0
        for rid, r in arec.items():
            src = union([mesh_by_path[m["path"]]["bbox"] for m in r["meshes"]])
            exp = transform_bbox(src)
            for side in ("min", "max"):
                for i in range(3):
                    worst = max(worst, abs(exp[side][i] - r["bbox_canonical_cm"][side][i]))
        report(worst <= TOL, f"A2 {key} bboxes == corner-transformed source boxes",
               f"worst diff {worst:.2e} cm")

        # A3
        lu = union([r["bbox_canonical_cm"] for r in arec.values()])
        span_l = [lu["max"][i] - lu["min"][i] for i in range(3)]
        span_s = [skel_union["max"][i] - skel_union["min"][i] for i in range(3)]
        axes = ["x", "y", "z"]
        exc = []
        for i in range(3):
            lo = skel_union["min"][i] - lu["min"][i]
            hi = lu["max"][i] - skel_union["max"][i]
            exc.append(f"{axes[i]}: layer span {span_l[i]:.3f} vs skeletal {span_s[i]:.3f}; "
                       f"min {'EXCEEDS by %.3f' % lo if lo > 0 else 'inside by %.3f' % -lo}, "
                       f"max {'EXCEEDS by %.3f' % hi if hi > 0 else 'inside by %.3f' % -hi}")
        if key == "skeletal":
            report(True, f"A3 {key} layer bounds (self — reference envelope)",
                   "; ".join(exc))
        else:
            outside = [rid for rid, r in arec.items()
                       if not intersects(r["bbox_canonical_cm"], skel_union, ENVELOPE_MARGIN_CM)]
            report(not outside, f"A3 {key} layer bounds vs skeletal envelope",
                   "; ".join(exc) + f"; records disjoint from skeletal union + "
                   f"{ENVELOPE_MARGIN_CM} cm: {outside}")

        # A4 — mirror symmetry
        pairs = []
        seen_pairs = set()
        for rid in arec:
            for cand in mirror_candidates(rid):
                if cand in arec and (cand, rid) not in seen_pairs:
                    pairs.append((rid, cand))
                    seen_pairs.add((rid, cand))
        devs = []
        worst_inv = 0.0
        for a, b in pairs:
            ab = arec[a]["bbox_canonical_cm"]
            bb = arec[b]["bbox_canonical_cm"]
            mirrored = {"min": [-bb["max"][0], bb["min"][1], bb["min"][2]],
                        "max": [-bb["min"][0], bb["max"][1], bb["max"][2]]}
            dev = max(abs(mirrored[s][i] - ab[s][i]) for s in ("min", "max") for i in range(3))
            devs.append((dev, a, b))
            # Source-frame deviation over the same mesh sets (stored
            # boxes, mm): the conversion is an isometry, so the
            # canonical deviation must equal 0.1x the source one.
            sa = union([mesh_by_path[m["path"]]["bbox"] for m in arec[a]["meshes"]])
            sb = union([mesh_by_path[m["path"]]["bbox"] for m in arec[b]["meshes"]])
            mir_s = {"min": [-sb["max"][0], sb["min"][1], sb["min"][2]],
                     "max": [-sb["min"][0], sb["max"][1], sb["max"][2]]}
            dev_s = max(abs(mir_s[s][i] - sa[s][i]) for s in ("min", "max") for i in range(3))
            worst_inv = max(worst_inv, abs(dev - 0.1 * dev_s))
        devs.sort(reverse=True)
        if pairs:
            sd = sorted(d for d, _, _ in devs)
            median_dev = sd[len(sd) // 2]
            p90_dev = sd[max(0, math.ceil(0.90 * len(sd)) - 1)]
            n_over = sum(1 for d, _, _ in devs if d >= MIRROR_TOL_CM)
            m6 = ("passes the Milestone-6 distributional thresholds"
                  if median_dev <= 0.1 and p90_dev <= 0.5 else
                  "source distribution exceeds the Milestone-6 muscle thresholds — "
                  "characterized below, not gated (see docstring)")
            report(worst_inv <= TOL,
                   f"A4 {key} mirror symmetry (transform invariance gated)",
                   f"{len(pairs)} pairs; worst |canonical dev - 0.1 x source dev| "
                   f"{worst_inv:.2e} cm; distribution: median {median_dev:.4f} cm, "
                   f"p90 {p90_dev:.4f} cm, {n_over} pairs >= {MIRROR_TOL_CM} cm "
                   f"(listed below); {m6}")
        else:
            note(f"A4 {key} mirror symmetry", "no left/right pairs in this system")
        for d, a, b in devs:
            if d < MIRROR_TOL_CM:
                continue
            fracs = {}
            for rid in (a, b):
                side = arec[rid].get("side")
                wrong = total = 0
                for m in arec[rid]["meshes"]:
                    with open(os.path.join(ROOT, m["path"]), "rb") as fh:
                        for line in fh:
                            if line.startswith(b"v "):
                                p = line.split()
                                cx = -float(p[1]) * 0.1
                                total += 1
                                if (side == "left" and cx > 0) or (side == "right" and cx < 0):
                                    wrong += 1
                fracs[rid] = (wrong / total) if total else 0.0
            mech = (f"cross-midline vertex fraction {a} {fracs[a]:.3%}, {b} {fracs[b]:.3%}")
            if fracs[a] == 0 and fracs[b] == 0:
                mech += " — mechanism NOT identified (no cross-midline geometry); flagged"
            note(f"A4c {key} outlier {a} / {b}", f"raw dev {d:.3f} cm; {mech}")

        # A5 (report only; skeletal against itself is meaningless)
        if key != "skeletal":
            no_hit = [rid for rid, r in arec.items()
                      if not any(intersects(r["bbox_canonical_cm"], bb) for bb in bone_boxes)]
            note(f"A5 {key} records intersecting no bone bbox",
                 f"count={len(no_hit)}: {no_hit}")

        # A6
        bad = [rid for rid, r in arec.items()
               if any(not math.isfinite(v) for s in ("min", "max")
                      for v in r["bbox_canonical_cm"][s])]
        report(not bad, f"A6 {key} no NaN/Inf", f"bad={bad}")

        # A7 — occurrence-level accounting: an occurrence is one
        # (record, fj) entry in a chosen composition; occurrences the
        # assembler de-duplicated (identical geometry under a second
        # fj in the same composition) are marked by the meta list.
        dropped_occ = set()
        dedup_ok = True
        for d in asm["meta"].get("deduped_files", []):
            comp = chosen(grec[d["record_id"]])
            if not any(m["fj"] == d["dropped"] for m in comp) or \
               not any(m["fj"] == d["kept"] for m in comp):
                dedup_ok = False
                continue
            dropped_occ.add((d["record_id"], d["dropped"]))
        exp_paths = set()
        exp_v = exp_f = 0
        for r in geom["records"]:
            for m in chosen(r):
                if (r["record_id"], m["fj"]) in dropped_occ:
                    continue
                exp_paths.add(m["path"])
                exp_v += m["vertices"]
                exp_f += m["faces"]
        got_paths = [m["path"] for r in asm["records"] for m in r["meshes"]]
        got_v = sum(r["totals"]["vertices"] for r in asm["records"])
        got_f = sum(r["totals"]["faces"] for r in asm["records"])
        per_record_ok = all(
            r["totals"]["vertices"] == sum(m["vertices"] for m in r["meshes"]) and
            r["totals"]["faces"] == sum(m["faces"] for m in r["meshes"])
            for r in asm["records"])
        report(set(got_paths) == exp_paths and got_v == exp_v
               and got_f == exp_f and per_record_ok and dedup_ok,
               f"A7 {key} totals vs chosen compositions",
               f"distinct paths {len(set(got_paths))} (expected {len(exp_paths)} after "
               f"{len(dropped_occ)} de-duplicated occurrences); "
               f"vertices {got_v} (expected {exp_v}); faces {got_f} (expected {exp_f}); "
               f"per-record sums {'ok' if per_record_ok else 'MISMATCH'}; "
               f"dedupe records {'ok' if dedup_ok else 'UNVERIFIABLE'}")

        # A8 (report)
        clin_rel = SYSTEMS[key][2]
        if clin_rel:
            # A system's clinical tranche may span more than one
            # file (Milestone 39: nervous adds major-nerves.json).
            clin_files = clin_rel if isinstance(clin_rel, tuple) \
                else (clin_rel,)
            crec, n_variants = [], 0
            for one in clin_files:
                clin = json.load(open(os.path.join(ROOT, one)))
                crec.extend(clin["records"])
                n_variants += len(clin.get("variants", []))
            inv_ids = set(grec)
            clin_only = 0
            for c in crec:
                g = c.get("geometry_record_ids")
                if g is None and isinstance(c.get("geometry"), dict):
                    g = c["geometry"].get("inventory_record_ids")
                if not g:
                    clin_only += 1
            extra = f"; variants {n_variants}" if n_variants else ""
            note(f"A8 {key} clinical tranche",
                 f"{len(crec)} records (census {exp_clin}); clinical-only "
                 f"(no inventory link) {clin_only}{extra}")
            report(len(crec) == exp_clin, f"A8 {key} clinical count == census",
                   f"{len(crec)} vs {exp_clin}")

    print(f"\n{'ALL GATED CHECKS PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
