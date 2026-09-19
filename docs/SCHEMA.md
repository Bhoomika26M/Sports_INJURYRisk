# SCHEMA.md

PostgreSQL 16. `gen_random_uuid()` is native, no extension needed. This is the single source of truth for the data model — if code and this file disagree, the code is wrong unless a `/docs/DECISIONS.md` entry says otherwise.

**Revision note (Milestone 3):** the M3 tables below include CHECK constraints from the start — the Milestone 2 audit (`IMPLEMENTATION_REVIEW.md`, finding H2) found `camera_view`, `plane`, and `confidence` were missing their constraints in the actual M2 migration despite being specified here. Don't repeat that gap.

---

## Milestone 1 — built and migrated

```sql
CREATE TYPE user_role AS ENUM (
    'athlete', 'coach', 'physiotherapist', 'sports_scientist', 'admin'
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            user_role NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked         BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE athletes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    coach_id        UUID REFERENCES users(id),
    sport_type      VARCHAR(100) NOT NULL,
    position        VARCHAR(100),
    date_of_birth   DATE NOT NULL,
    height_cm       NUMERIC(5,2),
    weight_kg       NUMERIC(5,2),
    dominant_side   VARCHAR(10) CHECK (dominant_side IN ('left', 'right')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE injury_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id      UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    injury_type     VARCHAR(255) NOT NULL,
    body_part       VARCHAR(100) NOT NULL,
    injury_date     DATE NOT NULL,
    recovery_date   DATE,
    severity        VARCHAR(20) CHECK (severity IN ('minor', 'moderate', 'severe')),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE training_load_entries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id          UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    entry_date          DATE NOT NULL,
    session_type        VARCHAR(100),
    duration_minutes    INTEGER,
    rpe                 SMALLINT CHECK (rpe BETWEEN 1 AND 10),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_athletes_coach_id ON athletes(coach_id);
CREATE INDEX idx_injury_history_athlete_id ON injury_history(athlete_id);
CREATE INDEX idx_training_load_athlete_id ON training_load_entries(athlete_id);
```

---

## Milestone 2 — built and migrated

```sql
CREATE TYPE video_processing_status AS ENUM (
    'pending_upload', 'uploaded', 'processing', 'completed', 'failed'
);

CREATE TABLE videos (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id                UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    uploaded_by                UUID NOT NULL REFERENCES users(id),
    movement_type               VARCHAR(50) NOT NULL,
    storage_key                 VARCHAR(500) NOT NULL,
    original_filename           VARCHAR(255),
    duration_seconds            NUMERIC(6,2),
    fps                         NUMERIC(5,2),
    resolution_width            INTEGER,
    resolution_height           INTEGER,
    camera_view                 VARCHAR(20) NOT NULL CHECK (camera_view IN ('sagittal', 'frontal', 'other')),
    processing_status           video_processing_status NOT NULL DEFAULT 'pending_upload',
    person_count_detected       INTEGER,
    detection_rate              NUMERIC(4,3),
    error_code                  VARCHAR(50),
    error_message                TEXT,
    job_id                      VARCHAR(255),
    progress_pct                 INTEGER NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    annotated_video_key          VARCHAR(500),
    thumbnail_key                VARCHAR(500),
    processing_started_at        TIMESTAMPTZ,
    processing_completed_at      TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_videos_athlete_id ON videos(athlete_id);
CREATE INDEX idx_videos_processing_status ON videos(processing_status);

CREATE TABLE pose_frames (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id        UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_number    INTEGER NOT NULL,
    timestamp_ms    INTEGER NOT NULL,
    keypoints       JSONB NOT NULL,
    model_used      VARCHAR(20) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(video_id, frame_number)
);

CREATE TABLE biomechanical_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id        UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_number    INTEGER NOT NULL,
    metric_name     VARCHAR(50) NOT NULL,
    metric_value    NUMERIC(8,3) NOT NULL,
    plane           VARCHAR(20) NOT NULL CHECK (plane IN ('sagittal','frontal','transverse')),
    confidence      VARCHAR(10) NOT NULL CHECK (confidence IN ('validated','qualitative')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pose_frames_video_id ON pose_frames(video_id);
CREATE INDEX idx_biomechanical_metrics_video_id ON biomechanical_metrics(video_id);
```

*(These three CHECK constraints — `camera_view`, `plane`, `confidence` — were missing from the actual M2 migration per `IMPLEMENTATION_REVIEW.md` finding H2. If you're reading this after applying that fix, they should already be live; if not, apply H2 before continuing.)*

---

## Milestone 3 — build and migrate now

```sql
CREATE TABLE movement_baselines (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id     UUID REFERENCES athletes(id),  -- NULL = population-level (only kind built in M3 v1)
    movement_type  VARCHAR(50) NOT NULL,
    metric_name    VARCHAR(50) NOT NULL,
    mean_value     NUMERIC(8,3) NOT NULL,
    std_dev        NUMERIC(8,3) NOT NULL,
    sample_size    INTEGER NOT NULL CHECK (sample_size >= 0),
    computed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(athlete_id, movement_type, metric_name)
);

CREATE TABLE anomaly_scores (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id               UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_number           INTEGER,
    anomaly_score          NUMERIC(6,3) NOT NULL CHECK (anomaly_score BETWEEN 0 AND 100),
    method                 VARCHAR(30) NOT NULL CHECK (method = 'isolation_forest'),
    baseline_sample_size   INTEGER NOT NULL,
    flagged                BOOLEAN NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE risk_scores (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id           UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE UNIQUE,
    athlete_id         UUID NOT NULL REFERENCES athletes(id),
    overall_score      NUMERIC(5,2) NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    risk_category      VARCHAR(20) NOT NULL CHECK (risk_category IN ('low','moderate','high','critical')),
    score_breakdown    JSONB NOT NULL,
    methodology_note   TEXT NOT NULL DEFAULT 'Composite of movement-pattern anomaly vs. population baseline, a bounded symmetry flag, and a bounded prior-injury flag. Not a trained injury-prediction model. See docs/SCIENCE_CONSTRAINTS.md.',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_score_id   UUID NOT NULL REFERENCES risk_scores(id) ON DELETE CASCADE,
    category        VARCHAR(30) NOT NULL CHECK (category IN ('exercise','mobility','strengthening','recovery','training_modification')),
    title           VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL,
    priority        SMALLINT NOT NULL CHECK (priority BETWEEN 1 AND 5),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_anomaly_scores_video_id ON anomaly_scores(video_id);
CREATE INDEX idx_recommendations_risk_score_id ON recommendations(risk_score_id);
```

---

## Milestone 4 — designed now, migrate when M4 starts, not before

```sql
CREATE TABLE notifications (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                 VARCHAR(30) NOT NULL,
    title                VARCHAR(255) NOT NULL,
    body                 TEXT NOT NULL,
    read_at              TIMESTAMPTZ,
    related_athlete_id   UUID REFERENCES athletes(id),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE report_exports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by    UUID NOT NULL REFERENCES users(id),
    athlete_id      UUID REFERENCES athletes(id),
    report_type     VARCHAR(30) NOT NULL,
    format          VARCHAR(10) NOT NULL CHECK (format IN ('pdf','xlsx')),
    storage_key     VARCHAR(500),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','generating','ready','failed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
