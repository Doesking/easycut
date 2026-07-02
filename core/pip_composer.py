"""
EasyCut 画中画 / 多轨道叠加模块
支持：PIP、左右分屏、上下分屏、四宫格
"""
import subprocess, os, logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# PIP 位置预设
PIP_POSITIONS = {
    "top_left":      {"x": "10", "y": "10"},
    "top_right":     {"x": "W-w-10", "y": "10"},
    "bottom_left":   {"x": "10", "y": "H-h-10"},
    "bottom_right":  {"x": "W-w-10", "y": "H-h-10"},
    "center":        {"x": "(W-w)/2", "y": "(H-h)/2"},
}

# 画中画大小预设
PIP_SIZES = {
    "small": 0.25,
    "medium": 0.35,
    "large": 0.5,
}

# 分屏布局
SPLIT_LAYOUTS = ["left_right", "top_bottom", "quad"]


def pip_overlay(
    main_path: str,
    pip_path: str,
    output_path: str,
    position: str = "bottom_right",
    pip_size: str = "medium",
    width: int = 1920,
    height: int = 1080,
) -> bool:
    """画中画：在主流上叠加小窗"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    scale = PIP_SIZES.get(pip_size, 0.35)
    pos = PIP_POSITIONS.get(position, PIP_POSITIONS["bottom_right"])
    pip_w = int(width * scale)
    pip_h = int(height * scale)

    # 主视频缩放到目标分辨率，PIP 视频缩放到小窗大小
    filter_str = (
        f"[0:v]scale={width}:{height},setsar=1[main];"
        f"[1:v]scale={pip_w}:{pip_h},setsar=1[pip];"
        f"[main][pip]overlay={pos['x']}:{pos['y']}"
    )

    return _run_ffmpeg(main_path, pip_path, output_path, filter_str)


def split_screen(
    left_path: str,
    right_path: str,
    output_path: str,
    layout: str = "left_right",
    width: int = 1920,
    height: int = 1080,
) -> bool:
    """分屏：左右/上下/四宫格"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if layout == "left_right":
        filter_str = (
            f"[0:v]scale={width//2}:{height},setsar=1[left];"
            f"[1:v]scale={width//2}:{height},setsar=1[right];"
            f"[left][right]hstack"
        )
    elif layout == "top_bottom":
        filter_str = (
            f"[0:v]scale={width}:{height//2},setsar=1[top];"
            f"[1:v]scale={width}:{height//2},setsar=1[bot];"
            f"[top][bot]vstack"
        )
    elif layout == "quad":
        hw, hh = width // 2, height // 2
        filter_str = (
            f"[0:v]scale={hw}:{hh},setsar=1[tl];"
            f"[1:v]scale={hw}:{hh},setsar=1[tr];"
            f"[tl][tr]hstack[top];"
            f"[top][top]vstack"
        )
    else:
        logger.error(f"Unknown layout: {layout}")
        return False

    return _run_ffmpeg(left_path, right_path, output_path, filter_str)


def multi_clip_timeline(
    clips: List[Dict],
    output_path: str,
    width: int = 1920,
    height: int = 1080,
) -> bool:
    """多片段时间轴合成：按顺序拼接 + 支持 PIP 片段"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if not clips:
        return False

    # 构建 concat 滤镜
    inputs = []
    vf_parts = []
    af_parts = []
    total = len(clips)

    for i, clip in enumerate(clips):
        path = clip.get("path", "")
        speed = clip.get("speed", 1.0)
        is_pip = clip.get("pip", False)
        pip_pos = clip.get("pip_position", "bottom_right")
        pip_size = clip.get("pip_size", "small")

        if not os.path.exists(path):
            logger.warning(f"Clip not found: {path}")
            continue

        inputs.extend(["-i", path])

        if is_pip and i > 0:
            # PIP 片段
            scale = PIP_SIZES.get(pip_size, 0.25)
            pos = PIP_POSITIONS.get(pip_pos, PIP_POSITIONS["bottom_right"])
            vf_parts.append(
                f"[{i*2}:v]scale={width}:{height},setsar=1[main{i}];"
                f"[{i*2+1}:v]scale={int(width*scale)}:{int(height*scale)}"
                f"[pip{i}];[main{i}][pip{i}]overlay={pos['x']}:{pos['y']}[v{i}]"
            )
        elif speed != 1.0:
            vf_parts.append(f"[{i*2}:v]setpts={1/speed:.4f}*PTS[v{i}]")
        else:
            vf_parts.append(f"[{i*2}:v]scale={width}:{height},setsar=1[v{i}]")

        if speed != 1.0:
            from core.speed_control import _build_atempo
            af_parts.append(f"[{i*2+1}:a]{_build_atempo(speed)}[a{i}]")
        else:
            af_parts.append(f"[{i*2+1}:a]aformat=sample_rates=44100[a{i}]")

    # Concat all
    v_labels = "".join(f"[v{i}]" for i in range(len(vf_parts)))
    a_labels = "".join(f"[a{i}]" for i in range(len(af_parts)))
    filter_str = ";".join(vf_parts + af_parts) + f";{v_labels}concat=n={len(vf_parts)}:v=1:a=0[v];{a_labels}concat=n={len(af_parts)}:v=0:a=1[a]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            logger.error(f"Timeline build failed: {r.stderr[-500:]}")
            return False
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Timeline error: {e}")
        return False


def _run_ffmpeg(main: str, secondary: str, output: str, vf: str) -> bool:
    """通用 FFmpeg 双输入叠加"""
    cmd = [
        "ffmpeg", "-y",
        "-i", main, "-i", secondary,
        "-filter_complex", vf,
        "-map", "0:a",
        "-c:v", "libx264", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            logger.error(f"FFmpeg failed: {r.stderr[-300:]}")
            return False
        return os.path.exists(output)
    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        return False
