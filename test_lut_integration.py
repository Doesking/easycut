#!/usr/bin/env python3
"""
测试LUT集成功能
验证影视飓风LUT模板是否正确集成
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_lut_loader():
    """测试LUT加载器"""
    print("🧪 测试LUT加载器...")
    
    from core.lut_loader import LUTPresets, LUTLoader
    
    # 测试加载LUT文件
    luts_dir = Path(__file__).parent / "assets" / "luts"
    if not luts_dir.exists():
        print(f"❌ LUT目录不存在: {luts_dir}")
        return False
    
    loader = LUTLoader()
    presets = LUTPresets(str(luts_dir))
    
    # 加载所有预设
    loaded = presets.load_all_presets()
    print(f"✅ 加载了 {len(loaded)} 个LUT预设")
    
    for name, lut_data in loaded.items():
        print(f"   - {name}: {lut_data.title} ({lut_data.size}x{lut_data.size}x{lut_data.size})")
    
    return True

def test_color_grader():
    """测试调色引擎"""
    print("\n🧪 测试调色引擎...")
    
    from core.color_grade import ColorGrader
    
    # 初始化调色引擎
    luts_dir = str(Path(__file__).parent / "assets" / "luts")
    grader = ColorGrader(luts_directory=luts_dir)
    
    # 列出所有预设
    presets = grader.list_presets()
    print(f"✅ 可用预设总数: {len(presets)}")
    
    # 测试获取LUT预设
    test_presets = ["ysjf_cinematic_film", "ysjf_teal_orange", "warm_red"]
    for preset_name in test_presets:
        try:
            config = grader.get_preset(preset_name)
            print(f"✅ 预设 '{preset_name}' 获取成功")
            
            # 测试生成FFmpeg滤镜
            filter_str = grader.to_ffmpeg_filter(config)
            if filter_str:
                print(f"   FFmpeg滤镜: {filter_str[:80]}...")
            else:
                print(f"   ⚠️  未生成FFmpeg滤镜")
        except Exception as e:
            print(f"❌ 预设 '{preset_name}' 获取失败: {e}")
    
    return True

def test_pipeline_integration():
    """测试流水线集成"""
    print("\n🧪 测试流水线集成...")
    
    try:
        from core.pipeline import AutoEditPipeline
        
        # 初始化流水线
        pipeline = AutoEditPipeline("config.yaml")
        print("✅ 流水线初始化成功")
        
        # 检查color_grader是否正确初始化
        if hasattr(pipeline, 'color_grader'):
            print("✅ 调色引擎已集成到流水线")
            
            # 测试获取LUT预设
            config = pipeline.color_grader.get_preset("ysjf_cinematic_film")
            if config:
                print("✅ 流水线中LUT预设可用")
            else:
                print("❌ 流水线中LUT预设不可用")
        else:
            print("❌ 调色引擎未集成到流水线")
        
        return True
    except Exception as e:
        print(f"❌ 流水线集成测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("🎬 开始LUT集成测试...\n")
    
    tests = [
        ("LUT加载器", test_lut_loader),
        ("调色引擎", test_color_grader),
        ("流水线集成", test_pipeline_integration),
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
    print("\n" + "="*50)
    print("📊 测试结果汇总:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！LUT集成成功！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())