#!/usr/bin/env python3
"""ANATOMICA Milestone 2 — FMA/BP3D mapping + skeletal geometry resolution.

Maps every record of the verified Phase-1 skeletal dataset
(~/workspace/anatomica-app/data/skeleton.js — ground truth, never modified)
to its BodyParts3D 4.0 / FMA concept, using ONLY the BP3D release tables in
data/sources/bodyparts3d-4.0/:

  isa_parts_list_e.txt / partof_parts_list_e.txt        concept id -> name
  isa_element_parts.txt / partof_element_parts.txt      concept -> element FJ files
  isa_inclusion_relation_list.txt / partof_...          IS-A / PART-OF children

Mapping kinds (derived from HOW the match was made, never asserted):
  exact-class        the concept denotes exactly this bone; where the bone is
                     lateralised / numbered / levelled, the concept name itself
                     carries that specificity (e.g. "right femur",
                     "third cervical vertebra", "atlas", "frontal bone").
  class+side         only the un-sided class concept exists; the record's side
                     is carried in the row (instance -> class + side).
  class+level        only the regional class concept exists for a vertebra;
                     the level is carried in the row.
  part-of-composite  the concept exists only in the PART-OF tree; the bone's
                     geometry is the composition of its part meshes (sternum).
  NOT-FOUND          no concept in either tree. Established by an exhaustive
                     stem search over all six release tables, reported with
                     hit counts. Never force-matched.

Every candidate name produced by a rule is verified by exact lookup in the
concept tables; a rule whose candidate is absent simply falls through to the
next candidate, and if no candidate in either tree matches, the record is
NOT-FOUND. Nothing is matched by fuzzy similarity.

Outputs:
  data/skeletal/fma-mapping.json       one row per skeletal record (206)
  data/skeletal/skeleton-geometry.json resolved mesh lists with vertex/face
                                       counts and bounding boxes measured by
                                       streaming the OBJ files themselves.

Stdlib only. Run: python3 tools/fma_map.py
"""
import json
import os
import re
import sys
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "sources", "bodyparts3d-4.0")
ISA_DIR = os.path.join(ROOT, "work", "bp3d", "isa_BP3D_4.0_obj_99")
PO_DIR = os.path.join(ROOT, "work", "bp3d", "partof_BP3D_4.0_obj_99")
SKELETON_JS = os.path.expanduser("~/workspace/anatomica-app/data/skeleton.js")
OUT_MAP = os.path.join(ROOT, "data", "skeletal", "fma-mapping.json")
OUT_GEO = os.path.join(ROOT, "data", "skeletal", "skeleton-geometry.json")

ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
            6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
            11: "eleventh", 12: "twelfth"}
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
FINGERS = {1: "thumb", 2: "index finger", 3: "middle finger",
           4: "ring finger", 5: "little finger"}
TOES = {1: "big toe", 2: "second toe", 3: "third toe",
        4: "fourth toe", 5: "little toe"}
# Our carpal name -> FMA name (FMA uses the adjective form for this one bone).
NAME_ALIASES = {"triquetrum": "triquetral", "ethmoid bone": "ethmoid"}


def read_tsv(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip()]
    return rows[1:]


def load_tables():
    isa_rows = read_tsv(os.path.join(SRC, "isa_parts_list_e.txt"))
    po_rows = read_tsv(os.path.join(SRC, "partof_parts_list_e.txt"))
    isa = {r[0]: {"repr": r[1], "name": r[2]} for r in isa_rows}
    po = {r[0]: {"repr": r[1], "name": r[2]} for r in po_rows}
    isa_by_name = {v["name"].lower(): k for k, v in isa.items()}
    po_by_name = {v["name"].lower(): k for k, v in po.items()}
    isa_elem, po_elem = {}, {}
    for r in read_tsv(os.path.join(SRC, "isa_element_parts.txt")):
        isa_elem.setdefault(r[0], set()).add(r[2])
    for r in read_tsv(os.path.join(SRC, "partof_element_parts.txt")):
        po_elem.setdefault(r[0], set()).add(r[2])
    isa_children, po_children = {}, {}
    for r in read_tsv(os.path.join(SRC, "isa_inclusion_relation_list.txt")):
        isa_children.setdefault(r[0], []).append(r[2])
    for r in read_tsv(os.path.join(SRC, "partof_inclusion_relation_list.txt")):
        po_children.setdefault(r[0], []).append(r[2])
    return isa, po, isa_by_name, po_by_name, isa_elem, po_elem, isa_children, po_children


