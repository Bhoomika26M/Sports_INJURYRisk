"""
HTML Report Generator for Video Analysis

Generates comprehensive HTML reports with:
- Video information
- Processing information
- Athlete detection
- Bounding box/tracking
- Pose estimation
- Skeleton visualization
- Pose confidence
- Movement windows
- Joint angles
- ROM
- Symmetry
- Trunk lean
- Alignment
- Stability
- Smoothness
- Movement quality
- Early-vs-late movement changes
- Warnings
- Limitations
"""

from typing import Dict, Optional
from pathlib import Path
from datetime import datetime
import json


class HTMLReportGenerator:
    """Generate HTML reports for video analysis."""
    
    def __init__(self):
        self.template = self._get_template()
    
    def generate(
        self,
        video_data: Dict,
        pose_analysis: Dict,
        biomechanics: Optional[Dict] = None,
        movement_windows: Optional[list] = None,
        output_path: str = "report.html"
    ) -> str:
        """
        Generate HTML report.
        
        Args:
            video_data: Video metadata
            pose_analysis: Pose analysis results
            biomechanics: Biomechanical analysis results
            movement_windows: Movement window data
            output_path: Output HTML file path
        
        Returns:
            Path to generated HTML file
        """
        # Generate HTML content
        html_content = self._render_html(
            video_data,
            pose_analysis,
            biomechanics,
            movement_windows
        )
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_file)
    
    def _render_html(
        self,
        video_data: Dict,
        pose_analysis: Dict,
        biomechanics: Optional[Dict],
        movement_windows: Optional[list]
    ) -> str:
        """Render HTML content."""
        html = self.template
        
        # Replace placeholders
        html = html.replace("{{TIMESTAMP}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html = html.replace("{{VIDEO_FILENAME}}", video_data.get("original_filename", "N/A"))
        html = html.replace("{{ACTIVITY_TYPE}}", video_data.get("activity_type", "N/A"))
        html = html.replace("{{DURATION}}", f"{video_data.get('duration', 0):.2f}s")
        html = html.replace("{{RESOLUTION}}", f"{video_data.get('width', 0)}x{video_data.get('height', 0)}")
        html = html.replace("{{FPS}}", f"{video_data.get('fps', 0):.2f}")
        
        # Pose quality
        pose_quality = pose_analysis.get("pose_quality", {})
        html = html.replace("{{VALID_FRAMES}}", str(pose_quality.get("valid_frames", 0)))
        html = html.replace("{{QUALITY_PERCENTAGE}}", f"{pose_quality.get('quality_percentage', 0):.1f}%")
        html = html.replace("{{MEAN_CONFIDENCE}}", f"{pose_quality.get('mean_confidence', 0):.3f}")
        
        # Biomechanics
        if biomechanics:
            # ROM
            joint_angles = biomechanics.get("joint_angles", {})
            knee_left = joint_angles.get("knee_left", {})
            knee_right = joint_angles.get("knee_right", {})
            html = html.replace("{{LEFT_KNEE_ROM}}", f"{knee_left.get('rom', 0):.1f}°")
            html = html.replace("{{RIGHT_KNEE_ROM}}", f"{knee_right.get('rom', 0):.1f}°")
            
            # Symmetry
            symmetry = biomechanics.get("symmetry", {})
            knee_asymmetry = symmetry.get("knee_asymmetry", {})
            html = html.replace("{{KNEE_ASYMMETRY}}", f"{knee_asymmetry.get('mean_asymmetry', 0):.2f}°")
            
            # Trunk lean
            trunk_lean = biomechanics.get("trunk_lean", {})
            html = html.replace("{{TRUNK_LEAN_MEAN}}", f"{trunk_lean.get('mean', 0):.2f}°")
            html = html.replace("{{TRUNK_LEAN_MAX}}", f"{trunk_lean.get('max', 0):.2f}°")
            
            # Movement quality
            movement_quality = biomechanics.get("movement_quality", {})
            html = html.replace("{{MOVEMENT_QUALITY_SCORE}}", f"{movement_quality.get('score', 0):.1f}")
        else:
            html = html.replace("{{LEFT_KNEE_ROM}}", "N/A")
            html = html.replace("{{RIGHT_KNEE_ROM}}", "N/A")
            html = html.replace("{{KNEE_ASYMMETRY}}", "N/A")
            html = html.replace("{{TRUNK_LEAN_MEAN}}", "N/A")
            html = html.replace("{{TRUNK_LEAN_MAX}}", "N/A")
            html = html.replace("{{MOVEMENT_QUALITY_SCORE}}", "N/A")
        
        # Movement windows
        if movement_windows:
            windows_html = self._generate_movement_windows_table(movement_windows)
            html = html.replace("{{MOVEMENT_WINDOWS_TABLE}}", windows_html)
        else:
            html = html.replace("{{MOVEMENT_WINDOWS_TABLE}}", "<p>No movement windows detected.</p>")
        
        # Movement change analysis
        movement_change = pose_analysis.get("movement_change_analysis", {})
        if movement_change and movement_change.get("status") == "success":
            change_html = self._generate_movement_change_section(movement_change)
            html = html.replace("{{MOVEMENT_CHANGE_SECTION}}", change_html)
        else:
            html = html.replace("{{MOVEMENT_CHANGE_SECTION}}", "<p>Insufficient data for movement-change analysis (need at least 3 repetitions).</p>")
        
        return html
    
    def _generate_movement_windows_table(self, movement_windows: list) -> str:
        """Generate HTML table for movement windows."""
        rows = ""
        for window in movement_windows:
            rep_num = window.get("repetition_number") or window.get("jump_number") or window.get("stride_number") or "-"
            rows += f"""
            <tr>
                <td>{rep_num}</td>
                <td>{window.get('start_time', 0):.2f}s</td>
                <td>{window.get('end_time', 0):.2f}s</td>
                <td>{window.get('duration', 0):.2f}s</td>
                <td>{window.get('phase', 'N/A')}</td>
            </tr>
            """
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>Rep/Phase</th>
                    <th>Start (s)</th>
                    <th>End (s)</th>
                    <th>Duration (s)</th>
                    <th>Phase</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
    
    def _generate_movement_change_section(self, movement_change: Dict) -> str:
        """Generate HTML section for movement change analysis."""
        comparison = movement_change.get("early_vs_late_comparison", {})
        
        items = ""
        for metric, data in comparison.items():
            if data:
                items += f"""
                <li>
                    <strong>{metric.replace('_', ' ').title()}:</strong> 
                    {data.get('direction', 'N/A')} 
                    ({data.get('percentage_change', 0):.1f}%)
                    <br>
                    <small>Early: {data.get('early_mean', 0):.2f}, Late: {data.get('late_mean', 0):.2f}</small>
                </li>
                """
        
        return f"""
        <div class="movement-change">
            <h4>Early vs Late Comparison</h4>
            <p><strong>Total Repetitions:</strong> {movement_change.get('total_repetitions', 0)}</p>
            <p><strong>Early Count:</strong> {movement_change.get('early_count', 0)}</p>
            <p><strong>Late Count:</strong> {movement_change.get('late_count', 0)}</p>
            <ul>
                {items}
            </ul>
        </div>
        """
    
    def _get_template(self) -> str:
        """Get HTML template."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Analysis Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
            border-left: 4px solid #4CAF50;
            padding-left: 10px;
        }
        h3 {
            color: #666;
            margin-top: 20px;
        }
        .section {
            margin-bottom: 30px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .info-item {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
        }
        .info-label {
            font-weight: bold;
            color: #555;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .warning {
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
        }
        .disclaimer {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
        }
        .movement-change {
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Video Analysis Report</h1>
        <p><strong>Generated:</strong> {{TIMESTAMP}}</p>
        
        <div class="section">
            <h2>1. Video Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Filename:</div>
                    <div>{{VIDEO_FILENAME}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Activity:</div>
                    <div>{{ACTIVITY_TYPE}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Duration:</div>
                    <div>{{DURATION}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Resolution:</div>
                    <div>{{RESOLUTION}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">FPS:</div>
                    <div>{{FPS}}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>2. Processing Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Detector:</div>
                    <div>YOLO11n</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Tracker:</div>
                    <div>ByteTrack</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Pose Model:</div>
                    <div>MediaPipe BlazePose</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Keypoints:</div>
                    <div>33 landmarks</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>3. Athlete Detection</h2>
            <p>YOLO11n person detection with ByteTrack multi-object tracking.</p>
            <p>Primary athlete tracked with stable ID throughout video.</p>
        </div>
        
        <div class="section">
            <h2>4. Bounding Box and Tracking</h2>
            <p>Bounding box expansion with 15% padding for ROI cropping.</p>
            <p>Coordinate mapping from ROI back to original frame coordinates.</p>
        </div>
        
        <div class="section">
            <h2>5. Pose Estimation</h2>
            <p>MediaPipe BlazePose 33-point landmark detection on cropped ROI.</p>
            <p>Landmarks mapped to original frame coordinates.</p>
        </div>
        
        <div class="section">
            <h2>6. Skeleton</h2>
            <p>33-point BlazePose skeleton with anatomical connections.</p>
            <p>Includes face, upper body, lower body, hands, and feet landmarks.</p>
        </div>
        
        <div class="section">
            <h2>7. Pose Confidence</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Valid Frames:</div>
                    <div>{{VALID_FRAMES}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Quality:</div>
                    <div>{{QUALITY_PERCENTAGE}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Mean Confidence:</div>
                    <div>{{MEAN_CONFIDENCE}}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>8. Movement Windows</h2>
            {{MOVEMENT_WINDOWS_TABLE}}
        </div>
        
        <div class="section">
            <h2>9. Joint Angles</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Left Knee ROM:</div>
                    <div>{{LEFT_KNEE_ROM}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Right Knee ROM:</div>
                    <div>{{RIGHT_KNEE_ROM}}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>10. Range of Motion (ROM)</h2>
            <p>ROM calculated from joint angle min/max across all frames.</p>
        </div>
        
        <div class="section">
            <h2>11. Symmetry</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Knee Asymmetry:</div>
                    <div>{{KNEE_ASYMMETRY}}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>12. Trunk Lean</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Mean:</div>
                    <div>{{TRUNK_LEAN_MEAN}}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Max:</div>
                    <div>{{TRUNK_LEAN_MAX}}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>13. Alignment</h2>
            <p>Alignment score based on trunk lean deviation from vertical.</p>
        </div>
        
        <div class="section">
            <h2>14. Stability</h2>
            <p>Stability calculated from variance of joint angles across frames.</p>
        </div>
        
        <div class="section">
            <h2>15. Smoothness</h2>
            <p>Smoothness calculated from variance of successive angle differences.</p>
        </div>
        
        <div class="section">
            <h2>16. Movement Quality</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Overall Score:</div>
                    <div>{{MOVEMENT_QUALITY_SCORE}}/100</div>
                </div>
            </div>
            <p>Components: confidence, symmetry, alignment, stability, ROM, smoothness</p>
        </div>
        
        <div class="section">
            <h2>17. Early-vs-Late Movement Changes</h2>
            {{MOVEMENT_CHANGE_SECTION}}
        </div>
        
        <div class="warning">
            <h3>18. Warnings</h3>
            <ul>
                <li>This analysis is based on 2D video without camera calibration</li>
                <li>Depth information is estimated, not measured</li>
                <li>Lighting conditions may affect pose estimation accuracy</li>
                <li>Occluded body parts may have lower confidence</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>19. Limitations</h2>
            <ul>
                <li>No 3D depth information (requires multi-camera setup)</li>
                <li>No ground reaction force measurement</li>
                <li>No EMG data for muscle activation</li>
                <li>Camera angle affects biomechanical measurements</li>
                <li>Individual anatomical differences not accounted for</li>
            </ul>
        </div>
        
        <div class="disclaimer">
            <h3>Medical Disclaimer</h3>
            <p><strong>This system provides biomechanical movement analysis and is not a medical diagnosis.</strong></p>
            <p>Results should be interpreted by qualified medical professionals. This tool is for informational purposes only and should not be used as a substitute for professional medical advice, diagnosis, or treatment.</p>
        </div>
    </div>
</body>
</html>
        """
