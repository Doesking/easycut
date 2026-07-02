"""
音乐选择器：BPM/情绪/能量曲线多维匹配 + 节拍分析
"""
import os
import json
import subprocess
import logging
import random
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATE_MUSIC_MAP = {
    "party_building": {
        "preferred_mood": ["majestic", "solemn", "patriotic", "inspiring"],
        "preferred_bpm": (60, 80),
        "preferred_energy": ["build_up", "steady"],
    },
    "conference": {
        "preferred_mood": ["professional", "steady", "uplifting"],
        "preferred_bpm": (70, 100),
        "preferred_energy": ["steady", "wave"],
    },
    "visit": {
        "preferred_mood": ["hopeful", "bright", "grand"],
        "preferred_bpm": (75, 110),
        "preferred_energy": ["build_up", "wave"],
    },
    "study": {
        "preferred_mood": ["focused", "calm", "gentle"],
        "preferred_bpm": (60, 80),
        "preferred_energy": ["steady", "build_up"],
    },
    "landscape": {
        "preferred_mood": ["ambient", "atmospheric", "ethereal", "cinematic"],
        "preferred_bpm": (50, 80),
        "preferred_energy": ["build_up", "ambient"],
    },
}


class MusicSelector:
    # 版权免费音乐推荐源
    COPYRIGHT_FREE_SOURCES = [
        {"name": "Pixabay Music", "url": "https://pixabay.com/music/"},
        {"name": "Uppbeat", "url": "https://uppbeat.io/"},
        {"name": "Mixkit", "url": "https://mixkit.co/free-stock-music/"},
        {"name": "YouTube Audio Library", "url": "https://studio.youtube.com/"},
    ]

    def __init__(self, library_path: str, config: dict):
        self.library_path = Path(library_path)
        self.config = config
        self.library = self._load_library()
        self._user_music: Dict[str, str] = {}  # task_id -> music_path

    def _load_library(self) -> List[Dict]:
        metadata_path = self.library_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        lib = []
        for ext in ('*.mp3', '*.wav', '*.m4a', '*.aac'):
            for f in self.library_path.glob(ext):
                info = self._probe_audio(str(f))
                lib.append({
                    "filename": f.name, "path": str(f),
                    "bpm": 75, "duration": info.get("duration", 180),
                    "mood": ["general"], "tags": [],
                    "energy_curve": "steady", "key": "C_major",
                })
        return lib

    def _probe_audio(self, path: str) -> dict:
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
                   "-show_format", path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            return {
                "duration": float(fmt.get("duration", 0)),
                "bitrate": int(fmt.get("bit_rate", 0)),
            }
        except Exception:
            return {"duration": 180, "bitrate": 192000}

    def select(self, template_name: str, target_duration: float,
               mood_override: Optional[str] = None) -> str:
        prefs = TEMPLATE_MUSIC_MAP.get(template_name,
                                        TEMPLATE_MUSIC_MAP["party_building"])

        if not self.library:
            logger.warning("音乐库为空，使用静默输出")
            return ""

        candidates = []
        for track in self.library:
            score = 0.0
            tm = [mood_override] if mood_override else prefs.get("preferred_mood", [])
            score += len(set(tm) & set(track.get("mood", []))) * 3.0

            pb = prefs.get("preferred_bpm", (60, 100))
            tb = track.get("bpm", 75)
            if pb[0] <= tb <= pb[1]:
                score += 2.0
            else:
                score -= min(abs(tb - pb[0]), abs(tb - pb[1])) * 0.02

            td = track.get("duration", 0)
            if td >= target_duration:
                score += 1.0
            elif td >= target_duration * 0.7:
                score += 0.5

            pe = prefs.get("preferred_energy", [])
            if track.get("energy_curve") in pe:
                score += 1.5

            candidates.append((track, score))

        candidates.sort(key=lambda x: x[1], reverse=True)

        if not candidates or candidates[0][1] <= 0:
            best = random.choice(self.library)
        else:
            best = candidates[0][0]

        track_path = best.get("path", str(self.library_path / best["filename"]))
        logger.info(f"选择BGM: {best.get('filename', track_path)} (BPM:{best.get('bpm')})")
        return track_path

    def analyze_beats(self, music_path: str) -> List[float]:
        if not music_path:
            return []
        return self._estimate_beats(music_path)

    def _estimate_beats(self, music_path: str) -> List[float]:
        bpm = 75
        for track in self.library:
            if track.get("path") == music_path or track.get("filename") in music_path:
                bpm = track.get("bpm", 75)
                break

        try:
            cmd = ["ffprobe", "-v", "quiet", "-show_entries",
                   "format=duration", "-of", "json", music_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            duration = float(data.get("format", {}).get("duration", 180))
        except Exception:
            duration = 180

        beat_interval = 60.0 / bpm
        beats = []
        t = 0
        while t < duration:
            beats.append(t)
            t += beat_interval

        logger.info(f"估算节拍: BPM={bpm}, {len(beats)}个节拍点")
        return beats

    def register_user_music(self, task_id: str, music_path: str):
        """注册用户上传的背景音乐"""
        self._user_music[task_id] = music_path
        # 分析并加入音乐库
        info = self._probe_audio(music_path)
        self.library.append({
            "filename": os.path.basename(music_path),
            "path": music_path,
            "bpm": 75,
            "duration": info.get("duration", 180),
            "mood": ["custom"],
            "tags": ["user_upload"],
            "energy_curve": "steady",
            "key": "C_major",
        })
        logger.info(f"用户音乐已注册: {music_path}")

    def select(self, template_name: str, target_duration: float,
               mood_override: Optional[str] = None,
               user_music_path: Optional[str] = None) -> str:
        """选择音乐，优先使用用户上传的"""
        if user_music_path and os.path.exists(user_music_path):
            logger.info(f"使用用户指定BGM: {user_music_path}")
            return user_music_path

        # 原始选择逻辑
        return self._select_from_library(template_name, target_duration, mood_override)

    def _select_from_library(self, template_name: str, target_duration: float,
                              mood_override: Optional[str] = None) -> str:
        """从音乐库中选择"""
        prefs = TEMPLATE_MUSIC_MAP.get(template_name,
                                        TEMPLATE_MUSIC_MAP["party_building"])

        if not self.library:
            logger.warning("音乐库为空，生成默认BGM")
            return self._generate_default_bgm(target_duration)

        candidates = []
        for track in self.library:
            score = 0.0
            tm = [mood_override] if mood_override else prefs.get("preferred_mood", [])
            score += len(set(tm) & set(track.get("mood", []))) * 3.0

            pb = prefs.get("preferred_bpm", (60, 100))
            tb = track.get("bpm", 75)
            if pb[0] <= tb <= pb[1]:
                score += 2.0
            else:
                score -= min(abs(tb - pb[0]), abs(tb - pb[1])) * 0.02

            td = track.get("duration", 0)
            if td >= target_duration:
                score += 1.0
            elif td >= target_duration * 0.7:
                score += 0.5

            pe = prefs.get("preferred_energy", [])
            if track.get("energy_curve") in pe:
                score += 1.5

            candidates.append((track, score))

        candidates.sort(key=lambda x: x[1], reverse=True)

        if not candidates or candidates[0][1] <= 0:
            logger.warning("无合适音乐，生成默认BGM")
            return self._generate_default_bgm(target_duration)

        best = candidates[0][0]
        track_path = best.get("path", str(self.library_path / best["filename"]))
        logger.info(f"选择BGM: {best.get('filename', track_path)} (BPM:{best.get('bpm')})")
        return track_path

    def _generate_default_bgm(self, duration: float) -> str:
        """用 FFmpeg 生成简单的默认背景音乐（版权免费）"""
        output = str(self.library_path / f"_default_bgm_{int(duration)}s.mp3")

        if os.path.exists(output):
            return output

        # 生成一段简单的环境音乐（正弦波 + 淡入淡出）
        freq = 220  # A3 音符
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={freq}:duration={duration}",
            "-af", (
                "aecho=0.8:0.5:40:0.3,"
                "lowpass=f=800,"
                f"afade=t=in:st=0:d=2,"
                f"afade=t=out:st={duration-3}:d=3,"
                "volume=0.15"
            ),
            "-c:a", "libmp3lame", "-b:a", "128k",
            output,
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            logger.info(f"生成默认BGM: {output}")
        except Exception as e:
            logger.warning(f"默认BGM生成失败: {e}")
            return ""

        return output

    def get_copyright_free_sources(self) -> List[Dict]:
        """获取版权免费音乐源列表"""
        return self.COPYRIGHT_FREE_SOURCES
