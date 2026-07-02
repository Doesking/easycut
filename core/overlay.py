""""
叠加层引擎：标题卡、字幕条、Logo角标、封面图、用户图片、片尾卡
"""
import os
import logging
import subprocess
import tempfile
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

POSITION_MAP = {
    "top_left": (30, 30),
    "top_right": ("W-w-30", 30),
    "bottom_left": (30, "H-h-30"),
    "bottom_right": ("W-w-30", "H-h-30"),
    "center": ("(W-w)/2", "(H-h)/2"),
}


class OverlayEngine:
    def __init__(self, config: dict):
        self.config = config

    def create_all(self, edit_plan, template_name: str,
                   extra_overlays=None, logo_path=None,
                   logo_position="top_right", remove_bg=False,
                   cover_image=None, user_images=None) -> List[Dict]:
        overlays = []
        # 封面图
        if cover_image and os.path.exists(cover_image):
            overlays.append(self._create_cover_overlay(cover_image))
        elif edit_plan.title:
            overlays.append(self._create_title_card(edit_plan, template_name))

        overlays.extend(self._create_lower_thirds(edit_plan, template_name))

        # Logo叠加
        if logo_path and os.path.exists(logo_path):
            logo = self._create_logo_overlay(logo_path, logo_position, remove_bg)
            overlays.append(logo)

        # 用户自定义图片
        if user_images:
            for img in user_images:
                overlays.append(self._create_user_image_overlay(img))

        overlays.append(self._create_ending_card(edit_plan, template_name))
        if extra_overlays:
            overlays.extend(extra_overlays)
        return overlays

    def _remove_white_bg(self, image_path: str) -> str:
        """去除白色背景（用 ImageMagick 或 FFmpeg 的 colorkey）"""
        output = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        # 使用 FFmpeg colorkey 滤镜去白底
        cmd = [
            "ffmpeg", "-y", "-i", image_path,
            "-vf", "colorkey=white:0.3:0.1",
            "-frames:v", "1", output,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            if os.path.getsize(output) > 100:
                logger.info(f"Logo白底去除完成: {output}")
                return output
        except Exception as e:
            logger.warning(f"去白底失败: {e}")
        return image_path

    def _create_cover_overlay(self, cover_path: str) -> Dict:
        """封面图覆盖"""
        return {
            "type": "cover", "image_path": cover_path,
            "start_time": 0, "duration": 4.0,
            "fade_in": 0.5, "fade_out": 1.0,
            "position": "center",
            "size": "fit",
        }

    def _create_user_image_overlay(self, img_info: Dict) -> Dict:
        """用户自定义图片叠加"""
        pos = img_info.get("position", "top_right")
        remove_bg = img_info.get("remove_bg", False)
        img_path = img_info.get("path", "")

        if remove_bg and img_path:
            img_path = self._remove_white_bg(img_path)

        # 支持自定义坐标
        pos_config = {}
        if isinstance(pos, dict):
            pos_config = {
                "x": pos.get("x", "W-w-30"),
                "y": pos.get("y", 30),
            }
        else:
            coords = POSITION_MAP.get(pos, POSITION_MAP["top_right"])
            pos_config = {"x": coords[0], "y": coords[1]}

        return {
            "type": "user_image", "image_path": img_path,
            "position": pos_config,
            "size": img_info.get("size", [150, 150]),
            "opacity": img_info.get("opacity", 0.9),
            "start_time": img_info.get("start_time", 0),
            "duration": img_info.get("duration", -1),
        }

    def _create_logo_overlay(self, logo_path, position="top_right",
                              remove_bg=False) -> Dict:
        lc = self.config.get("logo", {})

        # 去白底
        actual_path = logo_path
        if remove_bg:
            actual_path = self._remove_white_bg(logo_path)

        # 位置解析
        if isinstance(position, dict):
            x, y = position.get("x", "W-w-30"), position.get("y", 30)
        else:
            coords = POSITION_MAP.get(position, POSITION_MAP["top_right"])
            x, y = coords[0], coords[1]

        return {
            "type": "logo", "image_path": actual_path,
            "position": {"x": x, "y": y},
            "size": lc.get("size", [120, 120]),
            "opacity": lc.get("opacity", 0.9),
            "start_time": 0, "duration": -1, "margin": 30,
        }

    def _create_title_card(self, plan, tn):
        style = self._get_title_style(tn)
        return {
            "type": "title_card", "start_time": 0, "duration": 4.0,
            "fade_in": 1.0, "fade_out": 0.8,
            "elements": [
                {"type": "text", "content": plan.title, "fontsize": style["title_size"],
                 "color": style["text_color"], "position": ("center", "center"),
                 "y_offset": -30, "fade_in": 1.5},
                {"type": "text", "content": plan.subtitle, "fontsize": style["subtitle_size"],
                 "color": style["subtitle_color"], "position": ("center", "center"),
                 "y_offset": 40, "fade_in": 2.0},
                {"type": "text", "content": plan.organization, "fontsize": style["org_size"],
                 "color": style["text_color"], "position": ("center", "bottom"),
                 "y_offset": 80, "fade_in": 2.5},
            ]
        } if plan.title else {}

    def _create_lower_thirds(self, plan, tn):
        thirds, seen = [], set()
        style = self._get_lower_third_style(tn)
        phase_names = {
            "opening": "活动开幕", "speech": "重要讲话", "meeting": "会议现场",
            "visit": "参观考察", "study": "学习交流", "group_photo": "合影留念",
            "flag_ceremony": "升旗仪式", "document_sign": "签约仪式",
        }
        ct = 0
        for clip in plan.clips:
            phase = clip.phase
            if phase and phase not in seen and phase in phase_names:
                txt = phase_names[phase]
                if txt:
                    thirds.append({
                        "type": "lower_third", "start_time": ct + 0.5, "duration": 4.0,
                        "fade_in": 0.5, "fade_out": 0.5,
                        "elements": [
                            {"type": "rectangle", "color": style["bg_color"],
                             "opacity": style["bg_opacity"], "x": 60, "y": "H-180",
                             "width": 500, "height": 80},
                            {"type": "text", "content": txt, "fontsize": style["font_size"],
                             "color": style["text_color"], "x": 90, "y": "H-165"},
                        ]
                    })
                    seen.add(phase)
            ct += clip.duration
        return thirds

    def _create_ending_card(self, plan, tn):
        style = self._get_title_style(tn)
        return {
            "type": "ending_card", "start_time": -6.0, "duration": 5.0,
            "fade_in": 1.0, "fade_out": 1.0,
            "elements": [
                {"type": "text", "content": plan.organization or plan.title,
                 "fontsize": style["title_size"] - 10, "color": style["text_color"],
                 "position": ("center", "center"), "y_offset": -20},
                {"type": "text", "content": plan.date_text,
                 "fontsize": style["subtitle_size"] - 4, "color": style["subtitle_color"],
                 "position": ("center", "center"), "y_offset": 30},
            ]
        }

    def _get_title_style(self, tn):
        styles = {
            "party_building": {"bg_color": "0x1a0a0a", "text_color": "#FFFFFF",
                "subtitle_color": "#CCCCCC", "accent_color": "#C41E24",
                "title_size": 72, "subtitle_size": 36, "org_size": 28},
            "conference": {"bg_color": "0x0a0a1a", "text_color": "#FFFFFF",
                "subtitle_color": "#BBBBCC", "accent_color": "#2255AA",
                "title_size": 68, "subtitle_size": 34, "org_size": 26},
            "visit": {"bg_color": "0x0a1a0a", "text_color": "#FFFFFF",
                "subtitle_color": "#CCDCCC", "accent_color": "#228B22",
                "title_size": 68, "subtitle_size": 34, "org_size": 26},
            "study": {"bg_color": "0x1a1a0a", "text_color": "#FFFFFF",
                "subtitle_color": "#CCCCBB", "accent_color": "#CC8800",
                "title_size": 64, "subtitle_size": 32, "org_size": 24},
        }
        return styles.get(tn, styles["party_building"])

    def _get_lower_third_style(self, tn):
        styles = {
            "party_building": {"bg_color": "0xB41E1E", "bg_opacity": 0.85,
                "text_color": "#FFFFFF", "font_size": 36},
            "conference": {"bg_color": "0x1E3A8A", "bg_opacity": 0.80,
                "text_color": "#FFFFFF", "font_size": 34},
            "visit": {"bg_color": "0x1E6B1E", "bg_opacity": 0.80,
                "text_color": "#FFFFFF", "font_size": 34},
            "study": {"bg_color": "0x8B6914", "bg_opacity": 0.80,
                "text_color": "#FFFFFF", "font_size": 32},
        }
        return styles.get(tn, styles["party_building"])
