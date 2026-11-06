//! Data-path tests over the real Milestone-6 packs in web/data/.
//! These re-derive, from the binary packs alone, the numbers the
//! manifest and records.json claim — the same checks the web shell's
//! Node smoke test (tools/verify_web.js, W1–W5) runs, in Rust.

use anatomica_native::model::{decode_pick_id, encode_pick_id, LayerKind};
use anatomica_native::pack::{Pack, PackError};
use anatomica_native::{model, pack_manifest_report};
use std::path::PathBuf;

fn data_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../web/data")
}

fn load(kind: LayerKind) -> (model::ManifestLayer, Pack) {
    let dir = data_dir();
    let manifest = model::load_manifest(&dir.join("manifest.json")).expect("manifest");
    let layer = manifest
        .layers
        .get(kind.manifest_key())
        .unwrap_or_else(|| panic!("manifest layer {}", kind.manifest_key()))
        .clone();
    let pack = Pack::load(&dir.join(format!("{}.bin", kind.manifest_key()))).expect("pack");
    (layer, pack)
}

#[test]
fn packs_match_manifest() {
    for kind in LayerKind::ALL {
        let (layer, pack) = load(kind);
        let report = pack_manifest_report(kind, &pack, &layer);
        for (ok, line) in &report {
            assert!(ok, "manifest mismatch: {line}");
        }
    }
}

#[test]
fn slots_constant_within_ranges_and_indices_local() {
    for kind in LayerKind::ALL {
        let (layer, pack) = load(kind);
        for range in &layer.ranges {
            let v0 = range.vertex_start as usize;
            let v1 = v0 + range.vertex_count as usize;
            assert!(
                pack.record_ids[v0..v1].iter().all(|&s| s == range.slot),
                "{} slot {}: record ids not constant",
                range.record_id,
                range.slot
            );
            let i0 = range.index_start as usize;
            let i1 = i0 + range.index_count as usize;
            for &idx in &pack.indices[i0..i1] {
                assert!(
                    (idx as usize) >= v0 && (idx as usize) < v1,
                    "{}: index {idx} escapes its vertex range",
                    range.record_id
                );
            }
        }
    }
}

#[test]
fn pack_bboxes_reproduce_records_json() {
    let dir = data_dir();
    let records = model::load_records(&dir.join("records.json")).expect("records");
    for kind in LayerKind::ALL {
        let (layer, pack) = load(kind);
        for range in &layer.ranges {
            let rec = records
                .by_id(&range.record_id)
                .unwrap_or_else(|| panic!("records.json missing {}", range.record_id));
            let want = rec.bbox().expect("record bbox");
            let (mn, mx) = pack.range_bounds(range.vertex_start, range.vertex_count);
            for i in 0..3 {
                // f32 positions vs f64 record values: the web smoke
                // test measured worst 7.6e-6 cm; allow 2e-4.
                assert!(
                    (mn[i] as f64 - want.min[i]).abs() < 2e-4,
                    "{} min[{i}]: pack {} vs records {}",
                    range.record_id,
                    mn[i],
                    want.min[i]
                );
                assert!(
                    (mx[i] as f64 - want.max[i]).abs() < 2e-4,
                    "{} max[{i}]: pack {} vs records {}",
                    range.record_id,
                    mx[i],
                    want.max[i]
                );
            }
        }
    }
}

#[test]
fn pick_id_roundtrip() {
    for kind in LayerKind::ALL {
        for slot in [0u32, 1, 198, 358, 359, 65_535] {
            let id = encode_pick_id(kind, slot);
            // Framebuffer bytes as the native pick shader writes
            // them: low three id bytes in RGB, byte 3 (layer bit)
            // in alpha.
            let rgba = [
                (id & 0xFF) as u8,
                ((id >> 8) & 0xFF) as u8,
                ((id >> 16) & 0xFF) as u8,
                ((id >> 24) & 0xFF) as u8,
            ];
            assert_eq!(decode_pick_id(rgba), Some((kind, slot)));
        }
    }
    assert_eq!(decode_pick_id([0, 0, 0, 0]), None, "alpha 0 = miss");
}

#[test]
fn version_handshake_refuses_unknown_versions() {
    let dir = data_dir();
    let bytes = std::fs::read(dir.join("skeleton.bin")).expect("skeleton bytes");
    let mut bad = bytes.clone();
    bad[4..8].copy_from_slice(&3u32.to_le_bytes());
    match Pack::parse(&bad) {
        Err(PackError::UnsupportedVersion(3)) => {}
        other => panic!("expected UnsupportedVersion(3), got {other:?}"),
    }
    let mut bad_magic = bytes;
    bad_magic[0] = b'X';
    match Pack::parse(&bad_magic) {
        Err(PackError::BadMagic(_)) => {}
        other => panic!("expected BadMagic, got {other:?}"),
    }
}
