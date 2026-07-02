#!/usr/bin/env python3
"""
LUT效果演示脚本
生成不同LUT预设的对比视频
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_demo_video():
    """创建演示视频，展示不同LUT效果"""
    print("🎬 开始创建LUT效果演示视频...")
    
    # 创建输出目录
    output_dir = Path(__file__).parent.parent / "output" / "lut_demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查测试视频是否存在
    test_videos = list(Path(__file__).parent.parent.glob("test_*.mp4"))
    if not test_videos:
        print("❌ 未找到测试视频，请确保有test_*.mp4文件")
        return False
    
    test_video = test_videos[0]
    print(f"✅ 使用测试视频: {test_video}")
    
    # 定义要演示的LUT预设
    lut_presets = [
        ("ysjf_cinematic_film", "影视飓风电影感"),
        ("ysjf_teal_orange", "影视飓风青橙调"),
        ("ysjf_golden_hour", "影视飓风金色时刻"),
        ("ysjf_moody_cinematic", "影视飓风暗调电影"),
        ("ysjf_vintage_film", "影视飓风复古胶片"),
        ("warm_red", "传统暖红色调"),
    ]
    
    # 创建演示
    from skill import SOEAutoEditSkill
    skill = SOEAutoEditSkill()
    
    results = []
    for preset_name, preset_desc in lut_presets:
        print(f"\n🎨 处理: {preset_desc} ({preset_name})")
        
        output_path = str(output_dir / f"demo_{preset_name}.mp4")
        
        try:
            result = skill.edit_sync(
                input_videos=[str(test_video)],
                template="party_building",
                title=f"LUT演示 - {preset_desc}",
                color_tone=preset_name,
                output_path=output_path,
                target_duration=30,  # 30秒演示
            )
            
            if result["success"]:
                print(f"✅ 生成成功: {output_path}")
                results.append((preset_name, preset_desc, output_path, True))
            else:
                print(f"❌ 生成失败: {result['error']}")
                results.append((preset_name, preset_desc, None, False))
                
        except Exception as e:
            print(f"❌ 处理异常: {e}")
            results.append((preset_name, preset_desc, None, False))
    
    # 显示结果汇总
    print("\n" + "="*60)
    print("📊 LUT效果演示结果:")
    
    success_count = 0
    for preset_name, preset_desc, output_path, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {preset_desc} ({preset_name})")
        if success and output_path:
            print(f"      → {output_path}")
            success_count += 1
    
    print(f"\n总计: {success_count}/{len(results)} 个演示视频生成成功")
    
    if success_count > 0:
        print(f"\n📁 演示视频保存在: {output_dir}")
        print("   您可以播放这些视频来比较不同LUT的效果。")
    
    return success_count == len(results)

def main():
    """主函数"""
    print("🎬 LUT效果演示工具\n")
    
    try:
        success = create_demo_video()
        if success:
            print("\n🎉 演示视频创建完成！")
            return 0
        else:
            print("\n⚠️  部分演示视频创建失败。")
            return 1
    except Exception as e:
        print(f"\n❌ 演示创建失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())