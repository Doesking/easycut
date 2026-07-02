#!/usr/bin/env python3
"""
测试LUT新功能
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.lut_loader import LUTLoader, LUTPresets

def test_lut_cache():
    """测试LUT缓存功能"""
    print("=== 测试LUT缓存功能 ===")
    
    loader = LUTLoader()
    
    # 测试加载LUT文件
    lut_dir = "assets/luts"
    if os.path.exists(lut_dir):
        for filename in os.listdir(lut_dir):
            if filename.endswith('.cube'):
                filepath = os.path.join(lut_dir, filename)
                lut_data = loader.load_cube_file(filepath)
                if lut_data:
                    print(f"✅ 加载成功: {filename} - {lut_data.title} ({lut_data.size}x{lut_data.size}x{lut_data.size})")
                else:
                    print(f"❌ 加载失败: {filename}")
    
    # 获取缓存统计
    stats = LUTLoader.get_cache_stats()
    print(f"\n缓存统计:")
    print(f"  缓存大小: {stats['cache_size']} 个LUT")
    print(f"  命中次数: {stats['hits']}")
    print(f"  未命中次数: {stats['misses']}")
    print(f"  命中率: {stats['hit_rate']:.1%}")
    print(f"  内存使用: {stats['memory_usage_mb']:.1f} MB")
    
    return True

def test_user_lut_directory():
    """测试用户LUT目录"""
    print("\n=== 测试用户LUT目录 ===")
    
    lut_dir = "uploads/luts"
    if os.path.exists(lut_dir):
        print(f"✅ 用户LUT目录存在: {lut_dir}")
        files = [f for f in os.listdir(lut_dir) if f.endswith('.cube')]
        print(f"  用户上传LUT数量: {len(files)}")
        for f in files:
            print(f"  - {f}")
    else:
        print(f"⚠️  用户LUT目录不存在: {lut_dir}")
        os.makedirs(lut_dir, exist_ok=True)
        print(f"✅ 已创建用户LUT目录: {lut_dir}")
    
    return True

def test_lut_presets():
    """测试LUT预设管理"""
    print("\n=== 测试LUT预设管理 ===")
    
    # 测试系统LUT目录
    system_dir = "assets/luts"
    if os.path.exists(system_dir):
        presets = LUTPresets(system_dir)
        presets.load_all_presets()
        
        print(f"系统LUT预设数量: {len(presets._presets)}")
        for name, lut in presets._presets.items():
            print(f"  - {name}: {lut.title} ({lut.size}x{lut.size}x{lut.size})")
    
    return True

def test_lut_compression():
    """测试LUT压缩功能"""
    print("\n=== 测试LUT压缩功能 ===")
    
    loader = LUTLoader()
    test_file = "assets/luts/ysjf_cinematic_film.cube"
    
    if os.path.exists(test_file):
        lut_data = loader.load_cube_file(test_file)
        if lut_data:
            # 测试压缩
            compressed = lut_data.get_compressed_data()
            original_size = lut_data.data.nbytes
            compressed_size = len(compressed)
            
            print(f"原始大小: {original_size / 1024:.1f} KB")
            print(f"压缩后大小: {compressed_size / 1024:.1f} KB")
            print(f"压缩率: {compressed_size / original_size:.1%}")
            
            # 测试解压
            from core.lut_loader import LUTData
            restored = LUTData.from_compressed_data(
                compressed, lut_data.size, 
                lut_data.domain_min, lut_data.domain_max,
                lut_data.title, lut_data.file_path
            )
            
            if restored.data.shape == lut_data.data.shape:
                print("✅ 压缩/解压测试通过")
            else:
                print("❌ 压缩/解压测试失败")
    
    return True

if __name__ == "__main__":
    print("开始测试LUT新功能...\n")
    
    tests = [
        test_lut_cache,
        test_user_lut_directory,
        test_lut_presets,
        test_lut_compression
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            results.append(False)
    
    print(f"\n=== 测试总结 ===")
    print(f"通过: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败")