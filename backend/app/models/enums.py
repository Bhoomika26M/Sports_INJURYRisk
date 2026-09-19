import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    COACH = "coach"
    PHYSIOTHERAPIST = "physiotherapist"
    SPORTS_SCIENTIST = "sports_scientist"
    ATHLETE = "athlete"


class BiologicalSex(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class DominantLeg(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"
    AMBIDEXTROUS = "ambidextrous"


class AnatomicalSide(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"
    BILATERAL = "bilateral"


class InjuryType(str, enum.Enum):
    ACL_TEAR = "acl_tear"
    ANKLE_SPRAIN = "ankle_sprain"
    HAMSTRING_STRAIN = "hamstring_strain"
    PATELLAR_TENDINOPATHY = "patellar_tendinopathy"
    MENISCUS_TEAR = "meniscus_tear"
    GROIN_STRAIN = "groin_strain"
    OTHER = "other"


class MovementType(str, enum.Enum):
    SQUAT = "squat"
    JUMP_LANDING = "jump_landing"
    RUNNING = "running"


class CameraView(str, enum.Enum):
    FRONTAL = "frontal"
    SAGITTAL = "sagittal"
    OBLIQUE = "oblique"


class ProcessingStatus(str, enum.Enum):
    PENDING_UPLOAD = "pending_upload"
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    POSE_ESTIMATION = "pose_estimation"
    BIOMECHANICS_CALC = "biomechanics_calc"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskTier(str, enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
