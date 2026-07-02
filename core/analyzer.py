"""
视频分析模块：场景检测、关键帧提取、画面特征分析
纯 FFmpeg + OpenCV 驱动，无需 GUI 软件
"""
import subprocess
import json
import logging
import tempfile
from dataclasses import dataclass, field
from typing import List, Tuple
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SceneInfo:
    """场景信息"""
    source_path: str
    scene_index: int
    start_time: float
    end_time: float
    duration: float
    avg_brightness: float = 0
    avg_saturation: float = 0
    motion_score: float = 0
    face_count: int = 0
    dominant_colors: List[Tuple] = field(default_factory=list)
    avg_audio_level: float = 0
    has_speech: bool = False
    scene_type: str = "unknown"
    thumbnail_path: str = ""
    category: str = "unknown"
    category_confidence: float = 0
    quality_score: float = 0
    relevance_score: float = 0

    @property
    def midpoint(self) -> float:
        return self.start_time + self.duration / 2


class VideoAnalyzer:
    """视频分析器"""

    def __init__(self, config: dict):
        self.threshold = config.get("threshold", 27.0)
        self.min_scene_length = config.get("min_scene_length", 2.0)
        self.max_scene_length = config.get("max_scene_length", 30.0)

    def analyze(self, video_path: str) -> List[SceneInfo]:
        logger.info(f"分析视频: {video_path}")
        video_info = self._get_video_info(video_path)
        logger.info(f"  分辨率: {video_info['width']}x{video_info['height']}, "
                     f"时长: {video_info['duration']:.1f}s, FPS: {video_info['fps']}")

        boundaries = self._detect_scenes(video_path, video_info)
        logger.info(f"  检测到 {len(boundaries)} 个场景边界")

        scenes = []
        for i, (start, end) in enumerate(boundaries):
            scene = SceneInfo(
                source_path=video_path, scene_index=i,
                start_time=start, end_time=end, duration=end - start
            )
            self._extract_visual_features(video_path, scene, video_info)
            self._extract_audio_features(video_path, scene)
            scene.thumbnail_path = self._extract_thumbnail(video_path, scene, i)
            scenes.append(scene)

        valid = [s for s in scenes if self.min_scene_length <= s.duration <= self.max_scene_length]
        logger.info(f"  有效场景: {len(valid)}/{len(scenes)}")
        return valid

    def _get_video_info(self, video_path: str) -> dict:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
               "-show_format", "-show_streams", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        vs = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), {})
        fps_str = vs.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30
        else:
            fps = float(fps_str)
        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "width": int(vs.get("width", 1920)),
            "height": int(vs.get("height", 1080)),
            "fps": fps,
        }

    def _detect_scenes(self, video_path: str, video_info: dict) -> List[Tuple[float, float]]:
        """FFmpeg scene filter 检测场景切换"""
        import re
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"select='gt(scene,{self.threshold / 100})',showinfo",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr

        cut_points = {0.0, video_info["duration"]}
        for line in output.split('\n'):
            m = re.search(r"pts_time:(\d+\.?\d*)", line)
            if m:
                cut_points.add(float(m.group(1)))

        sorted_pts = sorted(cut_points)
        boundaries, current = [], 0.0
        for pt in sorted_pts[1:]:
            if pt - current >= self.min_scene_length:
                boundaries.append((current, pt))
                current = pt

        if video_info["duration"] - current > self.min_scene_length:
            boundaries.append((current, video_info["duration"]))

        return boundaries

    def _extract_visual_features(self, video_path: str, scene: SceneInfo, video_info: dict):
        """OpenCV 采样分析视觉特征"""
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(scene.midpoint * fps))

        bright_vals, sat_vals, motion_vals = [], [], []
        prev_gray = None

        for _ in range(5):
            ret, frame = cap.read()
            if not ret:
                break
            small = cv2.resize(frame, (320, 180))
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            bright_vals.append(np.mean(hsv[:, :, 2]))
            sat_vals.append(np.mean(hsv[:, :, 1]))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                motion_vals.append(np.mean(cv2.absdiff(gray, prev_gray)) / 255.0)
            prev_gray = gray

        cap.release()

        scene.avg_brightness = float(np.mean(bright_vals)) if bright_vals else 0
        scene.avg_saturation = float(np.mean(sat_vals)) if sat_vals else 0
        scene.motion_score = float(np.mean(motion_vals)) if motion_vals else 0

        # 室内外判断
        if scene.avg_brightness > 140 and scene.avg_saturation > 80:
            scene.scene_type = "outdoor"
        elif scene.avg_brightness > 100 and scene.motion_score > 0.15:
            scene.scene_type = "outdoor"
        else:
            scene.scene_type = "indoor"

        # 人脸检测
        if scene.avg_brightness > 50:
            self._detect_faces(video_path, scene, int(scene.midpoint * fps))

    def _detect_faces(self, video_path: str, scene: SceneInfo, frame_pos: int):
        import cv2
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = cap.read()
        cap.release()
        if ret:
            small = cv2.resize(frame, (640, 360))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(30, 30))
            scene.face_count = len(faces)

    def _extract_audio_features(self, video_path: str, scene: SceneInfo):
        import re
        cmd = [
            "ffmpeg", "-v", "quiet", "-i", video_path,
            "-ss", str(scene.start_time), "-t", str(scene.duration),
            "-af", "volumedetect", "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        m = re.search(r"mean_volume:\s*(-?\d+\.?\d*)", output)
        if m:
            scene.avg_audio_level = float(m.group(1))
        scene.has_speech = scene.avg_audio_level > -35

    def _extract_thumbnail(self, video_path: str, scene: SceneInfo, index: int) -> str:
        thumb_dir = Path(tempfile.gettempdir()) / "soe_editor_thumbs"
        thumb_dir.mkdir(exist_ok=True)
        thumb_path = str(thumb_dir / f"scene_{index:04d}.jpg")
        subprocess.run([
            "ffmpeg", "-v", "quiet", "-ss", str(scene.midpoint),
            "-i", video_path, "-vframes", "1", "-q:v", "5",
            "-s", "320x180", thumb_path, "-y"
        ], capture_output=True)
        return thumb_path
