"""
内容分类器：基于启发式规则识别场景类型
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

CLASSIFICATION_RULES = {
    "speech": {
        "conditions": {"face_count": (1, 2), "motion_score": (0, 0.08),
                       "has_speech": True, "avg_brightness": (80, 220)},
        "weight": 1.0
    },
    "meeting": {
        "conditions": {"face_count": (3, 50), "scene_type": "indoor",
                       "motion_score": (0, 0.12)},
        "weight": 0.9
    },
    "group_photo": {
        "conditions": {"face_count": (5, 100), "motion_score": (0, 0.05),
                       "avg_brightness": (100, 255)},
        "weight": 1.1
    },
    "visit": {
        "conditions": {"motion_score": (0.08, 1.0),
                       "scene_type": ("indoor", "outdoor")},
        "weight": 0.8
    },
    "flag_ceremony": {
        "conditions": {"avg_saturation": (0, 80), "motion_score": (0, 0.1),
                       "face_count": (3, 100)},
        "weight": 1.2,
        "color_hint": "red_dominant"
    },
    "document_sign": {
        "conditions": {"face_count": (1, 4), "scene_type": "indoor",
                       "motion_score": (0, 0.06), "has_speech": False},
        "weight": 0.7
    },
    "handshake": {
        "conditions": {"face_count": (2, 4), "motion_score": (0.03, 0.15)},
        "weight": 0.9
    },
    "award": {
        "conditions": {"face_count": (2, 6), "motion_score": (0, 0.1),
                       "avg_brightness": (120, 255)},
        "weight": 0.85
    },
    # 风光摄影
    "wide_landscape": {
        "conditions": {"face_count": (0, 2), "motion_score": (0, 0.06),
                       "avg_brightness": (50, 200), "scene_type": "outdoor"},
        "weight": 1.0
    },
    "drone_shot": {
        "conditions": {"face_count": (0, 0), "motion_score": (0.03, 0.3)},
        "weight": 0.9
    },
    "sunset": {
        "conditions": {"avg_brightness": (20, 90), "face_count": (0, 1),
                       "avg_saturation": (30, 150)},
        "weight": 1.1
    },
    "closeup": {
        "conditions": {"face_count": (0, 0), "motion_score": (0, 0.04)},
        "weight": 0.7
    },
    "water": {
        "conditions": {"motion_score": (0.05, 0.5), "scene_type": "outdoor"},
        "weight": 0.8
    },
    "timelapse": {
        "conditions": {"motion_score": (0.2, 1.0), "face_count": (0, 0)},
        "weight": 1.2
    },
}


class ContentClassifier:
    def __init__(self, config: dict):
        self.confidence_threshold = config.get("confidence_threshold", 0.6)

    def classify_batch(self, scenes: List) -> List:
        for scene in scenes:
            scene.category, scene.category_confidence = self._classify_single(scene)
        return scenes

    def _classify_single(self, scene) -> tuple:
        scores = {}
        for category, rule in CLASSIFICATION_RULES.items():
            conditions = rule["conditions"]
            total = len(conditions)
            matched = 0
            for key, expected in conditions.items():
                actual = getattr(scene, key, None)
                if actual is None:
                    continue
                if isinstance(expected, tuple):
                    if expected[0] <= actual <= expected[1]:
                        matched += 1
                elif isinstance(expected, bool):
                    if actual == expected:
                        matched += 1
                else:
                    if actual == expected:
                        matched += 1
            scores[category] = (matched / total) * rule.get("weight", 1.0) if total > 0 else 0

        # 红色主导加成
        if self._has_red_dominant(scene):
            for cat in ["flag_ceremony"]:
                if cat in scores:
                    scores[cat] += 0.2

        if not scores:
            return "unknown", 0.0

        best = max(scores, key=scores.get)
        if scores[best] >= self.confidence_threshold:
            return best, scores[best]
        return "general", scores[best]

    def _has_red_dominant(self, scene) -> bool:
        if scene.dominant_colors:
            for c in scene.dominant_colors:
                if c[0] > 150 and c[0] > c[1] * 1.5 and c[0] > c[2] * 1.5:
                    return True
        return scene.avg_saturation > 100 and scene.avg_brightness > 100
