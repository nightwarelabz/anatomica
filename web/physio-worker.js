/* ANATOMICA web shell — engine worker.
   Runs the wasm engines (physiology + theatre) off the main thread:
   physio course/hormone runs and theatre debriefs integrate for
   seconds-to-minutes of CPU, and blocking the UI thread for that
   long would freeze the shell. The pkg is the wasm-bindgen
   --target web build; a module worker can import its glue directly
   and the default init() resolves anatomica_wasm_bg.wasm relative
   to the glue's own URL, so no path plumbing is needed.
   Protocol: {id, fn, args:[...]} -> {id, ok:true, result} |
   {id, ok:false, error}. Engine-level failures are NOT exceptions:
   the exports return {"error": "..."} strings, passed through as
   ordinary results for the caller to surface. */
import init, { physio, theatre_run, theatre_validate } from "./pkg/anatomica_wasm.js";

const ready = init().then(
  () => null,
  (e) => String((e && e.message) || e)
);
const FNS = { physio, theatre_run, theatre_validate };

self.onmessage = async (ev) => {
  const { id, fn, args } = ev.data || {};
  const initErr = await ready;
  if (initErr) {
    self.postMessage({ id, ok: false, error: "wasm init failed: " + initErr });
    return;
  }
  try {
    const f = FNS[fn];
    if (!f) throw new Error("unknown engine function '" + fn + "'");
    self.postMessage({ id, ok: true, result: f(...(args || [])) });
  } catch (e) {
    self.postMessage({ id, ok: false, error: String((e && e.message) || e) });
  }
};
