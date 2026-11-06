//! ANW1 geometry pack reader — the same packs the web shell consumes
//! (written by `tools/pack_web_geometry.py`, format ANW1 v2).
//!
//! Layout (all little-endian):
//!   header 128 B: magic 'ANW1', u32 version, u32 vertexCount,
//!   u32 indexCount, u32 recordCount, u32 edgeIndexCount, then five
//!   u64 section offsets (positions, normals, recordIds, indices,
//!   edges) starting at byte 24.
//!   positions:  float32 x3 per vertex, canonical cm frame
//!               (x+ = subject right, y+ = up, z+ = anterior)
//!   normals:    int8 x4 per vertex (snorm xyz, pad 0), smooth
//!   recordIds:  uint32 per vertex — the record slot within the layer
//!   indices:    uint32 x3 per face
//!   edges:      uint32 x2 per unique undirected edge (wireframe)
//!
//! Version handshake (design/08 verification gates): a pack whose
//! format version this shell does not implement is refused, never
//! silently misread.

use std::fmt;
use std::path::Path;

pub const HEADER_BYTES: usize = 128;
pub const EXPECTED_VERSION: u32 = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PackHeader {
    pub version: u32,
    pub vertex_count: u32,
    pub index_count: u32,
    pub record_count: u32,
    pub edge_index_count: u32,
    /// Byte offsets of [positions, normals, record_ids, indices, edges].
    pub offsets: [u64; 5],
}

#[derive(Debug)]
pub enum PackError {
    Io(std::io::Error),
    TooSmall { len: usize },
    BadMagic([u8; 4]),
    UnsupportedVersion(u32),
    /// A section offset/size does not line up with the header counts.
    LayoutMismatch(String),
}

impl fmt::Display for PackError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PackError::Io(e) => write!(f, "io error: {e}"),
            PackError::TooSmall { len } => {
                write!(f, "pack too small: {len} bytes (< {HEADER_BYTES} header)")
            }
            PackError::BadMagic(m) => write!(f, "bad magic: {:?}", String::from_utf8_lossy(m)),
            PackError::UnsupportedVersion(v) => {
                write!(f, "unsupported ANW1 version {v} (this shell implements v{EXPECTED_VERSION})")
            }
            PackError::LayoutMismatch(s) => write!(f, "layout mismatch: {s}"),
        }
    }
}

impl std::error::Error for PackError {}

impl From<std::io::Error> for PackError {
    fn from(e: std::io::Error) -> Self {
        PackError::Io(e)
    }
}

fn u32_at(b: &[u8], off: usize) -> u32 {
    u32::from_le_bytes(b[off..off + 4].try_into().unwrap())
}

fn u64_at(b: &[u8], off: usize) -> u64 {
    u64::from_le_bytes(b[off..off + 8].try_into().unwrap())
}

fn read_u32s(bytes: &[u8], off: u64, count: u32) -> Vec<u32> {
    let (off, n) = (off as usize, count as usize);
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        out.push(u32_at(bytes, off + 4 * i));
    }
    out
}

/// One layer's merged static geometry, decoded into typed buffers.
#[derive(Debug)]
pub struct Pack {
    pub header: PackHeader,
    pub positions: Vec<[f32; 3]>,
    pub normals: Vec<[i8; 4]>,
    pub record_ids: Vec<u32>,
    pub indices: Vec<u32>,
    pub edges: Vec<u32>,
    pub file_bytes: u64,
}

impl Pack {
    pub fn load(path: &Path) -> Result<Pack, PackError> {
        let bytes = std::fs::read(path)?;
        Self::parse(&bytes)
    }

