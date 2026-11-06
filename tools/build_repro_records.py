#!/usr/bin/env python3
"""ANATOMICA Milestone 14 — reproductive system clinical
tranche.

Field-sourcing rule (set in Milestone 4, binding since): every
field value comes only from the sources actually consulted in
this session, and the record cites the source(s) it used for
that field in its `sources` map. A field the consulted sources
do not support is null and carries a `verify` entry instead.

Sources consulted in-session, 2026-11-06:
  S1  TeachMeAnatomy — "The Testes and Epididymis"
      (teachmeanatomy.info): scrotal position, posterolateral
      epididymis, descent via the inguinal canal carrying the
      supply, lobules of seminiferous tubules, Sertoli and
      Leydig cells, tunica vaginalis and albuginea, the sperm
      route rete testis -> efferent tubules -> epididymis, the
      epididymis' head/body/tail as one coiled duct, the
      testicular arteries from the abdominal aorta with their
      cremasteric and ductal anastomoses, pampiniform plexus ->
      testicular veins (left to left renal, right to IVC),
      lumbar/para-aortic lymphatics, testicular plexus.
  S2  TeachMeAnatomy — "The Prostate Gland"
      (teachmeanatomy.info): largest accessory gland,
      walnut-sized, two-thirds glandular one-third
      fibromuscular, position at the bladder neck, McNeal
      zones with their percentages, prostatic ducts opening
      into the prostatic urethra, prostatic arteries mainly
      from the internal iliac, prostatic plexus to the internal
      iliac veins with the Batson communication, inferior
      hypogastric innervation, the flanking neurovascular
      bundles.
  S3  SEER Training Modules (U.S. National Cancer Institute),
      "Duct System" (training.seer.cancer.gov): the duct
      order — testes, epididymis, ductus deferens, ejaculatory
      duct, urethra; the epididymis as a ~6 m coiled tube on
      the superior and posterior testis, maturing and storing
      sperm; the ductus deferens' full course (tail, inguinal
      canal, pelvic wall, over the ureter, behind the bladder,
      ampulla) and the spermatic cord's contents; the
      ejaculatory duct formed at the ampulla and emptying
      through the prostate; the urethra's three regions and
      its shared urinary/reproductive role.
  S4  OpenStax Anatomy and Physiology 2e, §27.1, read in the
      LibreTexts "Human Anatomy" chapter 23.2 mirror
      (med.libretexts.org): the scrotum (dartos, cremaster,
      septum; testes held 2–4 °C below core), testes 4–5 cm,
      tunica vaginalis and albuginea, 300–400 lobules,
      straight tubules -> rete testes -> 15–20 efferent
      ductules, epididymis ~6 m with ~12-day transit, semen
      composition (sperm ~5%, seminal vesicles ~60%), the
      prostate's citric acid, PSA and seminalplasmin, the
      bulbourethral mucus and pre-ejaculate, the ductal system
      and vasectomy, the urethra's three regions, and the
      penis — two corpora cavernosa, the corpus spongiosum
      around the spongy urethra, glans and prepuce, erection by
      nitric-oxide vasocongestion.
  S5  TeachMeAnatomy — "The Ovaries" (teachmeanatomy.info):
      paired oval organs on the posterior broad ligament via
      the mesovarium, the hilum, oocyte and sex-steroid
      production, surface/cortex/medulla components, the
      suspensory and ovarian ligaments, the ovarian arteries
      from the aorta with uterine contribution, the asymmetric
      ovarian veins, ovarian and uterine plexus innervation,
      para-aortic lymphatics.
  S6  TeachMeAnatomy — "The Uterus" (teachmeanatomy.info):
      fundus/body/cervix, anteversion and anteflexion,
      posterosuperior to the bladder and anterior to the
      rectum, the three wall layers with the endometrial
      strata, the broad, round, ovarian, cardinal and
      uterosacral ligaments, the uterine artery from the
      internal iliac crossing the ureter at the internal os,
      venous plexus to the uterine veins, iliac/sacral/aortic/
      inguinal lymphatics, uterovaginal plexus innervation.
  S7  OpenStax Anatomy and Physiology 2e, §27.2 (consulted in
      its LibreTexts mirrors at chapter/excerpt level): the
      ovaries as paired ovals 2–3 cm in the pelvic cavity on
      the mesovarium, the uterus ~5 cm wide by ~7 cm long with
      fundus, body and cervix and three wall layers, the
      uterine tubes with their distal fimbriae conveying the
      oocyte to the uterus, the vagina as a ~10 cm muscular
      canal whose fornix meets the cervix, and the vulva —
      mons pubis (the pad of fat over the pubic bone), labia,
      clitoris, vestibule and vestibular (Bartholin's) glands.
  S8  TeachMeAnatomy — "The Perineum" (teachmeanatomy.info;
      article text consulted in full extract): the
      diamond-shaped region at the pelvic outlet below the
      pelvic floor, its anatomical borders (pubic symphysis,
      tip of coccyx, inferior pubic/ischial rami and
      sacrotuberous ligaments, pelvic-floor roof, skin and
      fascia base) and surface borders (mons pubis in females,
      base of penis in males), the transverse ischial line
      dividing the urogenital and anal triangles, the anal
      triangle's contents (anal aperture, external anal
      sphincter, ischioanal fossae), the perineal body at the
      triangles' junction.
  S9  InnerBody — "Female Reproductive Organs of the Lower
      Torso" (innerbody.com; consulted at excerpt level): the
      vulva as the collective name of the external female
      organs, the labia majora and minora around the urinary
      and reproductive orifices, the vagina as the muscular
      epithelium-lined tube connecting vulva to cervix, the
      uterus between the vagina and the tubes, the tubes
      extending from the upper uterus toward the ovaries, the
      tract as a conduit for sperm and for birth.
  S10 The ANATOMICA project datasets themselves, consulted
      in-session: this milestone's BP3D 4.0 census
      (tools/repro_map.py — concept sets, probe counts, the
      sweep adjudications), the cardiovascular module
      inventory (Milestone 5 — the testicular artery and vein
      records and the five penile vessel records exist; no
      ovarian vessel record exists), the urinary module
      (Milestone 12 — inventory record 'urethra' FMA19667 and
      clinical record structure.urethra), the endocrine
      inventory (Milestone 13 — the testis line censused as
      its reproductive cross-reference) and the muscular
      module geometry (Milestone 4 — the external anal
      sphincter's mesh file set). Used only for dataset facts
      and cross-module pointers, never for anatomy the other
      sources state.

The tranche's shape follows the dataset's. The male line gets
its pathway and its organs: the pathway record states the
sperm route across stations two of which (ductus deferens,
ejaculatory duct) the release does not carry at all, and it
states the urethra relationship explicitly — the urethra is
the urinary module's single unsexed record, cross-referenced
here, never duplicated. The female line gets its pathway and
its organs as sourced text with the ABSENCE recorded on the
records themselves: the ovary record is the headline — fully
sourced clinical anatomy for a gonad the dataset does not
contain, whose arterial supply, unlike the testis', has no
cardiovascular record to point at because the release lacks
the ovarian vessels too. The one female structure the release
does carry, the mons pubis, gets the tranche's thinnest record
(tier C): the consulted sources describe what it is and
little more, and the record says so rather than padding. The
perineum closes the tranche as shared ground, its geometry
the sphincter the muscular module owns.

Tiers: A = every field valued and cited; B = a soft field is
null; C = a core field is null. Tier discipline is enforced
by finish() and re-derived independently by
tools/repro_check.py.
"""
import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV = os.path.join(ROOT, "data", "reproductive",
                   "reproductive-inventory.json")
