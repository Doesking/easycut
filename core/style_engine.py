"""
风格引擎：根据用户文字描述动态调整剪辑参数
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# 风格关键词映射
STYLE_KEYWORDS = {
    # 节奏
    "快节奏": {"pace": "fast", "clip_duration_bias": -0.3, "transition_speed": 1.3},
    "慢节奏": {"pace": "slow", "clip_duration_bias": 0.3, "transition_speed": 0.7},
    "紧张": {"pace": "intense", "clip_duration_bias": -0.4, "transition_speed": 1.5},
    "舒缓": {"pace": "gentle", "clip_duration_bias": 0.4, "transition_speed": 0.6},
    "大气": {"pace": "grand", "clip_duration_bias": 0.2, "transition_speed": 0.8},

    # 调色
    "暖色调": {"color_tone": "warm"},
    "冷色调": {"color_tone": "professional"},
    "明亮": {"color_tone": "bright"},
    "电影感": {"color_tone": "warm_red", "vignette": 1.2, "letterbox": True},
    "纪录片": {"color_tone": "professional", "vignette": 0.8},
    "复古": {"color_tone": "warm", "saturation_bias": -0.1},
    "高饱和度": {"saturation_bias": 0.2},
    "黑白": {"color_tone": "bw"},

    # 转场
    "硬切": {"transition": "cut"},
    "淡入淡出": {"transition": "fade"},
    "叠化": {"transition": "dissolve"},
    "闪白": {"transition": "flash_white"},
    "闪黑": {"transition": "flash_black"},

    # 字幕
    "字幕": {"subtitles": True},
    "无字幕": {"subtitles": False},
    "大字幕": {"subtitle_size": 1.2},
    "小字幕": {"subtitle_size": 0.8},

    # 特效
    "抖动": {"camera_shake": 0.5},
    "缩放": {"ken_burns": True},
    "慢动作": {"slow_motion": True, "speed_factor": 0.5},
    "快放": {"speed_up": True, "speed_factor": 2.0},

    # 音乐情绪
    "激昂": {"music_mood": "inspiring"},
    "庄重": {"music_mood": "solemn"},
    "温馨": {"music_mood": "warm"},
    "活泼": {"music_mood": "lively"},
    "科技感": {"music_mood": "futuristic"},
}


class StyleEngine:
    """风格引擎：解析用户描述 → 剪辑参数"""

    def parse(self, description: str) -> Dict:
        """
        解析风格描述，返回剪辑参数配置

        Args:
            description: 用户输入的风格描述文字

        Returns:
            {
                "pace": "normal",
                "color_tone": "warm_red",
                "transition": "fade",
                "transition_speed": 1.0,
                "clip_duration_bias": 0.0,
                "subtitles": True,
                "subtitle_size": 1.0,
                "vignette": 0.0,
                "letterbox": False,
                "saturation_bias": 0.0,
                "speed_factor": 1.0,
                "ken_burns": False,
                "music_mood": "majestic",
                "description": "原始描述",
            }
        """
        config = {
            "pace": "normal",
            "color_tone": "warm_red",
            "transition": "fade",
            "transition_speed": 1.0,
            "clip_duration_bias": 0.0,
            "subtitles": True,
            "subtitle_size": 1.0,
            "vignette": 0.0,
            "letterbox": False,
            "saturation_bias": 0.0,
            "speed_factor": 1.0,
            "ken_burns": False,
            "camera_shake": 0.0,
            "music_mood": "majestic",
            "description": description,
        }

        desc_lower = description.lower()

        # 匹配关键词
        for keyword, params in STYLE_KEYWORDS.items():
            if keyword in desc_lower or keyword in description:
                for key, value in params.items():
                    if key in config:
                        if isinstance(value, (int, float)) and isinstance(config[key], (int, float)):
                            if value > 1.0:
                                config[key] = value
                            else:
                                config[key] += value
                        else:
                            config[key] = value

                logger.info(f"风格匹配: '{keyword}' → {params}")

        # 智能推导：如果没有明确指定，根据描述长度和复杂度推断
        if config["pace"] == "normal" and len(description) > 0:
            # 短描述默认保留原节奏
            pass

        # 调色冲突解决：最后匹配的优先
        logger.info(f"风格解析完成: pace={config['pace']}, "
                     f"tone={config['color_tone']}, "
                     f"transition={config['transition']}")

        return config

    def apply_to_pipeline(self, style_config: Dict, pipeline_config: Dict) -> Dict:
        """将风格配置应用到流水线配置"""
        # 调色
        if "color_tone" in style_config:
            pipeline_config["color_tone"] = style_config["color_tone"]

        # 转场
        if "transition" in style_config:
            pipeline_config["transition_override"] = style_config["transition"]

        # 节奏影响片段时长
        pipeline_config["pace_bias"] = style_config.get("clip_duration_bias", 0)
        pipeline_config["transition_speed"] = style_config.get("transition_speed", 1.0)

        # 特效
        pipeline_config["ken_burns"] = style_config.get("ken_burns", False)
        pipeline_config["letterbox"] = style_config.get("letterbox", False)
        pipeline_config["speed_factor"] = style_config.get("speed_factor", 1.0)

        # 音乐
        pipeline_config["music_mood"] = style_config.get("music_mood", "majestic")

        return pipeline_config
