//! Manifest + records model: the JSON side of the shell data pack
//! (`web/data/manifest.json`, `web/data/records.json`), parsed with
//! the same field names the web shell uses. The manifest's per-record
//! ranges are the slot scheme shared by both shells: slot `n` of a
//! layer is `ranges[n]`, and the pack's per-vertex recordIds are
//! those slots — picking in either shell resolves through this table.
//!
//! Milestone 16: layers are the eleven Body Model systems. There is
//! no hardcoded layer enum — the manifest is the source of truth for
//! each layer's key, pick bit, label and colour (written there by
//! tools/pack_geometry.py; the web shell's literals are asserted
//! against it by tools/verify_web.js W1/W6).

use serde::Deserialize;
use serde_json::{Map, Value};
use std::collections::BTreeMap;
use std::path::Path;

/// One Body Model layer (system), as declared by the manifest.
#[derive(Debug, Clone, PartialEq)]
pub struct LayerInfo {
    /// System key: manifest "layers" key, pack file stem, and the
    /// `layer` field value in records.json — one name everywhere.
    pub key: String,
    pub label: String,
    /// Pick-id layer bit (1..=11), identical to the web shell's
    /// LAYER_BIT for this key.
    pub pick_bit: u32,
    /// Base colour, identical to the web shell's LAYER_STYLE.
    pub color: [f32; 3],
}

impl LayerInfo {
    pub fn from_manifest(manifest: &Manifest) -> Vec<LayerInfo> {
        manifest
            .layer_order
            .iter()
            .filter_map(|key| {
                let l = manifest.layers.get(key)?;
                Some(LayerInfo {
                    key: key.clone(),
                    label: l.label.clone(),
                    pick_bit: l.pick_bit,
                    color: l.color,
                })
            })
            .collect()
    }

    pub fn by_key<'a>(layers: &'a [LayerInfo], key: &str) -> Option<&'a LayerInfo> {
        layers.iter().find(|l| l.key == key)
    }

    pub fn by_pick_bit(layers: &[LayerInfo], bit: u32) -> Option<&LayerInfo> {
        layers.iter().find(|l| l.pick_bit == bit)
    }
}

/// Encode/decode the pick id: `id = (layer_bit << 24) | slot`,
/// byte 3 of the id riding in the framebuffer's alpha channel
/// (alpha 0 = miss; 1..=11 = hit + layer). This is the codec the
/// Milestone-7 roundtrip test specified and Milestone 7-FIX shipped
/// in the web shell; both shells now implement exactly this, and the
/// web side is regression-gated by tools/verify_web.js W6, which
/// executes the shipped decoder over every slot of every layer.
pub fn encode_pick_id(pick_bit: u32, slot: u32) -> u32 {
    (pick_bit << 24) | (slot & 0x00FF_FFFF)
}

pub fn decode_pick_id(rgba: [u8; 4], layers: &[LayerInfo]) -> Option<(String, u32)> {
    if rgba[3] == 0 {
        return None;
    }
    let id = (rgba[0] as u32)
        | ((rgba[1] as u32) << 8)
        | ((rgba[2] as u32) << 16)
        | ((rgba[3] as u32) << 24);
    let info = LayerInfo::by_pick_bit(layers, id >> 24)?;
    Some((info.key.clone(), id & 0x00FF_FFFF))
}

#[derive(Debug, Deserialize)]
pub struct Manifest {
    pub layer_order: Vec<String>,
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
    pub pick_bit: u32,
    pub label: String,
    pub color: [f32; 3],
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
    pub cross_midline_fraction: Option<f64>,
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
/// because the systems' records carry different field sets and the
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
    /// The record's layer key (a Body Model system), if it carries one.
    pub fn layer(&self) -> Option<&str> {
        self.get_str("layer")
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
    pub fn clinical_ids(&self) -> Vec<String> {
        self.raw
            .get("clinical_ids")
            .and_then(|v| v.as_array())
            .map(|a| {
                a.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default()
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
    /// Resolve (layer key, slot) → record, the shared picking scheme.
    pub fn by_slot(&self, layer_key: &str, slot: u32) -> Option<&Record> {
        self.records
            .iter()
            .find(|r| r.layer() == Some(layer_key) && r.slot() == Some(slot))
    }

    pub fn by_id(&self, id: &str) -> Option<&Record> {
        self.records.iter().find(|r| r.id() == id)
    }

    /// Union of the bboxes of all records with geometry in `keys`
    /// (canonical cm) — the framing target both shells aim at.
    pub fn union_bbox(&self, keys: &[&str]) -> Option<Bbox> {
        let mut mn = [f64::INFINITY; 3];
        let mut mx = [f64::NEG_INFINITY; 3];
        let mut any = false;
        for r in &self.records {
            match r.layer() {
                Some(k) if keys.contains(&k) => {}
                _ => continue,
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

/// Render a clinical field value of any authored shape (string,
/// list of scalars, nested object) as one line of panel text.
fn fmt_value(v: &Value) -> Option<String> {
    match v {
        Value::String(s) if !s.is_empty() => Some(s.clone()),
        Value::Number(n) => Some(n.to_string()),
        Value::Bool(b) => Some(b.to_string()),
        Value::Array(a) => {
            let parts: Vec<String> = a.iter().filter_map(fmt_value).collect();
            if parts.is_empty() {
                None
            } else {
                Some(parts.join("; "))
            }
        }
        Value::Object(o) => Some(flatten_obj(o)),
        _ => None,
    }
}

/// Human-readable record panel text — the native shell's record-panel
/// data hook (console here; the design's clinical UI layer later).
/// Shows the fields the record actually carries, plus its linked
/// clinical records (all systems), verify flags in full.
pub fn panel_text(records: &RecordsFile, layers: &[LayerInfo], rec: &Record) -> String {
    let mut s = String::new();
    let layer_label = rec
        .layer()
        .and_then(|k| LayerInfo::by_key(layers, k))
        .map(|l| l.label.as_str())
        .unwrap_or("?");
    s.push_str(&format!("{} — {} [{}]\n", rec.name(), rec.id(), layer_label));
    let fields: &[(&str, &str)] = match rec.layer() {
        Some("skeletal") => &[
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
            ("region", "Region"),
            ("region_group", "Region group"),
            ("subtree", "Subtree"),
        ],
    };
    for (key, label) in fields {
        if let Some(v) = rec.get_str(key) {
            if !v.is_empty() {
                s.push_str(&format!("  {label}: {v}\n"));
            }
        }
    }
    if let Some(ids) = rec.raw.get("concept_ids").and_then(|v| v.as_array()) {
        let names: Vec<&str> = ids.iter().filter_map(|v| v.as_str()).collect();
        if !names.is_empty() {
            s.push_str(&format!("  FMA concepts: {}\n", names.join(", ")));
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
    // Linked clinical records (every system): sourced fields shown
    // in the shape they were authored; verify flags always in full.
    for cid in rec.clinical_ids() {
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
                ("actions", "Actions"),
                ("relations", "Relations"),
                ("contents", "Contents"),
                ("description", "Description"),
                ("clinical_significance", "Clinical significance"),
                ("prevalence", "Prevalence"),
            ] {
                if let Some(v) = c.get(key).and_then(fmt_value) {
                    s.push_str(&format!("    {label}: {v}\n"));
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
            if let Some(note) = c.get("note") {
                if let Some(t) = fmt_value(note) {
                    s.push_str(&format!("    Note: {t}\n"));
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
