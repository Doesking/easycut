# EasyCut 易剪辑 v2.9

**AI 智能视频剪辑平台** — 专为国企宣传视频打造的一站式解决方案

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 核心功能

### 🎬 智能视频剪辑
- **8阶段自动剪辑流水线**：风格解析 → 视频分析 → 内容分类 → 评分选择 → 编辑计划 → 音乐选择 → 叠加层 → 调色 → 渲染
- **6个专业视频模板**：党建宣传、会议纪实、参观访问、学习培训、风光摄影、宣传视频
- **多格式导出**：MP4、MOV、剪映XML、EDL

### 🎨 专业调色系统
- **25个调色预设**：包含传统滤镜和3D LUT
- **影视飓风风格LUT**：5个专业电影感调色预设
- **自定义LUT上传**：支持.cube格式3D LUT文件
- **LUT预览功能**：实时预览调色效果

### 📸 智能照片处理
- **30+修图预设**：风景、人像、美食、建筑等
- **人脸美颜**：智能磨皮、美白、瘦脸
- **背景去除**：一键抠图
- **AI增强**：智能裁剪、水平校正、抗畸变

### 📝 AI脚本策划
- **智能脚本生成**：根据主题自动生成拍摄脚本
- **详细拍摄方案**：分场景脚本、镜头设计、解说词
- **多风格支持**：正式严谨、温情叙事、活力动感、纪实风格

### 🎵 音频处理
- **背景音乐混合**：自动匹配音乐风格
- **音量调节**：独立控制各音轨音量
- **语音识别**：基于Whisper的字幕生成

## 🚀 快速开始

### 环境要求
- Python 3.9+
- FFmpeg
- 约2GB磁盘空间（用于LUT文件和临时文件）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/easycut.git
cd easycut

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 生成LUT文件（可选）
python scripts/generate_luts.py

# 5. 启动服务
python web_server.py
```

### 访问界面
打开浏览器访问：**http://127.0.0.1:9090/**

## 📁 项目结构

```
easycut/
├── agent_api.py          # CLI入口 + FastAPI HTTP服务
├── skill.py              # 技能主入口
├── web_server.py         # Web前端服务
├── config.yaml           # 全局配置
├── requirements.txt      # Python依赖
│
├── core/                 # 核心引擎
│   ├── pipeline.py       # 主流水线
│   ├── color_grade.py    # 调色引擎
│   ├── lut_loader.py     # LUT文件加载器
│   ├── photo_enhancer.py # 照片增强
│   ├── face_enhancer.py  # 人脸美颜
│   ├── bg_remover.py     # 背景去除
│   ├── subtitle.py       # 字幕生成
│   ├── script_generator.py # 脚本生成
│   └── ...
│
├── assets/
│   └── luts/             # LUT文件目录
│       └── *.cube        # 3D LUT文件
│
├── templates/            # 视频模板配置
│   ├── party_building.json
│   ├── conference.json
│   └── ...
│
├── scripts/              # 工具脚本
│   └── generate_luts.py  # LUT生成脚本
│
├── ui_redesign/          # UI设计文件
│   ├── index_v3.html     # 最新UI设计
│   └── design-spec.md    # 设计规范
│
└── examples/             # 使用示例
    ├── lut_usage_example.yaml
    └── demo_lut_effects.py
```

## 🎯 使用指南

### 命令行使用

```bash
# 列出所有调色预设
python agent_api.py --list-tones

# 使用视频模板剪辑
python agent_api.py video.mp4 --template conference --tone ysjf_cinematic_film

# 使用自定义LUT
python agent_api.py video.mp4 --lut /path/to/custom.cube

# 照片修图
python agent_api.py photo.jpg --photo-preset landscape
```

### Web界面使用

1. **视频剪辑**
   - 选择视频模板
   - 上传视频文件
   - 选择调色风格
   - 点击"开始剪辑"

2. **照片修图**
   - 上传照片
   - 选择修图预设
   - 调整参数
   - 导出处理后的照片

3. **脚本策划**
   - 输入视频主题
   - 选择类别和风格
   - AI自动生成拍摄脚本
   - 查看详细拍摄方案

## 🎨 LUT预设列表

### 传统调色（8个）
- `vivid` - 鲜艳增强
- `cinema` - 电影质感
- `vintage` - 复古胶片
- `cool_tone` - 冷色调
- `warm_tone` - 暖色调
- `bw` - 黑白
- `high_contrast` - 高对比度
- `soft` - 柔和

### 影视飓风风格（5个）
- `ysjf_cinematic_film` - 电影感自然色调
- `ysjf_teal_orange` - 青橙电影调
- `ysjf_golden_hour` - 金色时刻暖调
- `ysjf_moody_cinematic` - 暗调电影感
- `ysjf_vintage_film` - 复古胶片感

### 通用LUT（6个）
- `landscape` - 风景优化
- `portrait` - 人像优化
- `vlog` - Vlog风格
- `dark_moody` - 暗调氛围
- `warm_sunset` - 暖色日落
- `bw_noir` - 黑白电影

## 🔧 配置说明

### config.yaml
```yaml
# Whisper模型配置
whisper:
  model_size: "medium"  # tiny/base/small/medium/large

# 输出配置
output:
  default_format: "mp4"
  default_resolution: "1080p"
  default_fps: 30

# LUT配置
lut:
  directory: "assets/luts"
  cache_enabled: true
```

## 📦 依赖说明

- **FastAPI** - Web框架
- **Uvicorn** - ASGI服务器
- **OpenCV** - 图像处理
- **Pillow** - 图像处理
- **NumPy** - 数值计算
- **PyYAML** - 配置解析
- **Whisper** - 语音识别
- **pymediainfo** - 媒体信息解析

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交Pull Request

## 📄 许可证

本项目采用 [MIT许可证](LICENSE) 开源。

## 🙏 致谢

- [FFmpeg](https://ffmpeg.org/) - 视频处理
- [OpenCV](https://opencv.org/) - 图像处理
- [Whisper](https://github.com/openai/whisper) - 语音识别
- [FastAPI](https://fastapi.tiangolo.com/) - Web框架
- 影视飓风 - LUT调色灵感

## 📧 联系方式

- GitHub: [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)
- Issues: [提交问题](https://github.com/YOUR_USERNAME/easycut/issues)

---

**EasyCut 易剪辑** — 让视频剪辑更简单、更专业、更高效！
