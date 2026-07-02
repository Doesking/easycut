"""
EasyCut 转场特效模块
支持：淡入淡出、交叉溶解、滑动、擦除、缩放
"""
import subprocess, os, logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# 转场预设
TRANSITIONS = {
    "fade": {
        "name": "淡入淡出",
        "filter": "fade=t=in:d={dur}:alpha=1,fade=t=out:st={total_dur}:d={dur}:alpha=1",
    },
    "dissolve": {
        "name": "交叉溶解",
        "filter": "blend=all_expr='A*(1-min(T/{dur},1))+B*(min(T/{dur},1))'",
    },
    "slide_left": {
        "name": "左滑入",
        "filter": "overlay=x='W-min(W,T/{dur}*W)':y=0",
    },
    "slide_right": {
        "name": "右滑入",
        "filter": "overlay=x='-W+min(W,T/{dur}*W)':y=0",
    },
    "slide_up": {
        "name": "上滑入",
        "filter": "overlay=x=0:y='H-min(H,T/{dur}*H)'",
    },
    "slide_down": {
        "name": "下滑入",
        "filter": "overlay=x=0:y='-H+min(H,T/{dur}*H)'",
    },
    "wipe_left": {
        "name": "左擦除",
        "filter": "overlay=x='max(0,W-T/{dur}*W)':y=0",
    },
    "zoom_in": {
        "name": "缩放进入",
        "filter": "overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2,scale=iw*min(1,T/{dur}):ih*min(1,T/{dur})",
    },
}


def build_transition_filter(
    transition_type: str,
    clip_duration: float,
    transition_dur: float = 0.5,
) -> str:
    """生成转场滤镜"""
    cfg = TRANSITIONS.get(transition_type, TRANSITIONS["fade"])
    total_dur = clip_duration - transition_dur

    filter_str = cfg["filter"].format(
        dur=transition_dur,
        total_dur=total_dur,
    )
    return filter_str


def apply_transition_clip(
    input_path: str,
    output_path: str,
    transition: str = "fade",
    duration: float = 0.5,
) -> bool:
    """对单个视频片段应用转场"""
    # 先获取视频时长
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", input_path,
    ]
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        import json
        info = json.loads(result.stdout)
        clip_dur = float(info["format"]["duration"])
    except Exception:
        clip_dur = 3.0

    if transition == "fade":
        vf = f"fade=t=in:d={duration},fade=t=out:st={clip_dur-duration}:d={duration}"
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", vf,
            "-af", f"afade=t=in:d={duration},afade=t=out:st={clip_dur-duration}:d={duration}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output_path,
        ]
    else:
        # 其他转场类型用于片段拼接
        vf = build_transition_filter(transition, clip_dur, duration)
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            output_path,
        ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"Transition error: {result.stderr[-200:]}")
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Transition exception: {e}")
        return False


def apply_transition_between(
    clip_a: str,
    clip_b: str,
    output_path: str,
    transition: str = "dissolve",
    duration: float = 0.5,
) -> bool:
    """在两个片段之间应用转场（xfade）"""
    cmd = [
        "ffmpeg", "-y",
        "-i", clip_a, "-i", clip_b,
        "-filter_complex",
        f"xfade=transition={transition}:duration={duration}:offset=0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"Xfade error: {result.stderr[-200:]}")
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Xfade exception: {e}")
        return False


def apply_transition_chain(
    clips: List[str],
    output_path: str,
    transition: str = "dissolve",
    duration: float = 0.5,
) -> bool:
    """多片段连续转场拼接（使用 xfade 链）"""
    import json as _json

    if len(clips) == 0:
        return False
    if len(clips) == 1:
        import shutil
        shutil.copy(clips[0], output_path)
        return os.path.exists(output_path)

    # 获取每个片段的时长
    durations = []
    for clip in clips:
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", clip],
                capture_output=True, text=True, timeout=10,
            )
            info = _json.loads(probe.stdout)
            durations.append(float(info["format"]["duration"]))
        except Exception:
            durations.append(3.0)

    # 构建 xfade 滤镜链
    filter_parts = []
    inputs = []
    cumulative = 0.0  # 累计偏移（第一个片段之后的总时长）

    for i, clip in enumerate(clips):
        inputs.extend(["-i", clip])
        if i == 0:
            cumulative += durations[i]
            continue

        prev = f"[{i-1}:v]" if i == 1 else f"[xf{i-2}]"
        curr = f"[{i}:v]"
        out = f"[outv]" if i == len(clips) - 1 else f"[xf{i-1}]"
        # offset: 第一个片段的总时长减去 transition 时长（因为与下一个片段重叠）
        offset = cumulative - duration
        filter_parts.append(
            f"{prev}{curr}xfade=transition={transition}:duration={duration}:offset={offset}{out}"
        )
        cumulative += durations[i] - duration  # 每个后续片段减去重叠

    filter_complex = ";".join(filter_parts)

    # 音频混音
    audio_parts = []
    for i in range(len(clips)):
        audio_parts.append(f"[{i}:a]adelay={int(cumulative * 1000) if i == 0 else 0}|{int(cumulative * 1000) if i == 0 else 0}")
    # 简化：用 amix
    audio_mix = "".join(f"[{i}:a]" for i in range(len(clips)))
    filter_complex += f";{audio_mix}amix=inputs={len(clips)}:duration=longest:dropout_transition=3[aout]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"Transition chain error: {result.stderr[-300:]}")
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Transition chain exception: {e}")
        return False
