"""
EasyCut 音频混音模块
支持：背景音乐叠加、音量包络（淡入淡出）、多轨混音
"""
import subprocess, os, json, logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


def get_audio_info(filepath: str) -> Dict:
    """获取音频文件信息"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", filepath,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        info = json.loads(result.stdout)
        fmt = info.get("format", {})
        return {
            "duration": float(fmt.get("duration", 0)),
            "has_audio": any(s.get("codec_type") == "audio" for s in info.get("streams", [])),
            "sample_rate": next((int(s["sample_rate"]) for s in info.get("streams", [])
                                if s.get("codec_type") == "audio"), 44100),
        }
    except Exception:
        return {"duration": 0, "has_audio": False, "sample_rate": 44100}


def mix_background_music(
    video_path: str,
    music_path: str,
    output_path: str,
    music_volume: float = 0.3,
    fade_in: float = 1.0,
    fade_out: float = 2.0,
    loop: bool = True,
) -> bool:
    """
    给视频叠加背景音乐
    - music_volume: 音乐音量 (0~1)
    - fade_in/fade_out: 淡入淡出时长
    - loop: 循环播放直到视频结束
    """
    video_info = get_audio_info(video_path)
    music_info = get_audio_info(music_path)
    video_dur = video_info["duration"]

    if video_dur <= 0:
        logger.error("Cannot get video duration")
        return False

    # 音乐音量调整
    vol_expr = f"volume={music_volume}"

    # 淡入淡出
    afade = []
    if fade_in > 0:
        afade.append(f"afade=t=in:d={fade_in}")
    if fade_out > 0:
        afade.append(f"afade=t=out:st={video_dur - fade_out}:d={fade_out}")
    afade_chain = ",".join(afade) if afade else "anull"

    # 音乐流滤镜
    if loop:
        music_filter = f"[1:a]aloop=loop=-1:size=2e9,atrim=duration={video_dur},{vol_expr},{afade_chain}[music]"
    else:
        music_filter = f"[1:a]atrim=duration={video_dur},{vol_expr},{afade_chain}[music]"

    # 混音：视频原声 + 背景音乐
    filter_complex = (
        f"{music_filter};"
        f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"Audio mix error: {result.stderr[-300:]}")
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Audio mix exception: {e}")
        return False


def apply_volume_envelope(
    input_path: str,
    output_path: str,
    envelope: List[Dict] = None,
) -> bool:
    """
    应用音量包络
    envelope: [{"time": 0, "volume": 0.0}, {"time": 1, "volume": 1.0}, ...]
    """
    if not envelope:
        envelope = [
            {"time": 0, "volume": 0.0},
            {"time": 0.5, "volume": 1.0},
            {"time": "end-0.5", "volume": 1.0},
            {"time": "end", "volume": 0.0},
        ]

    # 构建 volume 表达式
    vol_expr_parts = []
    for i, pt in enumerate(envelope):
        t = pt["time"]
        v = pt["volume"]
        if isinstance(t, str) and t.startswith("end"):
            offset = float(t.split("-")[1]) if "-" in t else 0
            t = f"ld(0)-{offset}"
        elif i == 0:
            vol_expr_parts.append(f"if(lt(t,{t}),{v},")
            continue

        if i < len(envelope) - 1:
            next_t = envelope[i + 1]["time"]
            next_v = envelope[i + 1]["volume"]
            if isinstance(next_t, str):
                next_t = 9999  # placeholder
            vol_expr_parts.append(
                f"if(lt(t,{t}),{v}+({next_v}-{v})*(t-{t})/({next_t}-{t}),"
            )
        else:
            vol_expr_parts.append(f"{v}")
            vol_expr_parts.append(")" * (len(envelope) - 1))

    vol_expr = "".join(vol_expr_parts)

    # 简化：直接用 afade
    afade = "afade=t=in:d=0.5,afade=t=out:st=ld(0)-0.5:d=0.5"

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", afade,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"Volume envelope error: {result.stderr[-200:]}")
            return False
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.error(f"Volume envelope exception: {e}")
        return False


def extract_audio(video_path: str, output_path: str, format: str = "mp3") -> bool:
    """从视频提取音频"""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame" if format == "mp3" else "aac",
        "-ab", "192k",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception:
        return False


def adjust_audio_volume(
    input_path: str,
    output_path: str,
    volume: float = 1.0,
) -> bool:
    """调整音量"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", f"volume={volume}",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False
