"""
主流水线：编排完整的 8 阶段自动剪辑流程
"""
import os
import json
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

import yaml

from .analyzer import VideoAnalyzer
from .classifier import ContentClassifier
from .scorer import SegmentScorer
from .editor import EditingEngine
from .music_selector import MusicSelector
from .overlay import OverlayEngine
from .color_grade import ColorGrader
from .renderer import VideoRenderer
from .style_engine import StyleEngine
from .agenda_matcher import AgendaMatcher
from .exporter import MultiFormatExporter

logger = logging.getLogger(__name__)


@dataclass
class EditRequest:
    input_paths: List[str]
    template: str = "party_building"
    title: str = ""
    subtitle: str = ""
    organization: str = ""
    date_text: str = ""
    output_path: str = ""
    target_duration: float = 0
    music_path: Optional[str] = None
    logo_path: Optional[str] = None
    cover_image: Optional[str] = None
    color_tone: Optional[str] = None
    priority_segments: List[Dict] = field(default_factory=list)
    # 新增
    style_description: str = ""          # 剪辑风格说明
    agenda_text: str = ""                # 会议议程文本
    style_config: Dict = field(default_factory=dict)  # 风格解析结果
    export_formats: List[str] = field(default_factory=lambda: ["mp4"])  # 输出格式
    export_resolution: str = "1080p"     # 输出分辨率
    export_fps: int = 30                 # 输出帧率
    export_capcut_timeline: bool = False # 是否导出剪映时间线
    logo_position: str = "top_right"     # Logo位置
    logo_remove_bg: bool = False         # Logo去白底
    user_images: List[Dict] = field(default_factory=list)  # 用户叠加图片


