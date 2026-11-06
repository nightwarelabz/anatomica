"use strict";
/* ANATOMICA web shell — Imaging mode (Milestone 19, Imaging v1).
   OHIF-pattern 2D viewer over the synthetic derived CT series in
   web/data/imaging.json (+ per-slice bins written by
   tools/imaging_derive.py). The atlas (viewer.js) is untouched: this
   file only adds a mode. Structure identity is shared with the atlas
   through records.json — a voxel whose label is crosswalked to a
   Body Model record opens the SAME record panel (select() from
   viewer.js); a record selected in the atlas highlights its label
   here. Labels with no adjudicated mapping stay source labels and
   never open a record.

   Display: slices are stored in DICOM display order (see
   imaging.json geometry.stored_orientation) and drawn as stored —
   patient left on screen right, anterior up (radiological
   convention). Window/level presets are the cited values in
   imaging.json meta.presets. Every subject is a different
   individual from the atlas Body Model — the manifest's provenance
   note says so, and so does the banner.

   Subjects (Milestone 32): imaging.json is a combined manifest —
   shared meta (presets, provenance) plus one block per derived
   subject (geometry, file patterns, labels, crosswalk accounting).
   The sidebar switcher swaps the ACTIVE subject via
   imgApplySubject(): series list, banner, legend, slice/MPR ranges
   and canvas size are rebuilt for the new subject, and no volatile
   state crosses over — the slice cache and the MPR volume are
   dropped, any label isolation is released, and the crosshair
   re-centres. img.man always holds the ACTIVE subject's effective
   manifest (shared meta merged with its block), so the rendering,
   picking and MPR code below reads exactly one subject at a time.

   MPR (Milestone 31): coronal and sagittal planes resliced from the
   same in-memory volume alongside the axial view — a pure
   re-indexing of stored voxels (no interpolation, no resampling of
   the stored data, no derived MPR files: display-only). All three
   planes share one voxel coordinate (img.vox); each plane draws the
   crosshair lines the other two imply, computed by the same
   mprPixel() the verifier executes. Plane display aspect derives
   from the recorded spacing, so an anisotropic volume would render
   true-shape rather than silently stretched (s0778 is 1.5 mm
   isotropic — the aspect is then exactly the voxel aspect). */

const IMG_GROUP_ORDER = ["skeletal", "cardiovascular", "respiratory", "digestive",
  "urinary", "lymphatic", "endocrine", "nervous", "muscular", "integumentary/other"];

const img = {
  mode: "atlas",
  booted: false,
  all: null,            // imaging.json (combined manifest, Milestone 32)
  subjId: null,         // active subject id
  man: null,            // ACTIVE subject's effective manifest
  byIndex: new Map(),   // label index -> manifest label entry
  labelsByRecord: new Map(), // record id -> [label indices] (mapped only)
  slice: 0,
  ww: 350, wl: 50,
  overlay: true, alpha: 0.5,
  solo: null,           // label index or null
  cache: new Map(),     // slice -> {hu: Int16Array, lbl: Uint8Array}
  cur: null,            // current slice data
  mpr: false,           // tri-plane layout on/off (Milestone 31)
  vol: null,            // {hu: Int16Array, lbl: Uint8Array} whole volume, stored order
  volLoading: false,
  vox: { c: 131, r: 131, k: 0 },  // the one shared crosshair voxel (stored coords)
};

const imgPath = (pattern, k) =>
  "data/" + pattern.replace("{slice:04d}", String(k).padStart(4, "0"));

