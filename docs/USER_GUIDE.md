# AthletiQ User & Clinical Workflow Guide

AthletiQ provides specialized dashboards and analytical views tailored for each user role in sports medicine and athletic performance.

---

## 1. Athlete User Guide

### 1.1 Account Setup & Profile Completion
1. Sign up using **Email & Password** or **Sign in with Google**.
2. Select the **Athlete** role.
3. Complete your biometric profile under **Profile**:
   - Sport type (e.g., Soccer, Basketball, Track & Field)
   - Position / Event
   - Height (cm) & Weight (kg)
   - Historical injuries (e.g., ACL sprain, hamstring strain)
   - Weekly training load & sessions

### 1.2 Video Upload & Movement Screening Guidelines
To obtain the highest kinematic accuracy from computer vision pose estimation:
- **Camera Position**: Mount the camera at approximately waist height (1.0m to 1.2m off the ground).
- **Distance**: Stand 3 to 4 meters away so your entire body (head to toes) is continuously in frame throughout the entire movement.
- **Lighting**: Ensure bright, diffuse lighting; avoid strong backlighting from windows or spotlights.
- **Clothing**: Wear contrast-colored athletic apparel (e.g., dark shorts/leggings against light backgrounds) so joint boundaries are distinct.
- **Movement Type Selection**: Select the movement pattern matching your drill:
  - `Squatting`: Bilateral knee flexion, valgus collapse, hip symmetry.
  - `Landing`: Countermovement jump or drop landing shock absorption.
  - `Running Gait` / `Sprinting`: Heel-strike, stride frequency, pelvic tilt.
  - `Cutting`: Lateral deceleration and plant-and-cut knee abduction angles.

### 1.3 Interpreting Your Screening Results
- **Overall Injury Risk Score**: 
  - **0% - 30% (Low)**: Biomechanical patterns are within safe clinical ranges.
  - **31% - 60% (Moderate)**: Mild kinematic asymmetry or early signs of joint strain.
  - **61% - 100% (High)**: High risk of non-contact ligament injury; corrective drills strongly recommended.
- **Corrective Drill Prescription**: Follow the step-by-step neuromuscular exercises provided in your dashboard to correct form and strengthen stabilizing muscle groups.

---

## 2. Coach User Guide

### 2.1 Squad Roster Management
- Navigate to **Athletes** to view your squad roster.
- Browse unassigned athletes and click **Add to My Squad** to connect them with your profile.
- Filter athletes by sport or injury risk status.

### 2.2 Squad Injury Risk Surveillance
- Monitor squad health badges at a glance.
- Click into an individual athlete to review their video trials, anomaly timeline, and kinematic progress over time.

### 2.3 Team Excel Export
- In the top right corner of the dashboard, click **Export Team Analysis (Excel)**.
- Downloads a 4-sheet formatted workbook:
  - **Squad Overview**: Athletes, sports, and overall risk levels.
  - **Injury Risk Matrix**: Detailed metric breakdown across all athletes.
  - **Kinematic Averages**: Peak valgus, trunk lean, and symmetry indices.
  - **Action Items**: Prescribed corrective drills for each athlete.

---

## 3. Physiotherapist & Sports Scientist Guide

### 3.1 Kinematic Analysis & Anomaly Diagnostics
- Access high-resolution angle-time kinematic curves for:
  - **Frontal Plane Knee Valgus**: Identifies dynamic medial collapse linked with ACL strain.
  - **Sagittal Plane Trunk Lean**: Evaluates lumbar shear and core stability.
  - **Bilateral Limb Asymmetry**: Measures percentage discrepancy between left and right limb loading.
- Anomaly markers on the video scrubber allow frame-by-frame inspection of peak stress events.

### 3.2 Clinical PDF Assessment Export
- Click **Export Report (PDF)** to generate a print-ready clinical document.
- Report includes:
  - Institutional header and clinician metadata.
  - Patient biometric history and injury timeline.
  - Kinematic metrics compared against normative clinical ranges (FIFA / ACSM).
  - Diagnostic narrative and physician signature section.

---

## 4. Administrator Guide

### 4.1 System & User Role Management
- Navigate to **User Roles** (`/admin/users`) to review all registered accounts across the platform.
- Reassign roles between Athlete, Coach, Physiotherapist, Sports Scientist, and Administrator.

### 4.2 System Health & Storage Monitoring
- System metrics available at `/api/v1/health/metrics`:
  - Process uptime and active worker count.
  - Upload storage allocation and disk space remaining.
  - Database table counts (users, athletes, videos, notifications).
