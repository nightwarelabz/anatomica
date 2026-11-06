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
   imaging.json meta.presets. The volume is ONE subject
   (TotalSegmentator s0778), a different individual from the atlas
   Body Model — the manifest's provenance note says so, and so does
   the banner. */

const IMG_GROUP_ORDER = ["skeletal", "cardiovascular", "respiratory", "digestive",
  "urinary", "lymphatic", "endocrine", "nervous", "muscular", "integumentary/other"];

const img = {
  mode: "atlas",
  booted: false,
  man: null,            // imaging.json
  byIndex: new Map(),   // label index -> manifest label entry
  labelsByRecord: new Map(), // record id -> [label indices] (mapped only)
  slice: 0,
  ww: 350, wl: 50,
  overlay: true, alpha: 0.5,
  solo: null,           // label index or null
  cache: new Map(),     // slice -> {hu: Int16Array, lbl: Uint8Array}
  cur: null,            // current slice data
};

const imgPath = (pattern, k) =>
  "data/" + pattern.replace("{slice:04d}", String(k).padStart(4, "0"));

async function imgBoot() {
  if (img.booted) return;
  img.booted = true;
  const man = await fetch("data/imaging.json").then(r => r.json());
  img.man = man;
  const g = man.geometry, dims = g.dims_voxels;
  for (const e of man.labels) {
    img.byIndex.set(e.index, e);
    for (const rid of e.record_ids || [])
      img.labelsByRecord.set(rid, [...(img.labelsByRecord.get(rid) || []), e.index]);
  }
  $("imgBanner").textContent = man.meta.banner + " · " + man.meta.provenance_note;
  // series list (OHIF-pattern: one study, image series + overlay series)
  const subj = man.meta.subject;
  $("imgSeries").innerHTML =
    `<div class="series"><b>CT · axial</b> — SYNTHETIC derived series<br>
       <span class="sm">${dims.slices} slices · ${dims.cols}×${dims.rows} · ` +
       `${g.spacing_mm.map(v => v.toFixed(1)).join("×")} mm · source: ${esc(subj.id)} ` +
       `(${esc(subj.meta_csv_row.study_type)})<br>${esc(subj.dataset)}</span></div>
     <div class="series"><b>SEG · label overlay</b><br>
       <span class="sm">${man.crosswalk_totals.labels_in_source_set} TotalSegmentator labels · ` +
       `${man.crosswalk_totals.labels_mapped} crosswalked to Body Model records · ` +
       `${man.crosswalk_totals.labels_unmapped} source-only (flagged)</span></div>`;
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
  // legend, grouped by system (M3 grouping), present labels first-class,
  // absent ones greyed
  const groups = new Map();
  for (const e of man.labels) {
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
  // controls
  const slider = $("imgSlice");
  slider.max = dims.slices - 1;
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
  cvs.width = dims.cols; cvs.height = dims.rows;
  cvs.addEventListener("click", ev => {
    const v = imgEventVoxel(ev);
    if (v) imgIdentify(v.c, v.r);
  });
  cvs.addEventListener("mousemove", ev => {
    const v = imgEventVoxel(ev);
    if (!v || !img.cur) return;
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
  // initial slice: the liver centroid slice when available (a slice a
  // reader recognises), else mid-volume
  const liver = man.labels.find(e => e.label === "liver" && e.geometry_lps);
  img.slice = liver
    ? Math.round((liver.geometry_lps.centroid_lps_mm[2] - g.ipp_first_slice_lps_mm[2]) / g.spacing_mm[2])
    : Math.floor(dims.slices / 2);
  imgSetWindow(img.ww, img.wl);
  await imgSetSlice(img.slice);
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
  const man = img.man;
  const [huBuf, lblBuf] = await Promise.all([
    fetch(imgPath(man.files.hu, k)).then(r => r.arrayBuffer()),
    fetch(imgPath(man.files.labels, k)).then(r => r.arrayBuffer()),
  ]);
  const d = { hu: new Int16Array(huBuf), lbl: new Uint8Array(lblBuf) };
  img.cache.set(k, d);
  if (img.cache.size > 24) img.cache.delete(img.cache.keys().next().value);
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

function imgRender() {
  if (!img.cur || !img.man) return;
  const { cols, rows } = img.man.geometry.dims_voxels;
  const cvs = $("imgCanvas"), ctx = cvs.getContext("2d");
  const out = ctx.createImageData(cols, rows);
  const lo = img.wl - img.ww / 2, hi = img.wl + img.ww / 2;
  const emph = imgEmphasis();
  const { hu, lbl } = img.cur;
  for (let i = 0; i < cols * rows; i++) {
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
  const z = img.man.geometry.ipp_first_slice_lps_mm[2] + img.slice * img.man.geometry.spacing_mm[2];
  $("imgSliceVal").textContent =
    `slice ${img.slice + 1} / ${img.man.geometry.dims_voxels.slices} · instance ${img.slice + 1} · z ${z.toFixed(1)} mm (LPS)`;
}

function imgIdentify(c, r) {
  const { cols } = img.man.geometry.dims_voxels;
  const hu = img.cur.hu[r * cols + c], li = img.cur.lbl[r * cols + c];
  const z = img.man.geometry.ipp_first_slice_lps_mm[2] + img.slice * img.man.geometry.spacing_mm[2];
  const head = `<div class="note">Imaging — slice ${img.slice + 1}, voxel (col ${c}, row ${r}), ` +
    `z ${z.toFixed(1)} mm LPS · HU ${hu} · ` +
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
