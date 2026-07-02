"""
照片智能修图引擎
- 类型识别: 人像/风光/美食/夜景/微距/建筑
- 风格预设: 按类别组织 30+ 预设
- 自然语言解析: 文字描述 → 修图参数
- 手动调节: 亮度/对比度/饱和度/色温/锐度/降噪

全本地 CPU 运算，使用 PIL + OpenCV
"""
import io
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw

logger = logging.getLogger("PhotoEnhancer")


class PhotoType(Enum):
    PORTRAIT = "portrait"          # 人像
    LANDSCAPE = "landscape"        # 风光
    FOOD = "food"                  # 美食
    NIGHT = "night"                # 夜景
    MACRO = "macro"                # 微距/特写
    ARCHITECTURE = "architecture"  # 建筑
    GENERAL = "general"            # 通用


@dataclass
class EnhanceParams:
    """修图参数"""
    brightness: float = 1.0       # 0.5-2.0
    contrast: float = 1.0         # 0.5-2.0
    saturation: float = 1.0       # 0-2.0
    sharpness: float = 1.0        # 0.5-3.0
    warmth: float = 0.0           # -100 to 100
    tint: float = 0.0             # -100 to 100 (green-magenta)
    highlights: float = 0.0       # -100 to 100
    shadows: float = 0.0          # -100 to 100
    denoise: float = 0.0          # 0-100
    vignette: float = 0.0         # 0-100
    grain: float = 0.0            # 0-100
    # 人像专用
    skin_smooth: float = 0.0      # 0-100
    face_brighten: float = 0.0    # 0-100
    eye_enhance: float = 0.0      # 0-100
    # 风光专用
    dehaze: float = 0.0           # 0-100
    sky_enhance: float = 0.0      # 0-100
    greenery: float = 0.0         # 0-100


# ═══════════════════════════════════════════
# 风格预设库（按类别组织）
# ═══════════════════════════════════════════

