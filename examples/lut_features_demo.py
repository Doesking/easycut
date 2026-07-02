#!/usr/bin/env python3
"""
LUT新功能演示脚本
展示用户上传、预览、缓存等功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.lut_loader import LUTLoader, LUTPresets

def demo_cache_stats():
    """演示缓存统计功能"""
    print("=== LUT缓存统计演示 ===")
    
    loader = LUTLoader()
    
    # 加载一些LUT文件
    lut_dir = "assets/luts"
    if os.path.exists(lut_dir):
        for filename in os.listdir(lut_dir)[:5]:  # 只加载前5个
            if filename.endswith('.cube'):
                filepath = os.path.join(lut_dir, filename)
                loader.load_cube_file(filepath)
    
    # 获取缓存统计
    stats = LUTLoader.get_cache_stats()
    print(f"缓存大小: {stats['cache_size']} 个LUT")
    print(f"命中率: {stats['hit_rate']:.1%}")
    print(f"内存使用: {stats['memory_usage_mb']:.1f} MB")
    
    return stats

def demo_lut_presets():
    """演示LUT预设管理"""
    print("\n=== LUT预设管理演示 ===")
    
    # 系统LUT目录
    system_dir = "assets/luts"
    if os.path.exists(system_dir):
        presets = LUTPresets(system_dir)
        presets.load_all_presets()
        
        print(f"系统LUT预设数量: {len(presets._presets)}")
        
        # 显示前5个预设
        for i, (name, lut) in enumerate(presets._presets.items()):
            if i >= 5:
                print("...")
                break
            print(f"  {i+1}. {name}: {lut.title} ({lut.size}x{lut.size}x{lut.size})")
    
    return presets

def demo_compression():
    """演示LUT压缩功能"""
    print("\n=== LUT压缩功能演示 ===")
    
    loader = LUTLoader()
    test_file = "assets/luts/ysjf_cinematic_film.cube"
    
    if os.path.exists(test_file):
        lut_data = loader.load_cube_file(test_file)
        if lut_data:
            # 测试压缩
            compressed = lut_data.get_compressed_data()
            original_size = lut_data.data.nbytes
            compressed_size = len(compressed)
            
            print(f"文件: {test_file}")
            print(f"原始大小: {original_size / 1024:.1f} KB")
            print(f"压缩后大小: {compressed_size / 1024:.1f} KB")
            print(f"压缩率: {compressed_size / original_size:.1%}")
            
            # 测试生成优化文件
            output_path = "output/optimized_lut.cube"
            os.makedirs("output", exist_ok=True)
            
            if lut_data.generate_optimized_cube_file(output_path, precision=4):
                optimized_size = os.path.getsize(output_path)
                print(f"优化文件大小: {optimized_size / 1024:.1f} KB")
                print(f"优化压缩率: {optimized_size / original_size:.1%}")
    
    return True

def demo_user_lut_directory():
    """演示用户LUT目录"""
    print("\n=== 用户LUT目录演示 ===")
    
    user_dir = "uploads/luts"
    if os.path.exists(user_dir):
        files = [f for f in os.listdir(user_dir) if f.endswith('.cube')]
        print(f"用户上传LUT数量: {len(files)}")
        
        if files:
            for f in files[:3]:  # 显示前3个
                print(f"  - {f}")
            if len(files) > 3:
                print(f"  ... 还有 {len(files) - 3} 个文件")
        else:
            print("暂无用户上传的LUT文件")
    else:
        print("用户LUT目录不存在")
    
    return True

def demo_api_endpoints():
    """演示API端点"""
    print("\n=== API端点演示 ===")
    
    endpoints = [
        ("POST", "/api/upload-lut", "上传自定义LUT文件"),
        ("GET", "/api/user-luts", "获取用户上传的LUT列表"),
        ("GET", "/api/lut-preview/{lut_name}", "生成LUT预览图像"),
        ("GET", "/api/lut-cache-stats", "获取缓存统计信息"),
        ("POST", "/api/lut-cache-clear", "清除LUT缓存"),
        ("GET", "/api/color-presets", "获取所有调色预设"),
    ]
    
    print("新增API端点:")
    for method, path, desc in endpoints:
        print(f"  {method:4} {path:30} - {desc}")
    
    return True

if __name__ == "__main__":
    print("LUT新功能演示\n")
    
    demos = [
        demo_cache_stats,
        demo_lut_presets,
        demo_compression,
        demo_user_lut_directory,
        demo_api_endpoints
    ]
    
    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"演示失败: {e}")
    
    print("\n=== 演示完成 ===")
    print("所有功能已集成到web_server.py中")
    print("启动Web服务器: python web_server.py")
    print("访问 http://localhost:8080 查看完整功能")