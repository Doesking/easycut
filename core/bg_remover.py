"""
EasyCut 背景去除 / 抠图模块
支持：人物/物体抠图 → 透明 PNG
基于 rembg (u2net)
"""
import numpy as np, cv2, logging
from typing import Optional
from pathlib import Path
import io, base64, os

logger = logging.getLogger(__name__)


class BackgroundRemover:
    def __init__(self):
        self._session = None

    def _load_model(self):
        if self._session is None:
            from rembg import new_session
            self._session = new_session("u2net")

    def remove_background(self, image: np.ndarray) -> np.ndarray:
        """去除背景，返回 RGBA (透明底)"""
        self._load_model()
        from rembg import remove as rembg_remove

        # 转 BGR → RGB → bytes → rembg → bytes → RGBA numpy
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = rembg_remove(rgb, session=self._session, only_mask=False)

        if result.shape[-1] == 4:
            return cv2.cvtColor(result, cv2.COLOR_RGBA2BGRA)
        else:
            # 只有3通道，补alpha
            alpha = np.ones((result.shape[0], result.shape[1], 1), dtype=np.uint8) * 255
            rgba = np.concatenate([result, alpha], axis=2)
            return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)

    def remove_background_white(self, image: np.ndarray) -> np.ndarray:
        """去除纯白背景，保留非白色区域"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # 膨胀 + 模糊边缘
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        mask = cv2.GaussianBlur(mask, (3, 3), 1)

        # 转为 RGBA
        mask_norm = mask.astype(np.float32) / 255.0
        bgra = np.dstack([image, (mask_norm * 255).astype(np.uint8)])
        return bgra

    def remove_logo_background(self, image: np.ndarray) -> np.ndarray:
        """专门用于 Logo 抠图：去除所有背景，输出透明底"""
        # 先用 rembg，如果效果不好，回退到颜色阈值法
        try:
            return self.remove_background(image)
        except Exception:
            pass

        # 回退：基于边缘检测的简单抠图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)

        # 找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask, contours, -1, 255, -1)

        # 膨胀填充
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.GaussianBlur(mask, (5, 5), 2)

        alpha = mask.astype(np.float32) / 255.0
        bgra = np.dstack([image, (alpha * 255).astype(np.uint8)])
        return bgra

    def image_to_png_bytes(self, rgba: np.ndarray) -> bytes:
        """RGBA numpy → PNG bytes"""
        rgb = cv2.cvtColor(rgba, cv2.COLOR_BGRA2RGBA)
        _, buf = cv2.imencode(".png", rgb)
        return buf.tobytes()

    def image_to_base64(self, rgba: np.ndarray) -> str:
        """RGBA numpy → base64 data URL"""
        png_bytes = self.image_to_png_bytes(rgba)
        return base64.b64encode(png_bytes).decode()
