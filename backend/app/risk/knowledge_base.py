"""Anatomical knowledge base for explainable risk findings.

Maps biomechanical measurements to the muscles and structures involved, using
standard anatomical (scientific) terminology. This is the layer that turns a
number like "trunk lean 28°" into "lumbar flexion under compressive load,
loading the erector spinae with underactive transversus abdominis".

Terminology notes
-----------------
- Muscles are named with Latin/English anatomical names
  (e.g. "gluteus maximus", "vastus medialis obliquus").
- Structures use clinical names (e.g. "patellofemoral joint",
  "lumbar intervertebral discs (L4–L5)").
- Descriptions are educational biomechanics, not a medical diagnosis.
"""

from typing import Dict, List

# Joint -> muscles acting on / stabilising that joint
JOINT_MUSCLES: Dict[str, Dict[str, List[str]]] = {
    "knee": {
        "primary": [
            "quadriceps femoris (rectus femoris, vastus lateralis, vastus medialis)",
            "hamstrings (biceps femoris, semitendinosus, semimembranosus)",
            "gastrocnemius",
        ],
        "stabilizers": [
            "gluteus medius",
            "vastus medialis obliquus (VMO)",
            "popliteus",
            "tibialis anterior",
        ],
    },
    "hip": {
        "primary": [
            "gluteus maximus",
            "iliopsoas",
            "rectus femoris",
            "hamstrings",
        ],
        "stabilizers": [
            "gluteus medius",
            "gluteus minimus",
            "tensor fasciae latae",
            "deep hip external rotators (piriformis, obturator group)",
        ],
    },
    "ankle": {
        "primary": ["gastrocnemius", "soleus", "tibialis anterior"],
        "stabilizers": [
            "peroneus longus/brevis",
            "tibialis posterior",
            "extensor digitorum longus",
        ],
    },
    "trunk": {
        "primary": [
            "rectus abdominis",
            "erector spinae (iliocostalis, longissimus, spinalis)",
            "external/internal obliques",
        ],
        "stabilizers": [
            "transversus abdominis",
            "multifidus",
            "quadratus lumborum",
            "latissimus dorsi",
        ],
    },
    "lower_back": {
        "primary": [
            "erector spinae",
            "iliopsoas",
            "latissimus dorsi",
        ],
        "stabilizers": [
            "transversus abdominis",
            "multifidus",
            "quadratus lumborum",
            "gluteus maximus",
        ],
    },
    "shoulder": {
        "primary": [
            "deltoid (anterior, lateral, posterior)",
            "pectoralis major",
            "latissimus dorsi",
        ],
        "stabilizers": [
            "rotator cuff (supraspinatus, infraspinatus, subscapularis, teres minor)",
            "serratus anterior",
            "trapezius",
        ],
    },
    "elbow": {
        "primary": ["biceps brachii", "triceps brachii", "brachialis"],
        "stabilizers": ["brachioradialis", "pronator teres"],
    },
}

# Risk tag -> clinical/scientific description of the problem
RISK_KNOWLEDGE: Dict[str, Dict] = {
    "lumbar_strain": {
        "scientific_term": "increased lumbar flexion moment under axial/compressive load",
        "structures_at_risk": [
            "lumbar intervertebral discs (L4–L5, L5–S1)",
            "posterior annulus fibrosus",
            "thoracolumbar fascia",
        ],
        "muscles_overactive": ["erector spinae", "iliopsoas"],
        "muscles_underactive": [
            "transversus abdominis",
            "multifidus",
            "gluteus maximus",
        ],
        "mechanism": (
            "Forward trunk displacement moves the load vector anterior to the "
            "spine, raising the flexion moment and compressive/shear load on "
            "the lumbar discs while the hip extensors contribute less."
        ),
    },
    "knee_overload_asymmetry": {
        "scientific_term": "asymmetric knee joint loading / limb-dominance compensation",
        "structures_at_risk": [
            "patellofemoral joint",
            "tibiofemoral joint (menisci)",
            "anterior cruciate ligament (via frontal-plane control deficits)",
        ],
        "muscles_overactive": ["quadriceps femoris (dominant limb)"],
        "muscles_underactive": [
            "gluteus medius",
            "vastus medialis obliquus (VMO)",
        ],
        "mechanism": (
            "Repeated side-to-side differences in knee flexion shift load to one "
            "limb, concentrating patellofemoral and tibiofemoral stress and "
            "pointing to reduced frontal-plane hip control."
        ),
    },
    "limited_rom_knee": {
        "scientific_term": "restricted knee flexion range of motion",
        "structures_at_risk": [
            "patellofemoral joint (increased contact stress at low flexion limits)",
            "ankle talocrural joint (compensatory dorsiflexion demand)",
        ],
        "muscles_overactive": ["gastrocnemius", "hamstrings"],
        "muscles_underactive": ["gluteus maximus", "quadriceps femoris"],
        "mechanism": (
            "Limited knee flexion may reflect restricted ankle dorsiflexion or "
            "hip mobility; the missing range is compensated for elsewhere "
            "(often lumbar flexion), moving load to structures not designed "
            "to absorb it."
        ),
    },
    "movement_control_deficit": {
        "scientific_term": "reduced eccentric control / angular velocity variability",
        "structures_at_risk": [
            "patellar tendon",
            "quadriceps and hamstring tendon insertions",
            "lumbar spine (via uncontrolled flexion)",
        ],
        "muscles_overactive": ["global movers (rectus femoris)", "spinal erectors"],
        "muscles_underactive": ["gluteus maximus", "multifidus", "deep hip rotators"],
        "mechanism": (
            "Jerky angular changes indicate the eccentric phase is not being "
            "controlled by the muscle-tendon unit, so energy is absorbed by "
            "passive structures (tendon and joint capsule)."
        ),
    },
    "pose_quality": {
        "scientific_term": "measurement reliability limitation",
        "structures_at_risk": [],
        "muscles_overactive": [],
        "muscles_underactive": [],
        "mechanism": (
            "Low landmark visibility or few valid frames reduce the precision of "
            "joint-angle measurements, so findings should be interpreted with "
            "caution."
        ),
    },
}


def get_joint_muscles(joint: str) -> Dict[str, List[str]]:
    """Muscles acting on a joint (empty lists if the joint is unknown)."""
    return JOINT_MUSCLES.get(joint, {"primary": [], "stabilizers": []})


def get_risk_knowledge(risk_tag: str) -> Dict:
    """Scientific description for a risk tag (empty dict if unknown)."""
    return RISK_KNOWLEDGE.get(risk_tag, {})
