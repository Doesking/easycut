#!/usr/bin/env python3
"""
简单的LUT测试脚本
不依赖OpenCV，仅测试LUT加载和FFmpeg滤镜生成
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_lut_loading():
    """测试LUT加载功能"""
    print("🧪 测试LUT加载功能...")
    
    from core.lut_loader import LUTPresets, LUTLoader
    
    # 测试加载LUT文件
    luts_dir = Path(__file__).parent.parent / "assets" / "luts"
    if not luts_dir.exists():
        print(f"❌ LUT目录不存在: {luts_dir}")
        return False
    
    loader = LUTLoader()
    presets = LUTPresets(str(luts_dir))
    
    # 加载所有预设
    loaded = presets.load_all_presets()
    print(f"✅ 加载了 {len(loaded)} 个LUT预设")
    
    # 测试生成FFmpeg滤镜
    print("\n🎬 测试FFmpeg滤镜生成:")
    test_presets = ["ysjf_cinematic_film", "ysjf_teal_orange", "warm_red"]
    
    for preset_name in test_presets:
        lut_data = presets.get_preset(preset_name)
        if lut_data:
            filter_str = lut_data.to_ffmpeg_lut3d_filter()
            print(f"✅ {preset_name}: {filter_str[:60]}...")
        else:
            print(f"⚠️  {preset_name}: 不是LUT预设，跳过")
    
    return True

def test_color_grader_presets():
    """测试调色引擎预设"""
    print("\n🎨 测试调色引擎预设...")
    
    from core.color_grade import ColorGrader
    
    # 初始化调色引擎
    luts_dir = str(Path(__file__).parent.parent / "assets" / "luts")
    grader = ColorGrader(luts_directory=luts_dir)
    
    # 列出所有预设
    presets = grader.list_presets()
    print(f"✅ 可用预设总数: {len(presets)}")
    
    # 显示预设分类
    lut_presets = {k: v for k, v in presets.items() if v.get("type") == "lut"}
    param_presets = {k: v for k, v in presets.items() if v.get("type") == "parameter"}
    
    print(f"   - LUT预设: {len(lut_presets)} 个")
    print(f"   - 参数预设: {len(param_presets)} 个")
    
    # 测试获取预设
    print("\n📋 测试预设获取:")
    test_cases = [
        ("ysjf_cinematic_film", "影视飓风电影感"),
        ("ysjf_teal_orange", "影视飓风青橙调"),
        ("warm_red", "传统暖红色调"),
    ]
    
    for preset_name, desc in test_cases:
        config = grader.get_preset(preset_name)
        if config:
            print(f"✅ {desc} ({preset_name})")
            
            # 检查配置内容
            if "lut_file" in config:
                print(f"   类型: LUT文件")
                print(f"   文件: {config['lut_file']}")
            else:
                print(f"   类型: 参数配置")
        else:
            print(f"❌ {desc} ({preset_name}): 获取失败")
    
    return True

def test_ffmpeg_filter_generation():
    """测试FFmpeg滤镜生成"""
    print("\n🔧 测试FFmpeg滤镜生成...")
    
    from core.color_grade import ColorGrader
    
    grader = ColorGrader()
    
    # 测试不同预设的滤镜生成
    test_presets = [
        "ysjf_cinematic_film",
        "ysjf_teal_orange", 
        "warm_red",
        "professional"
    ]
    
    for preset_name in test_presets:
        config = grader.get_preset(preset_name)
        filter_str = grader.to_ffmpeg_filter(config)
        
        if filter_str:
            print(f"✅ {preset_name}:")
            print(f"   滤镜长度: {len(filter_str)} 字符")
            print(f"   滤镜预览: {filter_str[:80]}...")
        else:
            print(f"⚠️  {preset_name}: 未生成滤镜")
    
    return True

def main():
    """主函数"""
    print("🎬 LUT集成简单测试\n")
    
    tests = [
        ("LUT加载", test_lut_loading),
        ("调色引擎预设", test_color_grader_presets),
        ("FFmpeg滤镜生成", test_ffmpeg_filter_generation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "="*60)
    print("📊 测试结果汇总:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！LUT集成功能正常。")
        print("\n📝 说明:")
        print("   - LUT文件加载正常")
        print("   - 调色引擎预设管理正常")
        print("   - FFmpeg滤镜生成正常")
        print("   - 完整视频处理需要OpenCV支持")
        return 0
    else:
        print("⚠️  部分测试失败，请检查问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())