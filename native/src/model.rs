//! Manifest + records model: the JSON side of the web data pack
//! (`web/data/manifest.json`, `web/data/records.json`), parsed with the
//! same field names the web shell uses. The manifest's per-record
//! ranges are the slot scheme shared by both shells: slot `n` of a
//! layer is `ranges[n]`, and the pack's per-vertex recordIds are those
//! slots — picking in either shell resolves through this table.

use serde::Deserialize;
use serde_json::{Map, Value};
use std::collections::BTreeMap;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LayerKind {
    Skeleton,
    Muscle,
}

impl LayerKind {
    pub const ALL: [LayerKind; 2] = [LayerKind::Skeleton, LayerKind::Muscle];

    /// Key in manifest.json ("layers" map) and pack file stem.
    pub fn manifest_key(&self) -> &'static str {
        match self {
            LayerKind::Skeleton => "skeleton",
            LayerKind::Muscle => "muscles",
        }
    }

    /// Value of the `layer` field in records.json.
    pub fn records_layer(&self) -> &'static str {
        match self {
            LayerKind::Skeleton => "skeleton",
            LayerKind::Muscle => "muscle",
        }
    }

    /// Pick-id layer bit, identical to the web shell's LAYER_BIT.
    pub fn pick_bit(&self) -> u32 {
        match self {
            LayerKind::Skeleton => 1,
            LayerKind::Muscle => 2,
        }
    }

    pub fn from_pick_bit(bit: u32) -> Option<LayerKind> {
        match bit {
            1 => Some(LayerKind::Skeleton),
            2 => Some(LayerKind::Muscle),
            _ => None,
        }
    }

    pub fn label(&self) -> &'static str {
        match self {
            LayerKind::Skeleton => "Skeleton",
            LayerKind::Muscle => "Muscles",
        }
    }

    /// Base colour, identical to the web shell's LAYER_STYLE.
    pub fn color(&self) -> [f32; 3] {
        match self {
            LayerKind::Skeleton => [0.78, 0.72, 0.60],
            LayerKind::Muscle => [0.55, 0.22, 0.19],
        }
    }
}

/// Encode/decode the pick id: `id = (layer_bit << 24) | slot` — the
/// web shell's documented layout and slot scheme.
///
/// One deliberate deviation from the web shell's code, because the
/// web code is buggy here (found by this milestone's roundtrip test,
/// recorded in MILESTONE-7.md): the web fragment shader writes only
/// the low three bytes of the id into RGB and fixes alpha at 1.0, so
/// the layer bit (byte 3) never reaches the framebuffer; its decode
/// computes `bit = id >>> 24` from a 24-bit reconstruction, which is
/// always 0, and every pick resolves against the muscle layer. The
/// native shell writes byte 3 into the alpha channel instead — alpha
/// was the web's hit flag (0 = miss), and layer bits are 1/2, so
/// alpha != 0 still means "hit" and now also carries the layer.
pub fn encode_pick_id(kind: LayerKind, slot: u32) -> u32 {
    (kind.pick_bit() << 24) | (slot & 0x00FF_FFFF)
}

pub fn decode_pick_id(rgba: [u8; 4]) -> Option<(LayerKind, u32)> {
    if rgba[3] == 0 {
        return None;
    }
    let id = (rgba[0] as u32)
        | ((rgba[1] as u32) << 8)
        | ((rgba[2] as u32) << 16)
        | ((rgba[3] as u32) << 24);
    let kind = LayerKind::from_pick_bit(id >> 24)?;
    Some((kind, id & 0x00FF_FFFF))
}