PRESET_LIBRARY = {
    "人像": {
        "自然通透": EnhanceParams(
            brightness=1.08, contrast=1.05, saturation=1.02,
            sharpness=1.15, skin_smooth=30, face_brighten=15,
            warmth=5, highlights=-10, shadows=10
        ),
        "日系清新": EnhanceParams(
            brightness=1.18, contrast=0.90, saturation=0.85,
            sharpness=1.05, skin_smooth=40, face_brighten=25,
            warmth=-5, highlights=20, shadows=15, vignette=10
        ),
        "复古胶片": EnhanceParams(
            brightness=0.95, contrast=1.15, saturation=0.90,
            sharpness=0.90, warmth=25, grain=15, vignette=25,
            highlights=-20, shadows=-10
        ),
        "黑白肖像": EnhanceParams(
            brightness=1.05, contrast=1.25, saturation=0,
            sharpness=1.30, highlights=10, shadows=-15,
            vignette=20, grain=10
        ),
        "商业精修": EnhanceParams(
            brightness=1.10, contrast=1.08, saturation=1.05,
            sharpness=1.40, skin_smooth=60, face_brighten=20,
            eye_enhance=30, warmth=3, highlights=-15, shadows=15
        ),
        "暖调写真": EnhanceParams(
            brightness=1.05, contrast=1.02, saturation=1.10,
            sharpness=1.10, skin_smooth=20, warmth=30,
            highlights=-5, shadows=5, vignette=15
        ),
        "冷艳时尚": EnhanceParams(
            brightness=1.02, contrast=1.18, saturation=0.92,
            sharpness=1.25, warmth=-15, tint=5,
            highlights=10, shadows=-10, vignette=12
        ),
    },
    "风光": {
        "电影感自然": EnhanceParams(
            brightness=1.03, contrast=1.10, saturation=1.15,
            sharpness=1.20, dehaze=30, sky_enhance=25,
            greenery=20, vignette=15, highlights=-15, shadows=20
        ),
        "青橙电影调": EnhanceParams(
            brightness=1.02, contrast=1.12, saturation=1.08,
            sharpness=1.15, warmth=10, tint=-5,
            sky_enhance=20, highlights=-10, shadows=15, vignette=10
        ),
        "金色时刻": EnhanceParams(
            brightness=1.08, contrast=1.05, saturation=1.25,
            sharpness=1.05, warmth=40, highlights=15,
            shadows=10, vignette=8, sky_enhance=15
        ),
        "暗调森林": EnhanceParams(
            brightness=0.92, contrast=1.15, saturation=0.85,
            sharpness=1.15, warmth=-5, greenery=35,
            highlights=-25, shadows=-10, vignette=25, dehaze=20
        ),
        "极简黑白": EnhanceParams(
            brightness=1.05, contrast=1.30, saturation=0,
            sharpness=1.25, highlights=15, shadows=-20,
            vignette=20, grain=12
        ),
        "HDR 超清": EnhanceParams(
            brightness=1.10, contrast=1.25, saturation=1.20,
            sharpness=1.50, dehaze=60, sky_enhance=40,
            highlights=-30, shadows=30, greenery=15
        ),
        "梦幻柔光": EnhanceParams(
            brightness=1.12, contrast=0.88, saturation=0.95,
            sharpness=0.85, warmth=15, highlights=25,
            shadows=10, vignette=15
        ),
    },
    "摄影师": {
        "Cartier-Bresson 几何黑白": EnhanceParams(
            brightness=1.02, contrast=1.30, saturation=0,
            sharpness=1.15, grain=12, vignette=10, shadows=15
        ),
        "Moriyama 粗粝街拍": EnhanceParams(
            brightness=0.85, contrast=1.60, saturation=0,
            sharpness=1.10, grain=35, vignette=25, shadows=30,
            highlights=15
        ),
        "Fan Ho 光影诗意": EnhanceParams(
            brightness=0.92, contrast=1.45, saturation=0,
            sharpness=1.20, shadows=25, vignette=15,
            highlights=-15
        ),
        "Saul Leiter 层次色彩": EnhanceParams(
            brightness=0.95, contrast=1.05, saturation=1.08,
            sharpness=0.95, warmth=3, vignette=15, tint=-3,
            shadows=5
        ),
        "Eggleston 日常强色彩": EnhanceParams(
            brightness=1.02, contrast=1.15, saturation=1.35,
            sharpness=1.10, warmth=8, highlights=-5
        ),
        "Stephen Shore 冷静纪实": EnhanceParams(
            brightness=1.05, contrast=1.08, saturation=0.95,
            sharpness=1.05, warmth=-3, vignette=5, shadows=10
        ),
        "Peter Lindbergh 克制黑白": EnhanceParams(
            brightness=1.02, contrast=1.15, saturation=0,
            sharpness=1.08, grain=5, vignette=8, shadows=8
        ),
    },
    "美食": {
        "诱人暖调": EnhanceParams(
            brightness=1.10, contrast=1.10, saturation=1.30,
            sharpness=1.20, warmth=25, highlights=10, shadows=5
        ),
        "清新亮调": EnhanceParams(
            brightness=1.20, contrast=1.02, saturation=1.15,
            sharpness=1.10, warmth=5, highlights=20, shadows=15
        ),
        "暗调质感": EnhanceParams(
            brightness=0.90, contrast=1.20, saturation=1.10,
            sharpness=1.25, warmth=15, highlights=-20, shadows=-5, vignette=20
        ),
    },
    "夜景": {
        "城市霓虹": EnhanceParams(
            brightness=1.15, contrast=1.20, saturation=1.35,
            sharpness=1.20, highlights=-15, shadows=25, denoise=40
        ),
        "暗夜氛围": EnhanceParams(
            brightness=0.95, contrast=1.15, saturation=1.05,
            sharpness=1.10, highlights=-25, shadows=-10, vignette=30, denoise=30
        ),
        "纯净夜景": EnhanceParams(
            brightness=1.25, contrast=1.10, saturation=1.10,
            sharpness=1.15, denoise=60, shadows=30, highlights=-20
        ),
    },
    "通用": {
        "一键增强": EnhanceParams(
            brightness=1.05, contrast=1.08, saturation=1.10, sharpness=1.15
        ),
        "暖色调": EnhanceParams(
            brightness=1.03, contrast=1.05, saturation=1.10,
            warmth=30, highlights=5, vignette=10
        ),
        "冷色调": EnhanceParams(
            brightness=1.02, contrast=1.08, saturation=0.95,
            warmth=-20, tint=5, highlights=-5
        ),
        "高对比": EnhanceParams(
            brightness=1.02, contrast=1.35, saturation=1.05,
            sharpness=1.30, highlights=-15, shadows=-15
        ),
        "褪色复古": EnhanceParams(
            brightness=1.05, contrast=0.90, saturation=0.70,
            warmth=20, highlights=15, shadows=10, grain=20, vignette=20
        ),
    },
}

