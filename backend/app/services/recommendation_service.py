from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.schemas.recommendation import Recommendation, RecommendationResponse
from app.services.anomaly_service import anomaly_service
from app.services.assessment_service import get_assessment
from app.models.athlete import AthleteProfile
from app.models.video import Video

class RecommendationEngine:
    def __init__(self):
        # A curated clinical and biomechanical recommendation library
        self.library = {
            # -------------------------------------------------------------
            # Professional Consultation & Technique Review (Original IDs)
            # -------------------------------------------------------------
            "professional_assessment_asymmetry": Recommendation(
                id="professional_assessment_asymmetry",
                title="Seek Assessment by a Physiotherapist",
                triggering_finding="High knee asymmetry or persistent movement imbalance detected.",
                rationale="Significant asymmetry can sometimes lead to compensatory patterns. A clinical professional can accurately measure strength and mobility deficits.",
                intended_audience="Athletes experiencing pain or showing persistent, significant movement imbalances.",
                limitations="This is a general screening finding, not a clinical determination of an underlying condition.",
                source_review_status="General Sports Science Consensus (Educational)",
                description="Consider booking a consultation with a qualified physiotherapist to undergo a formal musculoskeletal assessment.",
                action_type="consult_professional",
                category="consult_professional",
                target_region="Bilateral Lower Extremity",
                frequency="As scheduled with clinician"
            ),
            "coach_technique_trunk": Recommendation(
                id="coach_technique_trunk",
                title="Discuss Trunk Control with a Qualified Coach",
                triggering_finding="Excessive forward trunk lean observed during movement.",
                rationale="Trunk lean can alter center of mass and load distribution. Coaching feedback can help cue proper postural control.",
                intended_audience="Athletes refining their jump, landing, or running mechanics.",
                limitations="Does not address potential underlying core weakness or mobility restrictions, which require physical assessment.",
                source_review_status="Coaching Best Practices (Educational)",
                description="Review your movement technique with a qualified coach to ensure appropriate postural alignment during dynamic tasks.",
                action_type="technique_review",
                category="technique_review",
                target_region="Core & Lumbar Spine",
                frequency="Next training session"
            ),
            "data_quality_reassess": Recommendation(
                id="data_quality_reassess",
                title="Re-record with Better Quality or Seek Professional Input",
                triggering_finding="Low confidence data, tracking errors, or missing landmarks.",
                rationale="Computer vision algorithms cannot safely or accurately analyze movement when the input video is poor, leading to potentially misleading interpretations.",
                intended_audience="Users recording videos for analysis.",
                limitations="No kinematic conclusions can be drawn.",
                source_review_status="System Quality Control",
                description="The video quality was insufficient. Please re-record ensuring full body visibility and good lighting, or seek an in-person professional assessment rather than relying on estimated data.",
                action_type="consult_professional",
                category="consult_professional",
                target_region="System Capture",
                frequency="Immediate re-recording"
            ),
            "review_training_load": Recommendation(
                id="review_training_load",
                title="Review Training Progression",
                triggering_finding="Movement variability or potential fatigue indicators.",
                rationale="Unusual movement variability might indicate emerging fatigue or lack of movement familiarity.",
                intended_audience="Athletes managing high training volumes.",
                limitations="Does not replace clinical monitoring for overtraining syndrome.",
                source_review_status="General Load Management Principles (Educational)",
                description="Discuss your current training volumes and recovery periods with your coach or sports scientist to ensure safe progressions.",
                action_type="educational",
                category="training_modification",
                target_region="Systemic Workload",
                frequency="Weekly review"
            ),

            # -------------------------------------------------------------
            # Module 9: 1. Exercise Recommendations
            # -------------------------------------------------------------
            "exercise_eccentric_hamstrings": Recommendation(
                id="exercise_eccentric_hamstrings",
                title="Nordic Hamstring Curl Protocol",
                triggering_finding="High hamstring elongation demands or knee flexion asymmetry.",
                rationale="Eccentric knee flexor strength enhances fascicle length and increases tissue tolerance during terminal swing deceleration.",
                intended_audience="Athletes participating in sprinting and high-speed running sports.",
                limitations="Requires gradual progression to avoid excessive delayed-onset muscle soreness.",
                source_review_status="FIFA 11+ Part 2 / F-MARC Clinical Guideline",
                description="Perform kneeling Nordic hamstring lowering with ankles anchored, controlling the forward descent with knees and hamstrings.",
                action_type="educational",
                category="exercise",
                target_region="Hamstrings",
                sets_and_reps="3 sets x 5-8 repetitions",
                frequency="2-3x weekly"
            ),
            "exercise_jump_landing": Recommendation(
                id="exercise_jump_landing",
                title="Drop Jump Soft-Landing Mechanics Drill",
                triggering_finding="Stiff landing mechanics or elevated peak ground reaction forces.",
                rationale="Retraining knee flexion past 45 degrees upon contact increases deceleration duration, dampening ground impact shock.",
                intended_audience="Athletes performing jumping, landing, and cutting maneuvers.",
                limitations="Should be halted if knee valgus collapse persists during execution.",
                source_review_status="Clinical Biomechanics Consensus (Hewett Framework)",
                description="Step off a 30cm box and land softly on both feet, actively absorbing the impact into a balanced half-squat without knees collapsing inward.",
                action_type="educational",
                category="exercise",
                target_region="Knee & Quadriceps Complex",
                sets_and_reps="3 sets x 5 controlled landings",
                frequency="2x weekly during warm-ups"
            ),
            "exercise_squat_mechanics": Recommendation(
                id="exercise_squat_mechanics",
                title="Spanish Squat Quadriceps Loading",
                triggering_finding="Reduced knee flexion excursion or patellofemoral overload.",
                rationale="Fixing the proximal tibiae with an anchor band allows vertical shin descent, reducing shear moments on the anterior knee joint.",
                intended_audience="Athletes refining squat depth and bilateral knee symmetry.",
                limitations="Requires secure resistance band anchor.",
                source_review_status="Sports Physical Therapy Consensus",
                description="Place a rigid band behind knees and execute squats maintaining a vertical torso and deep bilateral knee flexion.",
                action_type="educational",
                category="exercise",
                target_region="Quadriceps & Patellar Tendon",
                sets_and_reps="4 sets x 10-12 repetitions",
                frequency="3x weekly"
            ),
            "exercise_single_leg_balance": Recommendation(
                id="exercise_single_leg_balance",
                title="Single-Leg Dynamic Stability Series",
                triggering_finding="Center of mass sway or postural instability.",
                rationale="Unilateral stance challenges ankle mechanoreceptors and activates gluteal stabilizers for joint control.",
                intended_audience="Field and court sport athletes with lateral movement demands.",
                limitations="Requires level surface and absence of acute ankle swelling.",
                source_review_status="Evidence-Based Proprioceptive Guidelines",
                description="Balance on one leg on an unstable surface while performing controlled clockwise reaches with the free leg.",
                action_type="educational",
                category="exercise",
                target_region="Ankle Complex & Foot",
                sets_and_reps="3 sets x 30 seconds each limb",
                frequency="Daily"
            ),

            # -------------------------------------------------------------
            # Module 9: 2. Mobility Improvement Suggestions
            # -------------------------------------------------------------
            "mobility_ankle_dorsiflexion": Recommendation(
                id="mobility_ankle_dorsiflexion",
                title="Weight-Bearing Ankle Lunge Mobilization",
                triggering_finding="Restricted ankle dorsiflexion (< 20 degrees).",
                rationale="Adequate ankle dorsiflexion is essential for deep squatting and prevents compensatory foot pronation and knee valgus.",
                intended_audience="Athletes with limited squat depth or history of lateral ankle sprains.",
                limitations="Avoid forcing through anterior ankle impingement pain.",
                source_review_status="Orthopaedic Physical Therapy Standards",
                description="Place foot 10cm from a wall and drive knee forward over middle toe until light calf tension is felt, maintaining heel contact.",
                action_type="educational",
                category="mobility",
                target_region="Talocrural Joint & Achilles",
                sets_and_reps="2 sets x 12 oscillatory pulses per side",
                frequency="Pre-training dynamic routine"
            ),
            "mobility_hip_flexor": Recommendation(
                id="mobility_hip_flexor",
                title="Half-Kneeling Hip Flexor Couch Stretch",
                triggering_finding="Excessive anterior pelvic tilt or forward trunk lean.",
                rationale="Relieving iliopsoas and rectus femoris tightness permits neutral pelvic alignment during running and hip extension.",
                intended_audience="Athletes with excessive lordosis or forward trunk sway.",
                limitations="Maintain posterior pelvic tilt; avoid hyperextending lumbar spine.",
                source_review_status="Clinical Postural Control Best Practices",
                description="Assume half-kneeling with rear foot elevated on a bench, tucking pelvis under and shifting weight forward through front hip.",
                action_type="educational",
                category="mobility",
                target_region="Iliopsoas & Rectus Femoris",
                sets_and_reps="3 sets x 40-second sustained holds",
                frequency="Daily post-training"
            ),
            "mobility_thoracic_extension": Recommendation(
                id="mobility_thoracic_extension",
                title="Thoracic Spine Extension Foam Roll",
                triggering_finding="Forward head posture or cervical spine deviations.",
                rationale="Restoring thoracic extension relieves cervical and shoulder impingement stress while promoting scapular upward rotation.",
                intended_audience="Overhead athletes and individuals displaying kyphotic posture.",
                limitations="Avoid placing foam roller directly on lower lumbar vertebrae.",
                source_review_status="Scapulothoracic Clinical Consensus",
                description="Rest mid-back over a foam roller with hands supporting head, gently extending backward over the roller at multiple spinal segments.",
                action_type="educational",
                category="mobility",
                target_region="Thoracic Spine & Ribcage",
                sets_and_reps="2 sets x 10 segment extensions",
                frequency="Daily"
            ),

            # -------------------------------------------------------------
            # Module 9: 3. Strengthening Recommendations
            # -------------------------------------------------------------
            "strength_glute_med_valgus": Recommendation(
                id="strength_glute_med_valgus",
                title="Gluteus Medius Lateral Monster Band Walks",
                triggering_finding="Dynamic knee valgus collapse or Trendelenburg pelvic drop.",
                rationale="Hip abductors and external rotators counteract knee abduction moments and stabilize the pelvis in single-leg support.",
                intended_audience="Athletes exhibiting medial knee collapse during landing or cutting.",
                limitations="Ensure toes remain pointed straight forward without hip rotation.",
                source_review_status="Neuromuscular Injury Risk Reduction Protocol",
                description="Affix a resistance band above knees or ankles in a mini-squat stance, taking controlled lateral steps while actively keeping knees apart.",
                action_type="educational",
                category="strengthening",
                target_region="Gluteus Medius & Hip Abductors",
                sets_and_reps="3 sets x 15 paces each direction",
                frequency="3x weekly"
            ),
            "strength_mcgill_core_big3": Recommendation(
                id="strength_mcgill_core_big3",
                title="McGill Big 3 Trunk Stabilization",
                triggering_finding="Excessive trunk lean or coronal lateral sway.",
                rationale="Co-contraction of abdominal wall and spinal musculature creates core stiffness, reducing lumbar shear forces.",
                intended_audience="Athletes needing postural control during high-impact sports.",
                limitations="Do not substitute ballistic sit-ups for these isometric braces.",
                source_review_status="Spine Biomechanics Research (McGill Model)",
                description="Perform isometric Bird-Dog contralateral reaches, Side-Bridges, and Modified Curl-Ups focusing on steady breathing and core bracing.",
                action_type="educational",
                category="strengthening",
                target_region="Core & Lumbo-Pelvic Midline",
                sets_and_reps="Descending pyramids (6-4-2 reps of 8-sec holds)",
                frequency="3-4x weekly"
            ),
            "strength_single_leg_rdl": Recommendation(
                id="strength_single_leg_rdl",
                title="Single-Leg Romanian Deadlift (SL RDL)",
                triggering_finding="Bilateral symmetry deficits or hamstring vulnerability.",
                rationale="Unilateral hinge loading trains eccentric hamstring force production and active foot-ankle stabilization.",
                intended_audience="Athletes with identified bilateral strength discrepancies.",
                limitations="Keep hips level throughout the movement without opening pelvis.",
                source_review_status="Strength & Conditioning Clinical Standards",
                description="Hinge forward on one leg with soft knee flexion and flat back, extending opposite leg straight backward until torso is parallel to floor.",
                action_type="educational",
                category="strengthening",
                target_region="Hamstrings & Posterior Chain",
                sets_and_reps="3 sets x 8 repetitions per leg",
                frequency="2x weekly"
            ),
            "strength_rotator_cuff": Recommendation(
                id="strength_rotator_cuff",
                title="Rotator Cuff External Rotation with Tubing",
                triggering_finding="Shoulder asymmetry or overhead sport activity.",
                rationale="External rotator co-activation centers the humeral head in the glenoid fossa during arm acceleration and deceleration.",
                intended_audience="Overhead athletes including baseball, tennis, and throwing disciplines.",
                limitations="Maintain neutral wrist and tucked elbow position.",
                source_review_status="Overhead Athlete Clinical Review",
                description="Anchor tubing at waist height with elbow tucked to side at 90 degrees; rotate forearm outward against resistance with smooth tempo.",
                action_type="educational",
                category="strengthening",
                target_region="Shoulder & Scapular Stabilizers",
                sets_and_reps="3 sets x 12-15 repetitions",
                frequency="3x weekly"
            ),

            # -------------------------------------------------------------
            # Module 9: 4. Recovery Planning
            # -------------------------------------------------------------
            "recovery_active_flush": Recommendation(
                id="recovery_active_flush",
                title="Low-Impact Active Regeneration Flush",
                triggering_finding="High movement variability or documented workload fatigue.",
                rationale="Submaximal aerobic cross-training enhances muscle perfusion and speeds metabolic clearance without eccentric muscle damage.",
                intended_audience="Athletes undergoing heavy training microcycles.",
                limitations="Keep heart rate strictly below 65% of max to preserve recovery.",
                source_review_status="Sports Physiology Recovery Consensus",
                description="Complete 20 minutes of light stationary cycling, elliptical, or pool walking at relaxed cadence followed by gentle breathing drills.",
                action_type="educational",
                category="recovery",
                target_region="Systemic Cardiovascular",
                sets_and_reps="20-25 minutes low intensity",
                frequency="Post-match or active rest days"
            ),
            "recovery_percussive_fascia": Recommendation(
                id="recovery_percussive_fascia",
                title="Targeted Lower-Limb Myofascial Percussion",
                triggering_finding="High peak ground reaction forces or landing stiffness.",
                rationale="Mechanical percussion dampens muscle spindle excitability, lowering passive muscle tension and subjective tissue soreness.",
                intended_audience="Athletes with high cumulative ground impact exposures.",
                limitations="Avoid bony prominences such as the patella and anterior shin.",
                source_review_status="Applied Sports Performance Guidelines",
                description="Apply percussive device across calves, quads, and gluteal tissues with light pressure, sweeping slowly across muscle bellies.",
                action_type="educational",
                category="recovery",
                target_region="Quadriceps, Calves, Gluteals",
                sets_and_reps="60-90 seconds per muscle group",
                frequency="Post-training recovery sessions"
            ),
            "recovery_sleep_hydration": Recommendation(
                id="recovery_sleep_hydration",
                title="Sleep Architecture & Hydration Rebalancing",
                triggering_finding="Elevated fatigue risk or high training workload.",
                rationale="Deep slow-wave sleep is the primary driver of growth hormone release and neuromuscular restorative remodeling.",
                intended_audience="All athletes balancing training stress with physiological adaptation.",
                limitations="Consistency is key; irregular sleep schedules impede hormonal cycles.",
                source_review_status="Clinical Sleep Medicine in Athletics",
                description="Maintain 8 to 9 hours of sleep in a cool, dark environment; consume sodium-potassium electrolyte fluids post-exercise.",
                action_type="educational",
                category="recovery",
                target_region="Systemic Autonomic Recovery",
                sets_and_reps="8-9 hours per night",
                frequency="Daily"
            ),

            # -------------------------------------------------------------
            # Module 9: 5. Training Modification Suggestions
            # -------------------------------------------------------------
            "training_acwr_regulation": Recommendation(
                id="training_acwr_regulation",
                title="Acute:Chronic Workload Ratio Regulation",
                triggering_finding="High training workload or chronic volume elevation.",
                rationale="Limiting acute workload spikes relative to chronic fitness maintains the ACWR in the optimal 0.8 - 1.3 safe zone.",
                intended_audience="Coaching staff and athletes monitoring longitudinal training loads.",
                limitations="Requires consistent tracking of session-RPE and GPS volume.",
                source_review_status="Gabbett Workload Framework (BJSM)",
                description="Structure microcycle load so that total volume does not increase by more than 10-15% week-over-week.",
                action_type="educational",
                category="training_modification",
                target_region="Weekly Training Volume",
                sets_and_reps="Maintain ACWR 0.8 - 1.3",
                frequency="Continuous weekly audit"
            ),
            "training_plyometric_deload": Recommendation(
                id="training_plyometric_deload",
                title="Plyometric Intensity Modification",
                triggering_finding="Stiff landing mechanics or knee valgus collapse.",
                rationale="Temporarily modifying high-stretch plyometrics allows motor retraining of deceleration mechanics under controlled forces.",
                intended_audience="Athletes exhibiting compromised landing mechanics.",
                limitations="Re-introduce reactive drop jumps once landing depth criteria are met.",
                source_review_status="Neuromuscular Conditioning Standards",
                description="Substitute maximal-effort reactive drop jumps with submaximal box step-offs into a controlled stick landing.",
                action_type="educational",
                category="training_modification",
                target_region="High-Impact Drills",
                sets_and_reps="50% intensity reduction for 2 microcycles",
                frequency="Next 1-2 training weeks"
            ),
            "training_velocity_cap_fatigue": Recommendation(
                id="training_velocity_cap_fatigue",
                title="Sprint Velocity Volume Cap",
                triggering_finding="Movement variability or late-trial kinematic drift.",
                rationale="Restricting maximum velocity exposures when acute fatigue is present protects the terminal swing hamstring elongation phase.",
                intended_audience="Speed-dependent athletes managing fixture congestion.",
                limitations="Does not apply to fresh athletes performing technical acceleration drills.",
                source_review_status="High Performance Track & Field Consensus",
                description="Limit high-speed sprint running to 85% maximum velocity when acute movement asymmetry or fatigue drift is identified.",
                action_type="educational",
                category="training_modification",
                target_region="High-Speed Running Volume",
                sets_and_reps="Cap top speed at 85-90%",
                frequency="During dense competition weeks"
            )
        }

    def generate_recommendations(
        self, 
        db: Session, 
        video_id: Optional[int] = None, 
        activity: str = "running",
        athlete_id: Optional[int] = None
    ) -> RecommendationResponse:
        """
        Module 9: Corrective Recommendation Engine
        Generates explainable, rule-based recommendations categorized across:
        1. Exercise Recommendations
        2. Mobility Improvement Suggestions
        3. Strengthening Recommendations
        4. Recovery Planning
        5. Training Modification Suggestions
        """
        recs: List[Recommendation] = []
        added_ids = set()
        
        def add_rec(rec_id: str):
            if rec_id not in added_ids and rec_id in self.library:
                recs.append(self.library[rec_id])
                added_ids.add(rec_id)

        # 0. Athlete context
        athlete = None
        if db:
            if video_id:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video and video.athlete_id:
                    athlete = db.query(AthleteProfile).filter(AthleteProfile.id == video.athlete_id).first()
            elif athlete_id:
                athlete = db.query(AthleteProfile).filter(AthleteProfile.id == athlete_id).first()

        # If no video is provided, supply baseline foundation recommendations
        if video_id is None:
            add_rec("mobility_hip_flexor")
            add_rec("strength_single_leg_rdl")
            add_rec("exercise_single_leg_balance")
            add_rec("recovery_active_flush")
            add_rec("review_training_load")

            return RecommendationResponse(
                video_id=None,
                athlete_id=athlete.id if athlete else None,
                recommendations=recs,
                exercise_recommendations=[r for r in recs if r.category == "exercise"],
                mobility_suggestions=[r for r in recs if r.category == "mobility"],
                strengthening_recommendations=[r for r in recs if r.category == "strengthening"],
                recovery_plan=[r for r in recs if r.category == "recovery"],
                training_modifications=[r for r in recs if r.category == "training_modification"]
            )

        # 1. Gather anomalies
        anomaly_data = anomaly_service.detect_anomalies(db, video_id)
        has_quality_issues = any(e.is_data_quality_issue for e in anomaly_data.events)
        
        # 2. Gather assessment
        assessment = get_assessment(db, video_id, activity)
        flags = assessment.get("flags", []) if assessment else []
        warnings = assessment.get("warnings", []) if assessment else []
        
        # -------------------------------------------------------------
        # Rule A: Conflicting or Insufficient Input
        # -------------------------------------------------------------
        if has_quality_issues or any("unreliable" in w.lower() for w in warnings):
            add_rec("data_quality_reassess")
            return RecommendationResponse(
                video_id=video_id, 
                athlete_id=athlete.id if athlete else None,
                recommendations=recs,
                exercise_recommendations=[],
                mobility_suggestions=[],
                strengthening_recommendations=[],
                recovery_plan=[],
                training_modifications=[r for r in recs if r.category == "training_modification"]
            )
            
        # -------------------------------------------------------------
        # Rule B: Trunk Lean
        # -------------------------------------------------------------
        has_trunk_lean = any("trunk lean" in f.lower() for f in flags) or any(e.metric == "trunk_lean" for e in anomaly_data.events)
        if has_trunk_lean:
            add_rec("coach_technique_trunk")
            add_rec("strength_mcgill_core_big3")
            add_rec("mobility_hip_flexor")
            
        # -------------------------------------------------------------
        # Rule C: Movement Asymmetry
        # -------------------------------------------------------------
        has_asymmetry = any("asymmetrical" in f.lower() or "symmetry" in f.lower() for f in flags) or any(e.metric == "knee_asymmetry" for e in anomaly_data.events)
        if has_asymmetry:
            add_rec("professional_assessment_asymmetry")
            add_rec("strength_single_leg_rdl")
            add_rec("exercise_single_leg_balance")
            
        # -------------------------------------------------------------
        # Rule D: Movement Variability / Motion Inconsistency
        # -------------------------------------------------------------
        has_variability = any(e.metric == "movement_variability" for e in anomaly_data.events)
        if has_variability:
            add_rec("review_training_load")
            add_rec("recovery_active_flush")
            add_rec("training_velocity_cap_fatigue")

        # -------------------------------------------------------------
        # Rule E: Dynamic Knee Valgus & Landing Mechanics
        # -------------------------------------------------------------
        has_valgus = any(e.metric == "knee_valgus" for e in anomaly_data.events)
        if has_valgus:
            add_rec("strength_glute_med_valgus")
            add_rec("exercise_jump_landing")
            add_rec("training_plyometric_deload")

        # -------------------------------------------------------------
        # Rule F: Activity-Specific Enhancements
        # -------------------------------------------------------------
        act = (activity or "running").lower()
        if act in ["jumping", "landing", "squatting"]:
            add_rec("exercise_jump_landing")
            add_rec("mobility_ankle_dorsiflexion")
            add_rec("exercise_squat_mechanics")
        elif act in ["running", "sprinting"]:
            add_rec("exercise_eccentric_hamstrings")
            add_rec("mobility_hip_flexor")
            add_rec("recovery_percussive_fascia")
        elif act == "throwing":
            add_rec("strength_rotator_cuff")
            add_rec("mobility_thoracic_extension")

        # -------------------------------------------------------------
        # Rule G: Athlete Context (Training Load & Systemic Recovery)
        # -------------------------------------------------------------
        if athlete and (athlete.training_load or "").lower() == "high":
            add_rec("training_acwr_regulation")
            add_rec("recovery_sleep_hydration")

        # Always ensure a balanced recovery strategy is included if any deficits are present
        if recs and not any(r.category == "recovery" for r in recs):
            add_rec("recovery_active_flush")

        # Group recommendations into their respective category lists
        exercise_recs = [r for r in recs if r.category == "exercise"]
        mobility_recs = [r for r in recs if r.category == "mobility"]
        strength_recs = [r for r in recs if r.category == "strengthening"]
        recovery_recs = [r for r in recs if r.category == "recovery"]
        training_mod_recs = [r for r in recs if r.category == "training_modification"]

        return RecommendationResponse(
            video_id=video_id,
            athlete_id=athlete.id if athlete else None,
            recommendations=recs,
            exercise_recommendations=exercise_recs,
            mobility_suggestions=mobility_recs,
            strengthening_recommendations=strength_recs,
            recovery_plan=recovery_recs,
            training_modifications=training_mod_recs
        )

recommendation_service = RecommendationEngine()