// === MPR CORE BEGIN (pure index geometry — no DOM, no viewer state;
// verify_web W10 slices this block out of the shipped source and
// executes it verbatim against the shipped bins) ===
// Stored orientation (Milestone 19): the volume arrays are indexed
// vol[(k*rows + r)*cols + c]; stored voxel (c, r, k) centre sits at
// LPS mm  ipp0 + (c*spacing[0], r*spacing[1], k*spacing[2]).
// A plane pixel IS a stored voxel — extraction is exact re-indexing,
// never interpolation. Display conventions (radiological):
//   axial    index k: u = c (patient left on screen right),
//                     v = r (anterior up)
//   coronal  index r: u = c (patient left on screen right),
//                     v from the top = superior, so k = slices-1-v
//   sagittal index c: viewed from the patient's left side —
//                     u = r (anterior on screen left),
//                     v from the top = superior, k = slices-1-v
function mprPlaneDims(plane, dims) {
  if (plane === "axial") return { w: dims.cols, h: dims.rows, through: "k", max: dims.slices - 1 };
  if (plane === "coronal") return { w: dims.cols, h: dims.slices, through: "r", max: dims.rows - 1 };
  return { w: dims.rows, h: dims.slices, through: "c", max: dims.cols - 1 };
}
function mprPlanePhysical(plane, dims, spacing) {
  // Physical extent (mm) of the plane's u/v axes, from the recorded
  // spacing — display aspect derives from these numbers, so an
  // anisotropic volume renders true-shape instead of stretched.
  const d = mprPlaneDims(plane, dims);
  const su = plane === "sagittal" ? spacing[1] : spacing[0];
  const sv = plane === "axial" ? spacing[1] : spacing[2];
  return { wMm: d.w * su, hMm: d.h * sv, uMm: su, vMm: sv };
}
function mprVoxel(plane, idx, u, v, dims) {
  if (plane === "axial") return { c: u, r: v, k: idx };
  if (plane === "coronal") return { c: u, r: idx, k: dims.slices - 1 - v };
  return { c: idx, r: u, k: dims.slices - 1 - v };
}
function mprPixel(plane, vox, dims) {
  // Inverse of mprVoxel: the plane index the voxel lies on, and its
  // pixel there — the crosshair correspondence between planes.
  if (plane === "axial") return { idx: vox.k, u: vox.c, v: vox.r };
  if (plane === "coronal") return { idx: vox.r, u: vox.c, v: dims.slices - 1 - vox.k };
  return { idx: vox.c, u: vox.r, v: dims.slices - 1 - vox.k };
}
function mprExtract(hu, lbl, dims, plane, idx) {
  const d = mprPlaneDims(plane, dims);
  const phu = new Int16Array(d.w * d.h), plb = new Uint8Array(d.w * d.h);
  for (let v = 0; v < d.h; v++) for (let u = 0; u < d.w; u++) {
    const x = mprVoxel(plane, idx, u, v, dims);
    const s = (x.k * dims.rows + x.r) * dims.cols + x.c, t = v * d.w + u;
    phu[t] = hu[s]; plb[t] = lbl[s];
  }
  return { w: d.w, h: d.h, hu: phu, lbl: plb };
}
function mprLps(vox, geo) {
  return [geo.ipp_first_slice_lps_mm[0] + vox.c * geo.spacing_mm[0],
          geo.ipp_first_slice_lps_mm[1] + vox.r * geo.spacing_mm[1],
          geo.ipp_first_slice_lps_mm[2] + vox.k * geo.spacing_mm[2]];
}
// === MPR CORE END ===

// Series list for the ACTIVE subject (OHIF-pattern: one study,
// image series + overlay series). Rebuilt on every subject switch.
function imgBuildSeries() {
  const man = img.man, g = man.geometry, dims = g.dims_voxels, subj = man.meta.subject;
  $("imgSeries").innerHTML =
    `<div class="series"><b>CT · axial + MPR</b> — SYNTHETIC derived series; coronal/sagittal planes are resliced in-browser from the same volume (display-only — no MPR files, no resampling)<br>
       <span class="sm">${dims.slices} slices · ${dims.cols}×${dims.rows} · ` +
       `${g.spacing_mm.map(v => v.toFixed(1)).join("×")} mm · source: ${esc(subj.id)} ` +
       `(${esc(subj.meta_csv_row.study_type)})<br>${esc(subj.dataset)}</span></div>
     <div class="series"><b>SEG · label overlay</b><br>
       <span class="sm">${man.crosswalk_totals.labels_in_source_set} TotalSegmentator labels · ` +
       `${man.crosswalk_totals.labels_mapped} crosswalked to Body Model records · ` +
       `${man.crosswalk_totals.labels_unmapped} source-only (flagged)</span></div>`;
}

