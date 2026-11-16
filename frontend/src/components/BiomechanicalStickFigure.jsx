import React, { useState, useMemo } from 'react';

/**
 * Skeletal segment pairs based on MediaPipe BlazePose landmarks
 */
const SKELETON_BONES = [
  ['left_shoulder', 'right_shoulder'],
  ['left_shoulder', 'left_elbow'],
  ['left_elbow', 'left_wrist'],
  ['right_shoulder', 'right_elbow'],
  ['right_elbow', 'right_wrist'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
  ['left_hip', 'right_hip'],
  ['left_hip', 'left_knee'],
  ['left_knee', 'left_ankle'],
  ['right_hip', 'right_knee'],
  ['right_knee', 'right_ankle'],
];

/**
 * BiomechanicalStickFigure:
 * 1. Checks if athlete's real pose keypoint data is available for this video run.
 * 2. If available, renders the athlete's ACTUAL extracted pose skeleton at peak deviation frame,
 *    and next to it renders the mathematically corrected posture.
 * 3. If real keypoint data is not passed/available, falls back gracefully to standard biomechanical archetypes.
 */
export const BiomechanicalStickFigure = ({ finding, activityType = 'squat', keypointsData = null }) => {
  const [activeTab, setActiveTab] = useState('visual'); // 'visual' | 'cues'
  const issue = (finding.issue || '').toLowerCase();
  const tag = (finding.risk_tag || '').toLowerCase();
  const clinicalTerm = (finding.scientific_term || '').toLowerCase();

  // Pattern detection
  let pattern = 'knee_asymmetry';
  if (issue.includes('asymmetry') || tag.includes('asymmetry')) {
    pattern = 'knee_asymmetry';
  } else if (issue.includes('trunk') || tag.includes('lumbar') || clinicalTerm.includes('lumbar')) {
    pattern = 'excessive_trunk_lean';
  } else if (issue.includes('rom') || tag.includes('limited_rom') || issue.includes('range of motion')) {
    pattern = 'shallow_knee_rom';
  } else if (issue.includes('smoothness') || issue.includes('jerk') || tag.includes('movement_control')) {
    pattern = 'valgus_or_control';
  }

  // Find a representative frame from the athlete's actual keypoint sequence (e.g. peak squat depth or midpoint)
  const realPoseFrame = useMemo(() => {
    if (!keypointsData || !Array.isArray(keypointsData) || keypointsData.length === 0) {
      return null;
    }
    // Pick the frame near lowest knee Y (lowest position = deepest squat point) or middle frame
    let deepestFrame = null;
    let maxKneeY = -1;

    for (const frame of keypointsData) {
      const kps = frame.keypoints || [];
      const leftKnee = kps.find(k => k.name === 'left_knee');
      const rightKnee = kps.find(k => k.name === 'right_knee');
      if (leftKnee && rightKnee) {
        const avgKneeY = (leftKnee.y + rightKnee.y) / 2;
        if (avgKneeY > maxKneeY) {
          maxKneeY = avgKneeY;
          deepestFrame = frame;
        }
      }
    }

    return deepestFrame || keypointsData[Math.floor(keypointsData.length / 2)] || null;
  }, [keypointsData]);

  // Convert normalized [0, 1] keypoints into SVG canvas viewBox coordinates (200x240)
  const realSkeleton = useMemo(() => {
    if (!realPoseFrame || !realPoseFrame.keypoints) return null;
    const kpMap = {};
    const kps = realPoseFrame.keypoints;

    // Find bounding box to center the athlete in the SVG canvas
    let minX = 1, maxX = 0, minY = 1, maxY = 0;
    kps.forEach(kp => {
      if (kp.confidence > 0.15) {
        minX = Math.min(minX, kp.x);
        maxX = Math.max(maxX, kp.x);
        minY = Math.min(minY, kp.y);
        maxY = Math.max(maxY, kp.y);
      }
    });

    const bodyWidth = Math.max(0.1, maxX - minX);
    const bodyHeight = Math.max(0.1, maxY - minY);

    // Scale to fit comfortably in 200x240 SVG with padding
    const targetW = 140;
    const targetH = 190;
    const scale = Math.min(targetW / bodyWidth, targetH / bodyHeight);
    const offsetX = (200 - bodyWidth * scale) / 2 - minX * scale;
    const offsetY = (240 - bodyHeight * scale) / 2 - minY * scale;

    kps.forEach(kp => {
      kpMap[kp.name] = {
        x: kp.x * scale + offsetX,
        y: kp.y * scale + offsetY,
        confidence: kp.confidence,
      };
    });

    return kpMap;
  }, [realPoseFrame]);

  // Generate the corrected pose by mathematically aligning the faulty joints
  const correctedSkeleton = useMemo(() => {
    if (!realSkeleton) return null;
    const corrected = JSON.parse(JSON.stringify(realSkeleton));

    if (pattern === 'knee_asymmetry' && corrected.left_knee && corrected.right_knee && corrected.left_hip && corrected.right_hip) {
      // Symmetrize knee depths and hips
      const avgKneeY = (corrected.left_knee.y + corrected.right_knee.y) / 2;
      const avgHipY = (corrected.left_hip.y + corrected.right_hip.y) / 2;
      corrected.left_knee.y = avgKneeY;
      corrected.right_knee.y = avgKneeY;
      corrected.left_hip.y = avgHipY;
      corrected.right_hip.y = avgHipY;
    } else if (pattern === 'excessive_trunk_lean' && corrected.left_shoulder && corrected.right_shoulder && corrected.left_hip && corrected.right_hip) {
      // Bring torso more upright (move shoulders posterior/upward relative to hips)
      const avgHipX = (corrected.left_hip.x + corrected.right_hip.x) / 2;
      const avgShoulderX = (corrected.left_shoulder.x + corrected.right_shoulder.x) / 2;
      const leanDiff = avgShoulderX - avgHipX;
      // Reduce forward offset by 60%
      corrected.left_shoulder.x -= leanDiff * 0.6;
      corrected.right_shoulder.x -= leanDiff * 0.6;
      corrected.left_shoulder.y -= 12;
      corrected.right_shoulder.y -= 12;
      if (corrected.nose) {
        corrected.nose.x -= leanDiff * 0.6;
        corrected.nose.y -= 12;
      }
    } else if (pattern === 'shallow_knee_rom' && corrected.left_knee && corrected.right_knee && corrected.left_hip && corrected.right_hip) {
      // Sink hips deeper into knee line
      corrected.left_hip.y += 18;
      corrected.right_hip.y += 18;
    }

    return corrected;
  }, [realSkeleton, pattern]);

  // Configurations for each pattern
  const PATTERN_CONFIGS = {
    knee_asymmetry: {
      title: 'Knee Asymmetry / Asymmetric Weight Shift',
      coachSummary: 'Athlete drops heavier into dominant limb, causing unequal knee flexion angles and shearing forces.',
      athleteTakeaway: 'Avoid favoring one leg. Distribute weight 50/50 through both mid-feet.',
      flawLabel: 'Flawed: Uneven Knee Depth (Asymmetric Loading)',
      fixLabel: 'Correct: Symmetrical Bilateral Knee Tracking',
      flawDetails: 'Left & right knees flex at different depths, placing asymmetric shear on patellofemoral cartilage.',
      fixDetails: 'Both knees flex uniformly in sync, keeping knees aligned over the 2nd toe and pelvis level.',
      renderFlaw: () => (
        <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
          <line x1="20" y1="210" x2="180" y2="210" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="4 4" />
          <circle cx="106" cy="40" r="14" fill="#F87171" stroke="#BD4006" strokeWidth="2.5" />
          <line x1="106" y1="54" x2="108" y2="105" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="82" y1="102" x2="134" y2="108" stroke="#BD4006" strokeWidth="5" strokeLinecap="round" />
          <line x1="106" y1="70" x2="68" y2="88" stroke="#64748B" strokeWidth="3" strokeLinecap="round" />
          <line x1="106" y1="70" x2="148" y2="76" stroke="#64748B" strokeWidth="3" strokeLinecap="round" />
          <line x1="84" y1="103" x2="72" y2="148" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="72" y1="148" x2="65" y2="210" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="65" y1="210" x2="50" y2="210" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="132" y1="108" x2="152" y2="155" stroke="#EF4444" strokeWidth="4" strokeLinecap="round" />
          <line x1="152" y1="155" x2="140" y2="210" stroke="#EF4444" strokeWidth="4" strokeLinecap="round" />
          <line x1="140" y1="210" x2="158" y2="210" stroke="#EF4444" strokeWidth="4" strokeLinecap="round" />
          <circle cx="152" cy="155" r="9" fill="#FEE2E2" stroke="#EF4444" strokeWidth="3" className="animate-pulse" />
          <text x="100" y="185" fill="#B91C1C" fontSize="10" fontWeight="bold" textAnchor="middle">
            Overloaded Knee (+Δθ)
          </text>
          <text x="100" y="197" fill="#6B7280" fontSize="9" textAnchor="middle">
            Uneven Pelvic Tilt
          </text>
        </svg>
      ),
      renderFix: () => (
        <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
          <line x1="20" y1="210" x2="180" y2="210" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="4 4" />
          <circle cx="100" cy="40" r="14" fill="#A7F3D0" stroke="#059669" strokeWidth="2.5" />
          <line x1="100" y1="54" x2="100" y2="105" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="75" y1="105" x2="125" y2="105" stroke="#059669" strokeWidth="5" strokeLinecap="round" />
          <line x1="100" y1="68" x2="65" y2="82" stroke="#64748B" strokeWidth="3" strokeLinecap="round" />
          <line x1="100" y1="68" x2="135" y2="82" stroke="#64748B" strokeWidth="3" strokeLinecap="round" />
          <line x1="75" y1="105" x2="62" y2="152" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="62" y1="152" x2="70" y2="210" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="70" y1="210" x2="54" y2="210" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="125" y1="105" x2="138" y2="152" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="138" y1="152" x2="130" y2="210" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="130" y1="210" x2="146" y2="210" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <circle cx="62" cy="152" r="7" fill="#D1FAE5" stroke="#10B981" strokeWidth="2.5" />
          <circle cx="138" cy="152" r="7" fill="#D1FAE5" stroke="#10B981" strokeWidth="2.5" />
          <line x1="62" y1="152" x2="138" y2="152" stroke="#10B981" strokeWidth="1.5" strokeDasharray="3 3" />
          <text x="100" y="148" fill="#047857" fontSize="9" fontWeight="bold" textAnchor="middle">
            Level Hip & Knee Planes
          </text>
          <text x="100" y="185" fill="#047857" fontSize="10" fontWeight="bold" textAnchor="middle">
            50% / 50% Even Force
          </text>
        </svg>
      ),
    },
    excessive_trunk_lean: {
      title: 'Excessive Forward Trunk Lean',
      coachSummary: 'Torso tilts beyond recommended hip hinge limit, drastically multiplying lumbar spine shear moment.',
      athleteTakeaway: 'Keep chest tall. Imagine a spotlight on your chest pointing straight ahead, not down at the floor.',
      flawLabel: 'Flawed: Torso Collapsed Forward (>45° Lean)',
      fixLabel: 'Correct: Upright Torso with Neutral Spine (<30°)',
      flawDetails: 'The center of mass moves far anterior to the lumbar spine, shifting demand from glutes to the lower back erector spinae.',
      fixDetails: 'Thoracic extension maintained, hips sink backward while torso stays parallel to shins, distributing work to hip extensors.',
      renderFlaw: () => (
        <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
          <line x1="20" y1="210" x2="180" y2="210" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="4 4" />
          <line x1="120" y1="210" x2="135" y2="160" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="135" y1="160" x2="90" y2="145" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="90" y1="145" x2="40" y2="105" stroke="#EF4444" strokeWidth="5" strokeLinecap="round" />
          <circle cx="30" cy="98" r="13" fill="#FEE2E2" stroke="#BD4006" strokeWidth="2.5" />
          <line x1="52" y1="115" x2="52" y2="165" stroke="#64748B" strokeWidth="3" strokeLinecap="round" />
          <circle cx="90" cy="145" r="10" fill="#FEE2E2" stroke="#EF4444" strokeWidth="3" className="animate-pulse" />
          <text x="105" y="100" fill="#B91C1C" fontSize="10" fontWeight="bold" textAnchor="middle">
            High Lumbar Shear (L4-S1)
          </text>
          <text x="105" y="114" fill="#6B7280" fontSize="9" textAnchor="middle">
            Trunk angle &gt; norm
          </text>
        </svg>
      ),
      renderFix: () => (
        <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
          <line x1="20" y1="210" x2="180" y2="210" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="4 4" />
          <line x1="115" y1="210" x2="128" y2="155" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="128" y1="155" x2="80" y2="145" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="80" y1="145" x2="68" y2="85" stroke="#059669" strokeWidth="4.5" strokeLinecap="round" />
          <circle cx="64" cy="72" r="13" fill="#A7F3D0" stroke="#059669" strokeWidth="2.5" />
          <line x1="72" y1="100" x2="110" y2="105" stroke="#64748B" strokeWidth="3" strokeLinecap="round" />
          <text x="125" y="85" fill="#047857" fontSize="10" fontWeight="bold" textAnchor="middle">
            Proud Chest & Neutral Spine
          </text>
          <text x="125" y="100" fill="#047857" fontSize="9" textAnchor="middle">
            Glutes/Core Absorbing Load
          </text>
        </svg>
      ),
    },
    shallow_knee_rom: {
      title: 'Restricted Knee Flexion Range of Motion (ROM)',
      coachSummary: 'Insufficient depth prevents full eccentric activation of quads & glutes, causing abrupt braking forces.',
      athleteTakeaway: 'Sit back deeper into your hips until thighs reach at least parallel (approx. 90° knee angle).',
      flawLabel: 'Flawed: Partial Depth / Incomplete Joint Articulation',
      fixLabel: 'Correct: Full Functional Depth (Thigh Parallel)',
      flawDetails: 'Stopping high concentrates patellar tendon stress during rapid deceleration and inhibits gluteus maximus recruitment.',
      fixDetails: 'Controlled descent through full available range of motion safely distributes contact pressures across the tibiofemoral joint.',
      renderFlaw: () => (
        <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
          <line x1="20" y1="210" x2="180" y2="210" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="4 4" />
          <line x1="110" y1="210" x2="118" y2="145" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="118" y1="145" x2="88" y2="120" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="88" y1="120" x2="78" y2="65" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <circle cx="76" cy="52" r="13" fill="#FEE2E2" stroke="#BD4006" strokeWidth="2.5" />
          <circle cx="118" cy="145" r="9" fill="#FEE2E2" stroke="#EF4444" strokeWidth="3" />
          <text x="110" y="175" fill="#B91C1C" fontSize="10" fontWeight="bold" textAnchor="middle">
            Restricted ROM (&lt;70°)
          </text>
          <text x="110" y="190" fill="#6B7280" fontSize="9" textAnchor="middle">
            Patellar tendon shock loading
          </text>
        </svg>
      ),
      renderFix: () => (
        <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
          <line x1="20" y1="210" x2="180" y2="210" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="4 4" />
          <line x1="115" y1="210" x2="128" y2="162" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="128" y1="162" x2="82" y2="160" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="82" y1="160" x2="72" y2="100" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <circle cx="70" cy="86" r="13" fill="#A7F3D0" stroke="#059669" strokeWidth="2.5" />
          <circle cx="128" cy="162" r="7" fill="#D1FAE5" stroke="#10B981" strokeWidth="2.5" />
          <text x="110" y="145" fill="#047857" fontSize="10" fontWeight="bold" textAnchor="middle">
            Parallel Depth (90°-110°)
          </text>
          <text x="110" y="185" fill="#047857" fontSize="9" textAnchor="middle">
            Full Glute & Quad Recruitment
          </text>
        </svg>
      ),
    },
    valgus_or_control: {
      title: 'Movement Control / Jerky Transitions',
      coachSummary: 'Velocity spikes and erratic acceleration indicate poor eccentric deceleration and stabilizing control.',
      athleteTakeaway: 'Count 3 seconds down on the descent. Control the weight throughout the entire movement.',
      flawLabel: 'Flawed: Uncontrolled Wobble / Jerky Deceleration',
      fixLabel: 'Correct: Smooth Tempo with Controlled Eccentric Arc',
      flawDetails: 'Inability of hip stabilizers to control velocity shifts mechanical shock directly onto ligaments.',
      fixDetails: 'Steady acceleration profiles allow continuous muscular tension and protect connective tissues.',
      renderFlaw: () => (
        <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
          <line x1="20" y1="210" x2="180" y2="210" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="4 4" />
          <circle cx="100" cy="40" r="13" fill="#FEE2E2" stroke="#BD4006" strokeWidth="2.5" />
          <line x1="100" y1="53" x2="100" y2="105" stroke="#BD4006" strokeWidth="4" strokeLinecap="round" />
          <line x1="80" y1="105" x2="120" y2="105" stroke="#BD4006" strokeWidth="5" />
          <line x1="80" y1="105" x2="96" y2="155" stroke="#EF4444" strokeWidth="4" strokeLinecap="round" />
          <line x1="96" y1="155" x2="68" y2="210" stroke="#EF4444" strokeWidth="4" strokeLinecap="round" />
          <line x1="120" y1="105" x2="104" y2="155" stroke="#EF4444" strokeWidth="4" strokeLinecap="round" />
          <line x1="104" y1="155" x2="132" y2="210" stroke="#EF4444" strokeWidth="4" strokeLinecap="round" />
          <text x="100" y="180" fill="#B91C1C" fontSize="10" fontWeight="bold" textAnchor="middle">
            Erratic Deceleration
          </text>
        </svg>
      ),
      renderFix: () => (
        <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
          <line x1="20" y1="210" x2="180" y2="210" stroke="#CBD5E1" strokeWidth="3" strokeDasharray="4 4" />
          <circle cx="100" cy="40" r="13" fill="#A7F3D0" stroke="#059669" strokeWidth="2.5" />
          <line x1="100" y1="53" x2="100" y2="105" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="80" y1="105" x2="120" y2="105" stroke="#059669" strokeWidth="5" />
          <line x1="80" y1="105" x2="68" y2="155" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="68" y1="155" x2="68" y2="210" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="120" y1="105" x2="132" y2="155" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <line x1="132" y1="155" x2="132" y2="210" stroke="#059669" strokeWidth="4" strokeLinecap="round" />
          <text x="100" y="175" fill="#047857" fontSize="10" fontWeight="bold" textAnchor="middle">
            Constant Muscular Control
          </text>
        </svg>
      ),
    },
  };

  const currentCfg = PATTERN_CONFIGS[pattern] || PATTERN_CONFIGS.knee_asymmetry;

  // Render a skeleton from an actual landmark dictionary
  const renderRealPoseSVG = (skel, isFlawed = true) => {
    if (!skel) return null;
    const strokeColor = isFlawed ? '#BD4006' : '#059669';
    const highlightColor = isFlawed ? '#EF4444' : '#10B981';

    return (
      <svg viewBox="0 0 200 240" className="w-full h-48 sm:h-56">
        <line x1="20" y1="215" x2="180" y2="215" stroke="#E2E8F0" strokeWidth="2.5" strokeDasharray="4 4" />
        
        {/* Draw Bones */}
        {SKELETON_BONES.map(([j1, j2], i) => {
          const p1 = skel[j1];
          const p2 = skel[j2];
          if (!p1 || !p2) return null;

          const isAtRisk = isFlawed && (j1.includes('knee') || j2.includes('knee') || j1.includes('hip') || j2.includes('hip'));

          return (
            <line
              key={i}
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke={isAtRisk ? highlightColor : strokeColor}
              strokeWidth={isAtRisk ? 4 : 3}
              strokeLinecap="round"
            />
          );
        })}

        {/* Draw Head */}
        {skel.nose && (
          <circle
            cx={skel.nose.x}
            cy={skel.nose.y}
            r="12"
            fill={isFlawed ? '#FFDBCF' : '#D1FAE5'}
            stroke={strokeColor}
            strokeWidth="2.5"
          />
        )}

        {/* Draw Joint Dots */}
        {Object.entries(skel).map(([name, pt], i) => {
          if (name === 'nose') return null;
          const isDanger = isFlawed && name.includes('knee');
          return (
            <circle
              key={i}
              cx={pt.x}
              cy={pt.y}
              r={isDanger ? 6 : 4}
              fill={isDanger ? '#FEE2E2' : '#FFFFFF'}
              stroke={isDanger ? '#EF4444' : strokeColor}
              strokeWidth={isDanger ? 3 : 2}
              className={isDanger ? 'animate-pulse' : ''}
            />
          );
        })}

        <text x="100" y="232" fill={isFlawed ? '#BD4006' : '#047857'} fontSize="10" fontWeight="bold" textAnchor="middle">
          {isFlawed ? 'Athlete Frame Skeleton' : 'Corrected Postural Vector'}
        </text>
      </svg>
    );
  };

  return (
    <div className="mt-4 p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-100 gap-2">
        <div className="flex items-center gap-2">
          <span className="p-1.5 bg-[#FFDBCF] text-[#BD4006] rounded-md">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </span>
          <div>
            <h4 className="font-semibold text-text-primary text-sm">{currentCfg.title}</h4>
            <p className="text-xs text-text-secondary">
              {realSkeleton ? 'Extracted from athlete frame with real joint coordinates' : 'Biomechanical Diagnostic & Correction Blueprint'}
            </p>
          </div>
        </div>
        
        {/* Toggle between Coach & Athlete cues */}
        <div className="flex bg-gray-100 p-0.5 rounded-lg text-xs font-medium self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('visual')}
            className={`px-3 py-1 rounded-md transition-all ${
              activeTab === 'visual' ? 'bg-white text-text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Visual Diagram
          </button>
          <button
            onClick={() => setActiveTab('cues')}
            className={`px-3 py-1 rounded-md transition-all ${
              activeTab === 'cues' ? 'bg-white text-text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Quick Coaching Cues
          </button>
        </div>
      </div>

      {activeTab === 'visual' ? (
        <div className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Flawed Stick Figure */}
            <div className="p-3 bg-red-50/60 rounded-xl border border-red-100 flex flex-col items-center">
              <div className="w-full flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-red-700 bg-red-100 px-2 py-0.5 rounded">
                  {realSkeleton ? 'Your Movement (Detected)' : 'Identified Risk / Flaw'}
                </span>
                <span className="text-xs text-red-600 font-medium">Excessive Strain</span>
              </div>
              <div className="w-full bg-white rounded-lg p-2 border border-red-100/80 shadow-inner flex items-center justify-center">
                {realSkeleton ? renderRealPoseSVG(realSkeleton, true) : currentCfg.renderFlaw()}
              </div>
              <p className="text-xs text-gray-700 mt-2 text-center font-medium">
                {currentCfg.flawLabel}
              </p>
              <p className="text-xs text-gray-500 mt-1 text-center">
                {currentCfg.flawDetails}
              </p>
            </div>

            {/* Corrective Stick Figure */}
            <div className="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100 flex flex-col items-center">
              <div className="w-full flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
                  Corrective Alignment
                </span>
                <span className="text-xs text-emerald-600 font-medium">Optimal Safety</span>
              </div>
              <div className="w-full bg-white rounded-lg p-2 border border-emerald-100/80 shadow-inner flex items-center justify-center">
                {correctedSkeleton ? renderRealPoseSVG(correctedSkeleton, false) : currentCfg.renderFix()}
              </div>
              <p className="text-xs text-gray-700 mt-2 text-center font-medium">
                {currentCfg.fixLabel}
              </p>
              <p className="text-xs text-gray-500 mt-1 text-center">
                {currentCfg.fixDetails}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div className="p-3 bg-orange-50/80 border border-orange-100 rounded-lg">
            <span className="text-xs font-bold text-orange-950 uppercase tracking-wide block mb-1">
              For the Coach (Technical Anatomy)
            </span>
            <p className="text-xs text-orange-950 leading-relaxed">
              {currentCfg.coachSummary}
            </p>
          </div>
          <div className="p-3 bg-emerald-50/80 border border-emerald-100 rounded-lg">
            <span className="text-xs font-bold text-emerald-950 uppercase tracking-wide block mb-1">
              For the Athlete (Simple Mindset Cue)
            </span>
            <p className="text-xs text-emerald-950 leading-relaxed font-medium">
              "{currentCfg.athleteTakeaway}"
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default BiomechanicalStickFigure;
