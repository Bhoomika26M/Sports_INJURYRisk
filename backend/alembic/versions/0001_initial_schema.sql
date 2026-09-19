-- Initial Schema Migration for Sports Injury Risk Detection
-- Generated from /docs/database_schema.md

-- 1. Create Custom Enumerations
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('admin', 'coach', 'physiotherapist', 'sports_scientist', 'athlete');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE biological_sex_enum AS ENUM ('male', 'female', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE dominant_leg_enum AS ENUM ('left', 'right', 'ambidextrous');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE anatomical_side_enum AS ENUM ('left', 'right', 'bilateral');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE injury_type_enum AS ENUM ('acl_tear', 'ankle_sprain', 'hamstring_strain', 'patellar_tendinopathy', 'meniscus_tear', 'groin_strain', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE movement_type_enum AS ENUM ('squat', 'jump_landing', 'running');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE camera_view_enum AS ENUM ('frontal', 'sagittal', 'oblique');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE processing_status_enum AS ENUM ('pending_upload', 'uploaded', 'preprocessing', 'pose_estimation', 'biomechanics_calc', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE risk_tier_enum AS ENUM ('low', 'moderate', 'high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Table: users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'athlete',
    phone_number VARCHAR(30),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- 3. Table: athletes
CREATE TABLE IF NOT EXISTS athletes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date_of_birth DATE NOT NULL,
    biological_sex biological_sex_enum NOT NULL,
    height_cm NUMERIC(5,2) NOT NULL CHECK (height_cm > 50 AND height_cm < 260),
    weight_kg NUMERIC(5,2) NOT NULL CHECK (weight_kg > 20 AND weight_kg < 300),
    dominant_leg dominant_leg_enum NOT NULL DEFAULT 'right',
    primary_sport VARCHAR(100) NOT NULL,
    team_affiliation VARCHAR(150),
    position VARCHAR(80),
    competitive_level VARCHAR(50) NOT NULL DEFAULT 'collegiate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_athletes_user_id ON athletes (user_id);
CREATE INDEX IF NOT EXISTS idx_athletes_team ON athletes (team_affiliation);

-- 4. Table: injury_history
CREATE TABLE IF NOT EXISTS injury_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    injury_type injury_type_enum NOT NULL,
    anatomical_side anatomical_side_enum NOT NULL,
    diagnosis_details VARCHAR(255),
    injury_date DATE NOT NULL,
    severity_grade VARCHAR(20),
    surgical_intervention BOOLEAN NOT NULL DEFAULT FALSE,
    return_to_play_date DATE,
    fully_resolved BOOLEAN NOT NULL DEFAULT TRUE,
    clinical_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_injury_history_athlete_id ON injury_history (athlete_id);
CREATE INDEX IF NOT EXISTS idx_injury_history_type ON injury_history (injury_type);

-- 5. Table: training_profiles
CREATE TABLE IF NOT EXISTS training_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    weekly_training_hours NUMERIC(4,1) NOT NULL CHECK (weekly_training_hours >= 0),
    sessions_per_week INTEGER NOT NULL CHECK (sessions_per_week >= 1),
    strength_sessions_per_week INTEGER NOT NULL DEFAULT 2,
    current_training_phase VARCHAR(50) NOT NULL DEFAULT 'in_season',
    acute_chronic_workload_ratio NUMERIC(4,2) CHECK (acute_chronic_workload_ratio IS NULL OR acute_chronic_workload_ratio >= 0),
    resting_heart_rate_bpm INTEGER,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_training_profiles_athlete_id ON training_profiles (athlete_id);

-- 6. Table: physical_assessments
CREATE TABLE IF NOT EXISTS physical_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    assessor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    assessment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    assessment_type VARCHAR(80) NOT NULL DEFAULT 'pre_season_baseline',
    weight_at_assessment_kg NUMERIC(5,2),
    ankle_dorsiflexion_left_cm NUMERIC(4,1),
    ankle_dorsiflexion_right_cm NUMERIC(4,1),
    single_leg_hop_left_cm NUMERIC(5,1),
    single_leg_hop_right_cm NUMERIC(5,1),
    y_balance_composite_score NUMERIC(5,2),
    clinical_observations TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_assessments_athlete_id ON physical_assessments (athlete_id);
CREATE INDEX IF NOT EXISTS idx_assessments_assessor_id ON physical_assessments (assessor_id);

-- 7. Table: coach_athlete_assignments
CREATE TABLE IF NOT EXISTS coach_athlete_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    assignment_role VARCHAR(50) NOT NULL DEFAULT 'head_coach',
    assigned_at DATE NOT NULL DEFAULT CURRENT_DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_coach_athlete_role UNIQUE (coach_id, athlete_id, assignment_role)
);
CREATE INDEX IF NOT EXISTS idx_coach_athlete_coach_id ON coach_athlete_assignments (coach_id);
CREATE INDEX IF NOT EXISTS idx_coach_athlete_athlete_id ON coach_athlete_assignments (athlete_id);

-- 8. Table: videos
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    assessment_id UUID REFERENCES physical_assessments(id) ON DELETE SET NULL,
    uploaded_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    file_path VARCHAR(512) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(50) NOT NULL DEFAULT 'video/mp4',
    duration_seconds NUMERIC(5,2),
    frame_rate_fps NUMERIC(5,2),
    frame_width INTEGER,
    frame_height INTEGER,
    movement_type movement_type_enum NOT NULL,
    camera_view camera_view_enum NOT NULL DEFAULT 'frontal',
    processing_status processing_status_enum NOT NULL DEFAULT 'pending_upload',
    calculated_metrics_summary JSONB,
    overall_risk_score NUMERIC(5,2) CHECK (overall_risk_score IS NULL OR (overall_risk_score >= 0 AND overall_risk_score <= 100)),
    risk_tier risk_tier_enum,
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_videos_athlete_id ON videos (athlete_id);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos (processing_status) WHERE processing_status != 'completed';
CREATE INDEX IF NOT EXISTS idx_videos_risk_tier ON videos (risk_tier);
CREATE INDEX IF NOT EXISTS idx_videos_movement_created ON videos (movement_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_metrics_gin ON videos USING gin (calculated_metrics_summary);