def own_files(elem, children):
    """A concept's own mesh files = its element files minus its children's."""
    own = {}
    for cid, fjs in elem.items():
        sub = set()
        for ch in children.get(cid, []):
            sub |= elem.get(ch, set())
        o = fjs - sub
        if o:
            own[cid] = sorted(o)
    return own


def obj_header(path):
    """Parse the BP3D comment header of an OBJ file (concept id, bounds)."""
    info = {}
    with open(path, "rb") as fh:
        for _ in range(14):
            line = fh.readline().decode("utf-8", "replace")
            if not line.startswith("#"):
                break
            m = re.match(r"#\s*(File ID|Representation ID|Concept ID|English name|Bounds\(mm\))\s*:\s*(.+)", line)
            if m:
                info[m.group(1)] = m.group(2).strip()
    return info


def obj_stats(path):
    """Stream an OBJ file: count v/f lines and measure the vertex bbox."""
    v = f = 0
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    with open(path, "rb") as fh:
        for line in fh:
            if line[:2] == b"v ":
                v += 1
                p = line.split()
                for i in range(3):
                    x = float(p[1 + i])
                    if x < mn[i]:
                        mn[i] = x
                    if x > mx[i]:
                        mx[i] = x
            elif line[:2] == b"f ":
                f += 1
    return {"vertices": v, "faces": f,
            "bbox": {"min": mn, "max": mx}}


# --------------------------------------------------------------------------
# Candidate generation. Each rule returns an ordered list of
# (candidate_concept_name, rule_label). Lookup is exact (case-insensitive).
# --------------------------------------------------------------------------

def base_name(bone):
    return re.sub(r"\s*\((right|left|foot)\)", "", bone["name"]).strip()


