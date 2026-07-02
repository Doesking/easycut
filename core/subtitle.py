"""
Whisper 语音识别自动字幕模块
本地运行，支持：
- faster-whisper 模型（tiny/base/small/medium/large）
- 自动语言检测 + 指定语言
- SRT/VTT 字幕格式输出
- 时间轴对齐
"""
import os, logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

# 内置字幕样式
SUBTITLE_STYLES = {
    "default": {
        "fontsize": 20,
        "fontcolor": "white",
        "bordercolor": "black",
        "borderw": 2,
        "alignment": 2,  # 底部居中
    },
    "movie": {
        "fontsize": 18,
        "fontcolor": "white",
        "bordercolor": "black@0.5",
        "borderw": 1.5,
        "alignment": 2,
    },
    "highlight": {
        "fontsize": 22,
        "fontcolor": "yellow",
        "bordercolor": "black",
        "borderw": 3,
        "alignment": 2,
    },
}


class WhisperSubtitle:
    def __init__(self, model_size: str = "medium", device: str = "auto",
                 compute_type: str = "auto", hf_endpoint: str = None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.hf_endpoint = hf_endpoint or os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            os.environ.setdefault("HF_ENDPOINT", self.hf_endpoint)
            logger.info(f"Loading Whisper model: {self.model_size} (HF: {self.hf_endpoint})")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(Path.home() / ".cache" / "whisper"),
            )
        return self._model

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> List[Dict]:
        """转录音频，返回分段列表 [{start, end, text}]"""
        model = self._load_model()
        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        logger.info(f"Detected language: {info.language} (prob={info.language_probability:.2f})")

        result = []
        for seg in segments:
            result.append({
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
            })
        return result

    def to_srt(self, segments: List[Dict]) -> str:
        """分段列表 → SRT 格式"""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = self._fmt_time(seg["start"])
            end = self._fmt_time(seg["end"])
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(seg["text"])
            lines.append("")
        return "\n".join(lines)

    def to_vtt(self, segments: List[Dict]) -> str:
        """分段列表 → VTT 格式"""
        lines = ["WEBVTT", ""]
        for i, seg in enumerate(segments, 1):
            start = self._fmt_time(seg["start"], ms_sep=".")
            end = self._fmt_time(seg["end"], ms_sep=".")
            lines.append(f"{start} --> {end}")
            lines.append(seg["text"])
            lines.append("")
        return "\n".join(lines)

    def to_ass(self, segments: List[Dict], style: str = "default") -> str:
        """分段列表 → ASS 格式（带样式）"""
        sty = SUBTITLE_STYLES.get(style, SUBTITLE_STYLES["default"])
        fontsize = sty["fontsize"]
        fontcolor = sty["fontcolor"]
        bordercolor = sty["bordercolor"]
        borderw = sty["borderw"]
        align = sty["alignment"]

        lines = [
            "[Script Info]",
            "Title: EasyCut Auto Subtitle",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: None",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,PingFang SC,{fontsize},&H00FFFFFF,&H000000FF,"
            f"&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,"
            f"{borderw},0,{align},10,10,10,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text",
        ]
        for seg in segments:
            start = self._fmt_ass_time(seg["start"])
            end = self._fmt_ass_time(seg["end"])
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{seg['text']}")
        return "\n".join(lines)

    @staticmethod
    def _fmt_time(seconds: float, ms_sep: str = ",") -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}{ms_sep}{ms:03d}"

    @staticmethod
    def _fmt_ass_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def burn_subtitles(
    video_path: str,
    srt_path: str,
    output_path: str,
    fontsize: int = 20,
    fontcolor: str = "white",
    borderw: int = 2,
) -> bool:
    """使用 FFmpeg 将字幕烧录到视频"""
    import subprocess

    # FFmpeg subtitles filter
    # 对 SRT 路径进行转义处理
    escaped_srt = srt_path.replace("\\", "/").replace(":", "\\\\:")
    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    # 使用 subtitles filter
    vf = (
        f"subtitles='{escaped_srt}':"
        f"force_style='Fontsize={fontsize},"
        f"PrimaryColour=&H{_color_to_ass(fontcolor)},"
        f"OutlineColour=&H00000000,"
        f"Outline={borderw},"
        f"Alignment=2'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-crf", "20",
        "-c:a", "copy",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"FFmpeg subtitle burn failed: {result.stderr[-200:]}")
            return False
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Subtitle burn error: {e}")
        return False


def _color_to_ass(color_name: str) -> str:
    """颜色名 → ASS 颜色代码（ABGR）"""
    colors = {
        "white": "00FFFFFF",
        "yellow": "0000FFFF",
        "green": "0000FF00",
        "cyan": "00FFFF00",
        "red": "000000FF",
        "blue": "00FF0000",
    }
    return colors.get(color_name.lower(), "00FFFFFF")
