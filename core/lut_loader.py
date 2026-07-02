"""
LUT文件加载器：支持标准.cube格式的3D LUT文件
用于视频调色引擎，支持FFmpeg lut3d滤镜
"""
import os
import re
from typing import Dict, List, Optional, Tuple
import numpy as np


class LUTLoader:
    """标准3D LUT文件加载器"""
    
    # 全局LUT缓存，跨实例共享
    _global_cache: Dict[str, 'LUTData'] = {}
    _cache_stats = {"hits": 0, "misses": 0}
    
    def __init__(self, use_global_cache: bool = True):
        self.use_global_cache = use_global_cache
        if not use_global_cache:
            self.lut_cache: Dict[str, 'LUTData'] = {}
    
    def load_cube_file(self, file_path: str) -> Optional['LUTData']:
        """
        加载.cube格式的3D LUT文件
        
        Args:
            file_path: .cube文件路径
            
        Returns:
            LUTData对象，包含LUT数据和元信息
        """
        if not os.path.exists(file_path):
            print(f"LUT文件不存在: {file_path}")
            return None
        
        # 检查缓存
        abs_path = os.path.abspath(file_path)
        
        # 使用全局缓存或实例缓存
        if self.use_global_cache:
            cache = LUTLoader._global_cache
        else:
            cache = self.lut_cache
        
        if abs_path in cache:
            LUTLoader._cache_stats["hits"] += 1
            return cache[abs_path]
        
        LUTLoader._cache_stats["misses"] += 1
        
        try:
            lut_data = self._parse_cube_file(file_path)
            if lut_data:
                cache[abs_path] = lut_data
            return lut_data
        except Exception as e:
            print(f"加载LUT文件失败: {e}")
            return None
    
    def _parse_cube_file(self, file_path: str) -> Optional['LUTData']:
        """
        解析.cube文件
        
        .cube文件格式：
        - 以#开头的行是注释
        - LUT_3D_SIZE <size> 定义LUT尺寸
        - DOMAIN_MIN <min_r> <min_g> <min_b> 定义域最小值（可选）
        - DOMAIN_MAX <max_r> <max_g> <max_b> 定义域最大值（可选）
        - 每行三个浮点数，空格分隔，表示R G B值
        - 数据顺序：蓝变化最慢，红最快（B-G-R顺序）
        """
        lut_size = 0
        domain_min = [0.0, 0.0, 0.0]
        domain_max = [1.0, 1.0, 1.0]
        title = ""
        data_lines = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 跳过空行
                if not line:
                    continue
                
                # 注释行
                if line.startswith('#'):
                    # 尝试提取标题
                    if 'Title' in line or 'title' in line or 'TITLE' in line:
                        title_match = re.search(r'[Tt]itle\s*[:=]?\s*(.+)', line)
                        if title_match:
                            title = title_match.group(1).strip()
                    continue
                
                # LUT尺寸
                if line.startswith('LUT_3D_SIZE'):
                    try:
                        lut_size = int(line.split()[1])
                    except (IndexError, ValueError):
                        print(f"无效的LUT_3D_SIZE格式: {line}")
                        return None
                    continue
                
                # 域最小值
                if line.startswith('DOMAIN_MIN'):
                    try:
                        parts = line.split()[1:]
                        domain_min = [float(x) for x in parts[:3]]
                    except (IndexError, ValueError):
                        pass
                    continue
                
                # 域最大值
                if line.startswith('DOMAIN_MAX'):
                    try:
                        parts = line.split()[1:]
                        domain_max = [float(x) for x in parts[:3]]
                    except (IndexError, ValueError):
                        pass
                    continue
                
                # 跳过其他元数据行
                if line.startswith(('TITLE', 'DESCRIPTION', 'LUT_1D_SIZE')):
                    continue
                
                # 数据行
                try:
                    values = [float(x) for x in line.split()]
                    if len(values) >= 3:
                        data_lines.append(values[:3])
                except ValueError:
                    continue
        
        # 验证LUT尺寸
        if lut_size == 0:
            print("未找到LUT_3D_SIZE定义")
            return None
        
        expected_entries = lut_size ** 3
        if len(data_lines) != expected_entries:
            print(f"LUT数据条目数不匹配: 期望 {expected_entries}, 实际 {len(data_lines)}")
            # 尝试截断或填充
            if len(data_lines) > expected_entries:
                data_lines = data_lines[:expected_entries]
            else:
                # 用零填充
                while len(data_lines) < expected_entries:
                    data_lines.append([0.0, 0.0, 0.0])
        
        # 转换为numpy数组
        lut_array = np.array(data_lines, dtype=np.float32)
        
        # 重塑为3D数组 (size, size, size, 3)
        # 注意：.cube文件的顺序是B-G-R，需要转换为R-G-B
        lut_3d = lut_array.reshape((lut_size, lut_size, lut_size, 3))
        
        # 从B-G-R转换为R-G-B
        # 原始索引：[b][g][r] -> 新索引：[r][g][b]
        lut_3d_rgb = np.transpose(lut_3d, (2, 1, 0, 3))
        
        return LUTData(
            size=lut_size,
            data=lut_3d_rgb,
            domain_min=domain_min,
            domain_max=domain_max,
            title=title or os.path.basename(file_path),
            file_path=file_path
        )
    
    def get_available_luts(self, directory: str) -> List[Dict[str, str]]:
        """
        获取目录中所有可用的LUT文件
        
        Args:
            directory: LUT文件目录
            
        Returns:
            LUT文件信息列表
        """
        luts = []
        if not os.path.exists(directory):
            return luts
        
        for filename in os.listdir(directory):
            if filename.lower().endswith('.cube'):
                filepath = os.path.join(directory, filename)
                try:
                    lut_data = self.load_cube_file(filepath)
                    if lut_data:
                        luts.append({
                            'name': lut_data.title,
                            'filename': filename,
                            'path': filepath,
                            'size': lut_data.size,
                            'description': f"{lut_data.size}x{lut_data.size}x{lut_data.size} LUT"
                        })
                except Exception as e:
                    print(f"读取LUT文件 {filename} 失败: {e}")
        
        return luts
    
    def clear_cache(self):
        """清除LUT缓存"""
        if self.use_global_cache:
            LUTLoader._global_cache.clear()
        else:
            self.lut_cache.clear()
    
    @classmethod
    def get_cache_stats(cls) -> Dict:
        """获取缓存统计信息"""
        return {
            "cache_size": len(cls._global_cache),
            "hits": cls._cache_stats["hits"],
            "misses": cls._cache_stats["misses"],
            "hit_rate": cls._cache_stats["hits"] / max(1, cls._cache_stats["hits"] + cls._cache_stats["misses"]),
            "memory_usage_mb": sum(lut.data.nbytes for lut in cls._global_cache.values()) / (1024 * 1024)
        }
    
    @classmethod
    def clear_global_cache(cls):
        """清除全局缓存"""
        cls._global_cache.clear()
        cls._cache_stats = {"hits": 0, "misses": 0}


