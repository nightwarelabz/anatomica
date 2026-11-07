# web/data — theatre and cases copies

`web/data/theatre/` and `web/data/cases/` are **byte-identical copies** of
repo sources that live outside `web/`:

| Copy | Source of truth |
| --- | --- |
| `web/data/theatre/procedures/*.json` | `theatre/procedures/*.json` |
| `web/data/theatre/traces/*.json` | `theatre/traces/*.json` |
| `web/data/cases/case.*.json`, `web/data/cases/parameters.json` | `cases/case.*.json`, `cases/parameters.json` |
| `web/data/cases/attempts/*.json` | `cases/attempts/*.json` |

Why copies: the static web shell is served from `web/` and can only fetch
files beneath it, while the canonical theatre and case data are authored
(and checked by their own tools) in `theatre/` and `cases/`. The shell
fetches these copies at runtime — theatre procedure/trace JSON for the
Theatre view, and the case, attempt and parameter JSON for the Case
Workbench (`web/cases.js`, the JavaScript port of `tools/case_run.py`).

Edit the sources in `theatre/` and `cases/`, never these copies, and
refresh the copies afterwards. From the repo root:

```sh
mkdir -p web/data/theatre/procedures web/data/theatre/traces web/data/cases/attempts
cp theatre/procedures/*.json web/data/theatre/procedures/
cp theatre/traces/*.json     web/data/theatre/traces/
cp cases/case.*.json cases/parameters.json web/data/cases/
cp cases/attempts/*.json     web/data/cases/attempts/
```

Verify a refresh is byte-identical with `cmp`, e.g.
`cmp theatre/procedures/proc.lap-cholecystectomy.json web/data/theatre/procedures/proc.lap-cholecystectomy.json`
(and likewise for the other files).
