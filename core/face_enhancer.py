"""
EasyCut 人脸美颜增强模块
支持：瘦脸、收下颌、美颜、大眼
基于 mediapipe Face Mesh
"""
import cv2, numpy as np, logging
from typing import Optional, Tuple, List
from pathlib import Path

logger = logging.getLogger(__name__)

# mediapipe 人脸关键点索引
JAWLINE = list(range(0, 17))       # 下颌线
LEFT_EYE = list(range(33, 42))     # 左眼
RIGHT_EYE = list(range(42, 51))    # 右眼
FACE_OVAL = list(range(0, 17)) + list(range(17, 27))  # 脸轮廓
NOSE_BRIDGE = list(range(27, 31))
CHIN = list(range(5, 12))          # 下巴


class FaceEnhancer:
    def __init__(self):
        self._mp_face = None
        self._mp_draw = None
        self._landmarker = None  # 缓存 landmarker

    def _load_mediapipe(self):
        if self._mp_face is None:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            self._mp = mp
            self._mp_tasks = python
            self._mp_vision = vision

    def detect_faces(self, image: np.ndarray) -> List[dict]:
        """检测所有人脸，返回关键点列表"""
        self._load_mediapipe()
        h, w = image.shape[:2]
        results = []

        # 缓存 landmarker 避免重复初始化
        if self._landmarker is None:
            import os
            model_path = os.environ.get('MEDIAPIPE_MODEL_PATH', '/tmp/mediapipe_face_landmarker.task')
            base_options = self._mp_tasks.BaseOptions(
                model_asset_path=model_path
            )
            options = self._mp_vision.FaceLandmarkerOptions(
                base_options=base_options,
                num_faces=10,
                running_mode=self._mp_vision.RunningMode.IMAGE,
            )
            self._landmarker = self._mp_vision.FaceLandmarker.create_from_options(options)

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        detection_result = self._landmarker.detect(mp_image)

        for face_lm in detection_result.face_landmarks:
            pts = [(int(p.x * w), int(p.y * h)) for p in face_lm]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            results.append({
                "landmarks": pts,
                "bbox": bbox,
                "jawline": [pts[i] for i in JAWLINE],
                "chin": [pts[i] for i in CHIN],
                "left_eye": [pts[i] for i in LEFT_EYE],
                "right_eye": [pts[i] for i in RIGHT_EYE],
                "face_oval": [pts[i] for i in FACE_OVAL],
            })

        return results

    def slim_face(self, image: np.ndarray, strength: float = 0.3) -> np.ndarray:
        """瘦脸：向内收缩下颌区域"""
        faces = self.detect_faces(image)
        if not faces:
            return image

        result = image.copy()
        h, w = image.shape[:2]

        for face in faces:
            jaw = np.array(face["jawline"], dtype=np.float32)
            chin = np.array(face["chin"], dtype=np.float32)
            oval = np.array(face["face_oval"], dtype=np.float32)

            # 计算脸部中心
            cx, cy = np.mean(oval, axis=0)

            # 对下颌线每个点向内收缩
            for pt in jaw:
                dx, dy = pt - np.array([cx, cy])
                dist = np.sqrt(dx**2 + dy**2)
                if dist > 0:
                    new_pt = np.array([cx, cy]) + (dx / dist) * dist * (1.0 - strength * 0.15)
                    # 用 warpAffine 做局部变形
                    self._local_warp(result, image, pt, tuple(new_pt.astype(int)), radius=30)

        return result

    def slim_jawline(self, image: np.ndarray, strength: float = 0.4) -> np.ndarray:
        """收下颌线：提升下颌线条，使脸型更V"""
        faces = self.detect_faces(image)
        if not faces:
            return image

        result = image.copy()
        for face in faces:
            chin = np.array(face["chin"], dtype=np.float32)
            cx, cy = np.mean(chin, axis=0)

            for pt in chin:
                # 向上向内移动
                dx = (pt[0] - cx) * 0.3
                dy = -abs(pt[1] - cy) * strength
                new_pt = (int(pt[0] - dx), int(pt[1] + dy))
                self._local_warp(result, image, tuple(pt), new_pt, radius=25)

        return result

    def smooth_skin(self, image: np.ndarray, strength: int = 10) -> np.ndarray:
        """磨皮美颜：双边滤波"""
        return cv2.bilateralFilter(image, strength, 30, 30)

    def enlarge_eyes(self, image: np.ndarray, scale: float = 1.1) -> np.ndarray:
        """大眼：眼睛区域放大"""
        faces = self.detect_faces(image)
        if not faces:
            return image

        result = image.copy()
        for face in faces:
            for eye_pts in [face["left_eye"], face["right_eye"]]:
                xs = [p[0] for p in eye_pts]
                ys = [p[1] for p in eye_pts]
                cx, cy = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
                w_e = max(xs) - min(xs)
                h_e = max(ys) - min(ys)

                # 提取眼睛区域并放大
                pad = 10
                x1 = max(0, cx - w_e // 2 - pad)
                y1 = max(0, cy - h_e // 2 - pad)
                x2 = min(result.shape[1], cx + w_e // 2 + pad)
                y2 = min(result.shape[0], cy + h_e // 2 + pad)

                eye_roi = result[y1:y2, x1:x2]
                if eye_roi.size == 0:
                    continue

                new_w = int(eye_roi.shape[1] * scale)
                new_h = int(eye_roi.shape[0] * scale)
                scaled = cv2.resize(eye_roi, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

                # 居中裁剪
                sx = max(0, (new_w - eye_roi.shape[1]) // 2)
                sy = max(0, (new_h - eye_roi.shape[0]) // 2)
                scaled = scaled[sy:sy+eye_roi.shape[0], sx:sx+eye_roi.shape[1]]

                if scaled.shape[:2] == eye_roi.shape[:2]:
                    result[y1:y2, x1:x2] = scaled

        return result

    def enhance_portrait(self, image: np.ndarray, options: dict = None) -> np.ndarray:
        """一键人像增强"""
        opts = options or {}
        result = image.copy()

        strength = opts.get("slim_face", 0)
        if strength > 0:
            result = self.slim_face(result, strength)

        strength = opts.get("slim_jawline", 0)
        if strength > 0:
            result = self.slim_jawline(result, strength)

        strength = opts.get("smooth_skin", 0)
        if strength > 0:
            result = self.smooth_skin(result, strength)

        scale = opts.get("enlarge_eyes", 0)
        if scale > 0:
            result = self.enlarge_eyes(result, scale)

        return result

    def _local_warp(self, dst: np.ndarray, src: np.ndarray, src_pt: tuple,
                    dst_pt: tuple, radius: int = 30):
        """局部变形：在 src_pt 附近区域做平移"""
        h, w = dst.shape[:2]
        x1 = max(0, min(src_pt[0], dst_pt[0]) - radius)
        y1 = max(0, min(src_pt[1], dst_pt[1]) - radius)
        x2 = min(w, max(src_pt[0], dst_pt[0]) + radius)
        y2 = min(h, max(src_pt[1], dst_pt[1]) + radius)

        if x2 <= x1 or y2 <= y1:
            return

        roi_src = src[y1:y2, x1:x2]
        roi_dst = dst[y1:y2, x1:x2]

        sx = src_pt[0] - x1
        sy = src_pt[1] - y1
        dx = dst_pt[0] - x1
        dy = dst_pt[1] - y1

        map_x, map_y = np.meshgrid(
            np.arange(roi_dst.shape[1], dtype=np.float32),
            np.arange(roi_dst.shape[0], dtype=np.float32)
        )
        map_x += (dx - sx) * 0.3
        map_y += (dy - sy) * 0.3

        try:
            warped = cv2.remap(roi_src, map_x, map_y, cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
            mask = np.zeros_like(roi_dst, dtype=np.float32)
            cv2.circle(mask, (radius, radius), radius, (1, 1, 1), -1)
            mask = cv2.GaussianBlur(mask, (21, 21), 10)
            dst[y1:y2, x1:x2] = (warped * mask + roi_dst * (1 - mask)).astype(np.uint8)
        except cv2.error:
            pass