// Legend for the ACTIVE subject, grouped by system (M3 grouping),
// present labels first-class, absent ones greyed. Rebuilt (and its
// row handlers rebound) on every subject switch.
function imgBuildLegend() {
  const groups = new Map();
  for (const e of img.man.labels) {
    if (!groups.has(e.system_group)) groups.set(e.system_group, []);
    groups.get(e.system_group).push(e);
  }
  const frag = [];
  for (const grp of IMG_GROUP_ORDER) {
    const es = groups.get(grp);
    if (!es) continue;
    frag.push(`<div class="lgroup">${esc(grp)}</div>`);
    for (const e of es) {
      const [r, gg, b] = e.color_rgb;
      const rec = e.mapping_status === "mapped"
        ? e.records.map(x => esc(x.name)).join(" + ")
        : (e.candidate_record_ids && e.candidate_record_ids.length
            ? "unmapped — source label (candidates unadjudicated)"
            : "unmapped — source label");
      frag.push(`<div class="lrow${e.present_in_subject ? "" : " absent"}" data-lbl="${e.index}">
        <span class="chip" style="background:rgb(${r},${gg},${b})"></span>
        <span class="nm">${esc(e.label)}<br><span class="rc">${rec}</span></span>
        <span class="rc">${e.present_in_subject ? e.voxels.toLocaleString() + " vox" : "not in scan"}</span></div>`);
    }
  }
  $("imgLegend").innerHTML = frag.join("");
  $("imgLegend").querySelectorAll(".lrow").forEach(row => {
    row.addEventListener("click", () => {
      const idx = +row.dataset.lbl;
      const e = img.byIndex.get(idx);
      if (!e.present_in_subject) return;
      img.solo = img.solo === idx ? null : idx;
      $("imgLegend").querySelectorAll(".lrow.solo").forEach(x => x.classList.remove("solo"));
      if (img.solo) row.classList.add("solo");
      imgRender();
    });
  });
}

// Make one manifest subject active (Milestone 32). img.man becomes
// that subject's effective manifest — the combined manifest's shared
// meta merged with the subject block — and EVERY piece of volatile
// per-subject state is reset: slice cache, current slice, whole MPR
// volume, label isolation, crosshair voxel, slider ranges, canvas
// size. Nothing computed from the previous subject survives a switch.
async function imgApplySubject(id) {
  const blk = img.all.subjects[id];
  if (!blk) return;
  img.subjId = id;
  img.man = {
    meta: Object.assign({}, img.all.meta, blk.meta),
    geometry: blk.geometry, files: blk.files,
    crosswalk_totals: blk.crosswalk_totals, labels: blk.labels,
  };
  img.byIndex = new Map();
  img.labelsByRecord = new Map();
  for (const e of img.man.labels) {
    img.byIndex.set(e.index, e);
    for (const rid of e.record_ids || [])
      img.labelsByRecord.set(rid, [...(img.labelsByRecord.get(rid) || []), e.index]);
  }
  img.cache = new Map();
  img.cur = null;
  img.vol = null;
  img.volLoading = false;
  img.solo = null;
  if (img.mpr) {  // MPR volume belongs to the old subject — close it
    img.mpr = false;
    $("imgMprBtn").classList.remove("on");
    $("mprGrid").hidden = true;
    $("imgCanvas").style.display = "";
  }
  document.querySelectorAll("#imgSubjects button").forEach(b =>
    b.classList.toggle("on", b.dataset.subj === id));
  $("imgBanner").textContent = img.man.meta.banner + " · " + img.man.meta.provenance_note;
  $("imgHover").textContent = "";
  imgBuildSeries();
  imgBuildLegend();
  const g = img.man.geometry, dims = g.dims_voxels;
  $("imgSlice").max = dims.slices - 1;
  const cvs = $("imgCanvas");
  cvs.width = dims.cols; cvs.height = dims.rows;
  $("mprAx").max = dims.slices - 1;
  $("mprCor").max = dims.rows - 1;
  $("mprSag").max = dims.cols - 1;
  // crosshair re-centres on the new volume; the axial slice starts at
  // the liver centroid slice when available (a slice a reader
  // recognises), else mid-volume — the Milestone 19 start rule
  img.vox = { c: Math.floor(dims.cols / 2), r: Math.floor(dims.rows / 2), k: 0 };
  const liver = img.man.labels.find(e => e.label === "liver" && e.geometry_lps);
  img.slice = liver
    ? Math.round((liver.geometry_lps.centroid_lps_mm[2] - g.ipp_first_slice_lps_mm[2]) / g.spacing_mm[2])
    : Math.floor(dims.slices / 2);
  imgSetWindow(img.ww, img.wl);
  await imgSetSlice(img.slice);
}