class LUTData:
    """LUT数据容器"""
    
    def __init__(self, size: int, data: np.ndarray, 
                 domain_min: List[float], domain_max: List[float],
                 title: str, file_path: str):
        self.size = size
        self.data = data  # shape: (size, size, size, 3)
        self.domain_min = domain_min
        self.domain_max = domain_max
        self.title = title
        self.file_path = file_path
    
    def to_ffmpeg_lut3d_filter(self) -> str:
        """
        生成FFmpeg lut3d滤镜字符串
        
        Returns:
            FFmpeg lut3d滤镜参数
        """
        # 使用临时文件路径，FFmpeg会直接读取文件
        return f"lut3d=file='{self.file_path}':interp=tetrahedral"
    
    def get_info(self) -> Dict:
        """获取LUT信息"""
        return {
            'title': self.title,
            'size': self.size,
            'domain_min': self.domain_min,
            'domain_max': self.domain_max,
            'file_path': self.file_path,
            'memory_mb': self.data.nbytes / (1024 * 1024)
        }
    
    def get_compressed_data(self) -> bytes:
        """获取压缩后的LUT数据（用于存储或传输）"""
        import zlib
        # 将numpy数组转换为字节并压缩
        data_bytes = self.data.tobytes()
        compressed = zlib.compress(data_bytes, level=6)  # 平衡压缩率和速度
        return compressed
    
    @classmethod
    def from_compressed_data(cls, compressed_data: bytes, size: int, 
                           domain_min: List[float], domain_max: List[float],
                           title: str, file_path: str) -> 'LUTData':
        """从压缩数据创建LUTData对象"""
        import zlib
        # 解压缩数据
        data_bytes = zlib.decompress(compressed_data)
        # 重塑为3D数组
        data = np.frombuffer(data_bytes, dtype=np.float32).reshape((size, size, size, 3))
        return cls(size, data, domain_min, domain_max, title, file_path)
    
    def generate_optimized_cube_file(self, output_path: str, precision: int = 6) -> bool:
        """生成优化的.cube文件（减少文件大小）"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入头部信息
                f.write(f"# Optimized LUT file\n")
                f.write(f"# Title: {self.title}\n")
                f.write(f"LUT_3D_SIZE {self.size}\n")
                f.write(f"DOMAIN_MIN {self.domain_min[0]:.6f} {self.domain_min[1]:.6f} {self.domain_min[2]:.6f}\n")
                f.write(f"DOMAIN_MAX {self.domain_max[0]:.6f} {self.domain_max[1]:.6f} {self.domain_max[2]:.6f}\n")
                
                # 写入数据（使用指定精度）
                # 注意：.cube文件格式要求B-G-R顺序
                lut_3d_bgr = np.transpose(self.data, (2, 1, 0, 3))
                lut_array = lut_3d_bgr.reshape(-1, 3)
                
                for i in range(lut_array.shape[0]):
                    r, g, b = lut_array[i]
                    f.write(f"{r:.{precision}f} {g:.{precision}f} {b:.{precision}f}\n")
                
            return True
        except Exception as e:
            print(f"生成优化LUT文件失败: {e}")
            return False


class LUTPresets:
    """LUT预设管理器"""
    
    def __init__(self, luts_directory: str = None):
        self.luts_directory = luts_directory or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'assets', 'luts'
        )
        self.loader = LUTLoader()
        self._presets: Dict[str, LUTData] = {}
    
    def load_all_presets(self) -> Dict[str, LUTData]:
        """加载所有预设LUT"""
        if not os.path.exists(self.luts_directory):
            os.makedirs(self.luts_directory, exist_ok=True)
            return self._presets
        
        for filename in os.listdir(self.luts_directory):
            if filename.lower().endswith('.cube'):
                filepath = os.path.join(self.luts_directory, filename)
                lut_data = self.loader.load_cube_file(filepath)
                if lut_data:
                    # 使用文件名（不含扩展名）作为预设名
                    preset_name = os.path.splitext(filename)[0]
                    self._presets[preset_name] = lut_data
        
        return self._presets
    
    def get_preset(self, name: str) -> Optional[LUTData]:
        """获取指定预设"""
        if not self._presets:
            self.load_all_presets()
        return self._presets.get(name)
    
    def list_presets(self) -> List[Dict[str, str]]:
        """列出所有可用预设"""
        if not self._presets:
            self.load_all_presets()
        
        return [
            {
                'name': name,
                'title': lut.title,
                'size': lut.size,
                'description': f"{lut.title} ({lut.size}x{lut.size}x{lut.size})"
            }
            for name, lut in self._presets.items()
        ]
    
    def add_preset(self, name: str, file_path: str) -> bool:
        """添加新的预设"""
        lut_data = self.loader.load_cube_file(file_path)
        if lut_data:
            self._presets[name] = lut_data
            return True
        return False
    
    def remove_preset(self, name: str) -> bool:
        """移除预设"""
        if name in self._presets:
            del self._presets[name]
            return True
        return False


# 全局LUT预设管理器实例
_global_lut_presets = None


def get_global_lut_presets() -> LUTPresets:
    """获取全局LUT预设管理器"""
    global _global_lut_presets
    if _global_lut_presets is None:
        _global_lut_presets = LUTPresets()
    return _global_lut_presets


def load_lut_for_ffmpeg(lut_path: str) -> Optional[str]:
    """
    加载LUT文件并返回FFmpeg滤镜字符串
    
    Args:
        lut_path: LUT文件路径
        
    Returns:
        FFmpeg lut3d滤镜字符串，失败返回None
    """
    loader = LUTLoader()
    lut_data = loader.load_cube_file(lut_path)
    if lut_data:
        return lut_data.to_ffmpeg_lut3d_filter()
    return None


def create_sample_cube_file(output_path: str, size: int = 33):
    """
    创建示例.cube文件（用于测试）
    
    Args:
        output_path: 输出文件路径
        size: LUT尺寸（默认33）
    """
    with open(output_path, 'w') as f:
        f.write(f"# Sample 3D LUT\n")
        f.write(f"TITLE \"Sample LUT {size}x{size}x{size}\"\n")
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write(f"DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write(f"DOMAIN_MAX 1.0 1.0 1.0\n")
        
        # 生成渐变测试LUT
        for b_idx in range(size):
            for g_idx in range(size):
                for r_idx in range(size):
                    r = r_idx / (size - 1)
                    g = g_idx / (size - 1)
                    b = b_idx / (size - 1)
                    f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
    
    print(f"示例LUT文件已创建: {output_path}")


if __name__ == "__main__":
    # 测试LUT加载器
    loader = LUTLoader()
    
    # 创建测试LUT
    test_path = "/tmp/test_lut.cube"
    create_sample_cube_file(test_path, 17)
    
    # 加载测试LUT
    lut_data = loader.load_cube_file(test_path)
    if lut_data:
        print(f"加载成功: {lut_data.title}")
        print(f"尺寸: {lut_data.size}x{lut_data.size}x{lut_data.size}")
        print(f"数据形状: {lut_data.data.shape}")
        print(f"FFmpeg滤镜: {lut_data.to_ffmpeg_lut3d_filter()}")
        print(f"内存占用: {lut_data.get_info()['memory_mb']:.2f} MB")
