"""
调色引擎：国企场景 + 风光摄影预设 + LUT调色
FFmpeg 滤镜链: eq → curves → vignette → lut3d → 裁切(letterbox)
"""
from typing import Dict, List, Optional
from pathlib import Path
from .lut_loader import LUTPresets, get_global_lut_presets


class ColorGrader:
    # 基础预设（传统参数调色）
    PRESETS = {
        # ── 国企场景 ──
        "warm_red": {
            "eq_brightness": 0.05, "eq_contrast": 1.10, "eq_saturation": 1.15,
            "curves_r": "0/0 0.25/0.28 0.5/0.55 0.75/0.78 1/1",
            "curves_g": "0/0 0.25/0.24 0.5/0.49 0.75/0.74 1/1",
            "curves_b": "0/0 0.25/0.22 0.5/0.47 0.75/0.72 1/1",
            "vignette_angle": "PI/5",
        },
        "professional": {
            "eq_brightness": 0.02, "eq_contrast": 1.05, "eq_saturation": 0.95,
            "curves_r": "0/0 0.5/0.5 1/1",
            "curves_g": "0/0 0.5/0.5 1/1",
            "curves_b": "0/0 0.5/0.5 1/1",
        },
        "bright": {
            "eq_brightness": 0.08, "eq_contrast": 1.08, "eq_saturation": 1.10,
            "curves_r": "0/0 0.5/0.52 1/1",
            "curves_g": "0/0 0.5/0.52 1/1",
            "curves_b": "0/0 0.5/0.53 1/1",
        },
        "warm": {
            "eq_brightness": 0.04, "eq_contrast": 1.05, "eq_saturation": 1.05,
            "curves_r": "0/0 0.5/0.54 1/1",
            "curves_g": "0/0 0.5/0.51 1/1",
            "curves_b": "0/0 0.5/0.47 1/1",
        },

        # ── 风光摄影 ──
        "nature_cinematic": {
            "description": "电影感自然色调",
            "eq_brightness": 0.02, "eq_contrast": 1.08, "eq_saturation": 1.10,
            "eq_gamma": 1.05,
            "curves_r": "0/0 0.3/0.32 0.5/0.52 0.7/0.72 1/1",
            "curves_g": "0/0 0.3/0.33 0.5/0.54 0.7/0.73 1/1",
            "curves_b": "0/0 0.3/0.30 0.5/0.50 0.7/0.70 1/1",
            "vignette": 1.0,
            "letterbox": True,
        },
        "golden_hour": {
            "description": "金色时刻暖调",
            "eq_brightness": 0.06, "eq_contrast": 1.05, "eq_saturation": 1.20,
            "eq_gamma": 1.02,
            "curves_r": "0/0 0.4/0.46 0.6/0.65 0.8/0.82 1/1",
            "curves_g": "0/0 0.4/0.44 0.6/0.61 0.8/0.80 1/1",
            "curves_b": "0/0 0.4/0.38 0.6/0.56 0.8/0.76 1/1",
            "vignette": 0.8,
        },
        "moody_forest": {
            "description": "暗调森林绿",
            "eq_brightness": -0.04, "eq_contrast": 1.12, "eq_saturation": 0.85,
            "eq_gamma": 0.95,
            "curves_r": "0/0 0.5/0.47 1/1",
            "curves_g": "0/0 0.5/0.53 1/1",
            "curves_b": "0/0 0.5/0.46 1/1",
            "vignette": 1.3,
            "letterbox": True,
        },
        "teal_orange": {
            "description": "青橙电影调",
            "eq_brightness": 0.01, "eq_contrast": 1.10, "eq_saturation": 1.05,
            "eq_gamma": 1.03,
            "curves_r": "0/0 0.3/0.34 0.6/0.62 1/1",
            "curves_g": "0/0 0.3/0.32 0.6/0.60 1/1",
            "curves_b": "0/0 0.3/0.28 0.6/0.58 1/1",
            "vignette": 0.6,
        },
    }

    def __init__(self, luts_directory: str = None):
        """初始化调色引擎，加载LUT预设"""
        self.lut_presets = LUTPresets(luts_directory)
        self.lut_presets.load_all_presets()

    def get_preset(self, preset_name: str) -> Dict:
        """
        获取预设配置
        
        Args:
            preset_name: 预设名称，可以是：
                - 传统预设名称（如 "warm_red", "professional"）
                - LUT预设名称（如 "ysjf_cinematic_film"）
                - LUT文件路径（以 .cube 结尾）
        
        Returns:
            预设配置字典
        """
        # 首先检查是否是传统预设
        if preset_name in self.PRESETS:
            return self.PRESETS[preset_name]
        
        # 检查是否是LUT预设
        lut_data = self.lut_presets.get_preset(preset_name)
        if lut_data:
            return {
                "lut_file": lut_data.file_path,
                "lut_title": lut_data.title,
                "lut_size": lut_data.size,
                "description": f"LUT: {lut_data.title}"
            }
        
        # 检查是否是LUT文件路径
        if preset_name.endswith('.cube'):
            from .lut_loader import LUTLoader
            loader = LUTLoader()
            lut_data = loader.load_cube_file(preset_name)
            if lut_data:
                return {
                    "lut_file": preset_name,
                    "lut_title": lut_data.title,
                    "lut_size": lut_data.size,
                    "description": f"LUT: {lut_data.title}"
                }
        
        # 如果都找不到，返回默认预设
        print(f"⚠️  未找到预设 '{preset_name}'，使用默认 warm_red")
        return self.PRESETS["warm_red"]

    def to_ffmpeg_filter(self, config: Dict) -> str:
        """
        将预设配置转换为FFmpeg滤镜字符串
        
        Args:
            config: 预设配置字典
            
        Returns:
            FFmpeg滤镜字符串
        """
        parts = []
        
        # 检查是否包含LUT文件
        lut_file = config.get("lut_file")
        if lut_file:
            # 使用LUT滤镜
            from .lut_loader import load_lut_for_ffmpeg
            lut_filter = load_lut_for_ffmpeg(lut_file)
            if lut_filter:
                parts.append(lut_filter)
                # 如果有LUT，仍然可以添加其他滤镜
                # 但通常LUT已经包含了完整的调色
        
        # 传统参数调色（如果没有LUT或需要额外调整）
        b = config.get("eq_brightness", 0)
        c = config.get("eq_contrast", 1.0)
        s = config.get("eq_saturation", 1.0)
        g = config.get("eq_gamma", 1.0)
        eq_parts = []
        if b != 0:
            eq_parts.append(f"brightness={b}")
        if c != 1.0:
            eq_parts.append(f"contrast={c}")
        if s != 1.0:
            eq_parts.append(f"saturation={s}")
        if g != 1.0:
            eq_parts.append(f"gamma={g}")
        if eq_parts:
            parts.append(f"eq={':'.join(eq_parts)}")

        curves = []
        for ch in ['r', 'g', 'b']:
            key = f"curves_{ch}"
            if key in config:
                curves.append(f"{ch}='{config[key]}'")
        if curves:
            parts.append(f"curves={':'.join(curves)}")

        # Vignette
        if config.get("vignette_angle"):
            parts.append(f"vignette=angle={config['vignette_angle']}")
        elif config.get("vignette"):
            # Modern vignette using format filter
            parts.append(f"vignette=PI/4:aspect=16/9")

        # Letterbox (电影宽银幕)
        if config.get("letterbox"):
            # 2.35:1 aspect ratio letterbox
            parts.append("crop=iw:iw/2.35,scale=1920:816,pad=1920:1080:(ow-iw)/2:(oh-ih)/2")

        return ",".join(parts) if parts else ""

    def list_presets(self) -> Dict:
        """列出所有预设及描述（包括传统预设和LUT预设）"""
        presets = {}
        
        # 添加传统预设
        for name, cfg in self.PRESETS.items():
            presets[name] = {
                "type": "parameter",
                "description": cfg.get("description", name)
            }
        
        # 添加LUT预设
        lut_list = self.lut_presets.list_presets()
        for lut_info in lut_list:
            presets[lut_info['name']] = {
                "type": "lut",
                "description": lut_info['description'],
                "title": lut_info['title'],
                "size": lut_info['size']
            }
        
        return presets

    def list_lut_presets(self) -> List[Dict]:
        """仅列出LUT预设"""
        return self.lut_presets.list_presets()

    def get_available_luts(self) -> List[Dict]:
        """获取所有可用的LUT文件信息"""
        return self.lut_presets.list_presets()