async function imgBoot() {
  if (img.booted) return;
  img.booted = true;
  const man = await fetch("data/imaging.json").then(r => r.json());
  img.all = man;
  // subject switcher (Milestone 32): one button per derived subject
  const subjBar = $("imgSubjects");
  for (const id of Object.keys(man.subjects)) {
    const row = man.subjects[id].meta.subject.meta_csv_row;
    const b = document.createElement("button");
    b.dataset.subj = id;
    b.textContent = `${id} · ${row.age} y ${row.gender} · ${row.study_type}`;
    b.addEventListener("click", () => imgApplySubject(id));
    subjBar.appendChild(b);
  }
  // presets (values + citations ship in the manifest)
  const presets = $("imgPresets");
  for (const p of man.meta.presets) {
    const b = document.createElement("button");
    b.className = "preset"; b.textContent = `${p.label} W${p.window_width}/L${p.window_level}`;
    b.addEventListener("click", () => imgSetWindow(p.window_width, p.window_level));
    presets.appendChild(b);
  }
  presets.insertAdjacentHTML("beforeend",
    `<p style="color:var(--dim);font-size:11px;margin:6px 0 0">Preset values as cited in ` +
    `imaging.json (${man.meta.preset_sources.length} consulted sources).</p>`);
  // controls (registered once; handlers read the ACTIVE subject
  // through img.man at event time, so a subject switch needs no
  // re-wiring — ranges and canvas size are set by imgApplySubject)
  const slider = $("imgSlice");
  slider.addEventListener("input", () => imgSetSlice(+slider.value));
  $("imgPrev").addEventListener("click", () => imgSetSlice(img.slice - 1));
  $("imgNext").addEventListener("click", () => imgSetSlice(img.slice + 1));
  $("imgWW").addEventListener("input", () => imgSetWindow(+$("imgWW").value, img.wl, true));
  $("imgWL").addEventListener("input", () => imgSetWindow(img.ww, +$("imgWL").value, true));
  $("imgOverlay").addEventListener("change", () => { img.overlay = $("imgOverlay").checked; imgRender(); });
  $("imgAlpha").addEventListener("input", () => {
    img.alpha = +$("imgAlpha").value; $("imgAlphaVal").textContent = img.alpha.toFixed(2); imgRender();
  });
  $("imgAlphaVal").textContent = img.alpha.toFixed(2);
  const cvs = $("imgCanvas");
  cvs.addEventListener("click", ev => {
    const v = imgEventVoxel(ev);
    if (v) imgIdentify(v.c, v.r);
  });
  cvs.addEventListener("mousemove", ev => {
    const v = imgEventVoxel(ev);
    if (!v || !img.cur) return;
    const dims = img.man.geometry.dims_voxels;
    const hu = img.cur.hu[v.r * dims.cols + v.c];
    const li = img.cur.lbl[v.r * dims.cols + v.c];
    const name = li ? img.byIndex.get(li).label : "—";
    $("imgHover").textContent = `HU ${hu} · ${name}`;
  });
  cvs.addEventListener("wheel", ev => {
    ev.preventDefault();
    imgSetSlice(img.slice + (ev.deltaY > 0 ? 1 : -1));
  }, { passive: false });
  document.addEventListener("keydown", ev => {
    if (img.mode !== "imaging") return;
    if (ev.key === "ArrowDown") imgSetSlice(img.slice + 1);
    else if (ev.key === "ArrowUp") imgSetSlice(img.slice - 1);
    else if (ev.key === "PageDown") imgSetSlice(img.slice + 10);
    else if (ev.key === "PageUp") imgSetSlice(img.slice - 10);
    else return;
    ev.preventDefault();
  });
  // ---- MPR wiring (Milestone 31) ----
  $("mprAx").addEventListener("input", () => imgSetVox({ k: +$("mprAx").value }));
  $("mprCor").addEventListener("input", () => imgSetVox({ r: +$("mprCor").value }));
  $("mprSag").addEventListener("input", () => imgSetVox({ c: +$("mprSag").value }));
  for (const [plane, cvId] of [["axial", "imgAx"], ["coronal", "imgCor"], ["sagittal", "imgSag"]]) {
    const cv = $(cvId);
    cv.addEventListener("click", ev => {
      const v = imgPaneEventVoxel(ev, plane);
      if (!v) return;
      imgSetVox(v);
      imgIdentify(v.c, v.r, v.k, plane);
    });
    cv.addEventListener("mousemove", ev => {
      const v = imgPaneEventVoxel(ev, plane);
      if (!v) return;
      const d = imgVoxelData(v.c, v.r, v.k);
      if (!d) return;
      const lps = mprLps(v, img.man.geometry).map(x => x.toFixed(1)).join(", ");
      const name = d.lbl ? img.byIndex.get(d.lbl).label : "—";
      $("imgHover").textContent =
        `${plane} · voxel (c ${v.c}, r ${v.r}, k ${v.k}) · LPS (${lps}) mm · HU ${d.hu} · ${name}`;
    });
    cv.addEventListener("wheel", ev => {
      ev.preventDefault();
      const step = ev.deltaY > 0 ? 1 : -1,
            through = mprPlaneDims(plane, img.man.geometry.dims_voxels).through;
      imgSetVox({ [through]: img.vox[through] + step });
    }, { passive: false });
  }
  $("imgMprBtn").addEventListener("click", () => imgSetMpr(!img.mpr));
  window.addEventListener("resize", () => { if (img.mpr && img.vol) imgRenderMpr(); });
  // the default subject becomes active (builds series list, legend,
  // ranges; loads its starting slice)
  await imgApplySubject(man.default_subject || Object.keys(man.subjects)[0]);
}

