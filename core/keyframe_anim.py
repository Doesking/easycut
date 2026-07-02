"""
EasyCut 关键帧动画模块
支持：Ken Burns 效果（推拉摇移）、缓入缓出
"""
import subprocess, os, json, logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# 缓动函数（返回 0~1 的时间映射）
EASING = {
    "linear": "t",
    "ease_in": "t*t",
    "ease_out": "t*(2-t)",
    "ease_in_out": "if(lt(t,0.5),2*t*t,-1+(4-2*t)*t)",
    "smooth": "t*t*(3-2*t)",
}

PRESETS = {
    "ken_burns_slow": {
        "name": "慢速推镜",
        "x": "(iw-iw/zoom)/2", "y": "(ih-ih/zoom)/2",
        "zoom_start": 1.0, "zoom_end": 1.15,
    },
    "ken_burns_dramatic": {
        "name": "戏剧推镜",
        "x": "(iw-iw/zoom)/2", "y": "(ih-ih/zoom)/2",
        "zoom_start": 1.0, "zoom_end": 1.3,
    },
    "pan_left": {
        "name": "左移镜头",
        "x": "iw*0.1*(1-n/td)", "y": "(ih-ih/zoom)/2",
        "zoom_start": 1.1, "zoom_end": 1.1,
    },
    "pan_right": {
        "name": "右移镜头",
        "x": "iw*0.1*n/td", "y": "(ih-ih/zoom)/2",
        "zoom_start": 1.1, "zoom_end": 1.1,
    },
    "zoom_in": {
        "name": "推进聚焦",
        "x": "(iw-iw/zoom)/2", "y": "(ih-ih/zoom)/2",
        "zoom_start": 1.0, "zoom_end": 1.5,
    },
    "zoom_out": {
        "name": "拉远全景",
        "x": "(iw-iw/zoom)/2", "y": "(ih-ih/zoom)/2",
        "zoom_start": 1.5, "zoom_end": 1.0,
    },
}


def build_ken_burns_filter(
    preset: str = "ken_burns_slow",
    duration: float = 3.0,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> str:
    """生成 Ken Burns 效果的 FFmpeg 滤镜链"""
    cfg = PRESETS.get(preset, PRESETS["ken_burns_slow"])
    total_frames = int(duration * fps)

    # zoom 从 start 到 end 线性过渡（使用 zoom+delta 避免 ffmpeg 表达式解析问题）
    zoom_delta = (cfg['zoom_end'] - cfg['zoom_start']) / total_frames
    zoom_expr = f"zoom+{zoom_delta}"

    # x/y 表达式使用预设值
    x_expr = cfg.get("x", "(iw-iw/zoom)/2")
    y_expr = cfg.get("y", "(ih-ih/zoom)/2")

    filter_str = (
        f"zoompan=z='{zoom_expr}':"
        f"x='{x_expr}':y='{y_expr}':"
        f"d={total_frames}:s={width}x{height}:fps={fps}"
    )

    return filter_str


def apply_ken_burns(
    input_path: str,
    output_path: str,
    preset: str = "ken_burns_slow",
    duration: float = 3.0,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
) -> bool:
    """对单张图片/视频应用 Ken Burns 效果"""
    zoompan = build_ken_burns_filter(preset, duration, width, height, fps)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", f"[0:v]{zoompan},trim=duration={duration}[out]",
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"Ken Burns error: {result.stderr[-300:]}")
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except subprocess.TimeoutExpired:
        logger.error("Ken Burns timeout")
        return False


def build_crop_animation(
    duration: float = 3.0,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    start_crop: str = "iw:ih:0:0",
    end_crop: str = "iw:ih:0:0",
    easing: str = "ease_in_out",
) -> str:
    """生成裁剪动画（用于镜头运动）"""
    easing_fn = EASING.get(easing, "t")
    total_frames = int(duration * fps)

    return (
        f"crop={start_crop},"
        f"zoompan=z='1':x='0':y='0':d={total_frames}:s={width}x{height}:fps={fps}"
    )