@dataclass
class EditResult:
    success: bool
    output_path: str = ""
    duration: float = 0
    template_used: str = ""
    scenes_detected: int = 0
    scenes_selected: int = 0
    music_used: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AutoEditPipeline:
    def __init__(self, config_path: str = "config.yaml"):
        self.base_dir = Path(config_path).parent
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f) or {}

        self.analyzer = VideoAnalyzer(self.config.get("scene_detection", {}))
        self.classifier = ContentClassifier(self.config.get("classification", {}))
        self.scorer = SegmentScorer()
        self.editor = EditingEngine(self.config)
        self.music_selector = MusicSelector(
            str(self.base_dir / self.config.get("music", {}).get("library_path", "assets/music")),
            self.config.get("music", {}),
        )
        self.overlay_engine = OverlayEngine(self.config.get("overlays", {}))
        # 初始化调色引擎，加载LUT文件
        luts_dir = str(self.base_dir / "assets" / "luts")
        self.color_grader = ColorGrader(luts_directory=luts_dir)
        self.renderer = VideoRenderer(self.config.get("output", {}))
        self.style_engine = StyleEngine()
        self.agenda_matcher = AgendaMatcher()
        self.exporter = MultiFormatExporter()

    def _load_template(self, name: str) -> dict:
        tpl_path = self.base_dir / "templates" / f"{name}.json"
        if tpl_path.exists():
            with open(tpl_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _estimate_duration(self, template: dict, scenes: list) -> float:
        total = sum(s.duration for s in scenes)
        return min(max(total * 0.3, 120), 480)

    def _generate_output_path(self, request: EditRequest) -> str:
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        return str(output_dir / f"{request.template}_{ts}.mp4")

    async def execute(self, request: EditRequest) -> EditResult:
        logger.info(f"=== EasyCut 开始剪辑: 模板={request.template}, 输入={len(request.input_paths)}个视频 ===")
        t0 = time.time()

        try:
            # 阶段0: 风格解析 & 议程分析
            style_config = {}
            if request.style_description:
                logger.info(">>> 阶段0: 风格解析 & 议程分析")
                style_config = self.style_engine.parse(request.style_description)
                request.style_config = style_config

            agenda_items = []
            if request.agenda_text:
                agenda_items = self.agenda_matcher.parse_agenda(request.agenda_text)
                logger.info(f"  解析议程: {len(agenda_items)}项")

            # 阶段1: 视频分析
            logger.info(">>> 阶段1: 视频分析与场景检测")
            all_scenes = []
            for vp in request.input_paths:
                scenes = self.analyzer.analyze(vp)
                all_scenes.extend(scenes)
            logger.info(f"  检测到 {len(all_scenes)} 个有效场景")

            if not all_scenes:
                return EditResult(success=False, error="未检测到有效场景")

            # 阶段2: 内容分类
            logger.info(">>> 阶段2: 场景内容分类")
            classified = self.classifier.classify_batch(all_scenes)
            cats = {}
            for s in classified:
                cats[s.category] = cats.get(s.category, 0) + 1
            logger.info(f"  分类分布: {cats}")

            # 阶段2.5: 议程匹配（如果有议程）
            if agenda_items:
                logger.info(">>> 阶段2.5: 议程场景匹配")
                agenda_match = self.agenda_matcher.match_scenes_to_agenda(classified, agenda_items)
                timeline_plan = self.agenda_matcher.generate_timeline_plan(agenda_match, 180)
                request.priority_segments = [
                    {"category": s.category, "weight": 0.9}
                    for item in timeline_plan for s in item.get("scenes", [])
                ]

            # 阶段3: 评分选择
            logger.info(">>> 阶段3: 片段评分与选择")
            template = self._load_template(request.template)

            # 风格影响配置
            if style_config:
                template["color_tone"] = style_config.get("color_tone", template.get("color_tone", "warm_red"))

            target_dur = request.target_duration or self._estimate_duration(template, classified)
            scored = self.scorer.score_and_select(classified, template, target_dur,
                                                   request.priority_segments)

            # 阶段4: 编辑计划
            logger.info(">>> 阶段4: 生成剪辑计划")
            edit_plan = self.editor.create_plan(
                scored, template, target_dur,
                request.title, request.subtitle,
                request.organization, request.date_text,
            )

            # 风格影响转场
            if style_config.get("transition"):
                edit_plan.transition_override = style_config["transition"]

            # 阶段5: 音乐选择
            logger.info(">>> 阶段5: 音乐选择")
            music_mood = style_config.get("music_mood") if style_config else None
            if request.music_path:
                music_file = request.music_path
            else:
                music_file = self.music_selector.select(
                    request.template, edit_plan.total_duration,
                    mood_override=music_mood,
                    user_music_path=request.music_path,
                )
            beat_markers = self.music_selector.analyze_beats(music_file) if music_file else []
            if beat_markers:
                edit_plan = self.editor.sync_to_beats(edit_plan, beat_markers)

            # 阶段6: 叠加层（含Logo/封面/用户图片）
            logger.info(">>> 阶段6: 制作叠加层")
            overlay_layers = self.overlay_engine.create_all(
                edit_plan, request.template,
                logo_path=request.logo_path,
                logo_position=request.logo_position,
                remove_bg=request.logo_remove_bg,
                cover_image=request.cover_image,
                user_images=request.user_images,
            )

            # 阶段7: 调色
            logger.info(">>> 阶段7: 调色")
            color_preset = (style_config.get("color_tone") if style_config
                            else None) or request.color_tone or template.get("color_tone", "warm_red")
            color_config = self.color_grader.get_preset(color_preset)

            # 阶段8: 渲染
            logger.info(">>> 阶段8: 渲染输出")
            output_path = request.output_path or self._generate_output_path(request)
            final = self.renderer.render(edit_plan, music_file, overlay_layers,
                                         color_config, output_path)

            # 阶段9: 多格式导出
            exported = {"mp4": output_path}
            if request.export_capcut_timeline:
                logger.info(">>> 阶段9: 导出剪映时间线")
                timeline_path = output_path.rsplit(".", 1)[0] + "_timeline.xml"
                self.exporter.export_capcut_timeline(edit_plan, timeline_path, request.title)
                exported["capcut_timeline"] = timeline_path

            for fmt in request.export_formats:
                if fmt != "mp4":
                    logger.info(f">>> 阶段9: 导出 {fmt.upper()}")
                    fmt_path = output_path.rsplit(".", 1)[0] + f".{fmt}"
                    self.exporter.export_video(output_path, fmt_path, fmt,
                                               request.export_resolution,
                                               request.export_fps)
                    exported[fmt] = fmt_path

            elapsed = time.time() - t0
            logger.info(f"=== 剪辑完成! 用时 {elapsed:.1f}s | {output_path} ===")

            return EditResult(
                success=True, output_path=output_path,
                duration=final["duration"], template_used=request.template,
                scenes_detected=len(all_scenes), scenes_selected=len(edit_plan.clips),
                music_used=music_file,
                metadata={"render_info": final, "elapsed": elapsed,
                          "exported_formats": exported,
                          "style_applied": bool(style_config),
                          "agenda_matched": len(agenda_items)},
            )

        except Exception as e:
            logger.error(f"剪辑失败: {e}", exc_info=True)
            return EditResult(
                success=False, template_used=request.template,
                error=str(e),
            )

    async def preview(self, input_paths: List[str], template_name: str) -> Dict:
        logger.info(f"预览模式: {len(input_paths)}个视频, 模板={template_name}")
        all_scenes = []
        for vp in input_paths:
            all_scenes.extend(self.analyzer.analyze(vp))
        classified = self.classifier.classify_batch(all_scenes)
        cat_stats = {}
        for s in classified:
            if s.category not in cat_stats:
                cat_stats[s.category] = {"count": 0, "total_duration": 0}
            cat_stats[s.category]["count"] += 1
            cat_stats[s.category]["total_duration"] += s.duration
        return {
            "total_scenes": len(all_scenes),
            "total_duration": sum(s.duration for s in all_scenes),
            "category_distribution": cat_stats,
        }