function imgEventVoxel(ev) {
  const cvs = $("imgCanvas"), rect = cvs.getBoundingClientRect();
  const { cols, rows } = img.man.geometry.dims_voxels;
  const c = Math.floor((ev.clientX - rect.left) / rect.width * cols);
  const r = Math.floor((ev.clientY - rect.top) / rect.height * rows);
  return (c >= 0 && c < cols && r >= 0 && r < rows) ? { c, r } : null;
}

async function imgLoadSlice(k) {
  if (img.cache.has(k)) return img.cache.get(k);
  const man = img.man, subjAtStart = img.subjId;
  const [huBuf, lblBuf] = await Promise.all([
    fetch(imgPath(man.files.hu, k)).then(r => r.arrayBuffer()),
    fetch(imgPath(man.files.labels, k)).then(r => r.arrayBuffer()),
  ]);
  const d = { hu: new Int16Array(huBuf), lbl: new Uint8Array(lblBuf) };
  // a subject switch mid-flight must not seed the NEW subject's
  // cache with the old subject's slices (same indices, other volume)
  if (img.subjId === subjAtStart) {
    img.cache.set(k, d);
    if (img.cache.size > 24) img.cache.delete(img.cache.keys().next().value);
  }
  return d;
}

let imgLoadToken = 0;
async function imgSetSlice(k) {
  const n = img.man.geometry.dims_voxels.slices;
  img.slice = Math.max(0, Math.min(n - 1, k));
  $("imgSlice").value = img.slice;
  const token = ++imgLoadToken, target = img.slice;
  const data = await imgLoadSlice(target);
  if (token !== imgLoadToken) return; // superseded while loading
  img.cur = data;
  img.vox.k = img.slice;   // the MPR crosshair rides the axial slice
  imgRender();
}

function imgSetWindow(ww, wl, fromSlider = false) {
  img.ww = Math.max(1, ww); img.wl = wl;
  if (!fromSlider) { $("imgWW").value = img.ww; $("imgWL").value = img.wl; }
  $("imgWWVal").textContent = img.ww;
  $("imgWLVal").textContent = img.wl;
  document.querySelectorAll("#imgPresets .preset").forEach(b => {
    const m = b.textContent.match(/W(\d+)\/L(-?\d+)/);
    b.classList.toggle("on", m && +m[1] === img.ww && +m[2] === img.wl);
  });
  imgRender();
}