OUT = os.path.join(ROOT, "data", "reproductive",
                   "reproductive.json")

SOURCES = OrderedDict([
    ("S1", "TeachMeAnatomy — The Testes and Epididymis "
           "(teachmeanatomy.info): scrotal position and "
           "posterolateral epididymis, descent through the "
           "inguinal canal, lobules of Sertoli-lined "
           "seminiferous tubules, Leydig-cell testosterone, "
           "tunica vaginalis and albuginea, rete testis and "
           "efferent tubules, epididymal head/body/tail as one "
           "coiled duct, testicular arteries from the abdominal "
           "aorta with cremasteric and ductal anastomoses, "
           "pampiniform plexus to the testicular veins (left to "
           "the left renal vein, right to the IVC), lumbar "
           "lymphatics, testicular plexus innervation"),
    ("S2", "TeachMeAnatomy — The Prostate Gland "
           "(teachmeanatomy.info): largest accessory gland, "
           "walnut-sized, two-thirds glandular and one-third "
           "fibromuscular, position at the bladder neck, McNeal "
           "zones (central ~25%, transitional 5–10%, peripheral "
           "~65%, anterior fibromuscular stroma), prostatic "
           "ducts into the prostatic urethra, prostatic arteries "
           "mainly from the internal iliac, prostatic plexus to "
           "the internal iliac veins with the Batson "
           "communication, inferior hypogastric innervation, "
           "flanking neurovascular bundles"),
    ("S3", "SEER Training Modules (U.S. National Cancer "
           "Institute) — Duct System "
           "(training.seer.cancer.gov): duct order testes -> "
           "epididymis -> ductus deferens -> ejaculatory duct "
           "-> urethra; epididymis a ~6 m coiled tube maturing "
           "and storing sperm; the ductus deferens' course and "
           "ampulla; spermatic cord contents; ejaculatory duct "
           "formation and emptying; the urethra's three regions "
           "and shared urinary/reproductive role"),
    ("S4", "OpenStax Anatomy and Physiology 2e, §27.1 (read "
           "in the LibreTexts Human Anatomy ch. 23.2 mirror, "
           "med.libretexts.org): scrotum and its muscles, "
           "testes 4–5 cm with 300–400 lobules, straight "
           "tubules -> rete testes -> 15–20 efferent ductules, "
           "epididymis ~6 m / ~12-day transit, semen composition "
           "(sperm ~5%, seminal vesicles ~60%), prostatic "
           "citrate, PSA and seminalplasmin, bulbourethral "
           "mucus, the ductal system and vasectomy, the penis' "
           "erectile columns, glans and prepuce, erection by "
           "NO-mediated vasocongestion"),
    ("S5", "TeachMeAnatomy — The Ovaries "
           "(teachmeanatomy.info): paired ovals on the "
           "posterior broad ligament via the mesovarium, hilum, "
           "oocyte and oestrogen/progesterone production, "
           "surface/cortex/medulla, suspensory and ovarian "
           "ligaments, ovarian arteries from the aorta with "
           "uterine contribution, asymmetric ovarian veins, "
           "ovarian and uterine plexus innervation, para-aortic "
           "lymphatics"),
    ("S6", "TeachMeAnatomy — The Uterus "
           "(teachmeanatomy.info): fundus/body/cervix, "
           "anteversion and anteflexion, relations to bladder "
           "and rectum, perimetrium/myometrium/endometrium with "
           "the endometrial strata, broad, round, ovarian, "
           "cardinal and uterosacral ligaments, uterine artery "
           "from the internal iliac crossing the ureter, "
           "uterine venous plexus, iliac/sacral/aortic/inguinal "
           "lymphatics, uterovaginal plexus innervation"),
    ("S7", "OpenStax Anatomy and Physiology 2e, §27.2 "
           "(LibreTexts mirrors, consulted at chapter/excerpt "
           "level): ovaries as paired 2–3 cm ovals on the "
           "mesovarium, uterus ~5 cm wide by ~7 cm long with "
           "three parts and three wall layers, uterine tubes "
           "with distal fimbriae, vagina a ~10 cm muscular "
           "canal with its fornix at the cervix, vulva including "
           "the mons pubis as the pad of fat over the pubic "
           "bone, labia, clitoris, vestibule and Bartholin's "
           "glands"),
    ("S8", "TeachMeAnatomy — The Perineum "
           "(teachmeanatomy.info; article text consulted in "
           "full extract): diamond region at the pelvic outlet, "
           "anatomical and surface borders, the transverse "
           "ischial line dividing urogenital and anal "
           "triangles, anal triangle contents (anal aperture, "
           "external anal sphincter, ischioanal fossae), the "
           "perineal body at the junction"),
    ("S9", "InnerBody — Female Reproductive Organs of the "
           "Lower Torso (innerbody.com; excerpt level): vulva "
           "as the collective external organs, labia majora and "
           "minora, vagina connecting vulva to cervix, uterus "
           "between vagina and tubes, tubes extending toward "
           "the ovaries, the tract as a conduit for sperm and "
           "for birth"),
    ("S10", "ANATOMICA project datasets consulted in-session: "
            "this milestone's BP3D 4.0 census "
            "(tools/repro_map.py), the cardiovascular module "
            "inventory (Milestone 5), the urinary module "
            "(Milestone 12), the endocrine inventory "
            "(Milestone 13) and the muscular module geometry "
            "(Milestone 4) — dataset facts and cross-module "
            "pointers only"),
])

ABSENCE = ("no BP3D 4.0 concept exists for this structure "
           "(probe-verified over all six release tables by "
           "tools/repro_map.py); the record is sourced text only "
           "and links no geometry")
PATHWAY = ("the pathway record links no geometry itself: its "
           "stations' geometry is held by this module's organ "
           "records where the release carries them (testis, "
           "epididymis, seminal vesicles, prostate, erectile "
           "tissues), and the ductus deferens and ejaculatory "
           "duct stations have no BP3D 4.0 concept at all "
           "(probe-verified over all six release tables by "
           "tools/repro_map.py)")
TA_VERIFY = ("ta_name: not asserted — no TA2 term list was "
             "consulted in this session")


def base(rid, name, typ, group, sex_line):
    return OrderedDict([
        ("id", rid), ("name", name), ("type", typ),
        ("group", group), ("sex_line", sex_line),
        ("ta_name", None), ("sources", OrderedDict()),
        ("verify", []), ("note", None),
        ("geometry_record_ids", []),
    ])


def link(rec, inv_by_name, names):
    for n in names:
        rec["geometry_record_ids"].append(inv_by_name[n]["record_id"])


def typed(rec, fields):
    for k, v in fields.items():
        rec[k] = v
    return rec


def finish(rec, core, soft):
    """Assign the sourcing tier and enforce the sourcing rule.

    An empty geometry link is acceptable only when a verify
    entry records either the dataset absence (ABSENCE) or the
    pathway's own no-geometry statement (PATHWAY).
    """
    problems = []
    for fname in core + soft:
        val = rec.get(fname)
        if val is None:
            if not any(fname in v for v in rec["verify"]):
                problems.append(
                    f"{rec['id']}: null field {fname} has no "
                    "verify entry naming it")
        else:
            if fname not in rec["sources"]:
                problems.append(
                    f"{rec['id']}: valued field {fname} has no "
                    "sources entry")
    if not rec["geometry_record_ids"]:
        if not any(ABSENCE in v or PATHWAY in v
                   for v in rec["verify"]):
            problems.append(
                f"{rec['id']}: no geometry links and no absence "
                "or pathway verify entry")
    if problems:
        raise SystemExit("\n".join(problems))
    core_null = any(rec.get(f) is None for f in core)
    soft_null = any(rec.get(f) is None for f in soft)
    rec["sourcing_tier"] = "C" if core_null else ("B" if soft_null
                                                   else "A")
    return rec


