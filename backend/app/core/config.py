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
    PROGRESS_CHUNK_FRAMES: int = 8        # sampled frames per progress update (fast updates)
    POSE_WORKERS: int = 0                 # parallel MediaPipe instances (0 = auto: min(4, cpu count))
    PREVIEW_EVERY_CHUNKS: int = 1         # refresh live preview frame every N chunks
    # Pose runs on a downscaled ROI: MediaPipe resizes to ~256px internally,
    # so feeding a 4K crop only adds conversion cost (mapping is scale-invariant)
    POSE_MAX_ROI_DIM: int = 640
    # MediaPipe pose model complexity: 0 = lite, 1 = full, 2 = heavy
    POSE_MODEL_COMPLEXITY: int = 0
    # Cap annotated-video width: 4K encodes dominate runtime and file size
    ANNOTATED_MAX_WIDTH: int = 960

    # --- Annotated output framing ("smart crop") ---    # When enabled, the annotated video (and the live preview) is cropped to a
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

    # --- Live annotated playback (streaming output) ---
    # The annotated video is muxed as a fragmented MP4 so it is playable in the
    # browser WHILE analysis is still running, instead of only when it finishes.
    # Requires the ffmpeg binary bundled by 'imageio-ffmpeg'; if it is missing,
    # analysis still succeeds and the UI falls back to preview stills.
    ANNOTATED_STREAM: bool = True
    # Frames per fragment (also the keyframe interval). Smaller makes playback
    # start sooner at a slightly higher bitrate.
    ANNOTATED_STREAM_FRAGMENT_FRAMES: int = 8
    # x264 quality/speed. Lower CRF = better and larger; veryfast keeps encoding
    # from becoming the pipeline bottleneck.
    ANNOTATED_STREAM_CRF: int = 23
    ANNOTATED_STREAM_PRESET: str = "veryfast"

    # --- Annotated output frame rate ---
    # Analysis samples pose at POSE_FPS (cheap). The *output* video does not have
    # to run at that rate: writing it at POSE_FPS makes fast movement step,
    # because a 30fps clip sampled at 15fps discards half its motion.
    # When enabled, the annotated video is rendered in a second pass at the
    # source frame rate, with pose interpolated between measured samples (linear,
    # between the temporally smoothed measurements). Analysis cost is unchanged;
    # the cost is one extra decode+encode pass.
    ANNOTATED_FULL_FPS: bool = True
    # Upper bound on the output frame rate, to keep file size sane on very
    # high-rate sources (e.g. 120fps phone footage). 0 means "use source fps".
    ANNOTATED_MAX_FPS: int = 60

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
    DETECT_MAX_WIDTH: int = 640
    # Inference size passed to YOLO. Left at the Ultralytics default (640) this
    # is explicit rather than implicit, and safely tunable per deployment.
    DETECT_IMGSZ: int = 480

    # --- Environment / email delivery ---
    # "development" prints OTPs and links to the console instead of emailing
    # them; ANY other value (e.g. "production") attempts a real SMTP send.
    ENVIRONMENT: str = "development"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "noreply@sportsinjuryrisk.com"

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

    # --- Supabase Cloud Storage & Database ---
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_BUCKET: str = "videos"

    # Priority: backend/.env, falling back to workspace root .env
    _backend_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    model_config = ConfigDict(env_file=_backend_env if os.path.exists(_backend_env) else ".env", extra="ignore")


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.VIDEO_UPLOAD_DIR, exist_ok=True)
