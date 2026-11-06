//! ANATOMICA native shell — Milestone 7 skeleton.
//!
//! Loads the ANW1 v2 Body Model packs (the same files the web shell
//! renders), asserts them against the pack manifest, and renders them
//! with wgpu: an orbit viewer for machines with a display, and a
//! headless offscreen verification renderer for machines without one.

pub mod camera;
pub mod model;
pub mod pack;
pub mod render;

use model::{LayerKind, ManifestLayer};
use pack::Pack;

/// The startup handshake between a pack and the manifest that
/// describes it: every count the manifest claims is compared against
/// the pack header and the pack's range table. Returns one
/// (passed, message) line per comparison — the native shell refuses
/// to render a pack that fails this (no silent misreads, design/08).
pub fn pack_manifest_report(
    kind: LayerKind,
    pack: &Pack,
    layer: &ManifestLayer,
) -> Vec<(bool, String)> {
    let name = kind.manifest_key();
    let mut out: Vec<(bool, String)> = Vec::new();
    let mut cmp = |label: &str, got: u64, want: u64| {
        out.push((
            got == want,
            format!("{name} {label}: pack {got} vs manifest {want}"),
        ));
    };
    cmp("records", pack.header.record_count as u64, layer.records as u64);
    cmp("vertices", pack.header.vertex_count as u64, layer.vertices as u64);
    cmp("indices", pack.header.index_count as u64, layer.indices as u64);
    cmp(
        "edge_indices",
        pack.header.edge_index_count as u64,
        layer.edge_indices as u64,
    );
    cmp("file bytes", pack.file_bytes, layer.bytes);
    let range_vertex_sum: u64 = layer.ranges.iter().map(|r| r.vertex_count as u64).sum();
    let range_index_sum: u64 = layer.ranges.iter().map(|r| r.index_count as u64).sum();
    cmp("range vertex sum", range_vertex_sum, layer.vertices as u64);
    cmp("range index sum", range_index_sum, layer.indices as u64);
    out.push((
        layer.ranges.len() as u64 == layer.records as u64,
        format!(
            "{name} range table entries: {} vs manifest records {}",
            layer.ranges.len(),
            layer.records
        ),
    ));
    // Slots are dense and ordered: ranges[n].slot == n, and ranges
    // tile the vertex/index buffers contiguously.
    let mut ok = true;
    let (mut v, mut i) = (0u32, 0u32);
    for (n, r) in layer.ranges.iter().enumerate() {
        if r.slot != n as u32 || r.vertex_start != v || r.index_start != i {
            ok = false;
            break;
        }
        v += r.vertex_count;
        i += r.index_count;
    }
    out.push((ok, format!("{name} ranges tile buffers contiguously, slots dense")));
    out
}
