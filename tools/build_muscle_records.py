#!/usr/bin/env python3
"""Build data/muscular/muscles.json — the Milestone 4 clinical tranche.

FIELD-SOURCING RULE (precision law): every origin / insertion / action /
innervation / arterial-supply value below was transcribed from a source
actually consulted in the build session (fetched page text or a search
extract read in-session); each field carries its source key. A field with
no consulted source is left null and listed in the record's "verify"
array — never filled from unaided recall.

Where two consulted sources conflict, the record follows the source
judged more reliable for that field and the conflict is recorded in the
record's note (known cases: StatPearls' levator scapulae entry duplicates
its latissimus dorsi data; StatPearls gives flexor carpi ulnaris a median
nerve; StatPearls gives teres minor the teres major origin; StatPearls
gives extensor pollicis brevis a distal-phalanx insertion — that field is
verify-flagged instead of entered).

Records are class-level (one per named muscle); the geometry link lists
the per-side inventory records from muscle-inventory.json.

Run:  python3 tools/build_muscle_records.py
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INV_PATH = os.path.join(ROOT, "data", "muscular", "muscle-inventory.json")
OUT_PATH = os.path.join(ROOT, "data", "muscular", "muscles.json")

SOURCES = {
    "TMA-SB": ("TeachMeAnatomy, 'The Superficial Back Muscles', "
               "teachmeanatomy.info/back/muscles/superficial/ "
               "(updated 2024-11-02; consulted 2026-11-06)"),
    "TMA-IB": ("TeachMeAnatomy, 'The Intrinsic Back Muscles', "
               "teachmeanatomy.info/back/muscles/intrinsic/ "
               "(updated 2025-11-06; consulted 2026-11-06)"),
    "TMA-SO": ("TeachMeAnatomy, 'Suboccipital Muscles', "
               "teachmeanatomy.info/neck/muscles/suboccipital/ "
               "(updated 2025-11-06; consulted 2026-11-06)"),
    "ANK-BACK": ("Sen Esmer T., 'Muscles of the Back' lecture, Ankara "
                 "University, hosted at docslib.org (consulted 2026-11-06 "
                 "via search extract)"),
    "GM-SO": ("Geeky Medics, 'The Suboccipital Muscles', "
              "geekymedics.com/the-suboccipital-muscles/ (consulted "
              "2026-11-06 via search extract)"),
    "SP-UL": ("StatPearls, 'Anatomy, Shoulder and Upper Limb, Muscles', "
              "statpearls.com/articlelibrary/viewarticle/31505/ "
              "(published 2023-07-24; consulted 2026-11-06)"),
    "TMA-IS": ("TeachMeAnatomy, 'The Intrinsic Muscles of the Shoulder', "
               "teachmeanatomy.info/upper-limb/muscles/shoulder/intrinsic/ "
               "(updated 2025-10-28; consulted 2026-11-06)"),
    "TMA-UA": ("TeachMeAnatomy, 'The Upper Arm Muscles - Anterior & "
               "Posterior Compartments', "
               "teachmeanatomy.info/upper-limb/muscles/upper-arm/ "
               "(updated 2026-04-10; consulted 2026-11-06)"),
    "TMA-AF": ("TeachMeAnatomy, 'Anterior Forearm Flexor Muscles', "
               "teachmeanatomy.info/upper-limb/muscles/anterior-forearm/ "
               "(updated 2025-12-15; consulted 2026-11-06)"),
    "MMS-HAND": ("MyMedSchool anatomy course, intrinsic hand muscles "
                 "table, mymedschool.org (consulted 2026-11-06 via "
                 "search extract)"),
}

# Each entry: key = BP3D class/set concept name used to resolve the
# geometry link against the inventory. Fields: o=origin, i=insertion,
# a=actions, n=nerve, r=root values, s=arterial supply (list) or None,
# src={field: source key}, v=extra verify fields, note.
E = []
def add(key, region, sub, o, i, a, n, r, s, src, v=(), note=None,
        name=None):
    E.append(dict(key=key, region=region, sub=sub, o=o, i=i, a=a, n=n,
                  r=r, s=s, src=src, v=list(v), note=note, name=name))

# ---------------------------------------------------------------- back
SB = "TMA-SB"; IB = "TMA-IB"; SO = "TMA-SO"
add("trapezius", "back", "superficial (extrinsic)",
    ["skull", "ligamentum nuchae", "spinous processes of C7-T12"],
    ["clavicle", "acromion", "spine of the scapula"],
    ["upper fibres elevate the scapula and rotate it during abduction "
     "of the arm", "middle fibres retract the scapula",
     "lower fibres pull the scapula inferiorly"],
    "accessory nerve", "C3, C4 (proprioceptor fibres)", None,
    dict(o=SB, i=SB, a=SB, n=SB, r=SB))
add("levator scapulae", "back", "superficial (extrinsic)",
    ["transverse processes of the C1-C4 vertebrae"],
    ["medial border of the scapula"],
    ["elevates the scapula"],
    "dorsal scapular nerve", None, None,
    dict(o=SB, i=SB, a=SB, n=SB), v=["innervation.root_values"],
    note="StatPearls' shoulder article gives this muscle the thoracodorsal "
         "nerve and latissimus dorsi actions (an apparent copy error in "
         "that source); the TeachMeAnatomy values are used.")
add("rhomboid major", "back", "superficial (extrinsic)",
    ["spinous processes of T2-T5 vertebrae"],
    ["medial border of the scapula, between the spine of the scapula "
     "and the inferior angle"],
    ["retracts and rotates the scapula"],
    "dorsal scapular nerve", "C4, C5", None,
    dict(o=SB, i=SB, a=SB, n=SB, r="SP-UL"))
add("rhomboid minor", "back", "superficial (extrinsic)",
    ["spinous processes of C7-T1 vertebrae"],
    ["medial border of the scapula, at the level of the spine of "
     "the scapula"],
    ["retracts and rotates the scapula"],
    "dorsal scapular nerve", "C4, C5", None,
    dict(o=SB, i=SB, a=SB, n=SB, r="SP-UL"))
add("serratus posterior superior", "back", "intermediate (extrinsic)",
    ["nuchal ligament", "spinous processes of C7-T3 vertebrae"],
    ["superior borders of ribs 2-4"],
    ["elevates the ribs it attaches to; proprioceptive role; "
     "contributes to deep inspiration"],
    "anterior rami of the upper thoracic spinal nerves", "T2-T5", None,
    dict(o="ANK-BACK", i="ANK-BACK", a="ANK-BACK", n="ANK-BACK",
         r="ANK-BACK"),
    note="Some teaching sources give the insertion as ribs 2-5; the "
         "Ankara University lecture value (ribs 2-4) is recorded.")
add("serratus posterior inferior", "back", "intermediate (extrinsic)",
    ["spinous processes of T11-L2 vertebrae"],
    ["inferior borders of ribs 8-12 near their angles"],
    ["depresses the ribs it attaches to; proprioceptive role; "
     "contributes to forced expiration"],
    "anterior rami of the lower thoracic spinal nerves", "T9-T12", None,
    dict(o="ANK-BACK", i="ANK-BACK", a="ANK-BACK", n="ANK-BACK",
         r="ANK-BACK"))
add("splenius capitis", "back", "intrinsic, superficial layer",
    ["lower aspect of the ligamentum nuchae",
     "spinous processes of C7-T3/4 vertebrae"],
    ["mastoid process", "occipital bone"],
    ["rotates the head to the same side",
     "acting together (bilaterally): extends the head and neck"],
    "posterior rami of the spinal nerves", "C3, C4", None,
    dict(o=IB, i=IB, a=IB, n=IB, r=IB))
add("splenius cervicis", "back", "intrinsic, superficial layer",
    ["spinous processes of T3-T6 vertebrae"],
    ["transverse processes of C1-3/4"],
    ["rotates the head to the same side",
     "acting together (bilaterally): extends the head and neck"],
    "posterior rami of the lower cervical spinal nerves", None, None,
    dict(o=IB, i=IB, a=IB, n=IB), v=["innervation.root_values"])
ES_ORIGIN = ["common tendinous origin of the erector spinae: lower "
             "thoracic and lumbar vertebrae, sacrum, posterior aspect "
             "of the iliac crest, sacroiliac and supraspinous ligaments"]
ES_ACTIONS = ["acts unilaterally to laterally flex the vertebral column",
              "acts bilaterally to extend the vertebral column and head"]
for key, ins in (
        ("iliocostalis lumborum",
         "costal angle of the ribs and the cervical transverse processes "
         "(attachments as stated for the iliocostalis column as a whole)"),
        ("iliocostalis thoracis",
         "costal angle of the ribs and the cervical transverse processes "
         "(attachments as stated for the iliocostalis column as a whole)"),
        ("iliocostalis cervicis",
         "costal angle of the ribs and the cervical transverse processes "
         "(attachments as stated for the iliocostalis column as a whole)"),
        ("longissimus thoracis",
         "lower ribs, transverse processes of C2-T12, and the mastoid "
         "process (attachments as stated for the longissimus column as "
         "a whole)"),
        ("longissimus cervicis",
         "lower ribs, transverse processes of C2-T12, and the mastoid "
         "process (attachments as stated for the longissimus column as "
         "a whole)"),
        ("longissimus capitis",
         "lower ribs, transverse processes of C2-T12, and the mastoid "
         "process (attachments as stated for the longissimus column as "
         "a whole)"),
        ("spinalis thoracis",
         "spinous processes of C2, T1-T8 and the occipital bone "
         "(attachments as stated for the spinalis column as a whole)")):
    add(key, "back", "intrinsic, intermediate layer (erector spinae)",
        ES_ORIGIN, [ins], ES_ACTIONS,
        "posterior rami of the spinal nerves", None, None,
        dict(o=IB, i=IB, a=IB, n=IB), v=["innervation.root_values"],
        note="Attachments are the consulted source's statement for the "
             "erector spinae column as a whole, not a part-specific "
             "statement.")
SS_ACTIONS = ["extends and contralaterally rotates the head and "
              "vertebral column"]
for key in ("semispinalis thoracis", "semispinalis cervicis",
            "semispinalis capitis"):
    add(key, "back", "intrinsic, deep layer (transversospinales)",
        ["transverse processes of C4-T10"],
        ["spinous processes of C2-T4 and the occipital bone (fibres "
         "ascend 4-6 vertebral segments)"],
        SS_ACTIONS, "posterior rami of the spinal nerves", None, None,
        dict(o=IB, i=IB, a=IB, n=IB), v=["innervation.root_values"],
        note="Attachments are the consulted source's statement for the "
             "semispinalis group as a whole, not a part-specific "
             "statement.")
for key in ("cervical rotator", "thoracic rotator", "lumbar rotator"):
    add(key, "back", "intrinsic, deep layer (transversospinales)",
        ["vertebral transverse processes"],
        ["lamina and spinous processes of the vertebrae above"],
        ["contributes to extension and rotation of the vertebral "
         "column", "stabilises the vertebrae",
         "proprioceptive function"],
        "posterior rami of the spinal nerves", None, None,
        dict(o=IB, i=IB, a=IB, n=IB), v=["innervation.root_values"],
        note="Values are the consulted source's statement for the "
             "rotatores group as a whole.")
for key in ("interspinalis thoracis", "set of interspinales cervicis",
            "set of interspinales lumborum"):
    add(key, "back", "intrinsic, minor deep (segmental)",
        ["adjacent spinous processes (spans between them)"],
        ["adjacent spinous processes (spans between them)"],
        ["stabilises the vertebral column"],
        None, None, None,
        dict(o=IB, i=IB, a=IB), v=["innervation"],
        note="The consulted source describes the span and action of the "
             "interspinales only; its innervation is not stated there.")
for key in ("lateral lumbar intertransversarius",
            "medial lumbar intertransversarius",
            "set of anterior cervical intertransversarii",
            "set of posterior cervical intertransversarii"):
    add(key, "back", "intrinsic, minor deep (segmental)",
        ["adjacent transverse processes (spans between them)"],
        ["adjacent transverse processes (spans between them)"],
        ["stabilises the vertebral column"],
        None, None, None,
        dict(o=IB, i=IB, a=IB), v=["innervation"],
        note="The consulted source describes the span and action of the "
             "intertransversarii only; its innervation is not stated "
             "there.")
for key in ("set of levatores costarum breves",
            "set of levatores costarum longi"):
    add(key, "back", "intrinsic, minor deep (segmental)",
        ["transverse processes of C7-T11"],
        ["the rib immediately below"],
        ["elevates the ribs"],
        None, None, None,
        dict(o=IB, i=IB, a=IB), v=["innervation"],
        note="The consulted source gives attachments and action for the "
             "levatores costarum; its innervation is not stated there.")
SO_SUPPLY = ["vertebral artery",
             "deep descending branches of the occipital artery"]
add("rectus capitis posterior major", "neck", "suboccipital",
    ["spinous process of the C2 vertebra (axis)"],
    ["lateral part of the inferior nuchal line of the occipital bone"],
    ["extension and rotation of the head"],
    "suboccipital nerve (posterior ramus of C1)", "C1", SO_SUPPLY,
    dict(o=SO, i=SO, a=SO, n=SO, r=SO, s="GM-SO"),
    note="Arterial supply is the consulted source's statement for the "
         "suboccipital group as a whole.")
add("rectus capitis posterior minor", "neck", "suboccipital",
    ["posterior tubercle of the C1 vertebra"],
    ["medial part of the inferior nuchal line of the occipital bone"],
    ["extension of the head"],
    "suboccipital nerve (posterior ramus of C1)", "C1", SO_SUPPLY,
    dict(o=SO, i=SO, a=SO, n=SO, r=SO, s="GM-SO"),
    note="Arterial supply is the consulted source's statement for the "
         "suboccipital group as a whole.")
add("obliquus capitis inferior", "neck", "suboccipital",
    ["spinous process of the C2 vertebra"],
    ["transverse process of C1"],
    ["extension and rotation of the head"],
    "suboccipital nerve (posterior ramus of C1)", "C1", SO_SUPPLY,
    dict(o=SO, i=SO, a=SO, n=SO, r=SO, s="GM-SO"),
    note="Arterial supply is the consulted source's statement for the "
         "suboccipital group as a whole.")
add("obliquus capitis superior", "neck", "suboccipital",
    ["transverse process of C1"],
    ["occipital bone, between the superior and inferior nuchal lines"],
    ["extension of the head"],
    "suboccipital nerve (posterior ramus of C1)", "C1", SO_SUPPLY,
    dict(o=SO, i=SO, a=SO, n=SO, r=SO, s="GM-SO"),
    note="Arterial supply is the consulted source's statement for the "
         "suboccipital group as a whole.")

# ---------------------------------------------------------- upper limb
SP = "SP-UL"; IS = "TMA-IS"; UA = "TMA-UA"; AF = "TMA-AF"
UL = "upper limb"
add("pectoralis major", UL, "shoulder, anterior axioappendicular",
    ["clavicular head: anterior surface of the medial clavicle",
     "sternocostal head: anterior sternum, costal cartilages of ribs "
     "1-6, and the external oblique aponeurosis"],
    ["lateral edge of the intertubercular groove of the humerus"],
    ["flexion of the humerus", "adduction of the humerus",
     "medial rotation of the humerus"],
    "lateral and medial pectoral nerves",
    "lateral pectoral nerve C5, C6, C7; medial pectoral nerve C8, T1",
    None, dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("pectoralis minor", UL, "shoulder, anterior axioappendicular",
    ["third, fourth and fifth ribs, close to their costal cartilages"],
    ["coracoid process"],
    ["depression of the shoulder", "protraction of the scapula"],
    "medial pectoral nerve", "C8, T1", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("subclavius", UL, "shoulder, anterior axioappendicular",
    ["first rib, medially"],
    ["middle of the clavicle, inferiorly"],
    ["depression and stabilisation of the clavicle"],
    "nerve to subclavius", "C5, C6", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("serratus anterior", UL, "shoulder, anterior axioappendicular",
    ["lateral surfaces of the first to eighth ribs"],
    ["anterior (costal) surface of the scapula, medially"],
    ["protraction of the scapula", "rotation of the scapula"],
    "long thoracic nerve", "C5, C6, C7", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("deltoid", UL, "shoulder, intrinsic (scapulohumeral)",
    ["lateral third of the clavicle", "acromion", "spine of the scapula"],
    ["deltoid tuberosity of the humerus"],
    ["anterior fibres: flexion and medial rotation of the arm",
     "middle fibres: abduction of the arm (the major abductor)",
     "posterior fibres: extension and lateral rotation of the arm"],
    "axillary nerve", "C5, C6", None,
    dict(o=IS, i=IS, a=IS, n=IS, r=SP))
add("teres major", UL, "shoulder, intrinsic (scapulohumeral)",
    ["posterior surface of the inferior angle of the scapula"],
    ["medial lip of the intertubercular groove of the humerus"],
    ["adducts and extends at the shoulder", "medially rotates the arm"],
    "lower subscapular nerve", "C5, C6", None,
    dict(o=IS, i=IS, a=IS, n=IS, r=SP))
add("supraspinatus", UL, "shoulder, rotator cuff",
    ["supraspinous fossa of the scapula"],
    ["greater tubercle of the humerus"],
    ["abduction of the upper limb at the shoulder (first 0-15 degrees; "
     "assists the deltoid for 15-90 degrees)"],
    "suprascapular nerve", "C5, C6", None,
    dict(o=IS, i=IS, a=IS, n=IS, r=SP))
add("infraspinatus", UL, "shoulder, rotator cuff",
    ["infraspinous fossa of the scapula"],
    ["greater tubercle of the humerus"],
    ["laterally rotates the arm"],
    "suprascapular nerve", "C5, C6", None,
    dict(o=IS, i=IS, a=IS, n=IS, r=SP))
add("subscapularis", UL, "shoulder, rotator cuff",
    ["subscapular fossa, on the costal surface of the scapula"],
    ["lesser tubercle of the humerus"],
    ["medially rotates the arm"],
    "upper and lower subscapular nerves", "C5, C6, C7", None,
    dict(o=IS, i=IS, a=IS, n=IS, r=SP))
add("teres minor", UL, "shoulder, rotator cuff",
    ["posterior surface of the scapula, adjacent to its lateral border"],
    ["greater tubercle of the humerus"],
    ["laterally rotates the arm"],
    "axillary nerve", "C5, C6", None,
    dict(o=IS, i=IS, a=IS, n=IS, r=SP),
    note="StatPearls gives the origin as the inferior angle of the "
         "scapula (the teres major origin); the TeachMeAnatomy value "
         "is used.")
ARM_SUPPLY = ["muscular branches of the brachial artery"]
add("coracobrachialis", UL, "arm, anterior compartment",
    ["coracoid process of the scapula"],
    ["medial side of the humeral shaft, at the level of the deltoid "
     "tuberosity"],
    ["flexion of the arm at the shoulder", "weak adduction"],
    "musculocutaneous nerve", "C5, C6, C7", ARM_SUPPLY,
    dict(o=UA, i=UA, a=UA, n=UA, r=SP, s=UA),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the arm as a whole.")
add("biceps brachii", UL, "arm, anterior compartment",
    ["long head: supraglenoid tubercle of the scapula",
     "short head: coracoid process of the scapula"],
    ["radial tuberosity",
     "fascia of the forearm via the bicipital aponeurosis"],
    ["supination of the forearm",
     "flexion of the arm at the elbow and at the shoulder"],
    "musculocutaneous nerve", "C5, C6", ARM_SUPPLY,
    dict(o=UA, i=UA, a=UA, n=UA, r=SP, s=UA),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the arm as a whole.")
add("brachialis", UL, "arm, anterior compartment",
    ["medial and lateral surfaces of the humeral shaft"],
    ["ulnar tuberosity, just distal to the elbow joint"],
    ["flexion at the elbow"],
    "musculocutaneous nerve, with contributions from the radial nerve",
    "C5, C6 (C7 small contribution)", ARM_SUPPLY,
    dict(o=UA, i=UA, a=UA, n=UA, r=SP, s=UA),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the arm as a whole.")
add("triceps brachii", UL, "arm, posterior compartment",
    ["long head: infraglenoid tubercle of the scapula",
     "lateral head: humerus, superior to the radial groove",
     "medial head: humerus, inferior to the radial groove"],
    ["olecranon of the ulna"],
    ["extension of the arm at the elbow"],
    "radial nerve", "C6, C7, C8", ["profunda brachii artery"],
    dict(o=UA, i=UA, a=UA, n=UA, r=SP, s=UA),
    note="Arterial supply is the consulted source's statement for the "
         "posterior compartment of the arm.")
add("anconeus", UL, "arm, posterior compartment",
    ["lateral epicondyle of the humerus"],
    ["olecranon process and posterior ulna"],
    ["extension of the forearm", "stabilisation of the elbow joint"],
    "radial nerve", "C7, C8, T1", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
FA_SUPPLY = ["ulnar artery and radial artery"]
add("pronator teres", UL, "forearm, anterior compartment, superficial",
    ["medial epicondyle of the humerus",
     "coronoid process of the ulna"],
    ["lateral surface of the mid-shaft of the radius"],
    ["pronation of the forearm"],
    "median nerve", "C6, C7", FA_SUPPLY,
    dict(o=AF, i=AF, a=AF, n=AF, r=SP, s=AF),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the forearm as a whole.")
add("flexor carpi radialis", UL,
    "forearm, anterior compartment, superficial",
    ["medial epicondyle of the humerus"],
    ["base of metacarpals II and III"],
    ["flexion and abduction at the wrist"],
    "median nerve", "C6, C7", FA_SUPPLY,
    dict(o=AF, i=AF, a=AF, n=AF, r=SP, s=AF),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the forearm as a whole.")
add("palmaris longus", UL, "forearm, anterior compartment, superficial",
    ["medial epicondyle of the humerus"],
    ["flexor retinaculum and palmar aponeurosis of the hand"],
    ["flexion at the wrist", "tenses the palmar aponeurosis"],
    "median nerve", "C7, C8", FA_SUPPLY,
    dict(o=AF, i=AF, a=AF, n=AF, r=SP, s=AF),
    note="Absent in about 15% of the population (TeachMeAnatomy). "
         "Arterial supply is the consulted source's statement for the "
         "anterior compartment of the forearm as a whole.")
add("flexor carpi ulnaris", UL,
    "forearm, anterior compartment, superficial",
    ["humeral head: medial epicondyle of the humerus",
     "ulnar head: olecranon of the ulna"],
    ["pisiform bone", "hook of hamate", "base of the 5th metacarpal"],
    ["flexion and adduction at the wrist"],
    "ulnar nerve", None, FA_SUPPLY,
    dict(o=AF, i=AF, a=AF, n=AF, s=AF),
    v=["innervation.root_values"],
    note="StatPearls gives this muscle a median-nerve supply, which "
         "conflicts with TeachMeAnatomy (ulnar nerve) and standard "
         "teaching; the TeachMeAnatomy value is used and the root "
         "values are left flagged rather than taken from the "
         "conflicting entry. Arterial supply is the consulted "
         "source's statement for the anterior compartment of the "
         "forearm as a whole.")
add("flexor digitorum superficialis", UL,
    "forearm, anterior compartment, intermediate",
    ["medial epicondyle of the humerus", "coronoid process",
     "anterior radius"],
    ["middle phalanges of the second to fifth fingers (four tendons "
     "through the carpal tunnel)"],
    ["flexes the metacarpophalangeal and proximal interphalangeal "
     "joints of the four fingers", "flexes at the wrist"],
    "median nerve", "C7, C8, T1", FA_SUPPLY,
    dict(o=SP, i=AF, a=AF, n=AF, r=SP, s=AF),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the forearm as a whole.")
add("flexor digitorum profundus", UL,
    "forearm, anterior compartment, deep",
    ["ulna and associated interosseous membrane"],
    ["distal phalanges of the four fingers"],
    ["flexes the distal interphalangeal joints of the fingers (the "
     "only muscle that can)", "flexes at the metacarpophalangeal "
     "joints and at the wrist"],
    "medial half: ulnar nerve; lateral half: anterior interosseous "
    "branch of the median nerve", "C8, T1", FA_SUPPLY,
    dict(o=AF, i=AF, a=AF, n=AF, r=SP, s=AF),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the forearm as a whole.")
add("flexor pollicis longus", UL, "forearm, anterior compartment, deep",
    ["anterior surface of the radius and surrounding interosseous "
     "membrane"],
    ["base of the distal phalanx of the thumb"],
    ["flexes the interphalangeal and metacarpophalangeal joints of "
     "the thumb"],
    "anterior interosseous branch of the median nerve", "C7, C8",
    FA_SUPPLY, dict(o=AF, i=AF, a=AF, n=AF, r=SP, s=AF),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the forearm as a whole.")
add("pronator quadratus", UL, "forearm, anterior compartment, deep",
    ["anterior surface of the distal ulna"],
    ["anterior surface of the distal radius"],
    ["pronates the forearm"],
    "anterior interosseous branch of the median nerve", "C7, C8",
    FA_SUPPLY, dict(o=AF, i=AF, a=AF, n=AF, r=SP, s=AF),
    note="Arterial supply is the consulted source's statement for the "
         "anterior compartment of the forearm as a whole.")
add("brachioradialis", UL, "forearm, posterior compartment, superficial",
    ["proximal supracondylar ridge of the humerus"],
    ["lateral surface of the distal end of the radius"],
    ["weak flexion of the forearm"],
    "radial nerve", "C5, C6, C7", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("extensor carpi radialis longus", UL,
    "forearm, posterior compartment, superficial",
    ["proximal supracondylar ridge of the humerus"],
    ["dorsal base of the second metacarpal"],
    ["extension and abduction of the wrist"],
    "radial nerve", "C6, C7", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("extensor carpi radialis brevis", UL,
    "forearm, posterior compartment, superficial",
    ["lateral epicondyle of the humerus"],
    ["dorsal base of the third metacarpal"],
    ["extension and abduction of the wrist"],
    "deep branch of the radial nerve", "C7, C8", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("extensor digitorum", UL, "forearm, posterior compartment, "
    "superficial",
    ["lateral epicondyle of the humerus"],
    ["extensor expansions on the dorsal aspect of the middle and "
     "distal phalanges of the second to fifth fingers"],
    ["extension of the proximal interphalangeal and "
     "metacarpophalangeal joints of the second to fifth fingers"],
    "posterior interosseous nerve", "C7, C8", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("extensor digiti minimi", UL,
    "forearm, posterior compartment, superficial",
    ["lateral epicondyle of the humerus"],
    ["extensor expansion on the dorsal aspect of the fifth finger"],
    ["extension of the little finger at the metacarpophalangeal and "
     "interphalangeal joints"],
    "posterior interosseous nerve", "C7, C8", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("extensor carpi ulnaris", UL,
    "forearm, posterior compartment, superficial",
    ["lateral epicondyle of the humerus", "posterior ulna"],
    ["base of the fifth metacarpal"],
    ["extension and adduction of the wrist"],
    "posterior interosseous nerve", "C7, C8", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("extensor indicis", UL, "forearm, posterior compartment, deep",
    ["dorsal surface of the distal ulna and interosseous membrane"],
    ["extensor expansion of the index finger"],
    ["extension of the index finger"],
    "posterior interosseous nerve", "C7, C8", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("supinator", UL, "forearm, posterior compartment, deep",
    ["lateral epicondyle of the humerus", "supinator crest of the ulna"],
    ["lateral surface of the radius"],
    ["supination of the forearm"],
    "deep branch of the radial nerve", "C7, C8", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("abductor pollicis longus", UL,
    "forearm, posterior compartment, deep",
    ["dorsal aspects of the proximal radius, ulna and interosseous "
     "membrane"],
    ["base of the first metacarpal"],
    ["abduction of the thumb at the carpometacarpal and "
     "metacarpophalangeal joints"],
    "posterior interosseous nerve", "C7, C8", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("extensor pollicis longus", UL, "forearm, posterior compartment, "
    "deep",
    ["dorsal aspect of the middle ulna and interosseous membrane"],
    ["distal phalanx of the thumb"],
    ["extension of the thumb at the carpometacarpal, "
     "metacarpophalangeal and interphalangeal joints"],
    "posterior interosseous nerve", "C7, C8", None,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP))
add("extensor pollicis brevis", UL, "forearm, posterior compartment, "
    "deep",
    ["dorsal aspect of the middle radius and interosseous membrane"],
    None,
    ["extension of the thumb at the carpometacarpal and "
     "metacarpophalangeal joints"],
    "posterior interosseous nerve", "C7, C8", None,
    dict(o=SP, a=SP, n=SP, r=SP), v=["insertion"],
    note="The consulted StatPearls text gives the insertion as the "
         "distal phalanx of the thumb, which conflicts with the "
         "standard proximal-phalanx attachment; the field is flagged "
         "for verification rather than entered from a conflicting "
         "source.")
HAND_SUPPLY = ["superficial and deep palmar arterial arches (formed "
               "by the radial and ulnar arteries)"]
add("opponens pollicis", UL, "hand, thenar",
    ["flexor retinaculum and tubercle of the trapezium"],
    ["lateral aspect of the first metacarpal"],
    ["opposition of the thumb"],
    "recurrent branch of the median nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Arterial supply is the consulted source's statement for the "
         "hand vasculature as a whole.")
add("abductor pollicis brevis", UL, "hand, thenar",
    ["flexor retinaculum and tubercle of the scaphoid"],
    ["lateral aspect of the proximal phalanx of the thumb"],
    ["abduction of the thumb at the metacarpophalangeal joint"],
    "recurrent branch of the median nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Arterial supply is the consulted source's statement for the "
         "hand vasculature as a whole.")
add("flexor pollicis brevis", UL, "hand, thenar",
    ["flexor retinaculum and tubercle of the trapezium"],
    ["lateral aspect of the proximal phalanx of the thumb"],
    ["flexion of the thumb at the metacarpophalangeal joint"],
    "recurrent branch of the median nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="The deep head is also supplied by the deep branch of the "
         "ulnar nerve (MyMedSchool hand-muscles table). Arterial "
         "supply is the consulted source's statement for the hand "
         "vasculature as a whole.")
add("adductor pollicis", UL, "hand, adductor compartment",
    ["second and third metacarpals and the capitate"],
    ["proximal phalanx and extensor expansion of the thumb"],
    ["adduction of the thumb"],
    "deep branch of the ulnar nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Arterial supply is the consulted source's statement for the "
         "hand vasculature as a whole.")
add("abductor digiti minimi of hand", UL, "hand, hypothenar",
    ["pisiform"],
    ["medial aspect of the proximal phalanx of the fifth finger"],
    ["abduction of the little finger at the metacarpophalangeal joint"],
    "deep branch of the ulnar nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Arterial supply is the consulted source's statement for the "
         "hand vasculature as a whole.")
add("flexor digiti minimi brevis of hand", UL, "hand, hypothenar",
    ["flexor retinaculum and hook of hamate"],
    ["medial aspect of the proximal phalanx of the fifth finger"],
    ["flexion of the little finger at the metacarpophalangeal joint"],
    "deep branch of the ulnar nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Arterial supply is the consulted source's statement for the "
         "hand vasculature as a whole.")
add("opponens digiti minimi of hand", UL, "hand, hypothenar",
    ["flexor retinaculum and hook of hamate"],
    ["medial aspect of the fifth metacarpal"],
    ["opposition of the little finger"],
    "deep branch of the ulnar nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Arterial supply is the consulted source's statement for the "
         "hand vasculature as a whole.")
add("set of dorsal interossei of hand", UL, "hand, interosseous (set)",
    ["adjacent metacarpals"],
    ["extensor expansions and proximal phalanges of the second, third "
     "and fourth fingers"],
    ["abduction of the second, third and fourth fingers away from "
     "the axial line"],
    "deep branch of the ulnar nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Values are the consulted source's statement for the dorsal "
         "interossei as a group. Arterial supply is the consulted "
         "source's statement for the hand vasculature as a whole.")
add("set of palmar interossei of hand", UL, "hand, interosseous (set)",
    ["palmar surfaces of the second, fourth and fifth metacarpals"],
    ["extensor expansions and proximal phalanges of the second, "
     "fourth and fifth fingers"],
    ["adduction of the second, fourth and fifth fingers towards the "
     "axial line"],
    "deep branch of the ulnar nerve", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Values are the consulted source's statement for the palmar "
         "interossei as a group. Arterial supply is the consulted "
         "source's statement for the hand vasculature as a whole.")
add("set of lumbricals of hand", UL, "hand, central compartment (set)",
    ["tendons of flexor digitorum profundus (first two unipennate, "
     "third and fourth bipennate)"],
    ["extensor expansions of the second to fifth fingers"],
    ["flexion of the metacarpophalangeal joints with extension of "
     "the interphalangeal joints"],
    "median nerve (lateral two lumbricals); deep branch of the ulnar "
    "nerve (medial two lumbricals)", "C8, T1", HAND_SUPPLY,
    dict(o=SP, i=SP, a=SP, n=SP, r=SP, s=SP),
    note="Values are the consulted source's statement for the "
         "lumbricals as a group. Arterial supply is the consulted "
         "source's statement for the hand vasculature as a whole.")


# ------------------------------------------------------- added sources
SOURCES.update({
    "TMA-GR": ("TeachMeAnatomy, 'Muscles of the Gluteal Region', "
               "teachmeanatomy.info/lower-limb/muscles/gluteal-region/ "
               "(updated 2026-04-09; consulted 2026-11-06)"),
    "GM-GLUT": ("Geeky Medics flashcard set, gluteal region (superior / "
                "inferior gluteal nerve root values), brainscape.com "
                "(consulted 2026-11-06 via search extract)"),
    "BS-LE": ("Lower-extremity muscle flashcard sets (piriformis, gemelli, "
              "quadratus femoris, pectineus and hamstring root values; "
              "soleus and fibularis attachments), brainscape.com "
              "(consulted 2026-11-06 via search extracts)"),
    "TMA-AT": ("TeachMeAnatomy, 'Muscles of the Anterior Thigh', "
               "teachmeanatomy.info/lower-limb/muscles/thigh/anterior-"
               "compartment/ (updated 2026-10-11; consulted 2026-11-06)"),
    "GM-AT": ("Geeky Medics, 'Muscles of the Anterior Thigh', "
              "geekymedics.com/muscles-of-the-anterior-thigh/ (consulted "
              "2026-11-06 via search extract)"),
    "TMA-MT": ("TeachMeAnatomy, 'Muscles of the Medial Thigh', "
               "teachmeanatomy.info/lower-limb/muscles/thigh/medial-"
               "compartment/ (updated 2025-11-06; consulted 2026-11-06)"),
    "SP-THIGH": ("StatPearls thigh-musculature articles (quadriceps "
                 "arterial supply statements), statpearls.com (consulted "
                 "2026-11-06 via search extracts)"),
    "SP-HAM": ("StatPearls, 'Anatomy, Bony Pelvis and Lower Limb: "
               "Posterior Thigh Muscles', NCBI Bookshelf NBK542215 "
               "(updated 2023-08-21) and 'Hamstring Muscle' point-of-care "
               "table, statpearls.com/point-of-care/36086 (consulted "
               "2026-11-06 via search extracts)"),
    "MS-ST": ("The Muscular System, 'Semitendinosus Muscle', "
              "themuscularsystem.com (consulted 2026-11-06 via search "
              "extract)"),
    "TMA-AL": ("TeachMeAnatomy, 'Muscles of the Anterior Leg', "
               "teachmeanatomy.info/lower-limb/muscles/leg/anterior-"
               "compartment/ (consulted 2026-11-06)"),
    "UOM-LEG": ("Leg-anatomy lecture tables (nerve and arterial supply "
                "by compartment of the leg), slideshare.net (consulted "
                "2026-11-06 via search extracts)"),
    "WIKI-PL": ("Wikipedia, 'Posterior compartment of the leg' (muscle "
                "table), en.wikipedia.org/wiki/Posterior_compartment_of_"
                "the_leg (consulted 2026-11-06 via search extract)"),
    "MS-PL": ("The Muscular System, 'Muscles of the Posterior "
              "Compartment of the Leg', themuscularsystem.com/legs/"
              "popliteus.html (consulted 2026-11-06 via search extract)"),
    "MS-DIA": ("The Muscular System, 'Diaphragm: Origin, Insertion, "
               "Openings, Function', themuscularsystem.com/torso/chest/"
               "diaphragm.html (consulted 2026-11-06)"),
    "WIKI-DIA": ("Wikipedia, 'Thoracic diaphragm', en.wikipedia.org/wiki/"
                 "Diaphragm_(anatomy) (consulted 2026-11-06 via search "
                 "extract)"),
    "SN-IC": ("Thoracic-wall study notes (intercostal muscles and "
              "transversus thoracis: attachments and innervation), "
              "study-notes-pdfs.s3.us-west-2.amazonaws.com/1031196.pdf "
              "(consulted 2026-11-06 via search extract)"),
    "SD-DIA": ("'Anatomy of the Diaphragm and Stomach' lecture deck "
               "(abdominal muscle table: external oblique row), "
               "slideshare.net (consulted 2026-11-06 via search extract)"),
    "KSU-NECK": ("Kentucky State University BIO 301 lecture notes, "
                 "'Muscles of the neck' (sternocleidomastoid and "
                 "scalenes), notes.edubirdie.com (consulted 2026-11-06 "
                 "via search extract)"),
    "MOORE-NECK": ("Moore, Clinically Oriented Anatomy, flashcard sets "
                   "(neck muscle attachments and scalene root values), "
                   "brainscape.com (consulted 2026-11-06 via search "
                   "extracts)"),
})

# ------------------------------------------- intrinsic back (TMA-IB page)
IB2 = "TMA-IB"
add("multifidus", "back", "intrinsic, deep (transversospinales)",
    ["sacrum", "posterior iliac spine",
     "common tendinous origin of the erector spinae",
     "mamillary processes of the lumbar vertebrae",
     "transverse processes of T1-T3 vertebrae",
     "articular processes of C4-C7 vertebrae"],
    ["spinous processes of the vertebrae 2-4 segments above the origin"],
    ["stabilises the vertebral column"],
    "posterior rami of the spinal nerves", None, None,
    dict(o=IB2, i=IB2, a=IB2, n=IB2),
    v=["innervation.root_values"],
    note="NO GEOMETRY: multifidus has no concept in the BodyParts3D/FMA "
         "tables (absence probe: 0 hits in all six tables) — a flagged "
         "data gap, recorded in MILESTONE-4.md. The clinical values are "
         "from the consulted TeachMeAnatomy intrinsic-back article.")

# ------------------------------------------------------ gluteal region
GR = "TMA-GR"; GLUT_SUP = ["superior gluteal artery",
                          "inferior gluteal artery"]
add("gluteus maximus", "lower limb", "gluteal region",
    ["posterior surface of the ilium, the sacrum and the coccyx"],
    ["iliotibial tract (iliotibial band)",
     "gluteal tuberosity of the femur"],
    ["extension of the thigh at the hip joint (primary extensor)",
     "lateral rotation of the thigh",
     "upper fibres abduct and lower fibres adduct the thigh"],
    "inferior gluteal nerve", "L5, S1, S2", ["inferior gluteal artery"],
    dict(o=GR, i=GR, a=GR, n=GR, r="GM-GLUT", s=GR))
add("gluteus medius", "lower limb", "gluteal region",
    ["gluteal surface of the ilium (between the posterior and anterior "
     "gluteal lines)"],
    ["lateral surface of the greater trochanter of the femur"],
    ["abduction of the thigh at the hip joint",
     "medial rotation of the thigh",
     "stabilises the pelvis during gait"],
    "superior gluteal nerve", "L4, L5, S1", ["superior gluteal artery"],
    dict(o=GR, i=GR, a=GR, n=GR, r="GM-GLUT", s=GR))
add("gluteus minimus", "lower limb", "gluteal region",
    ["gluteal surface of the ilium (between the anterior and inferior "
     "gluteal lines)"],
    ["anterior surface of the greater trochanter of the femur"],
    ["abduction of the thigh at the hip joint",
     "medial rotation of the thigh"],
    "superior gluteal nerve", "L4, L5, S1", ["superior gluteal artery"],
    dict(o=GR, i=GR, a=GR, n=GR, r="GM-GLUT", s=GR))
add("tensor fasciae latae", "lower limb", "gluteal region / lateral thigh",
    ["anterior superior iliac spine (ASIS)",
     "anterior part of the iliac crest"],
    ["iliotibial tract, which attaches to the lateral condyle of the "
     "tibia"],
    ["abduction of the thigh at the hip joint",
     "medial rotation of the thigh", "assists flexion of the thigh"],
    "superior gluteal nerve", "L4, L5, S1", ["superior gluteal artery"],
    dict(o=GR, i=GR, a=GR, n=GR, r="GM-GLUT", s=GR))
add("piriformis", "lower limb", "gluteal region (deep)",
    ["anterior surface of the sacrum"],
    ["medial side of the superior border of the greater trochanter"],
    ["lateral rotation of the extended thigh",
     "abduction of the flexed thigh"],
    "nerve to piriformis", "S1, S2", GLUT_SUP,
    dict(o=GR, i=GR, a=GR, n=GR, r="BS-LE", s=GR),
    note="Arterial supply is the consulted article's group statement "
         "for the gluteal region (superior and inferior gluteal "
         "arteries).")
add("obturator internus", "lower limb", "gluteal region (deep)",
    ["obturator membrane",
     "pelvic surfaces of the ilium and ischium around the obturator "
     "foramen"],
    ["medial surface of the greater trochanter of the femur"],
    ["lateral rotation of the extended thigh",
     "abduction of the flexed thigh"],
    "nerve to obturator internus", "L5, S1, S2", GLUT_SUP,
    dict(o=GR, i=GR, a=GR, n=GR, r="BS-LE", s=GR),
    note="Arterial supply is the consulted article's group statement "
         "for the gluteal region.")
add("gemellus superior", "lower limb", "gluteal region (deep)",
    ["ischial spine"],
    ["tendon of obturator internus, then the medial surface of the "
     "greater trochanter"],
    ["lateral rotation of the thigh (with obturator internus)"],
    "nerve to obturator internus", "L5, S1, S2", GLUT_SUP,
    dict(o=GR, i=GR, a=GR, n=GR, r="BS-LE", s=GR),
    note="Arterial supply is the consulted article's group statement "
         "for the gluteal region.")
add("gemellus inferior", "lower limb", "gluteal region (deep)",
    ["ischial tuberosity"],
    ["tendon of obturator internus, then the medial surface of the "
     "greater trochanter"],
    ["lateral rotation of the thigh (with obturator internus)"],
    "nerve to quadratus femoris", "L4, L5, S1", GLUT_SUP,
    dict(o=GR, i=GR, a=GR, n=GR, r="BS-LE", s=GR),
    note="Arterial supply is the consulted article's group statement "
         "for the gluteal region.")
add("quadratus femoris", "lower limb", "gluteal region (deep)",
    ["lateral border of the ischial tuberosity"],
    ["intertrochanteric crest of the femur (quadrate tubercle)"],
    ["lateral rotation of the thigh at the hip joint"],
    "nerve to quadratus femoris", "L4, L5, S1", GLUT_SUP,
    dict(o=GR, i=GR, a=GR, n=GR, r="BS-LE", s=GR),
    note="Arterial supply is the consulted article's group statement "
         "for the gluteal region.")

# ------------------------------------------------------ anterior thigh
AT = "TMA-AT"
QUAD_I = ["quadriceps tendon, then the patella; onward via the "
          "patellar ligament to the tibial tuberosity"]
add("psoas major", "lower limb", "anterior thigh (hip flexor group)",
    ["transverse processes and vertebral bodies of T12-L5, including "
     "the intervertebral discs"],
    ["lesser trochanter of the femur (common tendon with iliacus)"],
    ["flexion of the thigh at the hip joint",
     "lateral flexion of the vertebral column"],
    "anterior rami of spinal nerves L1-L3", "L1, L2, L3", None,
    dict(o="GM-AT", i=AT, a=AT, n=AT, r=AT))
add("iliacus", "lower limb", "anterior thigh (hip flexor group)",
    ["iliac fossa of the pelvis"],
    ["lesser trochanter of the femur (common tendon with psoas major)"],
    ["flexion of the thigh at the hip joint"],
    "femoral nerve", "L2, L3", None,
    dict(o=AT, i=AT, a=AT, n=AT, r="GM-AT"))
add("sartorius", "lower limb", "anterior compartment of thigh",
    ["anterior superior iliac spine (ASIS)"],
    ["superior part of the medial surface of the tibia (pes anserinus)"],
    ["flexion, abduction and lateral rotation of the thigh",
     "flexion of the leg at the knee joint"],
    "femoral nerve", "L2, L3", None,
    dict(o=AT, i=AT, a=AT, n=AT, r="GM-AT"))
add("rectus femoris", "lower limb", "anterior thigh (quadriceps)",
    ["anterior inferior iliac spine (AIIS)",
     "ilium just superior to the acetabulum"],
    QUAD_I,
    ["extension of the leg at the knee joint",
     "flexion of the thigh at the hip joint"],
    "femoral nerve", "L2, L3, L4", ["lateral femoral circumflex artery"],
    dict(o=AT, i=AT, a=AT, n=AT, r=AT, s="SP-THIGH"))
add("vastus lateralis", "lower limb", "anterior thigh (quadriceps)",
    ["greater trochanter of the femur",
     "lateral lip of the linea aspera"],
    ["quadriceps tendon, then the lateral margin of the patella; "
     "onward via the patellar ligament to the tibial tuberosity"],
    ["extension of the leg at the knee joint",
     "stabilises the patella laterally"],
    "femoral nerve", "L2, L3, L4", ["lateral femoral circumflex artery"],
    dict(o=AT, i=AT, a=AT, n=AT, r=AT, s="SP-THIGH"))
add("vastus medialis", "lower limb", "anterior thigh (quadriceps)",
    ["intertrochanteric line of the femur",
     "medial lip of the linea aspera"],
    ["quadriceps tendon, then the medial margin of the patella; "
     "onward via the patellar ligament to the tibial tuberosity"],
    ["extension of the leg at the knee joint",
     "stabilises the patella medially"],
    "femoral nerve", "L2, L3, L4",
    ["femoral artery", "profunda femoris artery",
     "superior medial genicular artery"],
    dict(o=AT, i=AT, a=AT, n=AT, r=AT, s="SP-THIGH"),
    note="Supply values are StatPearls' specific statement for vastus "
         "medialis (the lateral femoral circumflex artery supplies the "
         "other quadriceps components).")
add("vastus intermedius", "lower limb", "anterior thigh (quadriceps)",
    ["anterior and lateral surfaces of the shaft of the femur"],
    QUAD_I,
    ["extension of the leg at the knee joint"],
    "femoral nerve", "L2, L3, L4", ["lateral femoral circumflex artery"],
    dict(o=AT, i=AT, a=AT, n=AT, r=AT, s="SP-THIGH"))
add("pectineus", "lower limb", "anterior / medial thigh",
    ["pectineal line of the pubis"],
    ["pectineal line of the femur (just inferior to the lesser "
     "trochanter)"],
    ["adduction of the thigh at the hip joint",
     "flexion of the thigh at the hip joint"],
    "femoral nerve (may also receive a branch from the obturator "
    "nerve)", "L2, L3", None,
    dict(o=AT, i=AT, a=AT, n=AT, r="BS-LE"))

# -------------------------------------------------------- medial thigh
MT = "TMA-MT"
add("gracilis", "lower limb", "medial compartment of thigh",
    ["body of the pubis", "inferior pubic ramus"],
    ["superior part of the medial surface of the tibia (pes anserinus)"],
    ["adduction of the thigh at the hip joint",
     "flexion of the leg at the knee joint"],
    "obturator nerve", "L2, L3, L4", ["obturator artery"],
    dict(o=MT, i=MT, a=MT, n=MT, r=MT, s=MT))
add("adductor longus", "lower limb", "medial compartment of thigh",
    ["body of the pubis"],
    ["middle third of the linea aspera of the femur"],
    ["adduction of the thigh at the hip joint",
     "assists flexion of the thigh"],
    "obturator nerve", "L2, L3, L4", ["obturator artery"],
    dict(o=MT, i=MT, a=MT, n=MT, r=MT, s=MT))
add("adductor brevis", "lower limb", "medial compartment of thigh",
    ["body of the pubis", "inferior pubic ramus"],
    ["proximal part of the linea aspera of the femur"],
    ["adduction of the thigh at the hip joint"],
    "obturator nerve", "L2, L3, L4", ["obturator artery"],
    dict(o=MT, i=MT, a=MT, n=MT, r=MT, s=MT))
add("adductor magnus", "lower limb", "medial / posterior thigh",
    ["adductor part: inferior rami of the pubis and ischium",
     "hamstring part: ischial tuberosity"],
    ["adductor part: linea aspera of the femur",
     "hamstring part: adductor tubercle and medial supracondylar line "
     "of the femur"],
    ["adduction of the thigh at the hip joint",
     "flexion of the thigh (adductor part)",
     "extension of the thigh (hamstring part)"],
    "obturator nerve (adductor part); tibial component of the sciatic "
    "nerve (hamstring part)",
    "L2, L3, L4 (obturator part); L4-S3 (tibial component, as stated "
    "by the source)", ["obturator artery"],
    dict(o=MT, i=MT, a=MT, n=MT, r=MT, s=MT))
add("obturator externus", "lower limb", "medial compartment of thigh",
    ["outer surface of the obturator membrane and the bony margins "
     "of the obturator foramen"],
    ["trochanteric fossa of the femur"],
    ["lateral rotation of the thigh at the hip joint"],
    "obturator nerve", "L2, L3, L4", ["obturator artery"],
    dict(o=MT, i=MT, a=MT, n=MT, r=MT, s=MT))

# ----------------------------------------------------- posterior thigh
SH = "SP-HAM"
add("biceps femoris", "lower limb", "posterior compartment of thigh",
    ["long head: ischial tuberosity (conjoint tendon with "
     "semitendinosus)",
     "short head: lateral lip of the linea aspera of the femur"],
    ["lateral side of the head of the fibula (also the lateral "
     "collateral ligament and lateral tibial condyle)"],
    ["flexion of the leg at the knee joint",
     "extension of the thigh at the hip joint (long head)",
     "lateral rotation of the flexed leg"],
    "tibial nerve (long head); common fibular nerve (short head)",
    "L5, S1, S2",
    ["perforating branches of the profunda femoris artery",
     "inferior gluteal artery (long head)",
     "superior muscular branches of the popliteal artery (long head)"],
    dict(o=SH, i=SH, a=SH, n=SH, r="BS-LE", s=SH))
add("semitendinosus", "lower limb", "posterior compartment of thigh",
    ["ischial tuberosity (conjoint tendon with the long head of "
     "biceps femoris)"],
    ["superior part of the medial surface of the tibia (pes anserinus)"],
    ["extension of the thigh at the hip joint",
     "flexion of the leg at the knee joint",
     "medial rotation of the flexed leg"],
    "tibial nerve", "L5, S1, S2",
    ["perforating branches of the profunda femoris (deep femoral) "
     "artery"],
    dict(o="MS-ST", i="MS-ST", a="MS-ST", n="MS-ST", r="BS-LE",
         s="MS-ST"))
add("semimembranosus", "lower limb", "posterior compartment of thigh",
    ["superolateral impression of the ischial tuberosity"],
    ["posterior part of the medial condyle of the tibia"],
    ["extension of the thigh at the hip joint",
     "flexion of the leg at the knee joint",
     "medial rotation of the flexed leg"],
    "tibial nerve", "L5, S1, S2", None,
    dict(o=SH, i=SH, a=SH, n=SH, r="BS-LE"))

# --------------------------------------------------------- leg: anterior
AL = "TMA-AL"; UOM = "UOM-LEG"
ANT_ROOTS = "L4-S2 (nerve-level span stated by the source for the " \
            "anterior compartment)"
ANT_SUP = ["anterior tibial artery"]
ANT_NOTE = ("Arterial supply is the compartment statement of the "
            "consulted leg-lecture tables (anterior compartment: "
            "anterior tibial artery).")
add("tibialis anterior", "lower limb", "anterior compartment of leg",
    ["lateral surface of the tibia", "interosseous membrane"],
    ["medial cuneiform bone", "base of the first metatarsal bone"],
    ["dorsiflexion of the foot at the ankle joint",
     "inversion of the foot"],
    "deep fibular (peroneal) nerve", ANT_ROOTS, ANT_SUP,
    dict(o=AL, i=AL, a=AL, n=AL, r=AL, s=UOM), note=ANT_NOTE)
add("extensor hallucis longus", "lower limb", "anterior compartment of leg",
    ["medial surface of the fibula", "interosseous membrane"],
    ["base of the distal phalanx of the great toe"],
    ["extension of the great toe", "dorsiflexion of the foot"],
    "deep fibular (peroneal) nerve", ANT_ROOTS, ANT_SUP,
    dict(o=AL, i=AL, a=AL, n=AL, r=AL, s=UOM), note=ANT_NOTE)
add("extensor digitorum longus", "lower limb",
    "anterior compartment of leg",
    ["lateral condyle of the tibia", "medial surface of the fibula"],
    ["four tendons to the dorsal expansions and the middle and distal "
     "phalanges of the lateral four toes"],
    ["extension of the lateral four toes", "dorsiflexion of the foot"],
    "deep fibular (peroneal) nerve", ANT_ROOTS, ANT_SUP,
    dict(o=AL, i=AL, a=AL, n=AL, r=AL, s=UOM), note=ANT_NOTE)
add("fibularis tertius", "lower limb", "anterior compartment of leg",
    ["medial surface of the fibula (arising with extensor digitorum "
     "longus)"],
    ["dorsal surface of the base of the fifth metatarsal bone"],
    ["eversion of the foot", "dorsiflexion of the foot (weak)"],
    "deep fibular (peroneal) nerve", ANT_ROOTS, ANT_SUP,
    dict(o=AL, i=AL, a=AL, n=AL, r=AL, s=UOM),
    note="Variant: not present in all individuals (source statement). "
         + ANT_NOTE)

# ---------------------------------------------------------- leg: lateral
LAT_SUP = ["fibular (peroneal) artery"]
LAT_NOTE = ("Arterial supply is the compartment statement of the "
            "consulted leg-lecture tables (lateral compartment: "
            "fibular/peroneal artery). Root values for the superficial "
            "fibular nerve differ between consulted flashcard sources "
            "and are verify-flagged rather than entered.")
add("fibularis longus", "lower limb", "lateral compartment of leg",
    ["head of the fibula", "upper lateral surface of the fibula"],
    ["base of the first metatarsal bone",
     "medial cuneiform bone (tendon crosses the sole of the foot)"],
    ["eversion of the foot", "plantarflexion of the foot (weak)",
     "supports the transverse arch of the foot"],
    "superficial fibular (peroneal) nerve", None, LAT_SUP,
    dict(o="BS-LE", i="BS-LE", a=UOM, n="BS-LE", s=UOM),
    v=["innervation.root_values"], note=LAT_NOTE)
add("fibularis brevis", "lower limb", "lateral compartment of leg",
    ["lower lateral surface of the fibula"],
    ["tuberosity of the fifth metatarsal bone"],
    ["eversion of the foot", "plantarflexion of the foot (weak)"],
    "superficial fibular (peroneal) nerve", None, LAT_SUP,
    dict(o="BS-LE", i="BS-LE", a=UOM, n="BS-LE", s=UOM),
    v=["innervation.root_values"], note=LAT_NOTE)

# -------------------------------------------------------- leg: posterior
WP = "WIKI-PL"
DEEP_SUP = ["posterior tibial artery"]
DEEP_NOTE = ("Arterial supply is the compartment statement of the "
             "consulted leg-lecture tables (deep posterior "
             "compartment: posterior tibial artery).")
add("gastrocnemius", "lower limb", "posterior compartment of leg "
    "(superficial)",
    ["lateral head: lateral aspect of the lateral condyle of the femur",
     "medial head: popliteal surface of the femur, superior to the "
     "medial condyle"],
    ["posterior surface of the calcaneus via the calcaneal (Achilles) "
     "tendon"],
    ["plantarflexion of the foot at the ankle joint (especially with "
     "the knee extended)", "flexion of the leg at the knee joint"],
    "tibial nerve", "S1, S2", None,
    dict(o=WP, i=WP, a=WP, n=WP, r=WP))
add("soleus", "lower limb", "posterior compartment of leg (superficial)",
    ["soleal line and posterior surface of the tibia",
     "posterior surface of the head and upper shaft of the fibula"],
    ["posterior surface of the calcaneus via the calcaneal (Achilles) "
     "tendon"],
    ["plantarflexion of the foot at the ankle joint"],
    "tibial nerve", "S1, S2", None,
    dict(o="BS-LE", i=WP, a=WP, n=WP, r="BS-LE"))
add("plantaris", "lower limb", "posterior compartment of leg "
    "(superficial)",
    ["inferior end of the lateral supracondylar line of the femur",
     "oblique popliteal ligament"],
    ["calcaneus via the calcaneal (Achilles) tendon"],
    ["weakly assists gastrocnemius in plantarflexion of the foot"],
    "tibial nerve", None, None,
    dict(o=WP, i=WP, a=WP, n=WP),
    note="Nerve entered from the consulted article's compartment "
         "statement (the posterior compartment of the leg is supplied "
         "by the tibial nerve).")
add("popliteus", "lower limb", "posterior compartment of leg (deep)",
    ["lateral surface of the lateral condyle of the femur",
     "lateral meniscus of the knee joint"],
    ["posterior surface of the tibia, superior to the soleal line"],
    ["unlocks the knee joint by laterally rotating the femur on the "
     "fixed tibia", "weakly flexes the leg at the knee joint"],
    "tibial nerve", "L4, L5, S1", None,
    dict(o=WP, i=WP, a=WP, n=WP, r=WP))
add("tibialis posterior", "lower limb", "posterior compartment of leg "
    "(deep)",
    ["interosseous membrane",
     "posterior surface of the tibia, inferior to the soleal line",
     "posterior surface of the fibula"],
    ["tuberosity of the navicular bone", "cuneiform and cuboid bones",
     "bases of the second to fourth metatarsal bones"],
    ["plantarflexion of the foot at the ankle joint",
     "inversion of the foot",
     "supports the medial longitudinal arch of the foot"],
    "tibial nerve", "L4, L5", DEEP_SUP,
    dict(o=WP, i="MS-PL", a=WP, n=WP, r=WP, s=UOM), note=DEEP_NOTE)
add("flexor digitorum longus", "lower limb",
    "posterior compartment of leg (deep)",
    ["posterior surface of the tibia, inferior to the soleal line"],
    ["bases of the distal phalanges of the lateral four toes"],
    ["flexion of the lateral four toes",
     "assists plantarflexion and supports the longitudinal arches"],
    "tibial nerve", None, DEEP_SUP,
    dict(o=WP, i=WP, a=WP, n=WP, s=UOM),
    v=["innervation.root_values"],
    note="Root values conflict between consulted sources (S1, S2 in "
         "the Wikipedia table vs S2, S3 in a Gray's Atlas flashcard "
         "table) and are verify-flagged. " + DEEP_NOTE)
add("flexor hallucis longus", "lower limb",
    "posterior compartment of leg (deep)",
    ["inferior two-thirds of the posterior surface of the fibula",
     "interosseous membrane"],
    ["base of the distal phalanx of the great toe"],
    ["flexion of the great toe at all joints",
     "weak plantarflexion of the foot",
     "supports the medial longitudinal arch of the foot"],
    "tibial nerve", None, DEEP_SUP,
    dict(o=WP, i=WP, a=WP, n=WP, s=UOM),
    v=["innervation.root_values"],
    note="Root values conflict between consulted sources (S1, S2 in "
         "the Wikipedia table vs S2, S3 in a Gray's Atlas flashcard "
         "table) and are verify-flagged. " + DEEP_NOTE)

# --------------------------------------------------------------- thorax
MD = "MS-DIA"
add("diaphragm", "thorax", "respiratory",
    ["sternal part: posterior surface of the xiphoid process",
     "costal part: inner surfaces of the lower six ribs and their "
     "costal cartilages",
     "lumbar part: bodies of vertebrae L1-L3 and the medial and "
     "lateral arcuate ligaments (via the crura)"],
    ["central tendon of the diaphragm"],
    ["primary muscle of inspiration: contraction descends the dome, "
     "increasing the vertical diameter of the thoracic cavity"],
    "phrenic nerve", "C3, C4, C5",
    ["pericardiacophrenic artery", "musculophrenic artery",
     "inferior phrenic arteries"],
    dict(o=MD, i=MD, a=MD, n="WIKI-DIA", r="WIKI-DIA", s="WIKI-DIA"))
IC_NOTE = ("FMA/BP3D models the intercostals as single classes "
           "spanning all intercostal spaces; each space is supplied "
           "by its own intercostal nerve (T1-T11), so no single root "
           "value applies to the class record.")
add("external intercostal", "thorax", "intercostal spaces",
    ["lower border of the rib above (each intercostal space)"],
    ["upper border of the rib below"],
    ["elevation of the ribs during inspiration"],
    "intercostal nerves", None, None,
    dict(o="SN-IC", i="SN-IC", a=MD, n="SN-IC"),
    v=["innervation.root_values"], note=IC_NOTE)
add("internal intercostal", "thorax", "intercostal spaces",
    ["ridge on the inner surface (costal groove) of the rib above"],
    ["upper border of the rib below"],
    ["depression of the ribs during forced expiration"],
    "intercostal nerves", None, None,
    dict(o="SN-IC", i="SN-IC", a=MD, n="SN-IC"),
    v=["innervation.root_values"], note=IC_NOTE)
add("innermost intercostal", "thorax", "intercostal spaces",
    None, None,
    ["depression of the ribs during expiration (acting with the "
     "internal intercostals)"],
    None, None, None,
    dict(a=MD), v=["innervation"],
    note="Attachments and innervation were not separately stated in "
         "the consulted sources (the layer mirrors the internal "
         "intercostals); flagged rather than entered. " + IC_NOTE)
add("transversus thoracis", "thorax", "anterior thoracic wall (deep)",
    ["posterior surface of the lower sternum and xiphoid process"],
    ["inner surfaces and lower borders of the costal cartilages of "
     "ribs 2-6"],
    None, None, None, None,
    dict(o="SN-IC", i="SN-IC"))

# -------------------------------------------------------------- abdomen
add("external oblique", "abdomen", "anterolateral abdominal wall",
    ["outer surfaces of the lower eight ribs (ribs V-XII), as "
     "muscular slips"],
    ["lateral lip of the iliac crest",
     "aponeurosis ending in the linea alba"],
    None, None, None, None,
    dict(o="SD-DIA", i="SD-DIA"), v=["innervation"],
    note="The consulted extract's table row gives attachments only "
         "(nerve column truncated); actions and innervation are "
         "verify-flagged rather than entered.")

# ----------------------------------------------------------------- neck
KN = "KSU-NECK"; MN = "MOORE-NECK"
add("sternocleidomastoid", "neck", "superficial",
    ["sternal head: anterior surface of the manubrium sterni",
     "clavicular head: superior surface of the medial third of the "
     "clavicle"],
    ["lateral surface of the mastoid process of the temporal bone",
     "lateral half of the superior nuchal line"],
    ["unilateral: lateral flexion of the neck to the same side and "
     "rotation of the head to the opposite side",
     "bilateral: flexion of the neck (with extension at the "
     "atlanto-occipital joints)"],
    "spinal accessory nerve (CN XI)", "C2, C3 (proprioceptive)", None,
    dict(o=KN, i=MN, a=MN, n=KN, r=KN))
add("scalenus anterior", "neck", "lateral vertebral group",
    ["anterior tubercles of the transverse processes of C3-C6"],
    ["scalene tubercle on the inner border of the first rib"],
    ["elevation of the first rib during forced inspiration",
     "lateral flexion of the neck"],
    "anterior rami of cervical spinal nerves", "C4, C5, C6", None,
    dict(o=KN, i=KN, a=KN, n=MN, r=MN))
add("scalenus medius", "neck", "lateral vertebral group",
    ["posterior tubercles of the transverse processes of C2-C7"],
    ["superior surface of the first rib, posterior to the groove for "
     "the subclavian artery"],
    ["elevation of the first rib during forced inspiration",
     "lateral flexion of the neck"],
    "anterior rami of cervical spinal nerves", None, None,
    dict(o=KN, i=MN, a=KN, n=KN), v=["innervation.root_values"],
    note="Root values are not stated consistently across the "
         "consulted sources and are verify-flagged.")
add("scalenus posterior", "neck", "lateral vertebral group",
    ["posterior tubercles of the transverse processes of C4-C6"],
    ["outer surface of the second rib"],
    ["elevation of the second rib during forced inspiration",
     "lateral flexion of the neck"],
    "anterior rami of cervical spinal nerves", "C7, C8", None,
    dict(o=KN, i=MN, a=KN, n=MN, r=MN))

# ============================ build / emit ============================
FIELD_OF = {"o": "origin", "i": "insertion", "a": "actions",
            "n": "innervation.nerve", "r": "innervation.root_values",
            "s": "arterial_supply"}
VALUE_OF = {"origin": "o", "insertion": "i", "actions": "a",
            "innervation.nerve": "n", "innervation.root_values": "r",
            "arterial_supply": "s"}

# Entry keys whose literature concept spans several inventory records
# (exact inventory names; no fuzzy matching).
INV_KEYS_OVERRIDE = {
    "iliocostalis": ["iliocostalis cervicis", "iliocostalis lumborum",
                     "iliocostalis thoracis"],
    "longissimus": ["longissimus capitis", "longissimus cervicis",
                    "longissimus thoracis"],
    "semispinalis": ["semispinalis capitis", "semispinalis cervicis",
                     "semispinalis thoracis"],
    "rotatores": ["cervical rotator", "lumbar rotator",
                  "thoracic rotator"],
    "interspinales": ["interspinalis thoracis", "interspinales cervicis",
                      "interspinales lumborum"],
    "intertransversarii": ["anterior cervical intertransversarii",
                           "posterior cervical intertransversarii",
                           "lateral lumbar intertransversarius",
                           "medial lumbar intertransversarius"],
    "levatores costarum": ["levatores costarum breves",
                           "levatores costarum longi"],
    "abductor digiti minimi of hand": ["abductor digiti minimi of left hand",
                                       "abductor digiti minimi of right hand"],
    "flexor digiti minimi brevis of hand": [
        "flexor digiti minimi brevis of left hand",
        "flexor digiti minimi brevis of right hand"],
    "opponens digiti minimi of hand": [
        "opponens digiti minimi of left hand",
        "opponens digiti minimi of right hand"],
    "set of dorsal interossei of hand": ["dorsal interossei of left hand",
                                         "dorsal interossei of right hand"],
    "set of palmar interossei of hand": ["palmar interossei of left hand",
                                         "palmar interossei of right hand"],
    "set of lumbricals of hand": ["lumbricals of left hand",
                                  "lumbricals of right hand"],
}

def norm(name):
    s = name.lower()
    for p in ("set of right ", "set of left ", "set of ", "right ",
              "left "):
        if s.startswith(p):
            s = s[len(p):]
    if s.endswith(" muscle"):
        s = s[:-7]
    return s

def slug(key):
    s = key.lower().replace("(", "").replace(")", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def side_of(record_name):
    n = record_name.lower()
    if n.startswith("left ") or " of left " in n or \
            n.startswith("set of left "):
        return "left"
    if n.startswith("right ") or " of right " in n or \
            n.startswith("set of right "):
        return "right"
    return None

def tier_of(verify_fields):
    core = {"origin", "insertion", "actions", "innervation",
            "innervation.nerve"}
    soft = {"arterial_supply", "innervation.root_values"}
    f = set(verify_fields) - {"ta_name", "geometry"}
    if not f:
        return "A"
    if f <= soft:
        return "B"
    return "C"

def main():
    inv = json.load(open(INV_PATH))
    geo_path = os.path.join(ROOT, "data", "muscular",
                            "muscle-geometry.json")
    geo = json.load(open(geo_path))
    geo_by_rid = {g["record_id"]: g for g in geo["records"]}
    inv_by_key = {}
    for r in inv["records"]:
        inv_by_key.setdefault(norm(r["name"]), []).append(r)

    records = []
    unresolved = []
    linked_rids = set()
    for e in E:
        keys = INV_KEYS_OVERRIDE.get(e["key"], [e["key"]])
        matched = []
        for k in keys:
            matched.extend(inv_by_key.get(norm(k), []))
        sides = sorted({s for s in (side_of(r["name"]) for r in matched)
                        if s})
        if matched:
            for r in matched:
                linked_rids.add(r["record_id"])
            geometry = {
                "inventory_record_ids": [r["record_id"] for r in matched],
                "inventory_names": [r["name"] for r in matched],
                "sides_covered": sides if sides else ["un-sided"],
                "mesh_files_total": sum(
                    len(geo_by_rid[r["record_id"]]["isa_meshes"])
                    for r in matched),
                "geometry_file": "data/muscular/muscle-geometry.json",
            }
        else:
            geometry = None
            unresolved.append(e["key"])

        verify = []
        vfields = []
        for f in e["v"]:
            vfields.append(f)
            verify.append(f + ": flagged for verification — not stated "
                              "in the consulted sources (see note)")
        values = {"origin": e["o"], "insertion": e["i"],
                  "actions": e["a"], "innervation.nerve": e["n"],
                  "innervation.root_values": e["r"],
                  "arterial_supply": e["s"]}
        for field, val in values.items():
            if val is None and field not in vfields and \
                    not (field == "innervation.nerve" and
                         "innervation" in vfields) and \
                    not (field == "innervation.root_values" and
                         "innervation" in vfields):
                vfields.append(field)
                verify.append(field + ": not stated in the consulted "
                                      "sources")
        if "innervation" in vfields:
            # a bare 'innervation' flag covers nerve + root values
            verify = [v for v in verify
                      if not v.startswith("innervation.nerve: not stated")
                      and not v.startswith(
                          "innervation.root_values: not stated")]
            if not any(v.startswith("innervation:") for v in verify):
                verify.append("innervation: flagged for verification — "
                              "not stated in the consulted sources")
        verify.append("ta_name: not present in the consulted sources "
                      "or in the BodyParts3D/FMA tables")
        if geometry is None:
            vfields.append("geometry")
            verify.append("geometry: no inventory record resolved for "
                          "this concept (flagged gap — see "
                          "MILESTONE-4.md)")

        rec = {
            "record_id": "muscle." + slug(e["key"]),
            "kind": "muscle",
            "name": e["name"] or e["key"],
            "ta_name": None,
            "region": e["region"],
            "subregion": e["sub"],
            "origin": e["o"],
            "insertion": e["i"],
            "actions": e["a"],
            "innervation": {"nerve": e["n"], "root_values": e["r"]},
            "arterial_supply": e["s"],
            "geometry": geometry,
            "sources": {FIELD_OF[k]: v for k, v in e["src"].items()},
            "verify": verify,
            "note": e["note"],
            "sourcing_tier": tier_of(vfields),
        }
        records.append(rec)

    tiers = {"A": 0, "B": 0, "C": 0}
    by_region = {}
    for rec in records:
        tiers[rec["sourcing_tier"]] += 1
        d = by_region.setdefault(rec["region"], {"A": 0, "B": 0, "C": 0})
        d[rec["sourcing_tier"]] += 1

    out = {
        "meta": {
            "module": "muscular",
            "file": "data/muscular/muscles.json",
            "generated": "2026-11-06",
            "generator": "tools/build_muscle_records.py",
            "field_sourcing_rule": (
                "Every non-null clinical field value was entered only "
                "from a source consulted in the building session and "
                "is cited per field in the record's 'sources' map. "
                "Fields not available from a consulted source are "
                "null and carry an explicit entry in the record's "
                "'verify' list. No field was filled from unaided "
                "recall."),
            "ta_name_status": (
                "ta_name is null on every record in this tranche and "
                "verify-flagged: Terminologia Anatomica names were "
                "not present in the consulted sources and are not "
                "carried by the BodyParts3D/FMA tables used for the "
                "inventory."),
            "sourcing_tiers": (
                "A = every clinical field sourced; B = sourced except "
                "arterial supply and/or innervation root values; "
                "C = at least one core field (origin, insertion, "
                "actions, innervation) verify-flagged."),
            "geometry_linkage": (
                "geometry.inventory_record_ids reference records in "
                "data/muscular/muscle-inventory.json; mesh detail "
                "lives in data/muscular/muscle-geometry.json."),
            "counts": {
                "clinical_records": len(records),
                "tier_A_fully_sourced": tiers["A"],
                "tier_B_sourced_except_supply_or_roots": tiers["B"],
                "tier_C_partial": tiers["C"],
                "by_region": by_region,
                "inventory_records_total": len(inv["records"]),
                "inventory_records_linked": len(linked_rids),
                "unresolved_geometry_keys": unresolved,
            },
            "sources_bibliography": SOURCES,
        },
        "records": records,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=1)
    print(f"entries={len(E)} records={len(records)}")
    print("tiers:", tiers)
    print("by_region:", json.dumps(by_region))
    print("inventory linked:", len(linked_rids), "of",
          len(inv["records"]))
    print("unresolved geometry keys:", unresolved)

if __name__ == "__main__":
    main()