#[derive(Debug, Deserialize)]
pub struct Manifest {
    pub layers: BTreeMap<String, ManifestLayer>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct ManifestLayer {
    pub file: String,
    pub bytes: u64,
    pub vertices: u32,
    pub indices: u32,
    pub faces: u32,
    pub edges: u32,
    pub edge_indices: u32,
    pub records: u32,
    pub mesh_files: u32,
    pub ranges: Vec<RecordRange>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct RecordRange {
    pub slot: u32,
    pub record_id: String,
    pub vertex_start: u32,
    pub vertex_count: u32,
    pub index_start: u32,
    pub index_count: u32,
    pub mesh_files: u32,
}

#[derive(Debug, Deserialize, Clone, Copy)]
pub struct Bbox {
    pub min: [f64; 3],
    pub max: [f64; 3],
}

impl Bbox {
    pub fn centre(&self) -> [f64; 3] {
        [
            (self.min[0] + self.max[0]) / 2.0,
            (self.min[1] + self.max[1]) / 2.0,
            (self.min[2] + self.max[2]) / 2.0,
        ]
    }
    pub fn span(&self) -> [f64; 3] {
        [
            self.max[0] - self.min[0],
            self.max[1] - self.min[1],
            self.max[2] - self.min[2],
        ]
    }
}

/// One entry of records.json — kept as raw JSON plus typed accessors,
/// because bone and muscle records carry different field sets and the
/// panel shows what is present (same rule as the web shell).
#[derive(Debug, Clone)]
pub struct Record {
    pub raw: Value,
}

impl Record {
    pub fn get_str(&self, key: &str) -> Option<&str> {
        self.raw.get(key).and_then(|v| v.as_str())
    }
    pub fn id(&self) -> &str {
        self.get_str("id").unwrap_or("<no id>")
    }
    pub fn name(&self) -> &str {
        self.get_str("name").unwrap_or_else(|| self.id())
    }
    pub fn layer(&self) -> Option<LayerKind> {
        match self.get_str("layer") {
            Some("skeleton") => Some(LayerKind::Skeleton),
            Some("muscle") => Some(LayerKind::Muscle),
            _ => None,
        }
    }
    pub fn slot(&self) -> Option<u32> {
        self.raw.get("slot").and_then(|v| v.as_u64()).map(|v| v as u32)
    }
    pub fn has_geometry(&self) -> bool {
        self.raw
            .get("has_geometry")
            .and_then(|v| v.as_bool())
            .unwrap_or(false)
    }
    pub fn bbox(&self) -> Option<Bbox> {
        let b = self.raw.get("bbox_canonical_cm")?;
        if b.is_null() {
            return None;
        }
        serde_json::from_value(b.clone()).ok()
    }
}

#[derive(Debug)]
pub struct RecordsFile {
    pub records: Vec<Record>,
    pub clinical: BTreeMap<String, Value>,
}

impl RecordsFile {
    /// Resolve (layer, slot) → record, the shared picking scheme.
    pub fn by_slot(&self, kind: LayerKind, slot: u32) -> Option<&Record> {
        self.records
            .iter()
            .find(|r| r.layer() == Some(kind) && r.slot() == Some(slot))
    }

    pub fn by_id(&self, id: &str) -> Option<&Record> {
        self.records.iter().find(|r| r.id() == id)
    }

    /// Union of the bboxes of all records with geometry in `kinds`
    /// (canonical cm) — the framing target both shells aim at.
    pub fn union_bbox(&self, kinds: &[LayerKind]) -> Option<Bbox> {
        let mut mn = [f64::INFINITY; 3];
        let mut mx = [f64::NEG_INFINITY; 3];
        let mut any = false;
        for r in &self.records {
            if !kinds.contains(&r.layer()?) {
                continue;
            }
            if let Some(b) = r.bbox() {
                any = true;
                for i in 0..3 {
                    mn[i] = mn[i].min(b.min[i]);
                    mx[i] = mx[i].max(b.max[i]);
                }
            }
        }
        if any {
            Some(Bbox { min: mn, max: mx })
        } else {
            None
        }
    }
}

pub fn load_manifest(path: &Path) -> Result<Manifest, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    serde_json::from_str(&text).map_err(|e| format!("parse {}: {e}", path.display()))
}

pub fn load_records(path: &Path) -> Result<RecordsFile, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    let v: Value =
        serde_json::from_str(&text).map_err(|e| format!("parse {}: {e}", path.display()))?;
    let records = v
        .get("records")
        .and_then(|r| r.as_array())
        .ok_or("records.json: no records array")?
        .iter()
        .map(|raw| Record { raw: raw.clone() })
        .collect();
    let clinical = match v.get("clinical") {
        Some(Value::Object(m)) => m.iter().map(|(k, val)| (k.clone(), val.clone())).collect(),
        _ => BTreeMap::new(),
    };
    Ok(RecordsFile { records, clinical })
}

