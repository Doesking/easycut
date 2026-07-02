"""
渲染器：5步 FFmpeg 渲染流程
1. 逐个处理片段（缩放/变速/淡入淡出）
2. concat demuxer 拼接
3. 混合 BGM + 原声
4. 应用叠加层
5. 调色 + 最终编码
"""
import os
import subprocess
import logging
import tempfile
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoRenderer:
    def __init__(self, config: dict):
        self.resolution = config.get("resolution", [1920, 1080])
        self.fps = config.get("fps", 30)
        self.codec = config.get("codec", "libx264")
        self.bitrate = config.get("bitrate", "8M")

    def render(self, edit_plan, music_path, overlay_layers,
               color_config, output_path) -> dict:
        temp_dir = tempfile.mkdtemp(prefix="soe_render_")
        logger.info(f"开始渲染 | 临时目录: {temp_dir}")

        try:
            # 1. 拼接片段
            concat_video = self._concat_clips(edit_plan.clips, temp_dir)
            logger.info("  步骤1/5: 片段拼接完成")

            # 2. 混合音频
            if music_path and os.path.exists(music_path):
                mixed_video = self._mix_audio(concat_video, music_path,
                                              edit_plan.clips, temp_dir)
                logger.info("  步骤2/5: 音频混合完成")
            else:
                mixed_video = concat_video
                logger.info("  步骤2/5: 跳过（无BGM）")

            # 3. 叠加层
            overlaid_video = self._apply_overlays(mixed_video, overlay_layers, temp_dir)
            logger.info("  步骤3/5: 叠加层应用完成")

            # 4. 调色
            color_graded = self._apply_color_grade(overlaid_video, color_config, temp_dir)
            logger.info("  步骤4/5: 调色完成")

            # 5. 最终输出
            final_path = self._finalize(color_graded, output_path)
            info = self._get_video_info(final_path)
            logger.info(f"  步骤5/5: 渲染完成 → {final_path} ({info['duration']:.1f}s)")

            return {"path": final_path, "duration": info["duration"],
                    "size": info.get("size", 0)}

        except Exception as e:
            logger.error(f"渲染失败: {e}")
            raise
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _concat_clips(self, clips, temp_dir):
        processed = []
        for i, clip in enumerate(clips):
            out = os.path.join(temp_dir, f"clip_{i:04d}.mp4")
            self._process_single_clip(clip, out)
            processed.append(out)

        concat_list = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list, 'w') as f:
            for cp in processed:
                f.write(f"file '{cp}'\n")

        out = os.path.join(temp_dir, "concat_raw.mp4")
        self._run_ffmpeg([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c:v", self.codec, "-b:v", self.bitrate,
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(self.fps),
            "-s", f"{self.resolution[0]}x{self.resolution[1]}",
            "-movflags", "+faststart", out,
        ])
        return out

    def _process_single_clip(self, clip, output_path):
        filters = [
            f"scale={self.resolution[0]}:{self.resolution[1]}"
            f":force_original_aspect_ratio=decrease,"
            f"pad={self.resolution[0]}:{self.resolution[1]}"
            f":(ow-iw)/2:(oh-ih)/2:black,setsar=1"
        ]
        if clip.speed != 1.0:
            filters.append(f"setpts={1/clip.speed}*PTS")
        if clip.transition_in in ("fade", "fade_from_black", "fade_black"):
            filters.append("fade=t=in:st=0:d=0.8")
        if clip.transition_out in ("fade", "fade_to_black", "fade_black"):
            fs = clip.duration - 0.8
            if fs > 0:
                filters.append(f"fade=t=out:st={fs}:d=0.8")

        self._run_ffmpeg([
            "ffmpeg", "-y",
            "-ss", str(clip.start_time),
            "-i", clip.source_path,
            "-t", str(clip.duration),
            "-vf", ",".join(filters),
            "-c:v", self.codec, "-b:v", self.bitrate,
            "-an", "-r", str(self.fps), output_path,
        ])

    def _mix_audio(self, video_path, music_path, clips, temp_dir):
        total_dur = sum(c.duration for c in clips)

        # Check if video has audio stream
        has_audio = self._has_audio_stream(video_path)

        if not has_audio:
            # Video has no audio: just add BGM directly
            out = os.path.join(temp_dir, "mixed_audio.mp4")
            self._run_ffmpeg([
                "ffmpeg", "-y",
                "-i", video_path, "-i", music_path,
                "-filter_complex",
                f"[1:a]aloop=loop=-1:size=2e+09,"
                f"atrim=duration={total_dur},"
                f"afade=t=in:st=0:d=2,"
                f"afade=t=out:st={total_dur-3}:d=3,"
                f"volume=0.7[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", out,
            ])
            return out

        af = (
            f"[1:a]aloop=loop=-1:size=2e+09,"
            f"atrim=duration={total_dur},"
            f"afade=t=in:st=0:d=2,"
            f"afade=t=out:st={total_dur - 3}:d=3,"
            f"volume=0.7[bgm];"
            f"[0:a]volume=0.15[original];"
            f"[original][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        out = os.path.join(temp_dir, "mixed_audio.mp4")
        self._run_ffmpeg([
            "ffmpeg", "-y",
            "-i", video_path, "-i", music_path,
            "-filter_complex", af,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", out,
        ])
        return out

    def _has_audio_stream(self, path: str) -> bool:
        """检查视频是否有音频流"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_streams",
                 "-select_streams", "a", "-of", "json", path],
                capture_output=True, text=True, timeout=5)
            data = json.loads(result.stdout)
            return len(data.get("streams", [])) > 0
        except Exception:
            return False

    def _apply_overlays(self, video_path, overlays, temp_dir):
        if not overlays:
            return video_path

        # 检查 drawtext filter 是否可用
        has_drawtext = self._check_drawtext()

        fps = []
        for ov in overlays:
            if ov.get("type") in ("title_card", "ending_card"):
                start = ov.get("start_time", 0)
                dur = ov.get("duration", 4)
                if ov["type"] == "ending_card":
                    td = self._get_duration(video_path)
                    start = max(0, td + start)
                for elem in ov.get("elements", []):
                    if elem.get("type") == "text" and elem.get("content"):
                        if not has_drawtext:
                            continue
                        txt = elem["content"].replace("'", "'\\''").replace(":", "\\:")
                        fs = elem.get("fontsize", 48)
                        yoff = elem.get("y_offset", 0)
                        fps.append(
                            f"drawtext=text='{txt}':fontsize={fs}"
                            f":fontcolor=white:x=(w-text_w)/2"
                            f":y=(h-text_h)/2+{yoff}"
                            f":enable='between(t,{start},{start + dur})'"
                        )
            elif ov.get("type") == "lower_third":
                start = ov.get("start_time", 0)
                dur = ov.get("duration", 4)
                for elem in ov.get("elements", []):
                    if elem.get("type") == "rectangle":
                        x = elem.get("x", 60)
                        y = str(elem.get("y", "H-180")).replace("H", "h")
                        w = elem.get("width", 500)
                        h = elem.get("height", 80)
                        color = elem.get("color", "0xB41E1E")
                        opacity = elem.get("opacity", 0.85)
                        fps.append(
                            f"drawbox=x={x}:y={y}:w={w}:h={h}"
                            f":color={color}@{opacity}:t=fill"
                            f":enable='between(t,{start},{start + dur})'"
                        )
                    elif elem.get("type") == "text" and elem.get("content"):
                        if not has_drawtext:
                            continue
                        txt = elem["content"].replace("'", "'\\''").replace(":", "\\:")
                        fs = elem.get("fontsize", 36)
                        x = elem.get("x", 90)
                        y = str(elem.get("y", "H-165")).replace("H", "h")
                        fps.append(
                            f"drawtext=text='{txt}':fontsize={fs}"
                            f":fontcolor=white:x={x}:y={y}"
                            f":enable='between(t,{start},{start + dur})'"
                        )
        if not fps:
            return video_path
        out = os.path.join(temp_dir, "overlaid.mp4")
        self._run_ffmpeg([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", ",".join(fps),
            "-c:v", self.codec, "-b:v", self.bitrate,
            "-c:a", "copy", out,
        ])
        return out

    def _apply_color_grade(self, video_path, color_config, temp_dir):
        if not color_config:
            return video_path
        from .color_grade import ColorGrader
        fs = ColorGrader().to_ffmpeg_filter(color_config)
        if not fs:
            return video_path
        out = os.path.join(temp_dir, "color_graded.mp4")
        self._run_ffmpeg([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", fs,
            "-c:v", self.codec, "-b:v", self.bitrate,
            "-c:a", "copy", out,
        ])
        return out

    def _finalize(self, video_path, output_path):
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        self._run_ffmpeg([
            "ffmpeg", "-y", "-i", video_path,
            "-c:v", self.codec, "-b:v", self.bitrate,
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-pix_fmt", "yuv420p",
            output_path,
        ])
        return output_path

    def _check_drawtext(self) -> bool:
        """检查 FFmpeg 是否支持 drawtext filter"""
        try:
            r = subprocess.run(
                ["ffmpeg", "-filters"], capture_output=True, text=True)
            return "drawtext" in r.stdout
        except Exception:
            return False

    def _get_duration(self, path):
        try:
            r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                                "-show_format", path], capture_output=True, text=True)
            return float(json.loads(r.stdout).get("format", {}).get("duration", 0))
        except Exception:
            return 0

    def _get_video_info(self, path):
        try:
            r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                                "-show_format", path], capture_output=True, text=True)
            fmt = json.loads(r.stdout).get("format", {})
            return {"duration": float(fmt.get("duration", 0)),
                    "size": int(fmt.get("size", 0))}
        except Exception:
            return {"duration": 0, "size": 0}

    def _run_ffmpeg(self, cmd):
        logger.debug(f"FFmpeg: {' '.join(cmd[:6])}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr[-300:]}")
