import os
import sys
import shutil
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app.db.database import SessionLocal
from app.models.athlete import Athlete
from app.models.video import Video, ProcessingStatus
from app.models.pose_analysis import PoseAnalysis
from app.models.biomechanical_analysis import BiomechanicalAnalysis
from app.models.analysis_snapshot import AnalysisSnapshot

def run():
    db = SessionLocal()
    try:
        bench_athlete = db.query(Athlete).filter(Athlete.athlete_id == 'BENCHMARK-GOLD').first()
        if not bench_athlete:
            bench_athlete = Athlete(
                athlete_id='BENCHMARK-GOLD',
                sport_type='Benchmark / Reference Standard',
                position='Gold Standard Form',
                age=24,
                height=180.0,
                weight=75.0,
                injury_history='Optimal clinical kinematics form with symmetric loading and stable alignment.',
                training_load='Reference standard'
            )
            db.add(bench_athlete)
            db.commit()
            db.refresh(bench_athlete)
        print(f"Benchmark Athlete: {bench_athlete.id} ({bench_athlete.athlete_id})")

        # 1. Benchmark Lunges Video
        v_lunges = db.query(Video).filter(Video.activity_type == 'lunges', Video.processing_status == ProcessingStatus.COMPLETED).first()
        if v_lunges:
            fn = 'benchmark_gold_lunges.mp4'
            sp = os.path.join('uploads', fn)
            if not os.path.exists(sp) and os.path.exists(v_lunges.storage_path):
                shutil.copyfile(v_lunges.storage_path, sp)
            ann_src = os.path.join(os.path.dirname(v_lunges.storage_path), 'annotated_' + os.path.basename(v_lunges.storage_path))
            ann_dst = os.path.join('uploads', 'annotated_' + fn)
            if os.path.exists(ann_src) and not os.path.exists(ann_dst):
                shutil.copyfile(ann_src, ann_dst)

            b_video = db.query(Video).filter(Video.filename == fn).first()
            if not b_video:
                b_video = Video(
                    athlete_id=bench_athlete.id,
                    uploaded_by=v_lunges.uploaded_by,
                    filename=fn,
                    original_filename='Gold_Standard_Lunges_Form.mp4',
                    storage_path=sp,
                    activity_type='lunges',
                    file_size=v_lunges.file_size,
                    duration=v_lunges.duration,
                    fps=v_lunges.fps,
                    width=v_lunges.width,
                    height=v_lunges.height,
                    processing_status=ProcessingStatus.COMPLETED
                )
                db.add(b_video)
                db.commit()
                db.refresh(b_video)

                src_pa = db.query(PoseAnalysis).filter(PoseAnalysis.video_id == v_lunges.id).first()
                if src_pa:
                    b_pa = PoseAnalysis(
                        video_id=b_video.id,
                        pose_model=src_pa.pose_model,
                        pose_model_version=src_pa.pose_model_version,
                        analysis_version=src_pa.analysis_version,
                        total_frames=src_pa.total_frames,
                        processed_frames=src_pa.processed_frames,
                        frame_sample_rate=src_pa.frame_sample_rate,
                        pose_quality={'valid_frames': src_pa.total_frames, 'mean_confidence': 0.96},
                        keypoints_data=src_pa.keypoints_data,
                        tracking_data=src_pa.tracking_data,
                        roi_data=src_pa.roi_data,
                        movement_change_analysis=src_pa.movement_change_analysis,
                        normalized_skeleton=src_pa.normalized_skeleton
                    )
                    db.add(b_pa)
                    db.commit()
                    db.refresh(b_pa)

                    src_ba = db.query(BiomechanicalAnalysis).filter(BiomechanicalAnalysis.pose_analysis_id == src_pa.id).first()
                    ideal_mq = dict(src_ba.movement_quality or {})
                    ideal_mq['score'] = 93.5
                    ideal_sym = {'knee_asymmetry': {'mean_asymmetry': 3.1, 'max_asymmetry': 5.2}, 'hip_asymmetry': {'mean_asymmetry': 2.4, 'max_asymmetry': 4.1}}
                    ideal_tl = {'mean': -4.5, 'max': -7.5, 'min': -2.0, 'std': 1.1}
                    
                    b_ba = BiomechanicalAnalysis(
                        pose_analysis_id=b_pa.id,
                        joint_angles=src_ba.joint_angles,
                        rom=src_ba.rom,
                        symmetry=ideal_sym,
                        knee_alignment={'valgus_deviation': 1.1, 'status': 'optimal'},
                        trunk_lean=ideal_tl,
                        hip_stability={'pelvic_tilt_delta': 1.8},
                        balance={'cop_stability': 96.0},
                        velocity=src_ba.velocity,
                        acceleration=src_ba.acceleration,
                        movement_quality=ideal_mq
                    )
                    db.add(b_ba)
                    db.commit()

                    snap = AnalysisSnapshot(
                        athlete_id=bench_athlete.id,
                        video_id=b_video.id,
                        pose_analysis_id=b_pa.id,
                        activity_type='lunges',
                        sequence_index=1,
                        performed_at=datetime.utcnow(),
                        overall_risk_score=9.2,
                        risk_level='low',
                        findings_count=0,
                        metrics={
                            'risk_score': 9.2,
                            'findings_count': 0,
                            'movement_quality': 93.5,
                            'symmetry_score': 95.0,
                            'knee_asymmetry': 5.2,
                            'trunk_lean_max': 7.5,
                            'mean_pose_confidence': 0.96
                        }
                    )
                    db.add(snap)
                    db.commit()
            print(f"Benchmark Lunges Video ID: {b_video.id}")

        # 2. Benchmark Running Video
        v_running = db.query(Video).filter(Video.activity_type == 'running', Video.processing_status == ProcessingStatus.COMPLETED).first()
        if v_running:
            fn2 = 'benchmark_gold_running.mp4'
            sp2 = os.path.join('uploads', fn2)
            if not os.path.exists(sp2) and os.path.exists(v_running.storage_path):
                shutil.copyfile(v_running.storage_path, sp2)
            ann_src2 = os.path.join(os.path.dirname(v_running.storage_path), 'annotated_' + os.path.basename(v_running.storage_path))
            ann_dst2 = os.path.join('uploads', 'annotated_' + fn2)
            if os.path.exists(ann_src2) and not os.path.exists(ann_dst2):
                shutil.copyfile(ann_src2, ann_dst2)

            b_video2 = db.query(Video).filter(Video.filename == fn2).first()
            if not b_video2:
                b_video2 = Video(
                    athlete_id=bench_athlete.id,
                    uploaded_by=v_running.uploaded_by,
                    filename=fn2,
                    original_filename='Gold_Standard_Running_Form.mp4',
                    storage_path=sp2,
                    activity_type='running',
                    file_size=v_running.file_size,
                    duration=v_running.duration,
                    fps=v_running.fps,
                    width=v_running.width,
                    height=v_running.height,
                    processing_status=ProcessingStatus.COMPLETED
                )
                db.add(b_video2)
                db.commit()
                db.refresh(b_video2)

                src_pa2 = db.query(PoseAnalysis).filter(PoseAnalysis.video_id == v_running.id).first()
                if src_pa2:
                    b_pa2 = PoseAnalysis(
                        video_id=b_video2.id,
                        pose_model=src_pa2.pose_model,
                        pose_model_version=src_pa2.pose_model_version,
                        analysis_version=src_pa2.analysis_version,
                        total_frames=src_pa2.total_frames,
                        processed_frames=src_pa2.processed_frames,
                        frame_sample_rate=src_pa2.frame_sample_rate,
                        pose_quality={'valid_frames': src_pa2.total_frames, 'mean_confidence': 0.97},
                        keypoints_data=src_pa2.keypoints_data,
                        tracking_data=src_pa2.tracking_data,
                        roi_data=src_pa2.roi_data,
                        movement_change_analysis=src_pa2.movement_change_analysis,
                        normalized_skeleton=src_pa2.normalized_skeleton
                    )
                    db.add(b_pa2)
                    db.commit()
                    db.refresh(b_pa2)

                    src_ba2 = db.query(BiomechanicalAnalysis).filter(BiomechanicalAnalysis.pose_analysis_id == src_pa2.id).first()
                    ideal_mq2 = dict(src_ba2.movement_quality or {})
                    ideal_mq2['score'] = 96.0
                    ideal_sym2 = {'knee_asymmetry': {'mean_asymmetry': 2.4, 'max_asymmetry': 4.1}, 'hip_asymmetry': {'mean_asymmetry': 1.9, 'max_asymmetry': 3.2}}
                    ideal_tl2 = {'mean': -3.2, 'max': -5.1, 'min': -1.5, 'std': 0.9}

                    b_ba2 = BiomechanicalAnalysis(
                        pose_analysis_id=b_pa2.id,
                        joint_angles=src_ba2.joint_angles,
                        rom=src_ba2.rom,
                        symmetry=ideal_sym2,
                        knee_alignment={'valgus_deviation': 0.8, 'status': 'optimal'},
                        trunk_lean=ideal_tl2,
                        hip_stability={'pelvic_tilt_delta': 1.2},
                        balance={'cop_stability': 97.5},
                        velocity=src_ba2.velocity,
                        acceleration=src_ba2.acceleration,
                        movement_quality=ideal_mq2
                    )
                    db.add(b_ba2)
                    db.commit()

                    snap2 = AnalysisSnapshot(
                        athlete_id=bench_athlete.id,
                        video_id=b_video2.id,
                        pose_analysis_id=b_pa2.id,
                        activity_type='running',
                        sequence_index=1,
                        performed_at=datetime.utcnow(),
                        overall_risk_score=7.8,
                        risk_level='low',
                        findings_count=0,
                        metrics={
                            'risk_score': 7.8,
                            'findings_count': 0,
                            'movement_quality': 96.0,
                            'symmetry_score': 97.0,
                            'knee_asymmetry': 4.1,
                            'trunk_lean_max': 5.1,
                            'mean_pose_confidence': 0.97
                        }
                    )
                    db.add(snap2)
                    db.commit()
            print(f"Benchmark Running Video ID: {b_video2.id}")
        print("Benchmark seeding completed successfully!")
    finally:
        db.close()

if __name__ == '__main__':
    run()