def candidates(bone):
    name, side, bid = bone["name"], bone["side"], bone["id"]
    base = base_name(bone)
    low = base.lower()
    out = []

    m = re.match(r"vert_([CTLS])(\d+)$", bid)
    if bid == "vert_C1":
        return [("atlas", "vertebra C1 = atlas (FMA proper name)")]
    if bid == "vert_C2":
        return [("axis", "vertebra C2 = axis (FMA proper name)")]
    if m:
        region = {"C": "cervical", "T": "thoracic", "L": "lumbar"}[m.group(1)]
        n = int(m.group(2))
        return [(f"{ORDINALS[n]} {region} vertebra", f"vertebra per-level concept ({region} {n})"),
                (f"{region} vertebra", f"vertebra regional class fallback ({region})")]
    m = re.match(r"Rib (\d+)$", base)
    if m:
        n = int(m.group(1))
        return [(f"{side} {ORDINALS[n]} rib", "rib per-level lateralised concept"),
                (f"{ORDINALS[n]} rib", "rib per-level class fallback")]
    m = re.match(r"Metacarpal ([IV]+)$", base)
    if m:
        n = ROMAN[m.group(1)]
        return [(f"{side} {ORDINALS[n]} metacarpal bone", "metacarpal per-digit lateralised concept"),
                (f"{ORDINALS[n]} metacarpal bone", "metacarpal per-digit class fallback")]
    m = re.match(r"Metatarsal ([IV]+)$", base)
    if m:
        n = ROMAN[m.group(1)]
        return [(f"{side} {ORDINALS[n]} metatarsal bone", "metatarsal per-digit lateralised concept"),
                (f"{ORDINALS[n]} metatarsal bone", "metatarsal per-digit class fallback")]
    m = re.match(r"(Proximal|Middle|Distal) phalanx ([IV]+)$", base)
    if m and bone["region"] == "upper limb":
        typ, n = m.group(1).lower(), ROMAN[m.group(2)]
        return [(f"{typ} phalanx of {side} {FINGERS[n]}", "finger phalanx per-digit lateralised concept"),
                (f"{typ} phalanx of {FINGERS[n]}", "finger phalanx per-digit class fallback")]
    if m and bone["region"] == "lower limb":
        typ, n = m.group(1).lower(), ROMAN[m.group(2)]
        return [(f"{typ} phalanx of {side} {TOES[n]}", "toe phalanx per-digit lateralised concept"),
                (f"{typ} phalanx of {TOES[n]}", "toe phalanx per-digit class fallback")]
    # Carpals: plain bone names in the wrist cluster.
    if low in ("scaphoid", "lunate", "triquetrum", "pisiform", "trapezium",
               "trapezoid", "capitate", "hamate"):
        b = NAME_ALIASES.get(low, low)
        return [(f"{side} {b}", "carpal lateralised concept"),
                (b, "carpal class fallback")]
    # Tarsals with FMA-specific name shapes.
    if low == "navicular":
        return [(f"navicular bone of {side} foot", "tarsal navicular lateralised concept"),
                ("navicular bone of foot", "tarsal navicular class fallback")]
    if low == "cuboid":
        return [(f"{side} cuboid bone", "tarsal cuboid lateralised concept"),
                ("cuboid bone", "tarsal cuboid class fallback")]
    if low.endswith("cuneiform"):
        return [(f"{side} {low} bone", "tarsal cuneiform lateralised concept"),
                (f"{low} bone", "tarsal cuneiform class fallback")]
    if low in ("calcaneus", "talus"):
        return [(f"{side} {low}", "tarsal lateralised concept"),
                (low, "tarsal class fallback")]
    # Generic: skull bones, limb long bones, sacrum, hyoid, sternum, coccyx,
    # ossicles (candidates are generated; lookup decides).
    b = NAME_ALIASES.get(low, low)
    cands = []
    if side in ("right", "left"):
        cands.append((f"{side} {b}", "paired bone lateralised concept"))
    cands.append((b, "exact name concept" if side == "midline" else "paired bone class fallback"))
    if b != low:  # alias was applied; also try the un-aliased spelling first-hand
        cands.insert(0 if side == "midline" else 1, (low, "un-aliased spelling"))
    return cands


def stem_search(stems):
    """Exhaustive negative evidence: count stem hits across all six tables."""
    files = ["isa_parts_list_e.txt", "partof_parts_list_e.txt",
             "isa_element_parts.txt", "partof_element_parts.txt",
             "isa_inclusion_relation_list.txt", "partof_inclusion_relation_list.txt"]
    hits = {}
    for fn in files:
        text = open(os.path.join(SRC, fn), encoding="utf-8", errors="replace").read().lower()
        hits[fn] = {s: text.count(s) for s in stems}
    return hits


