"""
SOE Auto Editor - 技能主入口
"""
import asyncio
import logging
from typing import Dict, Any

from core.pipeline import AutoEditPipeline, EditRequest

logger = logging.getLogger(__name__)


class SOEAutoEditSkill:
    SKILL_META = {
        "name": "soe_auto_editor",
        "display_name": "国企宣传视频自动剪辑",
        "description": "自动分析视频素材，按模板剪辑生成党建、会议、参观、学习等宣传视频",
        "version": "1.0.0",
    }

    def __init__(self, config_path: str = "config.yaml"):
        self.pipeline = AutoEditPipeline(config_path)

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            input_videos = params.get("input_videos", [])
            if not input_videos:
                return {"success": False, "error": "未提供输入视频"}

            request = EditRequest(
                input_paths=input_videos,
                template=params.get("template", "party_building"),
                title=params.get("title", ""),
                subtitle=params.get("subtitle", ""),
                organization=params.get("organization", ""),
                date_text=params.get("date_text", ""),
                output_path=params.get("output_path", ""),
                target_duration=params.get("target_duration", 0),
                music_path=params.get("music_path"),
                logo_path=params.get("logo_path"),
                color_tone=params.get("color_tone"),
            )

            result = await self.pipeline.execute(request)

            return {
                "success": result.success,
                "output_path": result.output_path,
                "duration": round(result.duration, 1),
                "template_used": result.template_used,
                "scenes_detected": result.scenes_detected,
                "scenes_selected": result.scenes_selected,
                "music_used": result.music_used,
                "error": result.error,
                "metadata": result.metadata,
            }
        except Exception as e:
            logger.error(f"执行失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def preview(self, params: Dict[str, Any]) -> Dict[str, Any]:
        input_videos = params.get("input_videos", [])
        if not input_videos:
            return {"success": False, "error": "未提供输入视频"}
        template = params.get("template", "party_building")
        return await self.pipeline.preview(input_videos, template)

    def edit_sync(self, **kwargs) -> Dict[str, Any]:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.execute(kwargs))
        finally:
            loop.close()
