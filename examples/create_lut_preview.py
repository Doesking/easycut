#!/usr/bin/env python3
"""
创建LUT预览图像
生成测试图像并应用LUT效果
"""
import sys
import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_test_image(width=400, height=300):
    """创建测试图像"""
    # 创建渐变测试图像
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # 创建彩虹渐变
    for x in range(width):
        for y in range(height):
            # 创建HSL到RGB的渐变
            hue = x / width * 360
            saturation = 0.8
            lightness = 0.3 + (y / height) * 0.4
            
            # 简单的HSV到RGB转换
            h = hue / 60
            c = saturation * (1 - abs(2 * lightness - 1))
            x_val = c * (1 - abs(h % 2 - 1))
            m = lightness - c / 2
            
            if 0 <= h < 1:
                r, g, b = c, x_val, 0
            elif 1 <= h < 2:
                r, g, b = x_val, c, 0
            elif 2 <= h < 3:
                r, g, b = 0, c, x_val
            elif 3 <= h < 4:
                r, g, b = 0, x_val, c
            elif 4 <= h < 5:
                r, g, b = x_val, 0, c
            else:
                r, g, b = c, 0, x_val
            
            r = int((r + m) * 255)
            g = int((g + m) * 255)
            b = int((b + m) * 255)
            
            draw.point((x, y), fill=(r, g, b))
    
    return img

def apply_lut_to_image(image, lut_data):
    """将LUT应用到图像"""
    # 将图像转换为numpy数组
    img_array = np.array(image, dtype=np.float32) / 255.0
    
    # 获取LUT尺寸
    lut_size = lut_data.size
    
    # 应用LUT（简化版本，实际应该使用插值）
    # 这里我们只是演示，实际应用需要更复杂的3D插值
    result_array = img_array.copy()
    
    # 对每个像素应用LUT
    for i in range(img_array.shape[0]):
        for j in range(img_array.shape[1]):
            r, g, b = img_array[i, j]
            
            # 找到最近的LUT索引
            r_idx = int(r * (lut_size - 1))
            g_idx = int(g * (lut_size - 1))
            b_idx = int(b * (lut_size - 1))
            
            # 确保索引在范围内
            r_idx = min(r_idx, lut_size - 1)
            g_idx = min(g_idx, lut_size - 1)
            b_idx = min(b_idx, lut_size - 1)
            
            # 应用LUT
            result_array[i, j] = lut_data.data[r_idx, g_idx, b_idx]
    
    # 转换回0-255范围
    result_array = np.clip(result_array * 255, 0, 255).astype(np.uint8)
    
    return Image.fromarray(result_array)

def create_lut_preview():
    """创建LUT预览图像"""
    print("🎨 创建LUT预览图像...")
    
    # 创建输出目录
    output_dir = Path(__file__).parent.parent / "output" / "lut_previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载LUT
    from core.lut_loader import LUTPresets
    
    luts_dir = str(Path(__file__).parent.parent / "assets" / "luts")
    presets = LUTPresets(luts_dir)
    presets.load_all_presets()
    
    # 创建测试图像
    test_image = create_test_image(200, 150)  # 小尺寸以加快处理
    
    # 保存原始图像
    original_path = output_dir / "original.png"
    test_image.save(original_path)
    print(f"✅ 保存原始图像: {original_path}")
    
    # 应用每个LUT
    lut_list = presets.list_presets()
    
    for lut_info in lut_list[:5]:  # 只处理前5个，加快演示速度
        lut_name = lut_info['name']
        lut_data = presets.get_preset(lut_name)
        
        if lut_data:
            print(f"🎨 处理: {lut_name}")
            
            try:
                # 应用LUT
                result_image = apply_lut_to_image(test_image, lut_data)
                
                # 保存结果
                output_path = output_dir / f"{lut_name}.png"
                result_image.save(output_path)
                print(f"✅ 保存: {output_path}")
                
            except Exception as e:
                print(f"❌ 处理 {lut_name} 失败: {e}")
    
    print(f"\n📁 预览图像保存在: {output_dir}")
    print("   您可以查看这些图像来比较不同LUT的效果。")
    
    return True

def main():
    """主函数"""
    print("🎬 LUT预览图像生成器\n")
    
    try:
        success = create_lut_preview()
        if success:
            print("\n🎉 LUT预览图像创建完成！")
            return 0
        else:
            print("\n⚠️  LUT预览图像创建失败。")
            return 1
    except Exception as e:
        print(f"\n❌ 预览创建失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())