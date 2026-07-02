"""
片段评分器：多维度加权评分 + 按模板结构选择
"""
import logging
from typing import List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ScoredSegment:
    scene: object
    phase: str = ""
    total_score: float = 0
    scores_breakdown: Dict[str, float] = field(default_factory=dict)
    trim_start: float = 0
    trim_end: float = 0
    playback_speed: float = 1.0


class SegmentScorer:
    CATEGORY_BASE_SCORES = {
        "speech": 0.85, "meeting": 0.80, "group_photo": 0.75, "visit": 0.70,
        "flag_ceremony": 0.95, "document_sign": 0.80, "handshake": 0.65,
        "award": 0.75, "study": 0.70, "general": 0.40, "unknown": 0.20,
    }

    WEIGHTS = {
        "category": 0.25, "quality": 0.15, "people": 0.15,
        "motion": 0.10, "audio": 0.10, "duration": 0.10, "template_match": 0.15,
    }

    def score_and_select(self, scenes, template: dict, target_duration: float,
                         priorities=None) -> List[ScoredSegment]:
        scored = [self._score_scene(s, template) for s in scenes]
        structure = template.get("structure", [])
        selected = self._select_by_structure(scored, structure, target_duration)
        if priorities:
            selected = self._insert_priorities(selected, scored, priorities)
        logger.info(f"评分选择: {len(scenes)}个 → {len(selected)}个片段, "
                     f"总时长{sum(s.scene.duration for s in selected):.1f}s")
        return selected

    def _score_scene(self, scene, template: dict) -> ScoredSegment:
        scores = {
            "category": self.CATEGORY_BASE_SCORES.get(scene.category, 0.3),
            "quality": self._clamp(0.5 +
                (0.3 if 80 <= scene.avg_brightness <= 200 else
                 (-0.3 if scene.avg_brightness < 40 else 0)) +
                (0.2 if scene.avg_saturation > 50 else 0)),
            "people": (0.3 if scene.face_count == 0 else
                       0.6 if scene.face_count <= 2 else
                       0.8 if scene.face_count <= 10 else 1.0),
            "motion": (0.4 if scene.motion_score < 0.01 else
                       0.7 if scene.motion_score < 0.08 else
                       1.0 if scene.motion_score < 0.2 else
                       0.6 if scene.motion_score < 0.4 else 0.3),
            "audio": (1.0 if scene.has_speech and scene.avg_audio_level > -25 else
                      0.7 if scene.has_speech else 0.5),
            "duration": (1.0 if 3 <= scene.duration <= 15 else
                         0.7 if 2 <= scene.duration <= 25 else
                         0.3 if scene.duration <= 2 else 0.5),
        }

        needed = set()
        for phase in template.get("structure", []):
            for cat in phase.get("content", []):
                needed.add(cat)

        scores["template_match"] = (1.0 if scene.category in needed else
                                    0.3 if scene.category in ("general", "unknown") else 0.5)

        total = sum(scores[k] * self.WEIGHTS[k] for k in scores)
        return ScoredSegment(scene=scene, total_score=total, scores_breakdown=scores)

    def _select_by_structure(self, scored, structure, target_duration):
        if not structure:
            scored.sort(key=lambda s: s.total_score, reverse=True)
            return self._fill_duration(scored, target_duration)

        selected, remaining = [], list(scored)
        for pc in structure:
            pn = pc.get("phase", "")
            ct = pc.get("content", [])
            if "duration_ratio" in pc:
                pd = target_duration * pc["duration_ratio"]
            elif "duration" in pc:
                pd = sum(pc["duration"]) / 2
            else:
                pd = target_duration / len(structure)

            cand = [s for s in remaining if s.scene.category in ct or not ct] or remaining[:]
            cand.sort(key=lambda s: s.total_score, reverse=True)

            acc = 0
            for seg in cand:
                if acc >= pd:
                    break
                seg.phase = pn
                selected.append(seg)
                acc += seg.scene.duration
                if seg in remaining:
                    remaining.remove(seg)
        return selected

    def _fill_duration(self, segments, target):
        sel, acc = [], 0
        for s in segments:
            if acc >= target:
                break
            sel.append(s)
            acc += s.scene.duration
        return sel

    def _insert_priorities(self, selected, all_s, priorities):
        for p in reversed(priorities):
            tr = p.get("time_range", [])
            src = p.get("source", "")
            for seg in all_s:
                if (seg.scene.source_path == src and
                    seg.scene.start_time >= tr[0] and
                    seg.scene.end_time <= tr[1]):
                    seg.total_score = 999
                    selected.insert(0, seg)
                    break
        return selected

    @staticmethod
    def _clamp(v):
        return max(0, min(1, v))
