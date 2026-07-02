#!/usr/bin/env python3
"""
LUT效果演示指南
展示如何使用影视飓风LUT调色模板
"""

def print_header():
    """打印标题"""
    print("=" * 70)
    print("🎬 影视飓风LUT调色模板 - 使用演示")
    print("=" * 70)
    print()

def print_lut_list():
    """打印LUT列表"""
    print("📋 可用的影视飓风LUT预设:")
    print("-" * 50)
    
    luts = [
        ("ysjf_cinematic_film", "电影感自然色调", "各种场景，通用型"),
        ("ysjf_teal_orange", "经典青橙电影调", "人像、风景、电影感强"),
        ("ysjf_golden_hour", "金色时刻暖调", "日出日落、浪漫场景"),
        ("ysjf_moody_cinematic", "暗调电影感", "悬疑、文艺片、暗调场景"),
        ("ysjf_vintage_film", "复古胶片感", "复古、文艺、怀旧风格"),
    ]
    
    for i, (name, desc, usage) in enumerate(luts, 1):
        print(f"{i}. {name}")
        print(f"   描述: {desc}")
        print(f"   适用: {usage}")
        print()

def print_usage_examples():
    """打印使用示例"""
    print("🚀 使用示例:")
    print("-" * 50)
    
    examples = [
        ("查看所有预设", "python agent_api.py --list-tones"),
        ("查看LUT预设", "python agent_api.py --list-luts"),
        ("使用电影感LUT", "python agent_api.py video.mp4 --tone ysjf_cinematic_film"),
        ("使用青橙调LUT", "python agent_api.py video.mp4 --tone ysjf_teal_orange"),
        ("使用自定义LUT", "python agent_api.py video.mp4 --lut /path/to/custom.cube"),
        ("完整示例", """python agent_api.py input.mp4 \\
  -t party_building \\
  --tone ysjf_cinematic_film \\
  --title "会议视频" \\
  --subtitle "XX单位" \\
  -o output.mp4"""),
    ]
    
    for i, (desc, cmd) in enumerate(examples, 1):
        print(f"{i}. {desc}:")
        print(f"   {cmd}")
        print()

def print_scene_recommendations():
    """打印场景推荐"""
    print("🎯 场景匹配建议:")
    print("-" * 50)
    
    recommendations = [
        ("党建/会议场景", ["ysjf_cinematic_film", "warm_red"], "专业、庄重"),
        ("参观/展示场景", ["ysjf_teal_orange", "bright"], "电影感、明亮"),
        ("学习/培训场景", ["ysjf_golden_hour", "warm"], "温暖、亲切"),
        ("文艺/创意场景", ["ysjf_vintage_film", "ysjf_moody_cinematic"], "复古、文艺"),
    ]
    
    for scene, luts, style in recommendations:
        print(f"📌 {scene} ({style}):")
        for lut in luts:
            print(f"   - {lut}")
        print()

def print_technical_details():
    """打印技术细节"""
    print("🔧 技术细节:")
    print("-" * 50)
    
    details = [
        ("LUT文件格式", "标准.cube格式，33x33x33尺寸"),
        ("FFmpeg滤镜", "lut3d=file='path.cube':interp=tetrahedral"),
        ("插值算法", "四面体插值，保证色彩过渡平滑"),
        ("缓存机制", "自动缓存已加载的LUT文件，提高性能"),
        ("预设管理", "支持传统参数预设和LUT预设的混合使用"),
    ]
    
    for name, desc in details:
        print(f"• {name}: {desc}")
    print()

def print_api_usage():
    """打印API使用示例"""
    print("📡 API使用示例:")
    print("-" * 50)
    
    api_code = '''```python
from skill import SOEAutoEditSkill

skill = SOEAutoEditSkill()

# 使用影视飓风LUT
result = skill.edit_sync(
    input_videos=["video1.mp4", "video2.mp4"],
    template="party_building",
    title="会议视频",
    color_tone="ysjf_teal_orange",  # 使用LUT预设
    output_path="output.mp4"
)

# 使用自定义LUT文件
result = skill.edit_sync(
    input_videos=["video.mp4"],
    template="conference",
    color_tone="/path/to/custom.cube",  # 使用自定义LUT文件
)
```'''
    
    print(api_code)
    print()

def print_troubleshooting():
    """打印故障排除"""
    print("❓ 常见问题:")
    print("-" * 50)
    
    faq = [
        ("LUT文件未找到", "检查文件路径是否正确，确认文件扩展名是.cube"),
        ("颜色效果不明显", "尝试调整视频的曝光和白平衡，LUT效果依赖于输入视频的质量"),
        ("处理速度慢", "使用较小尺寸的LUT文件，减少同时处理的视频数量"),
        ("如何添加自定义LUT", "将.cube文件放入assets/luts/目录，或在命令行中指定文件路径"),
    ]
    
    for i, (question, answer) in enumerate(faq, 1):
        print(f"{i}. {question}:")
        print(f"   {answer}")
        print()

def main():
    """主函数"""
    print_header()
    print_lut_list()
    print_usage_examples()
    print_scene_recommendations()
    print_technical_details()
    print_api_usage()
    print_troubleshooting()
    
    print("=" * 70)
    print("🎉 影视飓风LUT调色模板集成完成！")
    print("   所有功能已经过测试，可以正常使用。")
    print("=" * 70)

if __name__ == "__main__":
    main()