/// Human-readable record panel text — the native shell's record-panel
/// data hook (console here; the design's clinical UI layer later).
/// Shows the fields the record actually carries, plus the linked
/// Milestone-4 clinical record for muscles, verify flags in full.
pub fn panel_text(records: &RecordsFile, rec: &Record) -> String {
    let mut s = String::new();
    let layer = rec.layer().map(|k| k.label()).unwrap_or("?");
    s.push_str(&format!("{} — {} [{}]\n", rec.name(), rec.id(), layer));
    let fields: &[(&str, &str)] = match rec.layer() {
        Some(LayerKind::Skeleton) => &[
            ("ta", "TA name"),
            ("division", "Division"),
            ("region", "Region"),
            ("subgroup", "Subgroup"),
            ("side", "Side"),
            ("classification", "Classification"),
            ("description", "Description"),
        ],
        _ => &[
            ("side", "Side"),
            ("representation", "Representation"),
            ("region_group", "Region group"),
            ("group_path", "Group path"),
        ],
    };
    for (key, label) in fields {
        if let Some(v) = rec.get_str(key) {
            if !v.is_empty() {
                s.push_str(&format!("  {label}: {v}\n"));
            }
        }
    }
    if let Some(arts) = rec.raw.get("articulations").and_then(|v| v.as_array()) {
        let names: Vec<String> = arts
            .iter()
            .map(|a| match a {
                Value::String(t) => t.clone(),
                Value::Object(o) => o
                    .get("name")
                    .and_then(|n| n.as_str())
                    .unwrap_or("?")
                    .to_string(),
                _ => "?".to_string(),
            })
            .collect();
        if !names.is_empty() {
            s.push_str(&format!("  Articulations: {}\n", names.join(", ")));
        }
    }
    if let Some(b) = rec.bbox() {
        s.push_str(&format!(
            "  BBox (canonical cm): min [{:.2}, {:.2}, {:.2}]  max [{:.2}, {:.2}, {:.2}]\n",
            b.min[0], b.min[1], b.min[2], b.max[0], b.max[1], b.max[2]
        ));
    }
    if !rec.has_geometry() {
        if let Some(note) = rec.get_str("geometry_note") {
            s.push_str(&format!("  Geometry: NONE — {note}\n"));
        } else {
            s.push_str("  Geometry: NONE\n");
        }
    }
    if let Some(cm) = rec
        .raw
        .get("cross_midline_fraction")
        .and_then(|v| v.as_f64())
    {
        if cm > 0.005 {
            s.push_str(&format!(
                "  Cross-midline vertices in source mesh: {:.1}%\n",
                cm * 100.0
            ));
        }
    }
    // Linked clinical record (muscles): Milestone-4 sourced fields.
    let clinical_id = rec
        .get_str("clinical_id")
        .map(|s| s.to_string())
        .or_else(|| {
            if rec.layer() == Some(LayerKind::Muscle) && records.clinical.contains_key(rec.id()) {
                Some(rec.id().to_string())
            } else {
                None
            }
        });
    if let Some(cid) = clinical_id {
        if let Some(c) = records.clinical.get(&cid) {
            s.push_str(&format!("  — clinical record {cid}"));
            if let Some(tier) = c.get("sourcing_tier").and_then(|v| v.as_str()) {
                s.push_str(&format!(" (sourcing tier {tier})"));
            }
            s.push('\n');
            for (key, label) in [
                ("origin", "Origin"),
                ("insertion", "Insertion"),
                ("innervation", "Innervation"),
                ("arterial_supply", "Arterial supply"),
            ] {
                if let Some(v) = c.get(key).and_then(|v| v.as_str()) {
                    if !v.is_empty() {
                        s.push_str(&format!("    {label}: {v}\n"));
                    }
                }
            }
            if let Some(actions) = c.get("actions").and_then(|v| v.as_array()) {
                let a: Vec<&str> = actions.iter().filter_map(|v| v.as_str()).collect();
                if !a.is_empty() {
                    s.push_str(&format!("    Actions: {}\n", a.join("; ")));
                }
            }
            if let Some(verify) = c.get("verify").and_then(|v| v.as_array()) {
                for flag in verify {
                    if let Some(t) = flag.as_str() {
                        s.push_str(&format!("    ⚠ verify: {t}\n"));
                    } else if let Some(o) = flag.as_object() {
                        s.push_str(&format!("    ⚠ verify: {}\n", flatten_obj(o)));
                    }
                }
            }
            if let Some(note) = c.get("note").and_then(|v| v.as_str()) {
                if !note.is_empty() {
                    s.push_str(&format!("    Note: {note}\n"));
                }
            }
        }
    }
    s
}

fn flatten_obj(o: &Map<String, Value>) -> String {
    o.iter()
        .map(|(k, v)| format!("{k}={v}"))
        .collect::<Vec<_>>()
        .join(", ")
}
