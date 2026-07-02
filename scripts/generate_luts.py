#!/usr/bin/env python3
"""
生成影视飓风风格的LUT预设文件
"""
import os
import numpy as np
from typing import Tuple


def generate_lut(size: int, transform_func, name: str, description: str, output_dir: str):
    """
    生成3D LUT文件
    
    Args:
        size: LUT尺寸（如17, 33, 65）
        transform_func: 颜色变换函数
        name: LUT名称
        description: LUT描述
        output_dir: 输出目录
    """
    filepath = os.path.join(output_dir, f"{name}.cube")
    
    with open(filepath, 'w') as f:
        # 写入头部
        f.write(f"# {description}\n")
        f.write(f"TITLE \"{name}\"\n")
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write(f"DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write(f"DOMAIN_MAX 1.0 1.0 1.0\n")
        f.write("\n")
        
        # 生成LUT数据
        # 注意：.cube文件的顺序是B-G-R（蓝变化最慢，红最快）
        for b_idx in range(size):
            for g_idx in range(size):
                for r_idx in range(size):
                    # 归一化到0-1范围
                    r = r_idx / (size - 1)
                    g = g_idx / (size - 1)
                    b = b_idx / (size - 1)
                    
                    # 应用变换
                    r_out, g_out, b_out = transform_func(r, g, b)
                    
                    # 限制范围
                    r_out = max(0.0, min(1.0, r_out))
                    g_out = max(0.0, min(1.0, g_out))
                    b_out = max(0.0, min(1.0, b_out))
                    
                    f.write(f"{r_out:.6f} {g_out:.6f} {b_out:.6f}\n")
    
    print(f"已生成: {filepath}")


def cinematic_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    影视飓风电影感调色
    - 增强对比度
    - 暗部偏青蓝
    - 高光偏暖橙
    - 降低饱和度
    """
    # 增强对比度
    contrast = 1.15
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 暗部偏青蓝
    shadow_mask = 1.0 - (r + g + b) / 3.0
    shadow_mask = max(0, shadow_mask - 0.3) * 2
    r -= shadow_mask * 0.05
    g += shadow_mask * 0.02
    b += shadow_mask * 0.08
    
    # 高光偏暖橙
    highlight_mask = (r + g + b) / 3.0
    highlight_mask = max(0, highlight_mask - 0.6) * 2
    r += highlight_mask * 0.06
    g += highlight_mask * 0.02
    b -= highlight_mask * 0.04
    
    # 降低饱和度
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    saturation = 0.85
    r = gray + saturation * (r - gray)
    g = gray + saturation * (g - gray)
    b = gray + saturation * (b - gray)
    
    return r, g, b


def fresh_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    影视飓风清新风格
    - 提亮整体
    - 增强绿色
    - 暗部偏绿
    - 高光偏青
    """
    # 提亮
    brightness = 0.05
    r += brightness
    g += brightness
    b += brightness
    
    # 增强绿色
    g *= 1.08
    
    # 暗部偏绿
    shadow_mask = 1.0 - (r + g + b) / 3.0
    shadow_mask = max(0, shadow_mask - 0.3) * 2
    r -= shadow_mask * 0.03
    g += shadow_mask * 0.05
    b -= shadow_mask * 0.02
    
    # 高光偏青
    highlight_mask = (r + g + b) / 3.0
    highlight_mask = max(0, highlight_mask - 0.6) * 2
    r -= highlight_mask * 0.02
    g += highlight_mask * 0.03
    b += highlight_mask * 0.05
    
    # 增加对比度
    contrast = 1.05
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    return r, g, b


def vintage_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    影视飓风复古风格
    - 降低饱和度
    - 暖色调
    - 暗部提亮
    - 添加颗粒感（通过曲线模拟）
    """
    # 降低饱和度
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    saturation = 0.75
    r = gray + saturation * (r - gray)
    g = gray + saturation * (g - gray)
    b = gray + saturation * (b - gray)
    
    # 暖色调
    r *= 1.05
    g *= 1.02
    b *= 0.95
    
    # 暗部提亮
    shadow_mask = 1.0 - (r + g + b) / 3.0
    shadow_mask = max(0, shadow_mask - 0.2) * 2
    r += shadow_mask * 0.05
    g += shadow_mask * 0.04
    b += shadow_mask * 0.03
    
    # 模拟胶片曲线（S型对比度）
    r = 0.5 + 0.5 * np.sin(np.pi * (r - 0.5))
    g = 0.5 + 0.5 * np.sin(np.pi * (g - 0.5))
    b = 0.5 + 0.5 * np.sin(np.pi * (b - 0.5))
    
    return r, g, b


def cyberpunk_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    影视飓风赛博朋克风格
    - 高对比度
    - 青蓝色调
    - 暗部深邃
    - 高光霓虹感
    """
    # 高对比度
    contrast = 1.25
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 青蓝色调
    r *= 0.9
    g *= 1.05
    b *= 1.1
    
    # 暗部深邃
    shadow_mask = 1.0 - (r + g + b) / 3.0
    shadow_mask = max(0, shadow_mask - 0.3) * 2
    r -= shadow_mask * 0.1
    g -= shadow_mask * 0.05
    b += shadow_mask * 0.05
    
    # 高光霓虹感
    highlight_mask = (r + g + b) / 3.0
    highlight_mask = max(0, highlight_mask - 0.6) * 2
    r += highlight_mask * 0.1
    g += highlight_mask * 0.05
    b += highlight_mask * 0.15
    
    return r, g, b


def natural_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    影视飓风自然风格
    - 轻微增强
    - 保持自然色彩
    - 轻微对比度提升
    """
    # 轻微对比度
    contrast = 1.05
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 轻微饱和度提升
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    saturation = 1.08
    r = gray + saturation * (r - gray)
    g = gray + saturation * (g - gray)
    b = gray + saturation * (b - gray)
    
    # 轻微提亮
    brightness = 0.02
    r += brightness
    g += brightness
    b += brightness
    
    return r, g, b


def film_emulation_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    胶片模拟风格
    - 模拟Kodak胶片色彩
    - 温暖的高光
    - 深沉的阴影
    """
    # Kodak胶片曲线
    r = 0.5 + 0.5 * np.sin(np.pi * (r * 0.9 - 0.45))
    g = 0.5 + 0.5 * np.sin(np.pi * (g * 0.95 - 0.475))
    b = 0.5 + 0.5 * np.sin(np.pi * (b * 0.85 - 0.425))
    
    # 温暖的高光
    highlight_mask = (r + g + b) / 3.0
    highlight_mask = max(0, highlight_mask - 0.5) * 2
    r += highlight_mask * 0.08
    g += highlight_mask * 0.04
    b -= highlight_mask * 0.02
    
    # 深沉的阴影
    shadow_mask = 1.0 - (r + g + b) / 3.0
    shadow_mask = max(0, shadow_mask - 0.4) * 2
    r -= shadow_mask * 0.05
    g -= shadow_mask * 0.03
    b += shadow_mask * 0.02
    
    # 降低饱和度
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    saturation = 0.85
    r = gray + saturation * (r - gray)
    g = gray + saturation * (g - gray)
    b = gray + saturation * (b - gray)
    
    return r, g, b


def landscape_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    风景优化风格
    - 增强天空蓝色
    - 增强绿色植被
    - 提升整体清晰度
    """
    # 增强天空蓝色
    blue_mask = b - (r + g) / 2
    blue_mask = max(0, blue_mask) * 2
    b += blue_mask * 0.1
    r -= blue_mask * 0.02
    
    # 增强绿色植被
    green_mask = g - (r + b) / 2
    green_mask = max(0, green_mask) * 1.5
    g += green_mask * 0.08
    
    # 提升对比度
    contrast = 1.12
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 轻微饱和度提升
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    saturation = 1.15
    r = gray + saturation * (r - gray)
    g = gray + saturation * (g - gray)
    b = gray + saturation * (b - gray)
    
    return r, g, b


def portrait_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    人像优化风格
    - 柔化肤色
    - 暖色调
    - 轻微提亮
    """
    # 肤色区域检测（简单判断）
    skin_mask = 0.0
    if r > 0.4 and g > 0.3 and b > 0.2 and r > g and r > b:
        skin_mask = min(1.0, (r - 0.4) * 3)
    
    # 柔化肤色区域
    r += skin_mask * 0.03
    g += skin_mask * 0.02
    b -= skin_mask * 0.01
    
    # 暖色调整体
    r *= 1.03
    g *= 1.01
    b *= 0.97
    
    # 轻微提亮
    brightness = 0.03
    r += brightness
    g += brightness
    b += brightness
    
    # 轻微降低对比度（柔化）
    contrast = 0.95
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    return r, g, b


def vlog_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    Vlog风格
    - 明亮清新
    - 中等饱和度
    - 暗部提亮
    """
    # 暗部提亮
    shadow_mask = 1.0 - (r + g + b) / 3.0
    shadow_mask = max(0, shadow_mask - 0.2) * 2
    r += shadow_mask * 0.08
    g += shadow_mask * 0.08
    b += shadow_mask * 0.08
    
    # 明亮
    brightness = 0.04
    r += brightness
    g += brightness
    b += brightness
    
    # 中等饱和度
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    saturation = 1.12
    r = gray + saturation * (r - gray)
    g = gray + saturation * (g - gray)
    b = gray + saturation * (b - gray)
    
    # 轻微对比度
    contrast = 1.05
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    return r, g, b


def dark_moody_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    暗调氛围风格
    - 压暗整体
    - 低饱和度
    - 冷色调
    """
    # 压暗
    brightness = -0.05
    r += brightness
    g += brightness
    b += brightness
    
    # 低饱和度
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    saturation = 0.7
    r = gray + saturation * (r - gray)
    g = gray + saturation * (g - gray)
    b = gray + saturation * (b - gray)
    
    # 冷色调
    r *= 0.92
    g *= 0.96
    b *= 1.05
    
    # 高对比度
    contrast = 1.2
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    return r, g, b


def warm_sunset_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    暖色日落风格
    - 金色暖调
    - 增强橙色
    - 柔和对比度
    """
    # 金色暖调
    r *= 1.1
    g *= 1.03
    b *= 0.85
    
    # 增强橙色（红+绿）
    orange_mask = min(r, g) - b
    orange_mask = max(0, orange_mask) * 2
    r += orange_mask * 0.05
    g += orange_mask * 0.03
    b -= orange_mask * 0.03
    
    # 柔和对比度
    contrast = 1.05
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 轻微饱和度提升
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    saturation = 1.1
    r = gray + saturation * (r - gray)
    g = gray + saturation * (g - gray)
    b = gray + saturation * (b - gray)
    
    return r, g, b


def bw_noir_transform(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """
    黑白电影风格
    - 经典黑白
    - 高对比度
    - 保留层次感
    """
    # 转灰度（电影感加权）
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    
    # S型对比度曲线
    gray = 0.5 + 0.5 * np.sin(np.pi * (gray - 0.5))
    
    # 暗部略微偏冷（模拟经典黑白胶片）
    # 通过微调RGB让纯黑白有细微色偏
    r = gray * 0.98
    g = gray * 1.0
    b = gray * 1.02
    
    return r, g, b


def main():
    """生成所有LUT预设"""
    output_dir = "/Users/chrishang/Documents/Codex/soe_auto_editor/assets/luts"
    os.makedirs(output_dir, exist_ok=True)
    
    # LUT尺寸（使用33，平衡质量和性能）
    lut_size = 33
    
    # 生成影视飓风风格LUT
    luts = [
        ("yingshi_cinematic", cinematic_transform, 
         "影视飓风电影感", "影视飓风电影感调色 - 增强对比度，暗部青蓝，高光暖橙"),
        
        ("yingshi_fresh", fresh_transform,
         "影视飓风清新", "影视飓风清新风格 - 提亮整体，增强绿色，高光偏青"),
        
        ("yingshi_vintage", vintage_transform,
         "影视飓风复古", "影视飓风复古风格 - 降低饱和度，暖色调，胶片曲线"),
        
        ("yingshi_cyberpunk", cyberpunk_transform,
         "影视飓风赛博朋克", "影视飓风赛博朋克风格 - 高对比度，青蓝色调，霓虹高光"),
        
        ("yingshi_natural", natural_transform,
         "影视飓风自然", "影视飓风自然风格 - 轻微增强，保持自然色彩"),
        
        ("film_emulation", film_emulation_transform,
         "胶片模拟", "经典胶片模拟 - Kodak胶片色彩，温暖高光，深沉阴影"),
        
        # 通用视频LUT
        ("landscape", landscape_transform,
         "风景优化", "风景优化风格 - 增强天空蓝和植被绿，提升清晰度"),
        
        ("portrait", portrait_transform,
         "人像优化", "人像优化风格 - 柔化肤色，暖色调，轻微提亮"),
        
        ("vlog", vlog_transform,
         "Vlog风格", "Vlog风格 - 明亮清新，中等饱和度，暗部提亮"),
        
        ("dark_moody", dark_moody_transform,
         "暗调氛围", "暗调氛围风格 - 压暗整体，低饱和度，冷色调"),
        
        ("warm_sunset", warm_sunset_transform,
         "暖色日落", "暖色日落风格 - 金色暖调，增强橙色，柔和对比度"),
        
        ("bw_noir", bw_noir_transform,
         "黑白电影", "黑白电影风格 - 经典黑白，高对比度，保留层次感"),
    ]
    
    for name, transform_func, title, description in luts:
        generate_lut(lut_size, transform_func, name, description, output_dir)
    
    print(f"\n所有LUT预设已生成到: {output_dir}")


if __name__ == "__main__":
    main()
