"""Pose coverage assessment — WHY detection was low, and whether partial results are still honest.

Pure functions (no cv2 / torch / DB) so every branch is unit-testable. The 70% floor is unchanged;
what changes is that a failure now says which of three different problems occurred:

  subject_too_small                  the selected person is too few pixels tall to measure reliably
  multiple_people_subject_unstable   several people were tracked and the selected athlete was only
                                     followed in a minority of frames (crossing / ID switches / left frame)
  low_detection_quality              the subject was tracked and big enough, but the pose model still
                                     failed on many frames (lighting, occlusion, framing)

Between PARTIAL_COVERAGE_FLOOR and the full floor a clip is accepted ONLY when the subject is large
enough and was reliably tracked; it is then stored with an explicit caveat. Below that, or when the
subject cannot be attributed to one person, the video fails: we never score footage we cannot measure.

The pixel / fraction thresholds are conservative heuristics, not validated cut-offs (docs/DECISIONS.md).
"""

from dataclasses import dataclass
from statistics import median
from typing import Literal

FULL_COVERAGE_FLOOR = 0.70
PARTIAL_COVERAGE_FLOOR = 0.40
MIN_SUBJECT_HEIGHT_PX = 160
SUBSTANTIVE_TRACK_FRACTION = 0.10   # a track must span >=10% of frames (min 5) to count as a person
SUBSTANTIVE_TRACK_MIN_FRAMES = 5


@dataclass(frozen=True)
class TrackingSummary:
    frames_processed: int
    frame_height: int | None
    max_persons: int                 # most people seen in any single frame
    tracked: bool                    # False when YOLO produced no track IDs
    tracks_seen: int                 # distinct track IDs (ID switches inflate this)
    substantive_tracks: int          # tracks present in a meaningful share of frames
    main_track_id: int | None
    main_track_frames: int
    main_track_coverage: float       # fraction of frames the selected athlete was followed
    subject_height_px: float | None  # median box height of the selected athlete

    @property
    def multi_person(self) -> bool:
        return self.substantive_tracks > 1

    @property
    def subject_height_ratio(self) -> float | None:
        if self.subject_height_px is None or not self.frame_height:
            return None
        return self.subject_height_px / self.frame_height


@dataclass(frozen=True)
class CoverageAssessment:
    outcome: Literal["ok", "partial", "reject"]
    code: str | None            # failure code (reject) or "partial_coverage" (partial)
    message: str | None         # user-facing failure reason (reject)
    caveat: str | None          # stored on the video when accepted with caveats (partial / multi-person)


def summarize_tracking(tracking: dict) -> TrackingSummary:
    tracks: dict[int, dict] = tracking.get("tracks") or {}
    # Denominator = frames the tracker actually ANALYSED. `frames_processed` counts frames READ, but with
    # stride > 1 (120/240 fps slow-motion clips) tracks only hold every stride-th frame, so dividing by it
    # understated coverage by a factor of `stride` and wrongly rejected perfectly tracked clips.
    person_counts = tracking.get("person_counts")
    frames = len(person_counts) if person_counts else int(tracking.get("frames_processed") or 0)
    main_id = tracking.get("main_track_id")
    main_frames = tracks.get(main_id, {}) if main_id is not None else {}

    min_len = max(SUBSTANTIVE_TRACK_MIN_FRAMES, SUBSTANTIVE_TRACK_FRACTION * frames)
    substantive = sum(1 for t in tracks.values() if len(t) >= min_len)
    heights = [b[3] - b[1] for b in main_frames.values()]

    return TrackingSummary(
        frames_processed=frames,
        frame_height=tracking.get("frame_height"),
        max_persons=int(tracking.get("max_persons") or 0),
        tracked=bool(tracking.get("tracked")),
        tracks_seen=len(tracks),
        substantive_tracks=substantive,
        main_track_id=main_id,
        main_track_frames=len(main_frames),
        main_track_coverage=(len(main_frames) / frames) if frames else 0.0,
        subject_height_px=float(median(heights)) if heights else None,
    )


def _people_clause(s: TrackingSummary) -> str:
    if not s.tracked and s.max_persons > 1:
        return f" Up to {s.max_persons} people were visible but identity tracking was unavailable."
    if not s.multi_person:
        return ""
    return (
        f" {s.substantive_tracks} people were tracked ({s.tracks_seen} track IDs in total); the athlete analysed "
        f"was track {s.main_track_id}, followed in {s.main_track_coverage:.0%} of frames."
    )


def multi_person_note(s: TrackingSummary) -> str:
    return (
        f"Multiple people in frame: {s.substantive_tracks} tracked ({s.tracks_seen} track IDs). Analysis followed "
        f"track {s.main_track_id} (the person present in the most frames, followed in {s.main_track_coverage:.0%}). "
        f"Verify on the annotated video that this is the intended athlete."
    )


def assess_coverage(s: TrackingSummary, detection_rate: float) -> CoverageAssessment:
    subject_small = s.subject_height_px is not None and s.subject_height_px < MIN_SUBJECT_HEIGHT_PX
    # Several people and either the athlete was followed in a minority of frames, or identity tracking was
    # unavailable altogether (so frames cannot be attributed to one person).
    subject_unstable = (s.multi_person and s.main_track_coverage < FULL_COVERAGE_FLOOR) or (
        not s.tracked and s.max_persons > 1
    )

    if detection_rate >= FULL_COVERAGE_FLOOR:
        return CoverageAssessment("ok", None, None, multi_person_note(s) if s.multi_person else None)

    measured = f"Pose was measured on the selected athlete in {detection_rate:.0%} of frames (full-confidence floor {FULL_COVERAGE_FLOOR:.0%})."

    if subject_small:
        ratio = s.subject_height_ratio
        size = f"~{s.subject_height_px:.0f} px tall" + (f" ({ratio:.0%} of frame height)" if ratio else "")
        return CoverageAssessment("reject", "subject_too_small", (
            f"The athlete is too small to measure reliably: the selected person is {size}; at least "
            f"{MIN_SUBJECT_HEIGHT_PX} px is needed. {measured}{_people_clause(s)} "
            f"Move the camera closer or zoom in on the athlete."), None)

    if subject_unstable:
        return CoverageAssessment("reject", "multiple_people_subject_unstable", (
            f"Several people are in the footage and the athlete could not be followed consistently. {measured}"
            f"{_people_clause(s)} Frames without the selected athlete are not measured (we do not substitute "
            f"another person). Re-record with the athlete clearly separated, or trim the clip to when only the "
            f"athlete is in view."), None)

    if detection_rate >= PARTIAL_COVERAGE_FLOOR:
        caveat = (
            f"Partial coverage: {measured} Results reflect only those frames and may not represent the whole "
            f"movement — lower confidence."
        )
        if s.multi_person:
            caveat += " " + multi_person_note(s)
        return CoverageAssessment("partial", "partial_coverage", None, caveat)

    return CoverageAssessment("reject", "low_detection_quality", (
        f"{measured} The athlete was tracked and large enough, but pose detection still failed on most frames — "
        f"below the {PARTIAL_COVERAGE_FLOOR:.0%} minimum for any result. Check lighting, occlusion, and that the "
        f"full body is in view.{_people_clause(s)}"), None)
