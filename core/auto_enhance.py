"""
EasyCut 自动增强模块
支持：自动裁剪、自动水平、自动抗畸变、AI一键优化
"""
import cv2, numpy as np, logging
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)


def auto_crop(image: np.ndarray, margin: int = 5) -> np.ndarray:
    """智能裁剪：去除边缘空白区域"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 检测非均匀区域
    edges = cv2.Canny(gray, 50, 150)
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)

    # 找边界
    coords = cv2.findNonZero(dilated)
    if coords is None:
        return image

    x, y, w, h = cv2.boundingRect(coords)
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(image.shape[1] - x, w + 2 * margin)
    h = min(image.shape[0] - y, h + 2 * margin)

    if w < 50 or h < 50:
        return image

    return image[y:y+h, x:x+w]


def auto_level(image: np.ndarray) -> np.ndarray:
    """自动水平校正：检测水平线并旋转"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    if lines is None:
        return image

    # 统计所有接近水平的线段角度
    angles = []
    for line in lines:
        rho, theta = line[0]
        angle = np.degrees(theta)
        # 只取接近水平 (0°~5° 或 175°~180°) 或垂直 (85°~95°)
        if angle < 5 or angle > 175:
            angles.append(angle)
        elif 85 < angle < 95:
            angles.append(angle)

    if not angles:
        return image

    # 取中位数角度
    median_angle = np.median(angles)
    if median_angle > 90:
        median_angle -= 180

    if abs(median_angle) < 0.3:
        return image  # 已经很水平了

    # 旋转
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, rot_mat, (w, h),
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated


def auto_lens_correction(image: np.ndarray) -> np.ndarray:
    """自动抗畸变（桶形/枕形畸变校正）"""
    h, w = image.shape[:2]

    # 使用标准相机矩阵
    focal = max(w, h)
    K = np.array([
        [focal, 0, w / 2],
        [0, focal, h / 2],
        [0, 0, 1]
    ], dtype=np.float64)

    # 检测畸变系数 (k1)
    # 简化：使用经验值
    D = np.array([-0.05, 0.01, 0, 0], dtype=np.float64)

    new_K, _ = cv2.getOptimalNewCameraMatrix(K, D, (w, h), 1, (w, h))
    corrected = cv2.undistort(image, K, D, None, new_K)
    return corrected


def auto_contrast(image: np.ndarray) -> np.ndarray:
    """自动对比度增强（CLAHE）"""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)

    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def auto_color_balance(image: np.ndarray) -> np.ndarray:
    """自动白平衡（灰度世界法）"""
    result = image.copy().astype(np.float32)

    for c in range(3):
        mean_val = np.mean(result[:, :, c])
        result[:, :, c] *= 128.0 / max(mean_val, 1.0)

    return np.clip(result, 0, 255).astype(np.uint8)


def auto_sharpen(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """智能锐化"""
    blur = cv2.GaussianBlur(image, (0, 0), 3)
    sharpened = cv2.addWeighted(image, 1.0 + strength * 0.5, blur, -strength * 0.5, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def ai_auto_enhance(image: np.ndarray) -> Tuple[np.ndarray, Dict]:
    """AI一键优化：自动应用最佳调整组合"""
    report = {}

    # 1. 自动水平
    leveled = auto_level(image)
    report["leveled"] = not np.array_equal(image, leveled)

    # 2. 自动裁剪
    cropped = auto_crop(leveled)
    report["cropped"] = cropped.shape != leveled.shape

    # 3. 抗畸变
    corrected = auto_lens_correction(cropped)

    # 4. 白平衡
    balanced = auto_color_balance(corrected)

    # 5. 对比度
    contrasted = auto_contrast(balanced)

    # 6. 锐化
    result = auto_sharpen(contrasted, 0.6)

    # 报告
    report["steps"] = []
    if report.get("leveled"): report["steps"].append("水平校正")
    if report.get("cropped"): report["steps"].append("智能裁剪")
    report["steps"].extend(["抗畸变", "白平衡", "对比度增强", "锐化"])

    return result, report