    pub fn parse(bytes: &[u8]) -> Result<Pack, PackError> {
        if bytes.len() < HEADER_BYTES {
            return Err(PackError::TooSmall { len: bytes.len() });
        }
        let magic: [u8; 4] = bytes[0..4].try_into().unwrap();
        if &magic != b"ANW1" {
            return Err(PackError::BadMagic(magic));
        }
        let version = u32_at(bytes, 4);
        if version != EXPECTED_VERSION {
            return Err(PackError::UnsupportedVersion(version));
        }
        let header = PackHeader {
            version,
            vertex_count: u32_at(bytes, 8),
            index_count: u32_at(bytes, 12),
            record_count: u32_at(bytes, 16),
            edge_index_count: u32_at(bytes, 20),
            offsets: [
                u64_at(bytes, 24),
                u64_at(bytes, 32),
                u64_at(bytes, 40),
                u64_at(bytes, 48),
                u64_at(bytes, 56),
            ],
        };
        let nv = header.vertex_count as u64;
        let ni = header.index_count as u64;
        let ne = header.edge_index_count as u64;
        let expect: [(u64, u64); 5] = [
            (128, nv * 12),
            (128 + nv * 12, nv * 4),
            (128 + nv * 16, nv * 4),
            (128 + nv * 20, ni * 4),
            (128 + nv * 20 + ni * 4, ne * 4),
        ];
        for (i, (want_off, size)) in expect.iter().enumerate() {
            let got_off = header.offsets[i];
            if got_off != *want_off {
                return Err(PackError::LayoutMismatch(format!(
                    "section {i}: offset {got_off} != expected {want_off}"
                )));
            }
            let end = got_off + size;
            if end as usize > bytes.len() {
                return Err(PackError::LayoutMismatch(format!(
                    "section {i}: end {end} beyond file length {}",
                    bytes.len()
                )));
            }
        }
        let total = expect[4].0 + expect[4].1;
        if total as usize != bytes.len() {
            return Err(PackError::LayoutMismatch(format!(
                "computed pack size {total} != file length {}",
                bytes.len()
            )));
        }

        let [po, no, ro, io, eo] = header.offsets;
        let n = header.vertex_count as usize;
        let mut positions = Vec::with_capacity(n);
        for i in 0..n {
            let o = po as usize + 12 * i;
            positions.push([
                f32::from_le_bytes(bytes[o..o + 4].try_into().unwrap()),
                f32::from_le_bytes(bytes[o + 4..o + 8].try_into().unwrap()),
                f32::from_le_bytes(bytes[o + 8..o + 12].try_into().unwrap()),
            ]);
        }
        let mut normals = Vec::with_capacity(n);
        for i in 0..n {
            let o = no as usize + 4 * i;
            normals.push([
                bytes[o] as i8,
                bytes[o + 1] as i8,
                bytes[o + 2] as i8,
                bytes[o + 3] as i8,
            ]);
        }
        let record_ids = read_u32s(bytes, ro, header.vertex_count);
        let indices = read_u32s(bytes, io, header.index_count);
        let edges = read_u32s(bytes, eo, header.edge_index_count);
        Ok(Pack {
            file_bytes: bytes.len() as u64,
            header,
            positions,
            normals,
            record_ids,
            indices,
            edges,
        })
    }

    /// Axis-aligned bounds over all positions (canonical cm).
    pub fn bounds(&self) -> ([f32; 3], [f32; 3]) {
        let mut mn = [f32::INFINITY; 3];
        let mut mx = [f32::NEG_INFINITY; 3];
        for p in &self.positions {
            for i in 0..3 {
                mn[i] = mn[i].min(p[i]);
                mx[i] = mx[i].max(p[i]);
            }
        }
        (mn, mx)
    }

    /// Bounds of one record's vertex range (canonical cm).
    pub fn range_bounds(&self, vertex_start: u32, vertex_count: u32) -> ([f32; 3], [f32; 3]) {
        let mut mn = [f32::INFINITY; 3];
        let mut mx = [f32::NEG_INFINITY; 3];
        for p in &self.positions[vertex_start as usize..(vertex_start + vertex_count) as usize] {
            for i in 0..3 {
                mn[i] = mn[i].min(p[i]);
                mx[i] = mx[i].max(p[i]);
            }
        }
        (mn, mx)
    }
}
