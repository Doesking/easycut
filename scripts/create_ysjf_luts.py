#!/usr/bin/env python3
"""
创建影视飓风风格的LUT文件
生成多种电影感调色风格的.cube文件
"""
import os
import numpy as np

def create_lut_file(filename, title, color_transform_func, size=33):
    """
    创建LUT文件
    
    Args:
        filename: 输出文件名
        title: LUT标题
        color_transform_func: 颜色转换函数，接收(r,g,b)返回(r,g,b)
        size: LUT尺寸（默认33x33x33）
    """
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                               'assets', 'luts', filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # 写入头部信息
        f.write(f"# {title}\n")
        f.write(f"# Generated for SOE Auto Editor\n")
        f.write(f"# Style: 影视飓风 Cinematic Look\n")
        f.write(f"TITLE \"{title}\"\n")
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
                    
                    # 应用颜色转换
                    r_out, g_out, b_out = color_transform_func(r, g, b)
                    
                    # 确保值在0-1范围内
                    r_out = max(0.0, min(1.0, r_out))
                    g_out = max(0.0, min(1.0, g_out))
                    b_out = max(0.0, min(1.0, b_out))
                    
                    f.write(f"{r_out:.6f} {g_out:.6f} {b_out:.6f}\n")
    
    print(f"✅ 创建LUT文件: {filename}")
    return output_path

def cinematic_film_look(r, g, b):
    """
    影视飓风电影感自然色调
    特点：轻微降低饱和度，增强对比度，电影感的色彩
    """
    # 转换为亮度
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    
    # 增强对比度（S曲线）
    contrast = 1.1
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 电影感的色彩偏移（轻微暖调）
    r = r * 1.02  # 轻微增加红色
    g = g * 1.00  # 保持绿色
    b = b * 0.98  # 轻微减少蓝色
    
    # 阴影偏蓝（电影感）
    if lum < 0.3:
        shadow_factor = (0.3 - lum) / 0.3
        b = b + shadow_factor * 0.02
    
    # 高光偏暖
    if lum > 0.7:
        highlight_factor = (lum - 0.7) / 0.3
        r = r + highlight_factor * 0.03
    
    return r, g, b

def teal_orange_cinematic(r, g, b):
    """
    影视飓风青橙电影调
    特点：经典的青橙色调，电影感强烈，适合人像和风景
    """
    # 计算亮度
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    
    # 青橙调色核心逻辑
    # 高光偏橙色（增加红，减少蓝）
    if lum > 0.5:
        factor = (lum - 0.5) * 2
        r = r + factor * 0.08
        g = g + factor * 0.02
        b = b - factor * 0.05
    
    # 阴影偏青色（减少红，增加蓝绿）
    if lum < 0.5:
        factor = (0.5 - lum) * 2
        r = r - factor * 0.04
        g = g + factor * 0.02
        b = b + factor * 0.06
    
    # 轻微增加饱和度
    avg = (r + g + b) / 3
    sat_factor = 1.15
    r = avg + (r - avg) * sat_factor
    g = avg + (g - avg) * sat_factor
    b = avg + (b - avg) * sat_factor
    
    return r, g, b

def golden_hour_warmth(r, g, b):
    """
    影视飓风金色时刻暖调
    特点：温暖的金色调，适合日出日落、浪漫场景
    """
    # 增加暖色调
    r = r * 1.12  # 显著增加红色
    g = g * 1.05  # 轻微增加绿色
    b = b * 0.88  # 减少蓝色
    
    # 增加对比度
    contrast = 1.08
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 高光更暖
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum > 0.6:
        factor = (lum - 0.6) / 0.4
        r = r + factor * 0.05
    
    return r, g, b

def moody_cinematic(r, g, b):
    """
    影视飓风暗调电影感
    特点：低饱和度，高对比度，电影感阴影，适合悬疑、文艺片
    """
    # 降低饱和度
    avg = (r + g + b) / 3
    sat_factor = 0.75
    r = avg + (r - avg) * sat_factor
    g = avg + (g - avg) * sat_factor
    b = avg + (b - avg) * sat_factor
    
    # 增加对比度（更强烈的S曲线）
    contrast = 1.2
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 阴影偏蓝绿
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum < 0.4:
        factor = (0.4 - lum) / 0.4
        g = g + factor * 0.02
        b = b + factor * 0.04
    
    # 整体轻微偏冷
    r = r * 0.98
    g = g * 1.01
    b = b * 1.03
    
    return r, g, b

def vintage_film(r, g, b):
    """
    影视飓风复古胶片感
    特点：褪色效果，柔和对比，怀旧色调
    """
    # 轻微褪色效果（提亮黑色）
    black_lift = 0.05
    r = r * (1 - black_lift) + black_lift
    g = g * (1 - black_lift) + black_lift
    b = b * (1 - black_lift) + black_lift
    
    # 降低对比度（柔和）
    contrast = 0.95
    r = (r - 0.5) * contrast + 0.5
    g = (g - 0.5) * contrast + 0.5
    b = (b - 0.5) * contrast + 0.5
    
    # 复古色调偏移（偏黄绿）
    r = r * 1.02
    g = g * 1.03
    b = b * 0.96
    
    # 轻微降低饱和度
    avg = (r + g + b) / 3
    sat_factor = 0.9
    r = avg + (r - avg) * sat_factor
    g = avg + (g - avg) * sat_factor
    b = avg + (b - avg) * sat_factor
    
    return r, g, b

def create_all_luts():
    """创建所有影视飓风风格的LUT"""
    print("🎬 开始创建影视飓风风格LUT文件...")
    
    lut_configs = [
        {
            "filename": "ysjf_cinematic_film.cube",
            "title": "影视飓风 Cinematic Film Look",
            "func": cinematic_film_look,
            "description": "电影感自然色调，适合各种场景"
        },
        {
            "filename": "ysjf_teal_orange.cube",
            "title": "影视飓风 Teal & Orange",
            "func": teal_orange_cinematic,
            "description": "经典青橙电影调，适合人像和风景"
        },
        {
            "filename": "ysjf_golden_hour.cube",
            "title": "影视飓风 Golden Hour",
            "func": golden_hour_warmth,
            "description": "金色时刻暖调，适合日出日落场景"
        },
        {
            "filename": "ysjf_moody_cinematic.cube",
            "title": "影视飓风 Moody Cinematic",
            "func": moody_cinematic,
            "description": "暗调电影感，适合悬疑文艺片"
        },
        {
            "filename": "ysjf_vintage_film.cube",
            "title": "影视飓风 Vintage Film",
            "func": vintage_film,
            "description": "复古胶片感，怀旧色调"
        }
    ]
    
    created_files = []
    for config in lut_configs:
        filepath = create_lut_file(
            config["filename"],
            config["title"],
            config["func"]
        )
        created_files.append(filepath)
        print(f"   {config['description']}")
    
    print(f"\n✨ 完成！共创建 {len(created_files)} 个LUT文件")
    print("📁 位置: assets/luts/")
    
    return created_files

if __name__ == "__main__":
    create_all_luts()