# 类别中文名
CATEGORY_NAMES = {
    "portrait": "人像", "landscape": "风光", "food": "美食",
    "night": "夜景", "macro": "微距", "architecture": "建筑",
    "general": "通用",
}

# 自然语言 → 风格关键词映射
STYLE_KEYWORDS = {
    "电影感": "电影感自然",
    "青橙": "青橙电影调", "青橙色": "青橙电影调",
    "金色": "金色时刻", "黄昏": "金色时刻", "日落": "金色时刻",
    "暗调": "暗调森林", "森林": "暗调森林", "暗绿": "暗调森林",
    "黑白": "极简黑白", "单色": "极简黑白",
    "HDR": "HDR 超清", "超清": "HDR 超清", "高清": "HDR 超清",
    "梦幻": "梦幻柔光", "柔光": "梦幻柔光", "朦胧": "梦幻柔光",
    "日系": "日系清新", "清新": "日系清新", "小清新": "日系清新",
    "胶片": "复古胶片", "复古": "复古胶片",
    "商业": "商业精修", "精修": "商业精修",
    "暖调": "暖色调", "温暖": "暖色调",
    "冷调": "冷色调", "冷艳": "冷艳时尚",
    "高对比": "高对比",
    "褪色": "褪色复古", "旧照片": "褪色复古",
    "诱人": "诱人暖调", "食欲": "诱人暖调",
    "明亮": "清新亮调",
    "质感": "暗调质感",
    "霓虹": "城市霓虹",
    "氛围": "暗夜氛围", "暗夜": "暗夜氛围",
    "纯净": "纯净夜景", "干净": "纯净夜景",
    # 摄影师
    "布列松": "Cartier-Bresson 几何黑白", "几何": "Cartier-Bresson 几何黑白",
    "森山": "Moriyama 粗粝街拍", "森山大道": "Moriyama 粗粝街拍", "粗粝": "Moriyama 粗粝街拍",
    "何藩": "Fan Ho 光影诗意", "光影": "Fan Ho 光影诗意",
    "索尔雷特": "Saul Leiter 层次色彩", "层次": "Saul Leiter 层次色彩",
    "埃格尔斯顿": "Eggleston 日常强色彩", "日常色彩": "Eggleston 日常强色彩",
    "史蒂芬肖尔": "Stephen Shore 冷静纪实", "纪实": "Stephen Shore 冷静纪实",
    "彼得林德伯格": "Peter Lindbergh 克制黑白",
}


