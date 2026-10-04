// Wire types — snake_case on purpose, mirrors the backend (see /AGENTS.md "Naming").

export type Role = "athlete" | "coach" | "physiotherapist" | "sports_scientist" | "admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  google_id: string | null;
  avatar_url: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Athlete {
  id: string;
  user_id: string | null;
  coach_id: string | null;
  full_name: string | null;
  sport_type: string;
  position: string | null;
  date_of_birth: string;
  height_cm: number | null;
  weight_kg: number | null;
  dominant_side: "left" | "right" | null;
  age: number | null;
}

export interface Injury {
  id: string;
  athlete_id: string;
  injury_type: string;
  body_part: string;
  injury_date: string;
  recovery_date: string | null;
  severity: "minor" | "moderate" | "severe" | null;
  notes: string | null;
}

export interface TrainingLoad {
  id: string;
  athlete_id: string;
  entry_date: string;
  session_type: string | null;
  duration_minutes: number | null;
  rpe: number | null;
  session_load: number | null;
  notes: string | null;
}

export interface Acwr {
  acwr: number | null;
  acute_load: number | null;
  chronic_load: number | null;
  flagged: boolean;
  message: string;
}

export type VideoStatus = "pending_upload" | "uploaded" | "processing" | "completed" | "failed";

export interface Video {
  id: string;
  athlete_id: string;
  uploaded_by: string;
  movement_type: string;
  original_filename: string | null;
  duration_seconds: number | null;
  fps: number | null;
  resolution_width: number | null;
  resolution_height: number | null;
  camera_view: string;
  processing_status: VideoStatus;
  detection_rate: number | null;
  person_count_detected?: number | null;
  /** Set when the clip was accepted with limits (several people, or the athlete measured on few frames). */
  coverage_caveat?: string | null;
  analysis?: { quality?: VideoQuality } | null;
  error_code: string | null;
  error_message: string | null;
  progress_pct: number;
  annotated_video_key: string | null;
  thumbnail_key: string | null;
  created_at: string;
}

export interface MovementMetricInfo {
  metric_name: string;
  plane: string;
  confidence: "validated" | "qualitative" | string;
  unit: string;
  description: string | null;
}

export interface MovementType {
  code: string;
  display_name: string;
  camera_views: string[];
  phases: string[] | null;
  metrics: MovementMetricInfo[];
}

export interface UploadTicket {
  video_id: string;
  upload_url: string;
  storage_key: string;
  expires_in: number;
}

export interface BiomechFrame {
  frame_number: number;
  metric_name: string;
  metric_value: number;
  plane: string;
  confidence: "validated" | "qualitative" | string;
  movement_phase: string | null;
}

export interface BiomechSummary {
  metric_name: string;
  peak_value: number | null;
  min_value: number | null;
  range_of_motion: number | null;
}

export interface Biomechanics {
  video_id: string;
  detection_rate: number | null;
  limb_symmetry_index: number | null;
  summary: BiomechSummary[];
  frames: BiomechFrame[];
}

export type RiskCategory = "low" | "moderate" | "high" | "critical";

export interface QualityWarning { code: string; message: string }
export interface VideoQuality { grade: "good" | "fair" | "poor" | "unknown"; warnings?: QualityWarning[] }

/** One of the five weighted components. `available:false` means "no data", which is NOT a zero. */
export interface RiskComponent {
  weight: number;
  available: boolean;
  points: number;
  max: number;
  score: number | null;
  detail?: { reason?: string } | string | null;
}

/** The five sub-scores the project brief asks for; `score: null` = not enough data to compute. */
export interface RiskSubScore { score: number | null; higher_is: string; definition: string }

export interface InjuryCategory {
  label: string;
  level: "low" | "moderate" | "high" | "critical" | "insufficient_data";
  based_on?: string[];
  video_kinematics_used?: boolean;
  drivers?: { factor: string; score: number }[];
}

export interface RepAnalysis {
  n_reps: number; mean_rep_s?: number; mean_cycle_s?: number; mean_descent_s?: number;
  mean_ascent_s?: number; cv_pct?: number; drift_pct?: number;
}
export interface GaitAnalysis { n_steps: number; cadence_spm: number; step_time_asymmetry_pct?: number | null }

export interface RiskScore {
  overall_score: number;
  risk_category: RiskCategory;
  data_completeness: number;
  score_breakdown: Record<string, RiskComponent>;
  sub_scores?: Record<string, RiskSubScore>;
  injury_categories?: Record<string, InjuryCategory>;
  baseline?: { videos: number; athletes?: number; movement_type: string; provisional?: boolean };
  quality?: VideoQuality;
  /** What the pose pipeline could actually measure on this clip (null fields = nothing to report). */
  data_quality?: { detection_rate: number | null; person_count_detected: number | null; caveat: string | null };
  movement?: { reps?: RepAnalysis | null; gait?: GaitAnalysis | null };
  methodology_note: string;
}

/** HTTP 202 body: the reference population is too small or too narrow. `unit` says what have/need count. */
export interface InsufficientBaseline {
  status: "insufficient_baseline_data";
  metric_name: string;
  unit: "videos" | "athletes";
  movement_type: string;
  have: number;
  need: number;
  coverage: { videos: { have: number; need: number }; athletes: { have: number; need: number } };
  excluded_incomplete?: number;
  message?: string;
}

export interface Recommendation {
  category: string;
  title: string;
  description: string;
  priority: number;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  read_at: string | null;
  related_athlete_id: string | null;
  created_at: string;
}

export interface NotificationPage extends Page<Notification> {
  unread_count: number;
}

export interface TeamOverview {
  total_athletes: number;
  total_videos: number;
  videos_completed: number;
  videos_failed: number;
  videos_processing: number;
  avg_risk_score: number | null;
  high_risk_count: number;
  critical_risk_count: number;
  low_risk_count: number;
  moderate_risk_count: number;
}

export interface CoachAthleteCard {
  athlete_id: string;
  name: string | null;
  sport: string;
  latest_risk_score: number | null;
  latest_risk_category: RiskCategory | null;
  last_assessed: string | null;
}

export interface CoachDashboard {
  overview: TeamOverview;
  athletes: CoachAthleteCard[];
}

export interface TrendPoint {
  video_id: string;
  movement_type: string;
  overall_score: number;
  risk_category: RiskCategory;
  created_at: string;
}

export interface AthleteTrend {
  athlete_id: string;
  points: TrendPoint[];
  total: number;
  methodology_note: string;
}

export interface MovementAnalytics {
  movement_type: string | null;
  videos_analyzed: number;
  baselines: Record<string, { mean: number; std: number; sample_size: number }>;
  anomaly_distribution: { mean?: number | null; p90?: number | null };
}