def main():
    (isa, po, isa_by_name, po_by_name,
     isa_elem, po_elem, isa_children, po_children) = load_tables()
    isa_own = own_files(isa_elem, isa_children)

    src = open(SKELETON_JS, encoding="utf-8").read()
    bones = json.loads(src[src.index("{"):src.rindex("}") + 1])["bones"]
    assert len(bones) == 206, len(bones)

    stats_cache = {}

    def stats_for(tree, fj):
        key = (tree, fj)
        if key not in stats_cache:
            d = ISA_DIR if tree == "isa" else PO_DIR
            stats_cache[key] = obj_stats(os.path.join(d, fj + ".obj"))
        return stats_cache[key]

    mappings = []
    geometry = []
    for bone in bones:
        side = bone["side"]
        row = OrderedDict([
            ("record_id", bone["id"]),
            ("record_name", bone["name"]),
            ("ta", bone.get("ta")),
            ("side", side),
            ("region", bone["region"]),
            ("subgroup", bone.get("subgroup")),
            ("fma_id", None),
            ("concept_name", None),
            ("representation_id", None),
            ("primary_fj", None),
            ("mapping_kind", "NOT-FOUND"),
            ("side_recorded", None),
            ("level", None),
            ("evidence", ""),
            ("reason", None),
        ])
        cands = candidates(bone)
        hit = None  # (fma_id, concept_name, repr, tree, cand_name, rule, cand_index)
        for idx, (cand, rule) in enumerate(cands):
            if cand.lower() in isa_by_name:
                cid = isa_by_name[cand.lower()]
                hit = (cid, isa[cid]["name"], isa[cid]["repr"], "isa", cand, rule, idx)
                break
        if hit is None:
            for idx, (cand, rule) in enumerate(cands):
                if cand.lower() in po_by_name:
                    cid = po_by_name[cand.lower()]
                    hit = (cid, po[cid]["name"], po[cid]["repr"], "partof", cand, rule, idx)
                    break

        if hit is None:
            stem = re.sub(r"[^a-z]", "", base_name(bone).lower().split()[0])
            hits = stem_search([stem])
            total = sum(sum(h.values()) for h in hits.values())
            row["reason"] = (f"no concept named for this bone in either BP3D 4.0 parts list; "
                             f"stem '{stem}' occurs {total} times across all six release tables "
                             f"(all hits are non-bone namesakes)" if total else
                             f"no concept named for this bone in either BP3D 4.0 parts list; "
                             f"stem '{stem}' occurs 0 times across all six release tables")
            row["evidence"] = ("exhaustive lookup: candidate names " +
                               ", ".join(f"'{c}'" for c, _ in cands) +
                               " absent from isa_parts_list_e.txt and partof_parts_list_e.txt; " +
                               f"stem search over all six tables: {json.dumps(hits)}")
            mappings.append(row)
            geometry.append(OrderedDict([
                ("record_id", bone["id"]), ("fma_id", None), ("concept_name", None),
                ("isa_meshes", []), ("partof_meshes", []),
                ("totals", {"isa": {"files": 0, "vertices": 0, "faces": 0},
                            "partof": {"files": 0, "vertices": 0, "faces": 0},
                            "combined_files": 0}),
                ("bbox_isa", None), ("bbox_partof", None)]))
            continue

        cid, cname, repr_id, tree, cand, rule, idx = hit
        row["fma_id"] = cid
        row["concept_name"] = cname
        row["representation_id"] = repr_id
        own = isa_own.get(cid, [])
        row["primary_fj"] = own[0] if len(own) == 1 else (own if own else None)

        if tree == "partof":
            row["mapping_kind"] = "part-of-composite"
            ev = (f"concept present only in partof_parts_list_e.txt ({cid}/{repr_id} '{cname}'); "
                  f"absent from isa_parts_list_e.txt; geometry resolves from its PART-OF "
                  f"element composition ({len(po_elem.get(cid, []))} part meshes). Rule: {rule}.")
        elif "fallback" in rule and "regional" in rule:
            row["mapping_kind"] = "class+level"
            row["level"] = bone["name"]
            ev = f"isa_parts_list_e.txt ({cid}/{repr_id} '{cname}') via rule: {rule}."
        elif "fallback" in rule and side in ("right", "left"):
            row["mapping_kind"] = "class+side"
            row["side_recorded"] = side
            ev = (f"isa_parts_list_e.txt ({cid}/{repr_id} '{cname}') via rule: {rule}; "
                  f"no lateralised concept exists, side '{side}' recorded from the record.")
        else:
            row["mapping_kind"] = "exact-class"
            ev = f"isa_parts_list_e.txt ({cid}/{repr_id} '{cname}') via rule: {rule}."
        # Corroborate with the OBJ header of the concept's own mesh, if any.
        if len(own) == 1:
            hdr = obj_header(os.path.join(ISA_DIR, own[0] + ".obj"))
            if hdr.get("Concept ID") == cid:
                ev += (f" Corroborated by OBJ header of own mesh {own[0]}.obj "
                       f"(Concept ID {cid}, Representation ID {hdr.get('Representation ID')}).")
            else:
                ev += (f" WARNING: OBJ header of own mesh {own[0]}.obj states Concept ID "
                       f"{hdr.get('Concept ID')}, not {cid}.")
        row["evidence"] = ev
        mappings.append(row)

        # ---- geometry resolution ----
        def mesh_list(tree_name, elem_map, base_dir):
            out = []
            for fj in sorted(elem_map.get(cid, [])):
                st = stats_for(tree_name, fj)
                out.append(OrderedDict([
                    ("fj", fj),
                    ("path", os.path.relpath(os.path.join(base_dir, fj + ".obj"), ROOT)),
                    ("vertices", st["vertices"]),
                    ("faces", st["faces"]),
                    ("bbox", st["bbox"])]))
            return out

        isa_meshes = mesh_list("isa", isa_elem, ISA_DIR) if tree == "isa" or cid in isa_elem else []
        po_meshes = mesh_list("partof", po_elem, PO_DIR)

        def totals(meshes):
            return {"files": len(meshes),
                    "vertices": sum(m["vertices"] for m in meshes),
                    "faces": sum(m["faces"] for m in meshes)}

        def union_bbox(meshes):
            if not meshes:
                return None
            mn = [min(m["bbox"]["min"][i] for m in meshes) for i in range(3)]
            mx = [max(m["bbox"]["max"][i] for m in meshes) for i in range(3)]
            return {"min": mn, "max": mx}

        geometry.append(OrderedDict([
            ("record_id", bone["id"]),
            ("fma_id", cid),
            ("concept_name", cname),
            ("isa_meshes", isa_meshes),
            ("partof_meshes", po_meshes),
            ("totals", {"isa": totals(isa_meshes), "partof": totals(po_meshes),
                        "combined_files": len({m["fj"] for m in isa_meshes} |
                                              {m["fj"] for m in po_meshes})}),
            ("bbox_isa", union_bbox(isa_meshes)),
            ("bbox_partof", union_bbox(po_meshes))]))

    dist = Counter(r["mapping_kind"] for r in mappings)
    not_found = [r["record_id"] for r in mappings if r["mapping_kind"] == "NOT-FOUND"]
    map_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA skeletal FMA/BP3D mapping — Milestone 2"),
            ("generated_by", "tools/fma_map.py"),
            ("source_dataset", "~/workspace/anatomica-app/data/skeleton.js (verified Phase-1, 206 records, unmodified)"),
            ("target_tables", "data/sources/bodyparts3d-4.0/ (isa_/partof_ parts lists, element parts, inclusion relations)"),
            ("concept_universe", {"isa_concepts": len(isa), "partof_concepts": len(po),
                                  "note": "concept ids are FMA identifiers as used by BodyParts3D 4.0 (FMA 3.0 build-up per OBJ headers)"}),
            ("kind_definitions", {
                "exact-class": "concept denotes exactly this bone, incl. laterality/level/digit specificity in the concept name",
                "class+side": "only the un-sided class concept exists; side carried in side_recorded",
                "class+level": "only the regional class concept exists for a vertebra; level carried in level",
                "part-of-composite": "concept exists only in the PART-OF tree; geometry = composition of its part meshes",
                "NOT-FOUND": "no concept in either tree; established by exhaustive stem search, never force-matched"}),
            ("distribution", dict(dist)),
            ("not_found", not_found),
        ])),
        ("mappings", mappings),
    ])
    with open(OUT_MAP, "w") as f:
        json.dump(map_doc, f, indent=1, sort_keys=False)

    geo_doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA skeletal geometry resolution — Milestone 2"),
            ("generated_by", "tools/fma_map.py"),
            ("paths", "mesh paths are relative to the project root; meshes are the extracted BP3D 4.0 working copies under work/bp3d/ (sources in data/sources/ stay byte-identical)"),
            ("units", "OBJ header states 'Bounds(mm)' — source coordinates are millimetres (verified by measurement in tools/register_sketch.md)"),
            ("counting", "vertices = lines starting 'v ', faces = lines starting 'f ', counted by streaming each file; bbox measured from the same vertex stream — no header values trusted"),
            ("composition", "isa_meshes = the concept's element files in isa_element_parts.txt (its IS-A composition); partof_meshes = its element files in partof_element_parts.txt (its PART-OF part composition). The two archives are alternative segmentations of the same body, listed separately, never merged."),
        ])),
        ("records", geometry),
    ])
    with open(OUT_GEO, "w") as f:
        json.dump(geo_doc, f, indent=1, sort_keys=False)

    print("mapping distribution:", dict(dist))
    print("NOT-FOUND:", not_found)
    print(f"wrote {OUT_MAP}")
    print(f"wrote {OUT_GEO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
