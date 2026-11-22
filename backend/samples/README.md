# Local Reference Movement Library & Video Specifications

You can place your own `.mp4` video files directly into this directory (`backend/samples/`) for movement analysis in the Kinematix application.

The app's **Movement Library** selector will automatically discover any video files placed here, displaying the activity type, file size, and motion characteristics.

---

## Bundled Reference Clips (Provenances & Specifications)

The following baseline reference clips are generated programmatically via `backend/app/services/sample_generator.py` using OpenCV primitives and transcoded with `imageio-ffmpeg` using the H.264 codec (`libx264`, `yuv420p`, `-movflags +faststart`).

> [!NOTE]
> **Asset Disclosure**:
> These clips are **computer-modeled movement simulations**. They are not recordings of real athletes, contain no personal identifiable information (PII), and do not use copyrighted commercial broadcasts. They are provided for reference movement inspection and testing the computer vision pipeline.

| Filename | Activity Choice | Kinematic Motion Pattern | Format | Size | Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `synthetic_deep_squat_baseline.mp4` | **Deep Squat** | Symmetrical baseline squat with neutral knee alignment and controlled descent. | H.264 MP4 | ~27 KB | Synthetic (Self-generated) |
| `synthetic_deep_squat_valgus.mp4` | **Deep Squat** | Deep squat showing increased knee-inward movement (dynamic valgus collapse) during descent. | H.264 MP4 | ~31 KB | Synthetic (Self-generated) |
| `synthetic_drop_jump_baseline.mp4` | **Drop Jump** | Box drop and landing with stable neutral knee tracking throughout ground contact. | H.264 MP4 | ~45 KB | Synthetic (Self-generated) |
| `synthetic_drop_jump_valgus.mp4` | **Drop Jump** | Box drop and landing with pronounced medial knee collapse (dynamic valgus) upon deceleration. | H.264 MP4 | ~47 KB | Synthetic (Self-generated) |
| `synthetic_drop_jump.mp4` | **Drop Jump** | Box drop, deceleration landing with dynamic medial knee valgus collapse, vertical rebound. | H.264 MP4 | ~53 KB | Synthetic (Self-generated) |
| `synthetic_side_cut.mp4` | **Side Cut** | Approach, sharp unilateral deceleration plant step, lateral weight shift, trunk tilt. | H.264 MP4 | ~55 KB | Synthetic (Self-generated) |
| `synthetic_deep_squat.mp4` | **Deep Squat** | Symmetrical bilateral descent past 90° knee flexion, forward trunk tilt, controlled ascent. | H.264 MP4 | ~46 KB | Synthetic (Self-generated) |
| `synthetic_running.mp4` | **Running** | Cyclical running gait, alternating knee drive, reciprocating arm swing, ground contact. | H.264 MP4 | ~93 KB | Synthetic (Self-generated) |
| `synthetic_sprinting.mp4` | **Sprinting** | High-velocity sprint mechanics, aggressive forward torso lean (24°), high knee drive pump. | H.264 MP4 | ~132 KB | Synthetic (Self-generated) |
| `synthetic_throwing.mp4` | **Throwing** | Kinetic chain overhead throw: windup on back foot, step forward, trunk rotation & follow-through. | H.264 MP4 | ~40 KB | Synthetic (Self-generated) |
| `marcus_jump_landing.mp4` | **Drop Jump** | Drop jump baseline test clip with knee valgus flag. | H.264 MP4 | ~482 KB | Synthetic (Self-generated) |

---

## Recommended Video Format & Recording Guidelines for Real Uploads

When uploading your own sports recordings for analysis:

1. **Video Container & Codec**:
   - Short `.mp4`, `.mov`, or `.webm` files encoded with the **H.264** video codec (`libx264` with `yuv420p` pixel format).
   - Standard frame rate: **30 FPS** or **60 FPS**.
2. **Camera Placement & Stability**:
   - Use a stationary camera or tripod mounted at hip height (approximately 1.0 m above the ground).
   - Position perpendicular to the primary plane of movement (frontal plane for valgus/asymmetry; sagittal plane for squat depth and trunk flexion).
3. **Framing & Athlete Visibility**:
   - The athlete's **entire body** must remain fully in frame from head to toe throughout the trial (including takeoff, flight, landing, and deceleration).
4. **Lighting & Contrast**:
   - Bright, uniform lighting with minimal shadows.
   - High visual contrast between the athlete's clothing and the gym/field background.
5. **Single Subject**:
   - Only one athlete moving in frame to prevent landmark tracking confusion.
6. **Clip Duration**:
   - Keep trials concise: **2 to 8 seconds** focused on the specific drill repetition.
7. **Supported Movement Selection**:
   - Always choose the corresponding movement label (`Drop Jump`, `Side Cut`, `Deep Squat`, `Running`, `Sprinting`, `Throwing`) before uploading.