class PhotoEnhancer:
    """照片智能修图引擎"""

    def __init__(self):
        self._face_cascade = None

    def detect_type(self, image: Image.Image) -> Dict:
        """识别照片类型"""
        result = {"type": "general", "confidence": 0.0, "features": {}}

        # 转 numpy 用于分析
        img_np = np.array(image.convert("RGB"))
        h, w = img_np.shape[:2]
        result["features"]["resolution"] = f"{w}x{h}"

        # 亮度分析
        gray = np.array(image.convert("L"))
        avg_brightness = float(np.mean(gray))
        brightness_var = float(np.std(gray))
        result["features"]["avg_brightness"] = round(avg_brightness, 1)
        result["features"]["brightness_var"] = round(brightness_var, 1)

        # 颜色分析
        r, g, b = img_np[:,:,0].mean(), img_np[:,:,1].mean(), img_np[:,:,2].mean()
        result["features"]["avg_color"] = f"R{r:.0f} G{g:.0f} B{b:.0f}"

        # 饱和度
        max_c = np.max(img_np, axis=2)
        min_c = np.min(img_np, axis=2)
        saturation = float(np.mean((max_c - min_c) / (max_c + 1e-6)))
        result["features"]["saturation"] = round(saturation, 3)

        scores = {}

        # 1. 人像检测
        face_count = self._detect_faces(image)
        result["features"]["faces"] = face_count
        if face_count >= 1:
            scores["portrait"] = min(face_count * 0.4, 1.0)
            # 高亮 + 有人脸 = 典型人像
            if avg_brightness > 80:
                scores["portrait"] += 0.2

        # 2. 风光检测
        if face_count == 0 and avg_brightness > 40:
            # 户外：亮度适中、色彩丰富
            if brightness_var > 40:
                scores["landscape"] = 0.5 + min(brightness_var / 120, 0.4)
            if saturation > 0.08:
                scores["landscape"] = scores.get("landscape", 0.3) + 0.15

        # 3. 夜景
        if avg_brightness < 50:
            scores["night"] = 0.4 + (50 - avg_brightness) / 50 * 0.5
            if saturation > 0.05:
                scores["night"] += 0.1

        # 4. 美食
        if face_count == 0 and avg_brightness > 80 and saturation > 0.1:
            # 暖色调 + 高饱和
            warmth = r - b
            if warmth > 15:
                scores["food"] = 0.5 + min(warmth / 80, 0.3)

        # 5. 微距
        if face_count == 0 and brightness_var < 25 and saturation > 0.06:
            scores["macro"] = 0.4 + (25 - brightness_var) / 25 * 0.3

        # 6. 建筑
        if face_count == 0 and brightness_var > 50 and saturation < 0.12:
            scores["architecture"] = 0.4 + min(brightness_var / 100, 0.3)

        # 确定类型
        if scores:
            best = max(scores, key=scores.get)
            result["type"] = best
            result["confidence"] = round(scores[best], 2)
            result["scores"] = {k: round(v, 2) for k, v in sorted(scores.items(), key=lambda x: -x[1])}

        result["category_name"] = CATEGORY_NAMES.get(result["type"], "通用")
        return result

    def _detect_faces(self, image: Image.Image) -> int:
        """OpenCV 人脸检测"""
        try:
            if self._face_cascade is None:
                import cv2
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self._face_cascade = cv2.CascadeClassifier(cascade_path)
            gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
            faces = self._face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(30, 30))
            return len(faces)
        except Exception:
            return 0

    def get_presets_for_type(self, photo_type: str) -> Dict:
        """获取照片类型对应的推荐预设"""
        cat = CATEGORY_NAMES.get(photo_type, "通用")
        return PRESET_LIBRARY.get(cat, PRESET_LIBRARY["通用"])

    def parse_style_request(self, text: str) -> Optional[str]:
        """从自然语言解析修图风格"""
        if not text:
            return None
        for keyword, preset_name in STYLE_KEYWORDS.items():
            if keyword in text:
                return preset_name
        return None

    def enhance(self, image: Image.Image, params: EnhanceParams) -> Image.Image:
        """应用修图参数"""
        img = image.convert("RGB")

        # 1. 亮度
        if params.brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(params.brightness)

        # 2. 对比度
        if params.contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(params.contrast)

        # 3. 饱和度
        if params.saturation != 1.0:
            img = ImageEnhance.Color(img).enhance(params.saturation)

        # 4. 锐度
        if params.sharpness != 1.0:
            img = ImageEnhance.Sharpness(img).enhance(params.sharpness)

        # 5. 色温调整 (RGB 通道偏移)
        if params.warmth != 0:
            img = self._adjust_warmth(img, params.warmth)

        # 6. 色调 (green-magenta)
        if params.tint != 0:
            img = self._adjust_tint(img, params.tint)

        # 7. 高光/阴影
        if params.highlights != 0 or params.shadows != 0:
            img = self._adjust_highlights_shadows(img, params.highlights, params.shadows)

        # 8. 降噪
        if params.denoise > 0:
            img = self._denoise(img, params.denoise / 100)

        # 9. 去雾
        if params.dehaze > 0:
            img = self._dehaze(img, params.dehaze / 100)

        # 10. 暗角
        if params.vignette > 0:
            img = self._add_vignette(img, params.vignette / 100)

        # 11. 颗粒
        if params.grain > 0:
            img = self._add_grain(img, params.grain / 100)

        # 12. 皮肤平滑
        if params.skin_smooth > 0:
            img = self._smooth_skin(img, params.skin_smooth / 100)

        # 13. 天空增强
        if params.sky_enhance > 0:
            img = self._enhance_sky(img, params.sky_enhance / 100)

        return img

    # ─── 底层处理 ───

    def _adjust_warmth(self, img: Image.Image, warmth: float) -> Image.Image:
        """色温：正=暖，负=冷"""
        arr = np.array(img, dtype=np.float32)
        factor = warmth / 100
        if factor > 0:
            arr[:,:,0] = np.clip(arr[:,:,0] * (1 + factor * 0.3), 0, 255)
            arr[:,:,2] = np.clip(arr[:,:,2] * (1 - factor * 0.2), 0, 255)
        else:
            arr[:,:,2] = np.clip(arr[:,:,2] * (1 - factor * 0.3), 0, 255)
            arr[:,:,0] = np.clip(arr[:,:,0] * (1 + factor * 0.2), 0, 255)
        return Image.fromarray(arr.astype(np.uint8))

    def _adjust_tint(self, img: Image.Image, tint: float) -> Image.Image:
        """色调：正=品红，负=绿"""
        arr = np.array(img, dtype=np.float32)
        factor = tint / 100
        if factor > 0:
            arr[:,:,1] = np.clip(arr[:,:,1] * (1 - factor * 0.15), 0, 255)
            arr[:,:,0] = np.clip(arr[:,:,0] * (1 + factor * 0.1), 0, 255)
            arr[:,:,2] = np.clip(arr[:,:,2] * (1 + factor * 0.1), 0, 255)
        else:
            arr[:,:,1] = np.clip(arr[:,:,1] * (1 - factor * 0.15), 0, 255)
        return Image.fromarray(arr.astype(np.uint8))

    def _adjust_highlights_shadows(self, img: Image.Image, highlights: float, shadows: float) -> Image.Image:
        """高光/阴影调整"""
        arr = np.array(img, dtype=np.float32)
        gray = 0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]

        # 高光蒙版 (>150)
        if highlights != 0:
            hl_mask = np.clip((gray - 150) / 80, 0, 1)
            factor = highlights / 100 * 0.3
            for c in range(3):
                arr[:,:,c] = arr[:,:,c] + hl_mask * factor * 255
            arr = np.clip(arr, 0, 255)

        # 阴影蒙版 (<80)
        if shadows != 0:
            sh_mask = np.clip((80 - gray) / 80, 0, 1)
            factor = shadows / 100 * 0.3
            for c in range(3):
                arr[:,:,c] = arr[:,:,c] + sh_mask * factor * 255
            arr = np.clip(arr, 0, 255)

        return Image.fromarray(arr.astype(np.uint8))

    def _denoise(self, img: Image.Image, strength: float) -> Image.Image:
        """降噪（双边滤波模拟）"""
        img = img.filter(ImageFilter.GaussianBlur(radius=strength * 3))
        return img

    def _dehaze(self, img: Image.Image, strength: float) -> Image.Image:
        """去雾（CLAHE + 对比度）"""
        arr = np.array(img)
        import cv2
        lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0 + strength * 4, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        arr = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        return Image.fromarray(arr)

    def _add_vignette(self, img: Image.Image, strength: float) -> Image.Image:
        """暗角"""
        w, h = img.size
        cx, cy = w / 2, h / 2
        max_r = np.sqrt(cx**2 + cy**2)

        # 生成径向渐变蒙版
        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((x - cx)**2 + (y - cy)**2)
        mask = 1 - np.clip((dist - max_r * 0.4) / (max_r * 0.6), 0, 1) * strength * 0.6

        arr = np.array(img, dtype=np.float32)
        for c in range(3):
            arr[:,:,c] = arr[:,:,c] * mask
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    def _add_grain(self, img: Image.Image, strength: float) -> Image.Image:
        """胶片颗粒"""
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, strength * 30, arr.shape)
        arr = np.clip(arr + noise, 0, 255)
        return Image.fromarray(arr.astype(np.uint8))

    def _smooth_skin(self, img: Image.Image, strength: float) -> Image.Image:
        """皮肤平滑（双边滤波）"""
        try:
            import cv2
            arr = np.array(img)
            d = int(5 + strength * 15)
            sigma_color = strength * 50
            sigma_space = strength * 50
            smoothed = cv2.bilateralFilter(arr, d, sigma_color, sigma_space)
            return Image.fromarray(smoothed)
        except Exception:
            # Fallback: Gaussian blur
            return img.filter(ImageFilter.GaussianBlur(radius=strength * 3))

    def _enhance_sky(self, img: Image.Image, strength: float) -> Image.Image:
        """天空增强（蓝色通道增强）"""
        arr = np.array(img, dtype=np.float32)
        # 粗略天空检测：上部 + 蓝色
        h = arr.shape[0]
        top_third = arr[:h//3, :, :]
        blue_channel = top_third[:,:,2]
        sky_mask = (blue_channel > 100) & (blue_channel > top_third[:,:,1])

        # 对天空区域增强蓝色和对比度
        full_mask = np.zeros((h, arr.shape[1]), dtype=bool)
        full_mask[:h//3, :] = sky_mask

        arr[full_mask, 2] = np.clip(arr[full_mask, 2] * (1 + strength * 0.3), 0, 255)
        arr[full_mask, 0] = np.clip(arr[full_mask, 0] * (1 - strength * 0.1), 0, 255)

        return Image.fromarray(arr.astype(np.uint8))

    def all_categories(self) -> Dict:
        """获取所有修图类别和预设"""
        return {
            cat: {"name": cat, "presets": list(presets.keys())}
            for cat, presets in PRESET_LIBRARY.items()
        }

    def get_params(self, category: str, preset_name: str) -> Optional[EnhanceParams]:
        """获取指定预设的参数"""
        presets = PRESET_LIBRARY.get(category, {})
        return presets.get(preset_name)

    def diagnose(self, detect_result: Dict, image: Image.Image) -> Dict:
        """照片诊断 — 基于 photo-postprocess-coach 的问题诊断逻辑"""
        features = detect_result.get("features", {})
        photo_type = detect_result.get("type", "general")
        problems = []
        potentials = []

        brightness = features.get("avg_brightness", 128)
        faces = features.get("faces", 0)
        saturation = features.get("saturation", 0.1)
        resolution = features.get("resolution", "unknown")

        # 1. 曝光问题
        if brightness < 60:
            problems.append({"severity": "high", "issue": "曝光不足", "desc": "画面偏暗，暗部细节丢失"})
        elif brightness > 220:
            problems.append({"severity": "high", "issue": "过曝", "desc": "高光溢出，亮部细节丢失"})
        elif brightness < 90:
            problems.append({"severity": "medium", "issue": "偏暗", "desc": "整体略暗，可提亮"})

        # 2. 人像特有问题
        if photo_type == "portrait" and faces > 0:
            if brightness < 100:
                problems.append({"severity": "medium", "issue": "面部偏暗", "desc": "人脸区域光线不足"})
            potentials.append({"aspect": "肤色", "suggestion": "可通过磨皮 + 提亮面部改善"})

        # 3. 风光特有问题
        if photo_type == "landscape":
            if saturation < 0.05:
                problems.append({"severity": "low", "issue": "色彩平淡", "desc": "饱和度偏低，风光色彩不够鲜明"})
            potentials.append({"aspect": "氛围", "suggestion": "加强天空蓝色和绿植饱和度"})

        # 4. 夜景特有问题
        if photo_type == "night":
            if brightness < 40:
                problems.append({"severity": "high", "issue": "噪点明显", "desc": "夜间拍摄噪点较多"})
            potentials.append({"aspect": "纯净度", "suggestion": "降噪 + 提升暗部细节"})

        # 5. 锐度
        if photo_type in ("landscape", "architecture"):
            potentials.append({"aspect": "锐度", "suggestion": "适度锐化增强细节"})

        # 推荐方案
        recommendations = []
        if photo_type == "portrait":
            recommendations = ["自然通透", "日系清新", "复古胶片"]
        elif photo_type == "landscape":
            recommendations = ["电影感自然", "青橙电影调", "HDR 超清"]
        elif photo_type == "night":
            recommendations = ["城市霓虹", "暗夜氛围", "纯净夜景"]
        elif photo_type == "food":
            recommendations = ["诱人暖调", "清新亮调", "暗调质感"]
        else:
            recommendations = ["一键增强", "高对比", "褪色复古"]

        return {
            "type": photo_type,
            "category_name": CATEGORY_NAMES.get(photo_type, "通用"),
            "problems": problems,
            "potentials": potentials,
            "recommendations": recommendations,
            "summary": self._diagnosis_summary(problems, photo_type),
        }

    def _diagnosis_summary(self, problems: list, photo_type: str) -> str:
        """一句话诊断"""
        if not problems:
            return "照片整体质量不错，可通过风格化调色锦上添花"

        high = [p for p in problems if p["severity"] == "high"]
        if high:
            issues = "、".join(p["issue"] for p in high)
            return f"主要问题：{issues}，建议优先修复"

        medium = [p for p in problems if p["severity"] == "medium"]
        if medium:
            issues = "、".join(p["issue"] for p in medium)
            return f"{issues}，可适当调整"

        return "照片整体良好，推荐尝试风格化修图"
