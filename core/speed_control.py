"""
EasyCut 视频变速模块
支持：0.25x ~ 4x 变速，独立控制视频/音频速度
"""
import subprocess, os, logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 预设变速档位
SPEED_PRESETS = {
    "0.25x": 0.25, "0.5x": 0.5, "0.75x": 0.75,
    "1x": 1.0,
    "1.25x": 1.25, "1.5x": 1.5, "2x": 2.0, "3x": 3.0, "4x": 4.0,
}


def change_speed(
    input_path: str,
    output_path: str,
    speed: float = 1.0,
    video_only: bool = False,
    audio_only: bool = False,
) -> bool:
    """变速视频，保持音调不变"""
    if speed == 1.0:
        # 不需要变速
        import shutil
        shutil.copy2(input_path, output_path)
        return True

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # FFmpeg setpts 用于视频变速，atempo 用于音频变速
    # atempo 范围 0.5 ~ 2.0，超出需要链式调用
    vf = f"setpts={1/speed:.4f}*PTS" if not audio_only else "null"
    af = _build_atempo(speed) if not video_only else "anull"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", f"[0:v]{vf}[v];[0:a]{af}[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            logger.error(f"Speed change failed: {r.stderr[-300:]}")
            return False
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Speed change error: {e}")
        return False


def _build_atempo(speed: float) -> str:
    """构建 atempo 滤镜链，支持 0.25x ~ 4x"""
    if 0.5 <= speed <= 2.0:
        return f"atempo={speed:.4f}"

    # 链式 atempo（每次最多 2x）
    remaining = speed
    chain = []
    while remaining > 2.0:
        chain.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        chain.append("atempo=0.5")
        remaining /= 0.5
    chain.append(f"atempo={remaining:.4f}")
    return ",".join(chain)


def get_clip_duration(input_path: str) -> float:
    """获取视频时长（秒）"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired):
        return 0.0
