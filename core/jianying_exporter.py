"""
剪映草稿导出器 — 生成 .jianying_draft 工程文件
基于 pyJianYingDraft 库
"""
import os, sys, logging
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pyJianYingDraft.draft_folder import DraftFolder
from pyJianYingDraft.track import TrackType
from pyJianYingDraft.video_segment import VideoSegment
from pyJianYingDraft.audio_segment import AudioSegment
from pyJianYingDraft.text_segment import TextSegment
from pyJianYingDraft.time_util import Timerange

logger = logging.getLogger(__name__)


def _us(seconds: float) -> int:
    """秒 → 微秒"""
    return int(seconds * 1_000_000)


class JianyingDraftExporter:

    def __init__(self, output_dir: str = "output/drafts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        project_name: str,
        video_clips: List[Dict],
        music_path: Optional[str] = None,
        title_text: str = "",
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
    ) -> str:
        draft_dir = self.output_dir / project_name
        draft_dir.mkdir(parents=True, exist_ok=True)

        df = DraftFolder(str(draft_dir))
        script = df.create_draft(project_name, width, height, fps, allow_replace=True)

        time_cursor = 0  # 当前时间 (秒)

        # 视频轨道
        if video_clips:
            vt = script.add_track(TrackType.video)
            for clip in video_clips:
                path = clip.get("path", "")
                if not path or not os.path.exists(path):
                    continue
                dur = clip.get("duration", 3.0)
                start_us = _us(time_cursor)
                duration_us = _us(dur)
                try:
                    seg = VideoSegment(
                        path,
                        target_timerange=Timerange(start_us, start_us + duration_us),
                        source_timerange=Timerange(0, duration_us),
                    )
                    vt.add_segment(seg)
                    time_cursor += dur
                except Exception as e:
                    logger.warning(f"add_video failed: {e}")

        total_dur = time_cursor

        # 音频
        if music_path and os.path.exists(music_path):
            try:
                at = script.add_track(TrackType.audio)
                seg = AudioSegment(
                    music_path,
                    target_timerange=Timerange(0, _us(total_dur)),
                )
                at.add_segment(seg)
            except Exception as e:
                logger.warning(f"add_audio failed: {e}")

        # 标题
        if title_text and total_dur > 0:
            try:
                tt = script.add_track(TrackType.text)
                seg = TextSegment(
                    title_text,
                    timerange=Timerange(0, _us(min(3.0, total_dur))),
                )
                tt.add_segment(seg)
            except Exception as e:
                logger.warning(f"add_text failed: {e}")

        script.save()
        logger.info(f"剪映草稿已生成: {draft_dir}")
        return str(draft_dir)
