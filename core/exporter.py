"""
多格式导出器：MP4 / MOV / 剪映兼容 XML 时间线
"""
import os
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger(__name__)

# 输出格式预设
FORMAT_PRESETS = {
    "mp4": {"ext": "mp4", "codec": "libx264", "mime": "video/mp4"},
    "mov": {"ext": "mov", "codec": "libx264", "mime": "video/quicktime"},
    "webm": {"ext": "webm", "codec": "libvpx-vp9", "mime": "video/webm"},
}

RESOLUTION_PRESETS = {
    "4k": (3840, 2160),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "vertical_1080": (1080, 1920),
    "square": (1080, 1080),
}

FPS_OPTIONS = [24, 25, 30, 60]


class MultiFormatExporter:
    """多格式导出器"""

    def __init__(self):
        pass

    def export_video(
        self,
        input_path: str,
        output_path: str,
        format: str = "mp4",
        resolution: str = "1080p",
        fps: int = 30,
        bitrate: str = "8M",
    ) -> str:
        """导出视频文件"""
        fmt = FORMAT_PRESETS.get(format, FORMAT_PRESETS["mp4"])
        res = RESOLUTION_PRESETS.get(resolution, (1920, 1080))

        if not output_path:
            output_path = input_path.rsplit(".", 1)[0] + f".{fmt['ext']}"

        if output_path == input_path:
            return input_path

        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-c:v", fmt["codec"], "-b:v", bitrate,
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(fps),
            "-s", f"{res[0]}x{res[1]}",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        logger.info(f"导出 {format.upper()}: {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            raise RuntimeError(f"导出失败: {result.stderr[-200:]}")

        return output_path

    def export_capcut_timeline(
        self,
        edit_plan,
        output_path: str,
        title: str = "",
    ) -> str:
        """
        导出剪映兼容的 XML 时间线文件

        生成 FCPXML 兼容格式，剪映桌面版可直接导入
        """
        if not output_path:
            output_path = edit_plan.title.replace(" ", "_") + "_timeline.xml"

        # 生成简化版 FCPXML
        root = ET.Element("fcpxml", version="1.8")

        # 资源库
        resources = ET.SubElement(root, "resources")
        resource_id = 0

        clip_map = {}
        for i, clip in enumerate(edit_plan.clips):
            rid = f"r{i+1}"
            asset = ET.SubElement(resources, "asset",
                                  id=rid,
                                  name=os.path.basename(clip.source_path),
                                  src=clip.source_path,
                                  start=f"{0}/{1}s",
                                  duration=f"{clip.duration}/{1}s",
                                  hasAudio="1",
                                  hasVideo="1")
            clip_map[i] = rid
            resource_id = i + 1

        # 主时间线
        tl = ET.SubElement(root, "fcpxml")
        project = ET.SubElement(root, "project", name=title or "EasyCut 时间线")
        seq = ET.SubElement(project, "sequence",
                            format=f"r{resource_id + 1}",
                            duration=f"{edit_plan.total_duration}/{1}s")

        spine = ET.SubElement(seq, "spine")
        ct = 0
        for i, clip in enumerate(edit_plan.clips):
            c = ET.SubElement(spine, "asset-clip",
                              ref=clip_map[i],
                              offset=f"{ct}/{1}s",
                              duration=f"{clip.duration}/{1}s",
                              name=f"{clip.phase or 'clip'}_{i}")
            ct += clip.duration

        # 格式化输出
        xml_str = ET.tostring(root, encoding="unicode")
        pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pretty)

        logger.info(f"导出剪映时间线: {output_path} ({len(edit_plan.clips)}片段)")
        return output_path

    def export_edl(self, edit_plan, output_path: str) -> str:
        """
        导出 EDL (Edit Decision List) 格式
        兼容 Premiere, DaVinci Resolve, Final Cut Pro
        """
        if not output_path:
            output_path = "timeline.edl"

        lines = [
            "TITLE: EasyCut Timeline",
            "FCM: NON-DROP FRAME",
            "",
        ]

        for i, clip in enumerate(edit_plan.clips, 1):
            # EDL 格式: 编号 卷名 模式 源入 源出 录入 录出
            src_in = self._timecode(clip.start_time)
            src_out = self._timecode(clip.end_time)
            rec_in = self._timecode(sum(c.duration for c in edit_plan.clips[:i-1]))
            rec_out = self._timecode(sum(c.duration for c in edit_plan.clips[:i]))

            clip_name = os.path.basename(clip.source_path)
            lines.append(
                f"{i:03d}  {clip_name[:8]:8s} V     C        "
                f"{src_in} {src_out} {rec_in} {rec_out}"
            )
            lines.append(f"* FROM CLIP NAME: {clip.source_path}")
            if clip.transition_in and clip.transition_in != "cut":
                lines.append(f"* EFFECT: {clip.transition_in.upper()}")

            lines.append("")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"导出 EDL: {output_path}")
        return output_path

    @staticmethod
    def _timecode(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        f = int((seconds - int(seconds)) * 30)
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
