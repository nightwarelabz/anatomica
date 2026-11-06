### 2. Quantitative Physiology & Pathophysiology

**2.1 Guyton and Hall Textbook of Medical Physiology — Elsevier, 14th ed. lineage (Hall)**
- Content: The quantitative canon the physiology engine should implement: circulation divided systemic (84% of blood volume) vs heart+lungs (16%); aortic velocity ~33 cm/s vs capillary ~0.3 mm/s; cardiac output ~100 mL/s (≈5–5.6 L/min men, 4.9 L/min women; cardiac index ~3 L/min/m²); total peripheral resistance **1 PRU** (range 0.2 vasodilated – 4 PRU constricted); total pulmonary resistance **0.14 PRU**; mean aortic pressure ~100 mmHg (120/80), mean pulmonary arterial **16 mmHg**, mean left atrial ~2 mmHg, functional capillary ~17 mmHg, glomerular capillary ~60 mmHg.
- 🔴 PAYWALLED text (Elsevier) — numbers above are published facts, widely reproduced; implement equations (Ohm/Poiseuille, Frank-Starling, renal autoregulation) in original code.
- URL: https://doctorlib.org/physiology/textbook-medical-physiology/14.html (12th-ed. chapter text, index only — do not copy into product)

**2.2 Standard haemodynamic normal ranges (critical-care consensus tables)**
- CO **4–8 L/min**; CI **2.5–4.2 L/min/m²**; SVR **770–1,500 dyn·s/cm⁵** (other tables 900–1,400); PVR **20–120 dyn·s/cm⁵**; MAP **70–95 mmHg** (target ≥65 in shock); RA mean 0–5, RV 17–32/1–7, PA 17–32/1–7 mean 9–19, PCWP/LA mean **4–12**, LV 90–140/5–12, aorta 90–140/60–90 mmHg; EF **60–70%** (tables vary 55–70).
- 🟡 CITE-ONLY — teach as ranges with source variance, not single values.
- URL: https://study-notes-pdfs.s3.us-west-2.amazonaws.com/28458757.pdf

**2.3 Lung mechanics / spirometry normals**
- FEV₁ and FVC **80–120% predicted**; FEV₁/FVC **0.70–0.80** normal, **<0.70 = obstruction**, normal/raised with both reduced = restriction; TLC/FRC/RV 75–120% predicted; tidal volume ~500 mL, residual volume ~1,200 mL; FVC ~4.5–5.0 L men, 3.0–3.5 L women; RR 12–20/min; PaO₂ 80–100, PaCO₂ 35–45 mmHg.
- 🟡 CITE-ONLY (GLI reference equations are the modern standard — spirometry must be %predicted by age/sex/height, never fixed litres alone).
- URL: https://www.slideshare.net/slideshow/pft-253869759/253869759

**2.4 Renal clearances**
- GFR (inulin clearance) **~125 mL/min/1.73 m²**; creatinine clearance ~135 mL/min measured (secretion adds ~10%); eGFR **>90** normal, **<60 for >3 months = CKD range**; renal plasma flow ~660 mL/min in Guyton lineage. Pregnancy: GFR +50% (see §9).
- 🟡 CITE-ONLY facts.
- URL: https://www.scribd.com/document/732394647/Physiology2-merged (index summary of standard teaching values)

**2.5 ATLS haemorrhage classes — see §3.3 for full table** (Class I <15%/<750 mL → Class IV >40%/>2,000 mL, HR <100 → >140, urine >30 → negligible mL/h).

**2.6 Sepsis-3 + Surviving Sepsis Campaign 2021 — Singer et al. JAMA 2016; Evans et al., SCCM/ESICM**
- Definitions: Sepsis = life-threatening organ dysfunction from dysregulated host response, operationalised as **SOFA rise ≥2** (>10% in-hospital mortality). Septic shock = vasopressor to keep **MAP ≥65 mmHg + lactate >2 mmol/L** despite adequate fluids.
- Hour-1 bundle (begin immediately): measure lactate (repeat q2–4h if raised), blood cultures *before* antibiotics (don't delay antibiotics >45 min for them), broad-spectrum antibiotics **within 1 h for shock / within 3 h for possible sepsis without shock**, **30 mL/kg balanced crystalloid** for hypotension or lactate ≥4 mmol/L, norepinephrine first-line (add vasopressin at NE ~0.25–0.50 mcg/kg/min, then epinephrine; hydrocortisone if refractory), source control within 6–12 h. SSC 2021 recommends *against* qSOFA as a sole screening tool vs SIRS/NEWS/MEWS.
- 🟡 CITE-ONLY / FREE TO READ — guideline PDFs widely available free via SCCM; text is society copyright. Numbers and bundle steps are teachable facts.
- URLs: https://emottawablog.com/2022/06/surviving-sepsis-the-2021-review/

**2.7 Acid–base interpretation standards**
- Normal ABG (OpenStax, ✅ CC-licensed table): **pH 7.35–7.45, PaO₂ 80–100 mmHg, PaCO₂ 35–45 mmHg, HCO₃⁻ 22–26 mEq/L, SaO₂ 95–98%**. Metabolic acidosis = pH <7.35 + HCO₃⁻ <22. Standard method to teach: pH → primary disorder (PaCO₂ vs HCO₃⁻) → compensation (Winter's formula etc.) → anion gap (Na⁺−[Cl⁻+HCO₃⁻], normal ~8–16) → delta checks. Stewart physicochemical approach is the alternative formalism — present as advanced/optional.
- ✅ OPEN for the normal-values table via OpenStax; interpretation algorithms are standard facts.
- URL: https://openstax.org/books/medical-surgical-nursing/pages/10-4-acid-base-imbalance

