# LUT调色功能使用指南

## 概述

SOE Auto Editor 现在支持LUT（查找表）调色功能，特别是集成了影视飓风风格的LUT模板。LUT是一种专业的视频调色工具，可以快速应用电影级的色彩风格。

## 可用的LUT预设

### 影视飓风风格LUT

| 预设名称 | 文件名 | 描述 | 适用场景 |
|---------|--------|------|----------|
| `ysjf_cinematic_film` | ysjf_cinematic_film.cube | 电影感自然色调 | 各种场景，通用型 |
| `ysjf_teal_orange` | ysjf_teal_orange.cube | 经典青橙电影调 | 人像、风景、电影感强 |
| `ysjf_golden_hour` | ysjf_golden_hour.cube | 金色时刻暖调 | 日出日落、浪漫场景 |
| `ysjf_moody_cinematic` | ysjf_moody_cinematic.cube | 暗调电影感 | 悬疑、文艺片、暗调场景 |
| `ysjf_vintage_film` | ysjf_vintage_film.cube | 复古胶片感 | 怀旧、文艺、复古风格 |

### 传统参数预设

| 预设名称 | 描述 |
|---------|------|
| `warm_red` | 暖红色调，适合国企党建场景 |
| `professional` | 专业色调，适合商务会议 |
| `bright` | 明亮色调，适合展示类视频 |
| `warm` | 温暖色调，适合一般场景 |

## 使用方法

### 1. 命令行使用

#### 列出所有可用预设
```bash
# 列出所有调色预设（包括LUT和传统预设）
python agent_api.py --list-tones

# 仅列出LUT预设
python agent_api.py --list-luts
```

#### 使用LUT预设剪辑视频
```bash
# 使用影视飓风电影感LUT
python agent_api.py video1.mp4 video2.mp4 -t party_building --tone ysjf_cinematic_film

# 使用影视飓风青橙调LUT
python agent_api.py video.mp4 --tone ysjf_teal_orange

# 使用自定义LUT文件
python agent_api.py video.mp4 --lut /path/to/your/lut.cube
```

#### 完整示例
```bash
# 党建视频，使用影视飓风电影感LUT，添加标题和Logo
python agent_api.py input1.mp4 input2.mp4 \
  -t party_building \
  --tone ysjf_cinematic_film \
  --title "庆祝建党100周年" \
  --subtitle "不忘初心 牢记使命" \
  --org "XX集团党委" \
  --date "2026年7月1日" \
  --logo logo.png \
  -o output.mp4
```

### 2. API使用

#### 通过HTTP API
```python
import requests

# 使用影视飓风LUT
response = requests.post("http://localhost:8080/api/v1/edit", json={
    "input_videos": ["video1.mp4", "video2.mp4"],
    "template": "party_building",
    "title": "会议视频",
    "color_tone": "ysjf_teal_orange",  # 使用LUT预设
    "output_path": "output.mp4"
})
```

#### 通过Python代码
```python
from skill import SOEAutoEditSkill

skill = SOEAutoEditSkill()

# 使用LUT预设
result = skill.edit_sync(
    input_videos=["video1.mp4", "video2.mp4"],
    template="party_building",
    title="学习视频",
    color_tone="ysjf_golden_hour",  # 使用LUT预设
)

# 使用自定义LUT文件
result = skill.edit_sync(
    input_videos=["video1.mp4"],
    template="conference",
    color_tone="/path/to/custom.cube",  # 使用自定义LUT文件
)
```

## LUT文件格式

### 支持的格式
- `.cube` 标准3D LUT文件格式
- 支持任意尺寸（17x17x17, 33x33x33, 65x65x65等）

### LUT文件结构
```
# 注释行
TITLE "LUT名称"
LUT_3D_SIZE 33
DOMAIN_MIN 0.0 0.0 0.0
DOMAIN_MAX 1.0 1.0 1.0
0.000000 0.000000 0.000000
0.031250 0.000000 0.000000
...
```

## 添加自定义LUT

### 方法1：放入assets/luts目录
将`.cube`文件放入 `assets/luts/` 目录，系统会自动识别。

### 方法2：指定文件路径
在命令行或API中直接指定LUT文件的完整路径。

## 技术实现

### FFmpeg滤镜链
LUT通过FFmpeg的`lut3d`滤镜应用：
```
lut3d=file='path/to/lut.cube':interp=tetrahedral
```

### 插值算法
- 使用四面体插值（tetrahedral interpolation）
- 保证色彩过渡平滑自然

## 最佳实践

### 场景匹配建议
1. **党建/会议场景**：`ysjf_cinematic_film` 或 `warm_red`
2. **参观/展示场景**：`ysjf_teal_orange` 或 `bright`
3. **学习/培训场景**：`ysjf_golden_hour` 或 `warm`
4. **文艺/创意场景**：`ysjf_vintage_film` 或 `ysjf_moody_cinematic`

### 性能考虑
- LUT文件越大（如65x65x65），处理越慢，但效果越精细
- 33x33x33是常用的平衡尺寸
- 系统会自动缓存已加载的LUT文件

## 故障排除

### 常见问题
1. **LUT文件未找到**
   - 检查文件路径是否正确
   - 确认文件扩展名是`.cube`

2. **颜色效果不明显**
   - 尝试调整视频的曝光和白平衡
   - LUT效果依赖于输入视频的质量

3. **处理速度慢**
   - 使用较小尺寸的LUT文件
   - 减少同时处理的视频数量

## 更新日志

### v1.0.0 (2026-07-02)
- 新增LUT调色功能
- 集成影视飓风风格LUT模板
- 支持自定义LUT文件
- 命令行和API全面支持LUT参数