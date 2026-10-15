import cv2
import tempfile
import os
import json
import pandas as pd
from src.tracker import StudentTracker
from src.detector import ObjectDetector
from src.pose_analyzer import PoseAnalyzer
from src.rules_engine import ExamRulesEngine
from src import i18n

class SurveillancePipeline:
    def __init__(self, obj_detector=None, pose_analyzer=None):
        self.detector = obj_detector or ObjectDetector(model_name="yolov8n.pt")
        self.pose_analyzer = pose_analyzer or PoseAnalyzer(model_name="yolov8n-pose.pt")

    def process_video(self, video_path, mode="Classroom / Exam Hall (CCTV)", frame_skip=3, progress_callback=None):
        if not video_path or not os.path.exists(video_path):
            return None, [], "No valid video file provided.", [], {}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, [], "Failed to open video file.", [], {}

        self.pose_analyzer.reset_baselines()

        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

        target_w = min(1280, orig_w)
        target_h = int(orig_h * (target_w / orig_w))
        target_w = target_w - (target_w % 2)
        target_h = target_h - (target_h % 2)

        temp_out = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        output_path = temp_out.name
        temp_out.close()

        effective_fps = max(10, int(orig_fps / frame_skip))
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        writer = cv2.VideoWriter(output_path, fourcc, effective_fps, (target_w, target_h))

        tracker = StudentTracker(max_distance=160.0, init_window_sec=2.5)
        rules_engine = ExamRulesEngine(mode=mode, fps=effective_fps)

        frame_idx = 0
        processed_count = 0
        snapshots = []
        snapshot_dir = tempfile.mkdtemp(prefix="exam_evidence_")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            if frame_idx % frame_skip != 0:
                continue

            processed_count += 1
            timestamp = frame_idx / orig_fps

            if progress_callback and total_frames > 0:
                pct = min(0.98, frame_idx / total_frames)
                progress_callback(pct, desc=f"正在分析视频流... {int(pct * 100)}%")

            if (orig_w, orig_h) != (target_w, target_h):
                frame = cv2.resize(frame, (target_w, target_h))

            person_boxes, prohibited_objects = self.detector.detect(frame)
            tracked_students = tracker.update(person_boxes, current_timestamp=timestamp)
            student_objects = self.detector.match_objects_to_students(tracked_students, prohibited_objects)
            student_poses = self.pose_analyzer.analyze(frame, tracked_students)
            student_statuses, new_incidents = rules_engine.evaluate_frame(
                timestamp, tracked_students, student_poses, student_objects
            )

            self._render_overlay(frame, tracked_students, prohibited_objects, student_statuses, timestamp, mode)

            if new_incidents:
                for inc in new_incidents:
                    snap_path = os.path.join(snapshot_dir, f"incident_{len(snapshots)+1}_{int(timestamp*10)}ds.jpg")
                    cv2.imwrite(snap_path, frame)
                    caption = (
                        f"{i18n.translate_student_id(inc['student_id'])} | "
                        f"{i18n.translate_violation(inc['violation'])} @ {inc['timestamp']}"
                    )
                    snapshots.append((snap_path, caption))

            writer.write(frame)

        cap.release()
        writer.release()

        incidents = rules_engine.confirmed_incidents
        total_students = len(tracker.tracks)
        flagged_students = len(set(inc["student_id"] for inc in incidents))
        clean_students = max(0, total_students - flagged_students)
        integrity = int((clean_students / max(1, total_students)) * 100)

        stats = {
            "total_students": total_students,
            "flagged_incidents": len(incidents),
            "clean_students": clean_students,
            "integrity_score": f"{integrity}%",
            "processed_frames": processed_count
        }

        summary_text = (
            f"Surveillance Audit Complete: Tracked {total_students} candidates over {processed_count} frames. "
            f"Logged {len(incidents)} confirmed violations ({flagged_students} suspect candidate(s), {clean_students} clean). "
            f"Room Integrity Index: {integrity}%."
        )

        return output_path, incidents, summary_text, snapshots, stats

    def _render_overlay(self, frame, students, prohibited_objects, statuses, timestamp, mode):
        h, w, _ = frame.shape

        cv2.rectangle(frame, (0, 0), (w, 42), (15, 23, 42), -1)
        cv2.putText(frame, f"AEGIS AI SURVEILLANCE  |  {mode}  |  TIME: {timestamp:05.1f}s  |  CANDIDATES: {len(students)}",
                    (16, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (241, 245, 249), 2)

        for obj in prohibited_objects:
            ox1, oy1, ox2, oy2 = obj["box"]
            cv2.rectangle(frame, (ox1, oy1), (ox2, oy2), (37, 99, 235), 2)
            cv2.putText(frame, f"! {obj['label']} ({int(obj['conf']*100)}%)",
                        (ox1, max(15, oy1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (37, 99, 235), 2)

        for s in students:
            sid = s["id"]
            x1, y1, x2, y2 = s["box"]
            st = statuses.get(sid, {"status": "NORMAL", "color": (16, 185, 129), "active_violations": []})

            color = st["color"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            label_text = s["label"]
            if st["status"] == "CHEATING_FLAGGED":
                label_text += " [VIOLATION]"
            elif st["status"] == "SUSPICIOUS":
                label_text += " [SUSPICIOUS]"

            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 2)
            cv2.rectangle(frame, (x1, max(0, y1 - th - 10)), (x1 + tw + 10, y1), color, -1)
            cv2.putText(frame, label_text, (x1 + 5, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2)

            if st["active_violations"]:
                v_text = " | ".join(st["active_violations"])
                (vw, vh), _ = cv2.getTextSize(v_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 2)
                cv2.rectangle(frame, (x1, y2), (x1 + vw + 10, y2 + vh + 8), (0, 0, 220), -1)
                cv2.putText(frame, v_text, (x1 + 5, y2 + vh + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 2)