def main():
    inv = json.load(open(INV))
    inv_by_name = {r["name"]: r for r in inv["records"]}
    records = []

    # ============ the male pathway ============
    r = base("pathway.male-reproductive-pathway",
             "Male reproductive pathway", "pathway",
             "Male pathway", "male")
    typed(r, {
        "description":
            "The route sperm take from production to exit. "
            "Formed in the seminiferous tubules of the testis, "
            "sperm leave the testis through the efferent "
            "ductules for the epididymis, and at ejaculation are "
            "driven along the ductus deferens, through the "
            "ejaculatory duct and out through the urethra — "
            "after they leave the testes, the sperm passes "
            "through the epididymis, ductus deferens, "
            "ejaculatory duct, and urethra (S3, S4).",
        "stations": [
            "seminiferous tubules", "straight tubules",
            "rete testis", "efferent ductules", "epididymis",
            "ductus deferens", "ejaculatory duct",
            "prostatic urethra", "membranous urethra",
            "spongy (penile) urethra",
            "external urethral orifice"],
        "urethra_relationship":
            "The pathway's terminal segment is the urethra — a "
            "structure this module does not own. The release "
            "carries exactly one urethra concept (FMA19667), "
            "unsexed and undivided, and the urinary module "
            "(Milestone 12) holds it as its inventory record "
            "'urethra', with clinical record structure.urethra: "
            "the urethra is the shared terminal channel of the "
            "urinary and male reproductive systems, running "
            "from the bladder to the external urethral orifice "
            "at the tip of the penis, a passageway for sperm "
            "and reproductive fluids and for urine — though "
            "never both at once, sphincters contracting to keep "
            "urine out of it while reproductive fluids pass "
            "(S3). It is censused there and cross-referenced "
            "here, never duplicated; its three regions "
            "(prostatic, membranous, spongy) exist in this "
            "module only as the pathway's sourced text, there "
            "being no regional urethra concepts in the release "
            "(S3, S4, S10).",
        "glands_in_order":
            "In the order their secretions join the stream: "
            "the seminal vesicles first, their duct joining the "
            "ductus deferens at its ampulla to form the "
            "ejaculatory duct, so their fluid enters with the "
            "sperm (S3, S4); the prostate next, its ducts "
            "opening into the prostatic urethra as the fluid "
            "passes (S2, S3); the bulbourethral glands last "
            "into the penile urethra — in fact discharged "
            "before the semen itself, as the pre-ejaculate "
            "(S3, S4).",
        "semen_composition":
            "Sperm make up only about 5 percent of the final "
            "volume of semen; the seminal vesicles contribute "
            "approximately 60 percent, the prostate and the "
            "bulbourethral glands most of the remainder (S4).",
        "clinical_note":
            "Vasectomy interrupts the pathway at its most "
            "accessible station: the ductus deferens is cut and "
            "sealed inside the scrotum, where it is bundled in "
            "the spermatic cord — clinicians regard the "
            "procedure as permanent (S4). The station is one "
            "the dataset does not carry at all.",
    })
    r["sources"] = OrderedDict([
        ("description", ["S3", "S4"]),
        ("stations", ["S3", "S4"]),
        ("urethra_relationship", ["S3", "S4", "S10"]),
        ("glands_in_order", ["S2", "S3", "S4"]),
        ("semen_composition", ["S4"]),
        ("clinical_note", ["S4"]),
    ])
    r["verify"] = [PATHWAY, TA_VERIFY]
    r["note"] = ("The pathway crosses two module boundaries by "
                 "design: it begins in this module's gonad and "
                 "ends in the urinary module's urethra, and two "
                 "of its stations are dataset absences carried "
                 "as sourced text.")
    records.append(finish(
        r, core=["description", "stations",
                 "urethra_relationship"],
        soft=["glands_in_order", "semen_composition",
              "clinical_note"]))

    # ============ male organs and glands ============
    r = base("organ.testis", "Testis", "organ",
             "Male organs and glands", "male")
    link(r, inv_by_name, ["right testis", "left testis"])
    typed(r, {
        "description":
            "The male gonads: paired ellipsoid organs housed "
            "within the scrotum, each suspended by the "
            "spermatic cord, the epididymis applied to the "
            "posterolateral surface of each, and the left "
            "testis usually sitting lower than the right (S1).",
        "parts":
            "Each testis is divided by septa of its dense "
            "fibrous capsule, the tunica albuginea, into "
            "lobules of seminiferous tubules — OpenStax counts "
            "300 to 400 lobules (S4) — where sperm develop, "
            "surrounded by sustentacular (Sertoli) cells, with "
            "the interstitial (Leydig) cells between the "
            "tubules producing testosterone (S1, S4). Formed "
            "sperm pass from the tubules into the straight "
            "tubules, then the rete testis, and leave through "
            "the efferent ductules (S4). Over the capsule lies "
            "the tunica vaginalis, a serous peritoneal sac "
            "covering the front and sides (S1, S4). No part, "
            "covering or tubule has a concept in the release — "
            "the data carries the organs as undivided volumes.",
        "function":
            "Spermatogenesis and androgen production: the "
            "testes produce sperm and androgens — principally "
            "testosterone, the hormone that supports male "
            "reproductive physiology — and are active "
            "throughout the reproductive lifespan (S1, S4).",
        "dimension":
            "Each testis is approximately 4 to 5 cm in length "
            "(S4). Sperm production proceeds more efficiently "
            "at 2 to 4 °C below core body temperature, which "
            "the scrotal position provides (S4).",
        "arterial_supply":
            "The paired testicular arteries arise from the "
            "abdominal aorta and descend through the inguinal "
            "canal in the spermatic cord — the route of the "
            "testis' own descent from the posterior abdominal "
            "wall; the cremasteric artery (from the inferior "
            "epigastric) and the artery of the ductus deferens "
            "(from the inferior vesical) anastomose with them "
            "(S1). The cardiovascular module carries both as "
            "records artery.right-testicular-artery and "
            "artery.left-testicular-artery, resolved by the "
            "checker (S10).",
        "venous_drainage":
            "The pampiniform plexus drains into the testicular "
            "veins, asymmetrically: the left testicular vein "
            "ends in the left renal vein, the right directly "
            "in the inferior vena cava (S1). Carried by the "
            "cardiovascular module as vein.right-testicular-"
            "vein and vein.left-testicular-vein (S10).",
        "lymphatic_drainage":
            "To the lumbar (para-aortic) lymph nodes, following "
            "the gonadal vessels back to their origin — not to "
            "the inguinal nodes, which drain the scrotal skin "
            "instead (S1). No lumbar node exists as a concept "
            "in the release (lymphatic module census), so this "
            "drainage is sourced text only.",
        "innervation":
            "Via the testicular plexus, derived from the renal "
            "and aortic plexuses (S1). No testicular nerve "
            "concept exists in the release (nervous module "
            "census), so this is sourced text only.",
        "relations":
            "Within the scrotum behind the penis, one testis "
            "per compartment of the scrotal septum (S4); the "
            "epididymis sits posterolateral (S1). Each testis "
            "reached the scrotum by descending from the "
            "posterior abdominal wall through the inguinal "
            "canal during development, carrying its vessels, "
            "nerves and lymphatics with it (S1).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S1"]),
        ("parts", ["S1", "S4"]),
        ("function", ["S1", "S4"]),
        ("dimension", ["S4"]),
        ("arterial_supply", ["S1", "S10"]),
        ("venous_drainage", ["S1", "S10"]),
        ("lymphatic_drainage", ["S1"]),
        ("innervation", ["S1"]),
        ("relations", ["S1", "S4"]),
    ])
    r["verify"] = [TA_VERIFY]
    r["note"] = ("The male gonad is the dataset's best-served "
                 "reproductive organ: geometry, its arteries and "
                 "veins in the cardiovascular module, and this "
                 "record — against the female gonad's sourced "
                 "text over a total dataset absence (organ.ovary).")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["dimension", "arterial_supply", "venous_drainage",
              "lymphatic_drainage", "innervation", "relations"]))

    r = base("structure.epididymis", "Epididymis", "structure",
             "Male organs and glands", "male")
    link(r, inv_by_name, ["right epididymis", "left epididymis"])
    typed(r, {
        "description":
            "A long, tightly coiled tube forming a "
            "comma-shaped organ along the superior and "
            "posterior margins of the testis — a single heavily "
            "coiled duct, not a bundle of ducts (S1, S3).",
        "parts":
            "Head, body and tail. The head is formed by the "
            "efferent ductules arriving from the rete testis; "
            "the body is the coiled duct itself; the tail is "
            "where mature sperm are stored and where the "
            "ductus deferens begins (S1, S3).",
        "function":
            "Maturation and storage: sperm leave the testis "
            "immature and incapable of fertilising an ovum, "
            "complete their maturation as they move through the "
            "epididymis, and are stored, fertile, in its tail "
            "until ejaculation (S3, S4).",
        "dimension":
            "About 6 metres long if straightened (S3, S4); "
            "sperm take an average of about 12 days to transit "
            "its coils (S4).",
        "relations":
            "Applied to the superior and posterior margins of "
            "the testis within the scrotum, continuous at its "
            "tail with the ductus deferens (S3).",
        "arterial_supply": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S1", "S3"]),
        ("parts", ["S1", "S3"]),
        ("function", ["S3", "S4"]),
        ("dimension", ["S3", "S4"]),
        ("relations", ["S3"]),
    ])
    r["verify"] = [
        "arterial_supply: no value asserted — none of the "
        "sources consulted in this session states the "
        "epididymis' own arterial supply in citable form (the "
        "testicular arteries are recorded on organ.testis); "
        "the field stays null rather than unsourced",
        TA_VERIFY,
    ]
    r["note"] = ("The only duct of the male pathway the release "
                 "carries — the pathway is continuous in the "
                 "data from the testis to here, and broken from "
                 "here on.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["dimension", "relations", "arterial_supply"]))

    r = base("duct.ductus-deferens", "Ductus deferens "
             "(vas deferens)", "duct", "Male organs and glands",
             "male")
    typed(r, {
        "description":
            "A fibromuscular tube continuous with the tail of "
            "the epididymis, conducting sperm from the scrotum "
            "to the ejaculatory duct (S3, S4).",
        "course":
            "It begins at the tail of the epididymis and turns "
            "sharply upward along the posterior margin of the "
            "testis; bundled in the spermatic cord, it enters "
            "the abdominopelvic cavity through the inguinal "
            "canal, passes along the lateral pelvic wall, "
            "crosses over the ureter and the posterior portion "
            "of the urinary bladder, and descends behind the "
            "bladder toward the prostate, enlarging into the "
            "ampulla just before it reaches the gland (S3, S4).",
        "function":
            "Transport and proximal storage: sperm are stored "
            "in its proximal portion near the epididymis, and "
            "peristaltic contraction propels them through it at "
            "ejaculation (S3).",
        "parts":
            "Its named dilation is the ampulla, the flask-like "
            "enlargement just before the prostate, where it "
            "joins the duct of the seminal vesicle to form the "
            "ejaculatory duct (S3, S4). The spermatic cord that "
            "carries its proximal portion also contains the "
            "testicular artery and veins, lymphatics, the "
            "testicular nerve and the cremaster muscle (S3).",
        "clinical_note":
            "Because the duct is physically accessible within "
            "the scrotum, surgical sterilisation — vasectomy — "
            "cuts and seals a small section of it; the "
            "procedure is considered permanent (S4).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S3", "S4"]),
        ("course", ["S3", "S4"]),
        ("function", ["S3"]),
        ("parts", ["S3", "S4"]),
        ("clinical_note", ["S4"]),
    ])
    r["verify"] = [
        ABSENCE + " — 'ductus deferens', 'vas deferens', "
        "'spermatic' and 'ejaculat' all score zero hits in "
        "both parts lists and in all six release tables; the "
        "ejaculatory duct it ends in is likewise absent, so "
        "the male pathway's middle is missing from the data "
        "entire",
        TA_VERIFY,
    ]
    r["note"] = ("Sourced-text record for the pathway's missing "
                 "middle: the duct a vasectomy interrupts has "
                 "no more presence in the dataset than the ovary "
                 "does.")
    records.append(finish(
        r, core=["description", "course", "function"],
        soft=["parts", "clinical_note"]))

    r = base("gland.seminal-vesicles", "Seminal vesicles",
             "gland", "Male organs and glands", "male")
    link(r, inv_by_name, ["right seminal vesicle",
                          "left seminal vesicle"])
    typed(r, {
        "description":
            "Paired glands whose ducts join the ampullae of "
            "the ductus deferens behind the bladder to form the "
            "ejaculatory ducts, which then pass through the "
            "prostate and empty into the urethra (S3, S4).",
        "function":
            "Their secretion contributes approximately 60 "
            "percent of semen volume: rich in fructose, which "
            "the sperm's mitochondria burn for the ATP of "
            "movement, and alkaline, neutralising the acidic "
            "environment of the vagina; its prostaglandins act "
            "on the cervix (S4). Sperm are immobile until mixed "
            "with the seminal glands' secretions (S4).",
        "relations":
            "Posterior to the urinary bladder, the ductus "
            "deferens arched over it to meet them (S4); the "
            "ejaculatory ducts they form traverse the prostate "
            "gland (S3).",
        "arterial_supply": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S3", "S4"]),
        ("function", ["S4"]),
        ("relations", ["S3", "S4"]),
    ])
    r["verify"] = [
        "arterial_supply: no value asserted — none of the "
        "sources consulted in this session states the seminal "
        "vesicles' arterial supply in citable form; the field "
        "stays null rather than unsourced",
        TA_VERIFY,
    ]
    r["note"] = ("Geometry-linked, unlike the duct they join: "
                 "the release carries the glands but not the "
                 "ductus deferens or the ejaculatory duct they "
                 "complete.")
    records.append(finish(
        r, core=["description", "function"],
        soft=["relations", "arterial_supply"]))

    r = base("gland.prostate", "Prostate gland", "gland",
             "Male organs and glands", "male")
    link(r, inv_by_name, ["prostate"])
    typed(r, {
        "description":
            "The largest accessory gland of the male "
            "reproductive system: a walnut-sized gland of "
            "muscular and glandular tissue — about two-thirds "
            "glandular, one-third fibromuscular — surrounding "
            "the prostatic urethra at the base of the urinary "
            "bladder (S2, S4). It is the one member the "
            "release files under its own genital system.",
        "parts":
            "McNeal's zones (S2): the central zone, about 25 "
            "percent, surrounds the ejaculatory ducts; the "
            "transitional zone, 5–10 percent, surrounds the "
            "urethra and is where benign prostatic hyperplasia "
            "arises; the peripheral zone, about 65 percent, is "
            "the posterior main body — the zone palpable on "
            "rectal examination; and the anterior fibromuscular "
            "stroma is the fourth zone. The traditional lobes "
            "are also described by the source (S2). The "
            "release carries the gland as one undivided "
            "concept: no zone or lobe exists in the data.",
        "function":
            "It excretes a milky fluid into the passing semen: "
            "proteolytic enzymes via prostatic ducts opening "
            "into the prostatic urethra — among them "
            "prostate-specific antigen (PSA), which "
            "liquefies semen after its initial coagulation — "
            "with citric acid and the antibiotic seminalplasmin "
            "(S2, S4).",
        "relations":
            "Inferior to the neck of the bladder, superior to "
            "the external urethral sphincter, levator ani "
            "inferolaterally, and the ampulla of the rectum "
            "posteriorly — the relation by which the peripheral "
            "zone is palpated on digital rectal examination "
            "(S2). Its thin fibrous capsule is adventitia-like, "
            "not a true capsule (S2).",
        "arterial_supply":
            "Prostatic arteries arising mainly from the "
            "internal iliac artery, with contributions from "
            "the internal pudendal and middle rectal arteries "
            "(S2).",
        "venous_drainage":
            "The prostatic venous plexus drains into the "
            "internal iliac veins, and communicates with the "
            "internal vertebral venous plexus (Batson's) (S2).",
        "innervation":
            "From the inferior hypogastric plexus (S2). The "
            "neurovascular bundles flank the gland on their "
            "way to the corpora cavernosa — the anatomical "
            "basis of nerve-sparing prostatectomy (S2).",
        "lymphatic_drainage": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S2", "S4"]),
        ("parts", ["S2"]),
        ("function", ["S2", "S4"]),
        ("relations", ["S2"]),
        ("arterial_supply", ["S2"]),
        ("venous_drainage", ["S2"]),
        ("innervation", ["S2"]),
    ])
    r["verify"] = [
        "lymphatic_drainage: no value asserted — none of the "
        "sources consulted in this session states the "
        "prostate's lymphatic drainage in citable form; the "
        "field stays null rather than unsourced",
        TA_VERIFY,
    ]
    r["note"] = ("The release's only genital-system member gets "
                 "the tranche's fullest gland record — geometry, "
                 "zones, relations and the nerve-sparing "
                 "relation included.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["relations", "arterial_supply", "venous_drainage",
              "innervation", "lymphatic_drainage"]))

    r = base("gland.bulbourethral-glands", "Bulbourethral "
             "glands (Cowper's glands)", "gland",
             "Male organs and glands", "male")
    typed(r, {
        "description":
            "Two small glands whose ducts open into the penile "
            "(spongy) urethra (S3, S4).",
        "function":
            "They release a thick, salty mucus that lubricates "
            "the end of the urethra and the vagina and cleans "
            "urine residues from the penile urethra; the fluid "
            "is released after arousal and shortly before the "
            "semen — the pre-ejaculate — and can pick up sperm "
            "already present in the urethra (S4).",
        "position": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S3", "S4"]),
        ("function", ["S4"]),
    ])
    r["verify"] = [
        ABSENCE + " — 'bulbourethral' and 'cowper' score zero "
        "hits in both parts lists and in all six release "
        "tables",
        "position: no value asserted — none of the sources "
        "consulted in this session places the glands (the deep "
        "perineal pouch) in citable form, and the pouch itself "
        "has no concept in the release; the field stays null "
        "rather than unsourced",
        TA_VERIFY,
    ]
    r["note"] = ("The third accessory gland completes the "
                 "pathway's gland order as sourced text; the "
                 "release carries its two companions but not it.")
    records.append(finish(
        r, core=["description", "function"], soft=["position"]))

    r = base("organ.penis", "Penis", "organ",
             "Male organs and glands", "male")
    link(r, inv_by_name, ["corpus cavernosum of penis",
                          "corpus spongiosum of penis",
                          "glans penis"])
    typed(r, {
        "description":
            "The male organ of copulation, delivering sperm "
            "into the female reproductive tract: flaccid for "
            "non-sexual actions such as urination, turgid and "
            "rod-like with sexual arousal (S4). The release has "
            "no penis concept — no concept is named 'penis' "
            "(exact-name probe-verified) — so this record is "
            "assembled from the three erectile structures the "
            "release does carry, with its vessels in the "
            "cardiovascular module (S10).",
        "parts":
            "The shaft is composed of three column-like "
            "chambers of erectile tissue: the two larger "
            "lateral corpora cavernosa, which together make up "
            "the bulk of the penis, and the smaller corpus "
            "spongiosum, felt as a raised ridge on the erect "
            "penis, which surrounds the spongy (penile) "
            "urethra (S4). The end of the penis is the glans "
            "penis, its skin rich in nerve endings; the skin "
            "of the shaft extends over the glans as a collar, "
            "the prepuce (foreskin) (S4). The prepuce has no "
            "concept in the release — 'prepuce' scores zero "
            "hits — and is text here only.",
        "function":
            "Copulation and semen delivery, and — through the "
            "spongy urethra it encloses — the exit of urine "
            "(S4). Erection is vasocongestion: on arousal, "
            "nitric oxide from nerve endings relaxes the smooth "
            "muscle of the penile arteries, the erectile "
            "chambers fill faster than the veins drain them, "
            "and the pressure of the filled chambers compresses "
            "the thin-walled venules, trapping the blood (S4).",
        "arterial_supply":
            "The penile arteries whose dilation drives "
            "erection (S4) are carried by name in the release "
            "only in the cardiovascular module: the dorsal "
            "arteries of the penis, records "
            "artery.right-dorsal-artery-of-penis and "
            "artery.left-dorsal-artery-of-penis (S10).",
        "venous_drainage":
            "The veins the release names for this organ are "
            "the cardiovascular module's records "
            "vein.deep-dorsal-vein-of-penis, "
            "vein.right-superficial-dorsal-vein-of-penis and "
            "vein.left-superficial-dorsal-vein-of-penis (S10); "
            "the erectile mechanism compresses the penile "
            "venules against drainage (S4).",
        "innervation": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S4", "S10"]),
        ("parts", ["S4"]),
        ("function", ["S4"]),
        ("arterial_supply", ["S4", "S10"]),
        ("venous_drainage", ["S4", "S10"]),
    ])
    r["verify"] = [
        "innervation: no value asserted — none of the sources "
        "consulted in this session states the penile "
        "innervation in citable form; the pudendal nerve is "
        "not asserted here, and no penile nerve concept exists "
        "in the release (nervous module census)",
        TA_VERIFY,
    ]
    r["note"] = ("An organ the dataset represents only in "
                 "pieces: three erectile structures here, five "
                 "vessels in the cardiovascular module, and no "
                 "whole-organ concept anywhere.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["arterial_supply", "venous_drainage",
              "innervation"]))

    # ============ the female pathway ============
    r = base("pathway.female-reproductive-pathway",
             "Female reproductive pathway", "pathway",
             "Female pathway", "female")
    typed(r, {
        "description":
            "The route of the oocyte, and in pregnancy of the "
            "conceptus: the ovary produces and releases the "
            "oocyte, the uterine tube conveys it to the uterus, "
            "the uterus receives it — the usual site of "
            "implantation — and the vagina is the tract's canal "
            "to the exterior (S5, S6, S9).",
        "stations": [
            "ovary", "uterine tube", "uterus", "cervix",
            "vagina", "vestibule of the vagina"],
        "function":
            "Gamete production in the ovary, transport along "
            "the tube, implantation and gestation in the "
            "uterus, and delivery through the vagina: the "
            "internal organs work together as a conduit for "
            "sperm to reach the egg and for the development "
            "and birth of the fetus (S9).",
        "dataset_note":
            "Every station of this pathway is a dataset "
            "absence: not one of these structures has a "
            "concept in BP3D 4.0 (probe-verified per sex line "
            "by tools/repro_map.py). The pathway record exists "
            "so that the module states the female tract's "
            "sourced anatomy and its total absence in one "
            "place; the only female geometry in the module is "
            "the mons pubis, which is not a station of this "
            "pathway but the surface landmark at its end "
            "(structure.mons-pubis).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S5", "S6", "S9"]),
        ("stations", ["S5", "S6", "S7", "S9"]),
        ("function", ["S9"]),
        ("dataset_note", ["S10"]),
    ])
    r["verify"] = [
        ABSENCE + " — for every station of the pathway, not "
        "one structure: 'ovary', 'uterus', 'vagina' and "
        "'uterine' all score zero hits in both parts lists "
        "and in all six release tables",
        TA_VERIFY,
    ]
    r["note"] = ("A pathway with no geometry at any station — "
                 "the exact inverse of the male pathway, whose "
                 "first stations are the dataset's best-served "
                 "organs.")
    records.append(finish(
        r, core=["description", "stations", "function"],
        soft=["dataset_note"]))

    # ============ female organs ============
    r = base("organ.ovary", "Ovary", "organ", "Female organs",
             "female")
    typed(r, {
        "description":
            "The female gonads: paired, oval organs attached "
            "to the posterior surface of the broad ligament of "
            "the uterus by the mesovarium, a fold of peritoneum "
            "continuous with the ovaries' outer surface, with "
            "neurovascular structures entering at the hilum "
            "(S5).",
        "parts":
            "Three histological components (S5): the surface, "
            "a simple cuboidal epithelium (the germinal "
            "epithelium) over a dense connective-tissue "
            "capsule; the cortex, a connective-tissue stroma "
            "carrying numerous ovarian follicles, each an "
            "oocyte surrounded by follicular cells; and the "
            "medulla, loose connective tissue with a rich "
            "neurovascular network entering at the hilum. No "
            "component has a concept in the release.",
        "function":
            "To produce oocytes (female gametes) in preparation "
            "for fertilisation, and to produce the sex steroid "
            "hormones oestrogen and progesterone in response to "
            "the pituitary gonadotrophins LH and FSH (S5).",
        "dimension":
            "Paired ovals some 2 to 3 cm long, seated in the "
            "pelvic cavity: the gonads develop in the "
            "mesonephric ridge and descend through the abdomen, "
            "but unlike the testes the ovaries stop in the "
            "pelvis (S5, S7).",
        "ligaments":
            "Two peritoneal ligaments (S5): the suspensory "
            "ligament of the ovary, extending from the "
            "mesovarium to the pelvic wall and containing the "
            "neurovascular structures; and the ligament of the "
            "ovary, extending from the ovary to the fundus of "
            "the uterus, then continuing from the uterus to "
            "the labium majus as the round ligament of the "
            "uterus.",
        "arterial_supply":
            "The paired ovarian arteries arise directly from "
            "the abdominal aorta, inferior to the renal "
            "arteries; there is also a contribution from the "
            "uterine arteries (S5). Dataset gap, recorded: the "
            "cardiovascular module carries no ovarian artery "
            "record, the release having no ovarian vessel "
            "concept either (S10) — unlike the testis, whose "
            "arteries the sister module holds, this supply has "
            "no cross-module pointer to resolve.",
        "venous_drainage":
            "Paired ovarian veins: the left drains into the "
            "left renal vein, the right directly into the "
            "inferior vena cava (S5) — the same asymmetry as "
            "the testicular veins, and likewise without a "
            "cardiovascular record in the release (S10).",
        "lymphatic_drainage":
            "Lymph from the ovaries drains into the para-aortic "
            "nodes (S5). No para-aortic node exists as a "
            "concept in the release (lymphatic module census).",
        "innervation":
            "Sympathetic and parasympathetic fibres from the "
            "ovarian and uterine (pelvic) plexuses "
            "respectively, reaching the ovary via the "
            "suspensory ligament to enter at the hilum (S5).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S5"]),
        ("parts", ["S5"]),
        ("function", ["S5"]),
        ("dimension", ["S5", "S7"]),
        ("ligaments", ["S5"]),
        ("arterial_supply", ["S5", "S10"]),
        ("venous_drainage", ["S5", "S10"]),
        ("lymphatic_drainage", ["S5"]),
        ("innervation", ["S5"]),
    ])
    r["verify"] = [
        ABSENCE + " — the absence is recorded on this record "
        "itself, as the milestone directs: 'ovary', 'ovarian', "
        "'ovarian follicle' and 'corpus luteum' score zero "
        "hits in both parts lists and in all six release "
        "tables; Milestone 13 recorded the same absence at "
        "the endocrine boundary and this record inherits it",
        TA_VERIFY,
    ]
    r["note"] = ("The module's headline record: a fully sourced "
                 "account (tier A on fields) of the female gonad "
                 "over a total dataset absence — the mirror "
                 "image of organ.testis, which has geometry, "
                 "vessels and a census line.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["dimension", "ligaments", "arterial_supply",
              "venous_drainage", "lymphatic_drainage",
              "innervation"]))

    r = base("duct.uterine-tube", "Uterine tube "
             "(Fallopian tube)", "duct", "Female organs",
             "female")
    typed(r, {
        "description":
            "Paired tubes extending laterally from the upper "
            "uterus toward the ovaries, serving as the pathway "
            "for oocytes from the ovary to the uterine cavity "
            "(S7, S9).",
        "parts":
            "The distal end, nearest the ovary, carries "
            "finger-like projections — the fimbriae — which "
            "overhang the ovary and receive the released "
            "oocyte (S7).",
        "function":
            "Transport: the tube conveys the oocyte, and after "
            "fertilisation the embryo, slowly to the uterus, "
            "where implantation follows (S7, S9).",
        "regional_subdivisions": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S7", "S9"]),
        ("parts", ["S7"]),
        ("function", ["S7", "S9"]),
    ])
    r["verify"] = [
        ABSENCE + " — 'uterine', 'fallopian' and 'fimbria' "
        "score zero hits in both parts lists and in all six "
        "release tables",
        "regional_subdivisions: the tube's named regions "
        "beyond the fimbriae are not asserted — they are not "
        "named in citable form in the sources consulted in "
        "this session, and no regional concept exists in the "
        "release; the field stays null rather than unsourced",
        TA_VERIFY,
    ]
    r["note"] = ("Sourced-text record; the fimbriae are its one "
                 "sourced part, the rest of the tube's regional "
                 "anatomy flagged rather than filled.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["regional_subdivisions"]))

    r = base("organ.uterus", "Uterus", "organ", "Female organs",
             "female")
    typed(r, {
        "description":
            "A thick-walled muscular organ of the female "
            "reproductive tract, capable of expansion to "
            "accommodate a growing fetus, connected distally "
            "to the vagina and laterally to the uterine tubes "
            "(S6). It is a secondary sex organ — a component of "
            "the tract that matures during puberty under the "
            "influence of the ovaries' sex hormones (S6).",
        "parts":
            "Three parts (S6): the fundus, the top of the "
            "uterus above the entry point of the uterine "
            "tubes; the body, the usual site for implantation "
            "of the blastocyst; and the cervix, the lower part "
            "linking the uterus with the vagina, structurally "
            "and functionally different to the rest of the "
            "uterus.",
        "function":
            "The maintenance and transportation of gametes "
            "(S6), the housing of the implanted conceptus "
            "through gestation, and — by the contractions of "
            "its myometrium — delivery (S6, S9).",
        "wall_layers":
            "The fundus and body are composed of three tissue "
            "layers (S6): the perimetrium, a double-layered "
            "peritoneal membrane; the myometrium, a thick "
            "smooth-muscle layer whose cells undergo "
            "hypertrophy and hyperplasia during pregnancy; and "
            "the endometrium, the inner mucous membrane, whose "
            "deep stratum basalis changes little through the "
            "cycle and is not shed, while its superficial "
            "stratum functionalis proliferates under oestrogen, "
            "becomes secretory under progesterone, and is shed "
            "at menstruation. No layer has a concept in the "
            "release.",
        "dimension":
            "About 5 cm wide and 7 cm long in the "
            "non-pregnant adult (S7).",
        "position":
            "In the normal adult the uterus is anteverted with "
            "respect to the vagina and anteflexed with respect "
            "to the cervix, lying immediately posterosuperior "
            "to the bladder and anterior to the rectum; its "
            "exact location varies with the distension of the "
            "bladder (S6).",
        "ligaments":
            "The tone of the pelvic floor is the primary "
            "support; the ligaments secure it further (S6): "
            "the broad ligament, a double layer of peritoneum "
            "attaching the sides of the uterus to the pelvis "
            "and acting as its mesentery; the round ligament, "
            "a gubernacular remnant running from the uterine "
            "horns to the labia majora via the inguinal canal, "
            "maintaining anteversion; the ovarian ligament, "
            "joining the ovaries to the uterus; the cardinal "
            "ligament at the base of the broad ligament, from "
            "the cervix to the lateral pelvic walls, containing "
            "the uterine artery and vein; and the uterosacral "
            "ligament, from the cervix to the sacrum. No "
            "ligament has a concept in the release.",
        "arterial_supply":
            "The uterine artery, a branch of the internal "
            "iliac artery (S6). It crosses the ureter "
            "approximately 1 cm lateral to the internal os — "
            "'water under the bridge' — the relation that "
            "hysterectomy must respect (S6).",
        "venous_drainage":
            "Via a plexus in the broad ligament that drains "
            "into the uterine veins (S6).",
        "lymphatic_drainage":
            "Via the iliac, sacral, aortic and inguinal lymph "
            "nodes (S6). None exists as a concept in the "
            "release (lymphatic module census).",
        "innervation":
            "Sympathetic fibres from the uterovaginal plexus — "
            "largely the anterior and intermediate parts of the "
            "inferior hypogastric plexus; parasympathetic "
            "fibres from the pelvic splanchnic nerves (S2–S4); "
            "the cervix largely by the inferior fibres of the "
            "uterovaginal plexus; afferents ascending through "
            "the inferior hypogastric plexus to T10–T12 and L1 "
            "(S6).",
    })
    r["sources"] = OrderedDict([
        ("description", ["S6"]),
        ("parts", ["S6"]),
        ("function", ["S6", "S9"]),
        ("wall_layers", ["S6"]),
        ("dimension", ["S7"]),
        ("position", ["S6"]),
        ("ligaments", ["S6"]),
        ("arterial_supply", ["S6"]),
        ("venous_drainage", ["S6"]),
        ("lymphatic_drainage", ["S6"]),
        ("innervation", ["S6"]),
    ])
    r["verify"] = [
        ABSENCE + " — 'uterus' and 'uterine' score zero hits "
        "in both parts lists and in all six release tables, "
        "and the wall layers with them: 'endometrium', "
        "'myometrium' and 'perimetrium' are likewise zero-hit "
        "probes",
        TA_VERIFY,
    ]
    r["note"] = ("Fully sourced (tier A on fields) over a total "
                 "dataset absence, like organ.ovary: the "
                 "release contains the ureter this organ's "
                 "artery crosses, but not the organ.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["wall_layers", "dimension", "position",
              "ligaments", "arterial_supply", "venous_drainage",
              "lymphatic_drainage", "innervation"]))

    r = base("organ.vagina", "Vagina", "organ", "Female organs",
             "female")
    typed(r, {
        "description":
            "A muscular, epithelium-lined tube known as the "
            "vagina connects the vulva to the cervix of the "
            "uterus (S9); it is continuous superiorly with the "
            "cervix and communicates with the exterior at the "
            "vaginal orifice in the vestibule (S7).",
        "parts":
            "Its upper end meets the cervix in the recess "
            "called the fornix (S7). The canal is a muscular "
            "tube lined with stratified squamous epithelium "
            "over smooth muscle (S7). The fornix named here is "
            "the vaginal one: the release's only fornix "
            "concepts are cerebral (the fornix of forebrain, "
            "nervous module) — the vaginal fornix has no "
            "concept, a naming collision the census sweep "
            "adjudicates (S10).",
        "function":
            "The tract's canal to the exterior: the internal "
            "organs work together as a conduit for sperm to "
            "reach the egg during intercourse and for the "
            "development and birth of the fetus, and the "
            "vagina is that conduit's lower passage, from the "
            "cervix to the vestibule (S9).",
        "dimension":
            "Approximately 10 cm long in the adult (S7).",
        "arterial_supply": None,
        "innervation": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S7", "S9"]),
        ("parts", ["S7", "S10"]),
        ("function", ["S9"]),
        ("dimension", ["S7"]),
    ])
    r["verify"] = [
        ABSENCE + " — 'vagina' and 'vaginal' score zero hits "
        "in both parts lists and in all six release tables",
        "arterial_supply: no value asserted — none of the "
        "sources consulted in this session states the "
        "vagina's arterial supply in citable form; the field "
        "stays null rather than unsourced",
        "innervation: no value asserted — none of the sources "
        "consulted in this session states the vagina's "
        "innervation in citable form; the field stays null "
        "rather than unsourced",
        TA_VERIFY,
    ]
    r["note"] = ("Sourced-text record; the dataset's only "
                 "'fornix' is in the brain, not here.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["dimension", "arterial_supply", "innervation"]))

    r = base("structure.vulva", "Vulva", "structure",
             "Female organs", "female")
    typed(r, {
        "description":
            "The external female reproductive organs, known "
            "collectively as the vulva: several folds of skin "
            "surrounding the urinary and reproductive orifices "
            "(S9).",
        "parts":
            "The mons pubis; the labia majora and labia minora, "
            "the folds surrounding the orifices; the clitoris; "
            "the vestibule, into which the urethra and vagina "
            "open; the vestibular (Bartholin's) glands flanking "
            "the vaginal opening; and the hymen (S7, S9). Of "
            "these, only the mons pubis has a concept in the "
            "release — held as this module's own record "
            "structure.mons-pubis; the clitoris, the labia, the "
            "vestibule and the glands are all zero-hit absences "
            "(S10).",
        "function":
            "The external genitalia of the female, seated in "
            "the urogenital triangle of the perineum around the "
            "openings of the urethra and the vagina (S8, S9).",
        "arterial_supply": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S9"]),
        ("parts", ["S7", "S9", "S10"]),
        ("function", ["S8", "S9"]),
    ])
    r["verify"] = [
        ABSENCE + " — 'vulva', 'clitoris', 'labia', 'labium' "
        "and 'hymen' score zero hits in both parts lists and "
        "in all six release tables; the mons pubis is the "
        "sole exception and is a separate record",
        "arterial_supply: no value asserted — none of the "
        "sources consulted in this session states the vulva's "
        "arterial supply in citable form; the field stays "
        "null rather than unsourced",
        TA_VERIFY,
    ]
    r["note"] = ("A collective term whose members are absent "
                 "almost to one: the vulva exists in this module "
                 "as a sourced parts list and a single fatty "
                 "pad of geometry.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["arterial_supply"]))

    r = base("structure.mons-pubis", "Mons pubis", "structure",
             "Female organs", "female")
    link(r, inv_by_name, ["mons pubis"])
    typed(r, {
        "description":
            "The pad of fat anteriorly over the pubic bone "
            "(S7): in the female it forms the surface anterior "
            "border of the perineum (S8). It is the only "
            "female-named reproductive concept in the release — "
            "filed in PART-OF under the pelvis, there being no "
            "female genital tree — and so it is the female "
            "line's only geometry (S10).",
        "parts": None,
        "function": None,
        "relations": None,
    })
    r["sources"] = OrderedDict([
        ("description", ["S7", "S8", "S10"]),
    ])
    r["verify"] = [
        "parts: no value asserted — the release carries the "
        "mons pubis as a single undivided concept and none of "
        "the sources consulted in this session subdivides it; "
        "the field stays null rather than unsourced",
        "function: no value asserted — beyond its descriptive "
        "identity as the fatty pad over the pubic bone, none "
        "of the sources consulted in this session assigns the "
        "mons pubis a function in citable form; the field "
        "stays null rather than unsourced",
        "relations: no value asserted — none of the sources "
        "consulted in this session states the mons pubis' "
        "relations in citable form beyond the perineum's "
        "surface border already carried in the description; "
        "the field stays null rather than unsourced",
        TA_VERIFY,
    ]
    r["note"] = ("The tranche's one tier-C record, and the "
                 "female line's one geometry record: the "
                 "dataset's entire female reproductive presence "
                 "is a pad of fat the sources describe in a "
                 "sentence. Recorded thin, not padded.")
    records.append(finish(
        r, core=["description", "parts", "function"],
        soft=["relations"]))

    # ============ shared: the perineum ============
    r = base("region.perineum", "Perineum", "region", "Shared",
             "shared")
    link(r, inv_by_name, ["perineum",
                          "anal part of perineum"])
    typed(r, {
        "description":
            "An anatomical region in the pelvis, located "
            "between the thighs, representing the most inferior "
            "part of the pelvic outlet and separated from the "
            "pelvic cavity superiorly by the pelvic floor (S8). "
            "In clinical usage the word is often narrowed to "
            "the area between the external genitalia and the "
            "anus; anatomically it is the whole diamond (S8).",
        "boundaries":
            "Anatomical borders (S8): anteriorly the pubic "
            "symphysis; posteriorly the tip of the coccyx; "
            "laterally the inferior pubic rami and inferior "
            "ischial rami and the sacrotuberous ligament; the "
            "roof is the pelvic floor and the base skin and "
            "fascia. Surface borders, with the limbs abducted "
            "(S8): anteriorly the mons pubis in females, the "
            "base of the penis in males; laterally the medial "
            "surfaces of the thighs; posteriorly the superior "
            "end of the intergluteal cleft.",
        "parts":
            "A theoretical line drawn transversely between the "
            "ischial tuberosities divides the diamond into the "
            "anterior urogenital triangle and the posterior "
            "anal triangle (S8). The anal triangle — bounded by "
            "the coccyx, the sacrotuberous ligaments and the "
            "intertuberosity line — contains the anal aperture, "
            "the external anal sphincter muscle and the paired "
            "ischioanal fossae (S8). The urogenital triangle is "
            "associated with the structures of the urogenital "
            "system, the external genitalia and the urethra "
            "(S8). At the junction of the two triangles sits "
            "the perineal body, an irregular fibromuscular mass "
            "at the central point of the perineum (S8). Of "
            "these named parts, none has a concept in the "
            "release: the triangles, the perineal body and the "
            "ischioanal fossae are all zero-hit shared-line "
            "probes (S10).",
        "function":
            "The region contains the structures that support "
            "the urogenital and gastrointestinal systems, and "
            "so plays its part in micturition, defecation, "
            "sexual intercourse and childbirth (S8).",
        "dataset_note":
            "The release's perineal geometry is a single "
            "muscle's shape: the perineum and its anal part "
            "carry the same four mesh files in PART-OF, and "
            "those four files are exactly the file set of the "
            "external anal sphincter — the muscular module's "
            "record muscle.external-anal-sphincter, censused "
            "in this module as a cross-reference (S10). The "
            "sphincter is the anal triangle's one muscular "
            "content the source names (S8) and the only "
            "perineal structure the dataset draws.",
    })
    r["sources"] = OrderedDict([
        ("description", ["S8"]),
        ("boundaries", ["S8"]),
        ("parts", ["S8", "S10"]),
        ("function", ["S8"]),
        ("dataset_note", ["S10"]),
    ])
    r["verify"] = [TA_VERIFY]
    r["note"] = ("Shared ground in every sense: one region for "
                 "both sex lines, its clinical anatomy sourced "
                 "whole, its geometry borrowed entire from a "
                 "muscle another module owns.")
    records.append(finish(
        r, core=["description", "boundaries", "parts",
                 "function"],
        soft=["dataset_note"]))

    tiers = {}
    tiers_by_group = {}
    tiers_by_sex = {}
    for rec in records:
        tiers[rec["sourcing_tier"]] = tiers.get(
            rec["sourcing_tier"], 0) + 1
        tiers_by_group.setdefault(rec["group"], {}).setdefault(
            rec["sourcing_tier"], 0)
        tiers_by_group[rec["group"]][rec["sourcing_tier"]] += 1
        tiers_by_sex.setdefault(rec["sex_line"], {}).setdefault(
            rec["sourcing_tier"], 0)
        tiers_by_sex[rec["sex_line"]][rec["sourcing_tier"]] += 1
    doc = OrderedDict([
        ("meta", OrderedDict([
            ("title", "ANATOMICA reproductive system clinical "
                      "records — Milestone 14"),
            ("generated_by", "tools/build_repro_records.py"),
            ("sources", SOURCES),
            ("record_count", len(records)),
            ("tiers", tiers),
            ("tiers_by_group", tiers_by_group),
            ("tiers_by_sex_line", tiers_by_sex),
            ("groups", list(OrderedDict.fromkeys(
                r["group"] for r in records))),
            ("sourcing_rule",
             "every field value is drawn only from the sources "
             "listed, consulted in this session, and cites them "
             "per field in the record's sources map; a field no "
             "consulted source supports is null and carries a "
             "verify entry naming it. TA names are not asserted "
             "anywhere in this tranche (no TA2 list consulted). "
             "Seven records link geometry the release carries "
             "(testis, epididymis, seminal vesicles, prostate, "
             "penis — assembled from its erectile parts — mons "
             "pubis, and the perineum with its anal part); the "
             "remaining nine link none — eight with the dataset "
             "absence recorded (the ductus deferens, the "
             "bulbourethral glands, and the female tract's "
             "pathway, ovary, uterine tube, uterus, vagina and "
             "vulva) and the male pathway with its own "
             "no-geometry statement. The "
             "urethra is not duplicated: the male pathway "
             "record states its relationship and points at the "
             "urinary module's records, and the checker "
             "resolves the pointer."),
        ])),
        ("records", records),
    ])
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print(f"wrote {OUT}: {len(records)} records, tiers {tiers}")
    print("tiers by group:", tiers_by_group)
    print("tiers by sex line:", tiers_by_sex)
    for rec in records:
        print(" ", rec["id"], rec["sourcing_tier"],
              "links:", rec["geometry_record_ids"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
