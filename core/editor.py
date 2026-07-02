"""
剪辑引擎：生成剪辑计划、控制节奏、转场逻辑
"""
import logging
from typing import List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ClipInfo:
    source_path: str
    start_time: float
    end_time: float
    duration: float
    phase: str
    transition_in: str = "fade"
    transition_out: str = "fade"
    transition_duration: float = 0.5
    speed: float = 1.0
    volume: float = 1.0
    fade_audio: bool = True
    category: str = ""


@dataclass
class EditPlan:
    clips: List[ClipInfo]
    title: str = ""
    subtitle: str = ""
    organization: str = ""
    date_text: str = ""
    total_duration: float = 0
    phases: List[Dict] = field(default_factory=list)
    beat_markers: List[float] = field(default_factory=list)


TRANSITION_SCHEMES = {
    "party_building": {
        "default": "fade", "speech_to_speech": "dissolve",
        "scene_change": "fade_black", "climax": "crossfade",
        "opening": "fade_from_black", "closing": "fade_to_black",
    },
    "conference": {
        "default": "fade", "speech_to_speech": "cut",
        "scene_change": "dissolve", "climax": "fade",
        "opening": "fade_from_black", "closing": "fade_to_black",
    },
    "visit": {
        "default": "dissolve", "speech_to_speech": "fade",
        "scene_change": "wipe", "climax": "crossfade",
        "opening": "fade_from_black", "closing": "fade_to_black",
    },
    "study": {
        "default": "fade", "speech_to_speech": "cut",
        "scene_change": "dissolve", "climax": "fade",
        "opening": "fade_from_black", "closing": "fade_to_black",
    },
}


class EditingEngine:
    def __init__(self, config: dict):
        self.config = config

    def create_plan(self, segments, template, target_duration,
                    title="", subtitle="", organization="", date_text=""):
        tn = template.get("name", "party_building")
        tr = TRANSITION_SCHEMES.get(tn, TRANSITION_SCHEMES["party_building"])

        clips, phases, ct, cp = [], [], 0, ""

        for i, seg in enumerate(segments):
            sc = seg.scene

            if i == 0:
                ti = tr.get("opening", "fade_from_black")
            elif seg.phase != cp:
                ti = tr.get("scene_change", "dissolve")
            elif sc.category == "speech":
                ti = tr.get("speech_to_speech", "cut")
            else:
                ti = tr.get("default", "fade")

            to = tr.get("closing", "fade_to_black") if i == len(segments) - 1 else "none"

            clip = ClipInfo(
                source_path=sc.source_path,
                start_time=sc.start_time,
                end_time=sc.end_time,
                duration=sc.duration,
                phase=seg.phase,
                transition_in=ti,
                transition_out=to,
                transition_duration=0.8 if "fade" in ti else 0.3,
                speed=seg.playback_speed,
                volume=0.3 if sc.has_speech else 0.1,
                category=sc.category,
            )
            clips.append(clip)

            if seg.phase != cp:
                phases.append({"phase": seg.phase, "start_time": ct, "index": i})
                cp = seg.phase

            ct += clip.duration

        plan = EditPlan(
            clips=clips, title=title, subtitle=subtitle,
            organization=organization, date_text=date_text,
            total_duration=ct, phases=phases,
        )
        logger.info(f"剪辑计划: {len(clips)}个片段, 总时长{ct:.1f}s, {len(phases)}个阶段")
        return plan

    def sync_to_beats(self, plan: EditPlan, beat_markers: List[float]):
        if not beat_markers:
            return plan

        sync_tol = 0.3
        ct = 0
        for clip in plan.clips:
            bb = min(beat_markers, key=lambda b: abs(b - ct))
            if abs(bb - ct) < sync_tol:
                adj = bb - ct
                if adj > 0.05:
                    clip.duration += adj
                    clip.end_time += adj
            ct += clip.duration

        plan.total_duration = ct
        plan.beat_markers = beat_markers
        logger.info(f"节拍同步完成, 总时长: {ct:.1f}s")
        return plan
