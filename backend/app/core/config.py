from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "test-secret-key-for-development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Milestone 2: Video Processing Settings
    VIDEO_UPLOAD_DIR: str = "uploads"
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024  # 500 MB
    MAX_VIDEO_DURATION: int = 300  # 5 minutes in seconds
    TARGET_PROCESSING_WIDTH: int = 640
    POSE_FPS: int = 15  # FPS for pose estimation
    POSE_CONFIDENCE_THRESHOLD: float = 0.3
    # Directory holding MediaPipe Tasks .task models (relative to backend/)
    POSE_MODEL_DIR: str = "models"
    
    # Progressive analysis / live progress
    PROGRESS_CHUNK_FRAMES: int = 20       # sampled frames per progress update
    POSE_WORKERS: int = 0                 # parallel MediaPipe instances (0 = auto: min(4, cpu count))
    PREVIEW_EVERY_CHUNKS: int = 2         # refresh live preview frame every N chunks
    # Pose runs on a downscaled ROI: MediaPipe resizes to ~256px internally,
    # so feeding a 4K crop only adds conversion cost (mapping is scale-invariant)
    POSE_MAX_ROI_DIM: int = 960
    # MediaPipe pose model complexity: 0 = lite, 1 = full, 2 = heavy
    POSE_MODEL_COMPLEXITY: int = 1
    # Cap annotated-video width: 4K encodes dominate runtime and file size
    ANNOTATED_MAX_WIDTH: int = 1280

    # --- Annotated output framing ("smart crop") ---
    # When enabled, the annotated video (and the live preview) is cropped to a
    # moving window that follows the tracked athlete, so the full body fills the
    # frame instead of being a small figure in a wide shot. Purely a render-time
    # operation - it does not change analysis cost.
    ANNOTATED_FOLLOW_ATHLETE: bool = True
    # Fractional padding around the detected body box. Larger = more context.
    ANNOTATED_CROP_PADDING: float = 0.55
    # Temporal smoothing for the follow window (0..1). Lower = steadier but
    # laggier; a large jump snaps instantly so cuts don't smear.
    ANNOTATED_CROP_SMOOTHING: float = 0.25
    # Smallest crop, as a fraction of the frame's smaller side. Stops a spurious
    # tiny detection from producing a mushily upscaled close-up.
    ANNOTATED_CROP_MIN_SCALE: float = 0.35

    # --- Pipeline profiling ---
    # When on, per-stage timings (detect / pose / render / encode / db / ...) are
    # accumulated and logged at the end of each run, and included in the
    # processing result. Off by default: it is cheap, but there is no reason to
    # pay for it in normal use. Turn on to find out where a slow video spends
    # its time before changing any tuning knobs.
    POSE_PROFILING: bool = False

    # --- Detection cost controls ---
    # Person detection is the single most expensive stage on high-resolution
    # footage (measured ~28% of wall time on 4K, ~147ms/frame). A person
    # bounding box is scale-invariant, so the detector does not need the full
    # source resolution: frames wider than this are downscaled before YOLO and
    # the returned box is scaled back up. 0 disables the downscale.
    DETECT_MAX_WIDTH: int = 1280
    # Inference size passed to YOLO. Left at the Ultralytics default (640) this
    # is explicit rather than implicit, and safely tunable per deployment.
    DETECT_IMGSZ: int = 640

    # --- Email OTP (password recovery / authenticated password change) ---
    OTP_LENGTH: int = 6                     # digits; leading zeros are preserved
    OTP_EXPIRE_MINUTES: int = 5             # OTP lifetime
    OTP_MAX_ATTEMPTS: int = 5               # verification attempts per issued code
    OTP_RESEND_COOLDOWN_SECONDS: int = 60   # minimum gap between OTP issues per account/purpose
    # Dedicated key used to HMAC-hash OTPs at rest. If left empty, a distinct
    # key is derived from SECRET_KEY via HKDF (domain-separated). Production
    # deployments should set this explicitly and rotate it independently.
    OTP_HMAC_SECRET: str = ""

    # --- Google Sign-In (OAuth 2.0 authorization code flow) ---
    # Feature is disabled until GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set.
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # Must exactly match an "Authorized redirect URI" in the Google Cloud
    # console for the OAuth client. Defaults to the frontend callback page.
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/auth/google/callback"
    # Where to send the browser after a successful / failed sign-in.
    GOOGLE_FRONTEND_SUCCESS_REDIRECT: str = "http://localhost:5173/dashboard"
    GOOGLE_FRONTEND_FAILURE_REDIRECT: str = "http://localhost:5173/login"
    # Google OAuth endpoints (rarely need changing).
    GOOGLE_AUTH_URI: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URI: str = "https://openidconnect.googleapis.com/v1/userinfo"
    # Lifetime (seconds) of the signed OAuth state value (CSRF protection).
    GOOGLE_STATE_EXPIRE_SECONDS: int = 600

    model_config = ConfigDict(env_file=".env")


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.VIDEO_UPLOAD_DIR, exist_ok=True)