function imgEmphasis() {
  if (img.solo) return new Set([img.solo]);
  if (typeof selected !== "undefined" && selected && img.labelsByRecord.has(selected.id))
    return new Set(img.labelsByRecord.get(selected.id));
  return null;
}

// The ONE shading path — axial view and every MPR plane paint through
// here, so window/level presets and the label overlay apply identically
// across planes by construction.
function imgPaint(ctx, w, h, hu, lbl) {
  const out = ctx.createImageData(w, h);
  const lo = img.wl - img.ww / 2, hi = img.wl + img.ww / 2;
  const emph = imgEmphasis();
  for (let i = 0; i < w * h; i++) {
    let gray = (hu[i] - lo) / (hi - lo);
    gray = gray < 0 ? 0 : gray > 1 ? 1 : gray;
    let r = gray * 255, g = r, b = r;
    const li = lbl[i];
    if (img.overlay && li) {
      const e = img.byIndex.get(li);
      const a = emph ? (emph.has(li) ? img.alpha : img.alpha * 0.12) : img.alpha;
      r = r * (1 - a) + e.color_rgb[0] * a;
      g = g * (1 - a) + e.color_rgb[1] * a;
      b = b * (1 - a) + e.color_rgb[2] * a;
    }
    out.data[i * 4] = r; out.data[i * 4 + 1] = g; out.data[i * 4 + 2] = b; out.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(out, 0, 0);
}

function imgRender() {
  if (!img.cur || !img.man) return;
  const { cols, rows } = img.man.geometry.dims_voxels;
  const cvs = $("imgCanvas"), ctx = cvs.getContext("2d");
  imgPaint(ctx, cols, rows, img.cur.hu, img.cur.lbl);
  const z = img.man.geometry.ipp_first_slice_lps_mm[2] + img.slice * img.man.geometry.spacing_mm[2];
  $("imgSliceVal").textContent =
    `slice ${img.slice + 1} / ${img.man.geometry.dims_voxels.slices} · instance ${img.slice + 1} · z ${z.toFixed(1)} mm (LPS)`;
  if (img.mpr && img.vol) imgRenderMpr();
}

// ---------- MPR (Milestone 31) ----------
// Data at a stored voxel: from the whole volume when MPR has loaded
// it, else from the current axial slice (single-plane mode).
function imgVoxelData(c, r, k) {
  const { cols, rows } = img.man.geometry.dims_voxels;
  if (img.vol) {
    const i = (k * rows + r) * cols + c;
    return { hu: img.vol.hu[i], lbl: img.vol.lbl[i] };
  }
  if (k === img.slice && img.cur) {
    const i = r * cols + c;
    return { hu: img.cur.hu[i], lbl: img.cur.lbl[i] };
  }
  return null;
}

function imgPaneEventVoxel(ev, plane) {
  const cv = ev.currentTarget, rect = cv.getBoundingClientRect();
  const dims = img.man.geometry.dims_voxels;
  const d = mprPlaneDims(plane, dims);
  const u = Math.floor((ev.clientX - rect.left) / rect.width * d.w);
  const v = Math.floor((ev.clientY - rect.top) / rect.height * d.h);
  if (u < 0 || u >= d.w || v < 0 || v >= d.h) return null;
  return mprVoxel(plane, mprPixel(plane, img.vox, dims).idx, u, v, dims);
}

// Assemble the whole volume from the per-slice bins (through the
// existing slice fetch path). The stored DICOM/bins are never touched;
// this is the in-memory volume the planes reslice.
async function imgLoadVolume() {
  if (img.vol || img.volLoading) return img.vol;
  img.volLoading = true;
  const subjAtStart = img.subjId;
  const dims = img.man.geometry.dims_voxels, n = dims.cols * dims.rows;
  const hu = new Int16Array(n * dims.slices), lbl = new Uint8Array(n * dims.slices);
  const CH = 16;
  for (let k0 = 0; k0 < dims.slices; k0 += CH) {
    if (img.subjId !== subjAtStart) { img.volLoading = false; return null; }
    const ks = [];
    for (let k = k0; k < Math.min(dims.slices, k0 + CH); k++) ks.push(k);
    await Promise.all(ks.map(async k => {
      const d = await imgLoadSlice(k);
      hu.set(d.hu, k * n); lbl.set(d.lbl, k * n);
    }));
    $("imgHover").textContent =
      `loading volume for MPR… ${Math.min(dims.slices, k0 + CH)}/${dims.slices} slices`;
  }
  if (img.subjId !== subjAtStart) { img.volLoading = false; return null; }
  img.vol = { hu, lbl };
  img.volLoading = false;
  return img.vol;
}

async function imgSetMpr(on) {
  img.mpr = on;
  $("imgMprBtn").classList.toggle("on", on);
  $("mprGrid").hidden = !on;
  $("imgCanvas").style.display = on ? "none" : "";
  if (!on) return;
  img.vox.k = img.slice;
  await imgLoadVolume();
  if (img.mpr) imgRenderMpr();
}

// Move the shared crosshair voxel (any subset of axes). The axial
// slice state follows k, so leaving MPR keeps the single-plane view
// where the crosshair left it.
function imgSetVox(patch) {
  const dims = img.man.geometry.dims_voxels;
  if (patch.c !== undefined) img.vox.c = Math.max(0, Math.min(dims.cols - 1, patch.c));
  if (patch.r !== undefined) img.vox.r = Math.max(0, Math.min(dims.rows - 1, patch.r));
  if (patch.k !== undefined) img.vox.k = Math.max(0, Math.min(dims.slices - 1, patch.k));
  if (img.vox.k !== img.slice) imgSetSlice(img.vox.k);  // re-renders, MPR included
  else if (img.mpr && img.vol) imgRenderMpr();
}

function imgSyncMprControls() {
  const dims = img.man.geometry.dims_voxels, g = img.man.geometry;
  $("mprAx").value = img.vox.k; $("mprCor").value = img.vox.r; $("mprSag").value = img.vox.c;
  const lps = mprLps(img.vox, g);
  $("pvAxial").textContent = `slice ${img.vox.k + 1}/${dims.slices} · z ${lps[2].toFixed(1)} mm`;
  $("pvCoronal").textContent = `row ${img.vox.r + 1}/${dims.rows} · y ${lps[1].toFixed(1)} mm`;
  $("pvSagittal").textContent = `col ${img.vox.c + 1}/${dims.cols} · x ${lps[0].toFixed(1)} mm`;
}

const MPR_CANVAS = { axial: "imgAx", coronal: "imgCor", sagittal: "imgSag" };
function imgRenderMpr() {
  if (!img.vol || !img.man) return;
  const dims = img.man.geometry.dims_voxels, spacing = img.man.geometry.spacing_mm;
  imgSyncMprControls();
  for (const plane of ["axial", "coronal", "sagittal"]) {
    const idx = mprPixel(plane, img.vox, dims).idx;
    const p = mprExtract(img.vol.hu, img.vol.lbl, dims, plane, idx);
    const cv = $(MPR_CANVAS[plane]);
    if (cv.width !== p.w || cv.height !== p.h) { cv.width = p.w; cv.height = p.h; }
    const ctx = cv.getContext("2d");
    imgPaint(ctx, p.w, p.h, p.hu, p.lbl);
    // crosshair: the lines the OTHER two coordinates imply in this
    // plane, from the same shared voxel via mprPixel()
    const px = mprPixel(plane, img.vox, dims);
    ctx.strokeStyle = "rgba(255,180,84,0.85)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(px.u + 0.5, 0); ctx.lineTo(px.u + 0.5, p.h);
    ctx.moveTo(0, px.v + 0.5); ctx.lineTo(p.w, px.v + 0.5);
    ctx.stroke();
    // on-screen watermark on every pane (the burned-in glyph voxels
    // also ride the data itself wherever a plane crosses the glyph
    // slab — W10 counts them in the coronal and sagittal planes)
    ctx.font = "bold 11px sans-serif";
    ctx.fillStyle = "rgba(242,200,119,0.95)";
    ctx.fillText("SYNTHETIC", 4, p.h - 4);
    // fit the pane box at the plane's PHYSICAL aspect (from spacing)
    const wrap = cv.parentElement, phys = mprPlanePhysical(plane, dims, spacing);
    const aw = wrap.clientWidth, ah = wrap.clientHeight;
    if (aw > 0 && ah > 0) {
      const s = Math.min(aw / phys.wMm, ah / phys.hMm);
      cv.style.width = (phys.wMm * s).toFixed(1) + "px";
      cv.style.height = (phys.hMm * s).toFixed(1) + "px";
    }
  }
}

function imgIdentify(c, r, k = img.slice, plane = "axial") {
  const d = imgVoxelData(c, r, k);
  if (!d) return;
  const hu = d.hu, li = d.lbl;
  const lps = mprLps({ c, r, k }, img.man.geometry).map(x => x.toFixed(1)).join(", ");
  const head = `<div class="note">Imaging — ${esc(plane)} plane, voxel (col ${c}, row ${r}, slice ${k + 1}), ` +
    `LPS (${lps}) mm · HU ${hu} · ` +
    (li ? `label <b>${esc(img.byIndex.get(li).label)}</b>` : "no label at this voxel") + `</div>`;
  if (!li) { panelEl.innerHTML = head + `<p class="empty">Background voxel (air / outside the body or an unsegmented structure).</p>`; return; }
  const e = img.byIndex.get(li);
  if (e.mapping_status === "mapped" && e.record_ids.length === 1) {
    const rec = byId.get(e.records[0].layer + ":" + e.record_ids[0]);
    select(rec, false);
    panelEl.insertAdjacentHTML("afterbegin", head +
      `<div class="note">Crosswalk: TotalSegmentator label <b>${esc(e.label)}</b> → this Body Model record ` +
      `(adjudicated mapping — ${esc(e.mapping_source || "Milestone 3 census")}). The atlas geometry is a ` +
      `different individual (BodyParts3D); identity is shared, space is not.</div>`);
    return;
  }
  if (e.mapping_status === "mapped") {
    const rows = e.records.map(x =>
      `<div class="row" data-rid="${esc(x.layer + ":" + x.id)}"><span class="nm">${esc(x.name)}</span>` +
      `<span class="badge inv">${esc(x.id)}</span></div>`).join("");
    panelEl.innerHTML = head +
      `<p>This label is crosswalked to <b>${e.record_ids.length} Body Model records</b> ` +
      `(one source label spanning several records — ${esc(e.mapping_note || "")}). Pick one:</p>` + rows;
    panelEl.querySelectorAll(".row").forEach(row =>
      row.addEventListener("click", () => select(byId.get(row.dataset.rid), false)));
    return;
  }
  const cand = e.candidate_record_ids && e.candidate_record_ids.length
    ? `<p>Candidate record(s) by name — <b>not adjudicated</b> by any milestone, shown as text only: ` +
      `${e.candidate_record_ids.map(esc).join(", ")}.</p>` : "";
  panelEl.innerHTML = head +
    `<p><span class="badge ver">⚠ unmapped</span> <b>${esc(e.label)}</b> is a TotalSegmentator source label ` +
    `with no adjudicated Body Model record mapping. ${esc(e.mapping_note || "")}</p>` + cand +
    `<p style="color:var(--dim)">HU in this label (whole volume): median ${e.hu ? e.hu.median : "—"}, ` +
    `${e.voxels.toLocaleString()} voxels.</p>`;
}

// ---------- mode switching ----------
function imgSetMode(m) {
  img.mode = m;
  document.body.classList.toggle("mode-imaging", m === "imaging");
  $("btnModeAtlas").classList.toggle("on", m === "atlas");
  $("btnModeImaging").classList.toggle("on", m === "imaging");
  $("leftAtlas").hidden = m !== "atlas";
  $("leftImg").hidden = m !== "imaging";
  $("imgwrap").hidden = m !== "imaging";
  if (m === "imaging") imgBoot();
  else if (img.solo) { img.solo = null; }
}
$("btnModeAtlas").addEventListener("click", () => imgSetMode("atlas"));
$("btnModeImaging").addEventListener("click", () => imgSetMode("imaging"));
