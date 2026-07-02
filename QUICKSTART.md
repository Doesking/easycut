# 🚀 快速开始 - 一键启动

## macOS / Linux 用户

### 方法一：双击启动（推荐）
1. 在 Finder 中找到 `EasyCut.command` 文件
2. 双击运行
3. 首次运行会自动安装依赖（需要网络连接）
4. 浏览器会自动打开 EasyCut 界面

### 方法二：终端启动
```bash
# 进入项目目录
cd easycut

# 给启动脚本添加执行权限
chmod +x EasyCut.command

# 运行启动脚本
./EasyCut.command
```

---

## Windows 用户

### 方法一：双击启动（推荐）
1. 在文件资源管理器中找到 `EasyCut.bat` 文件
2. 双击运行
3. 首次运行会自动安装依赖（需要网络连接）
4. 浏览器会自动打开 EasyCut 界面

### 方法二：命令行启动
```cmd
cd easycut
EasyCut.bat
```

---

## 首次运行说明

首次运行时，启动脚本会自动：
1. ✅ 检查 Python 环境（需要 3.9+）
2. ✅ 检查 FFmpeg（可选，用于视频处理）
3. ✅ 创建 Python 虚拟环境
4. ✅ 安装所有依赖包
5. ✅ 创建必要的目录
6. ✅ 启动 Web 服务
7. ✅ 自动打开浏览器

整个过程大约需要 1-3 分钟（取决于网络速度）。

---

## 启动后访问

服务启动后，浏览器会自动打开：
```
http://127.0.0.1:9090
```

如果没有自动打开，请手动在浏览器中访问上述地址。

---

## 停止服务

- **macOS/Linux**: 在终端窗口按 `Ctrl+C` 或关闭终端窗口
- **Windows**: 关闭命令行窗口

---

## 常见问题

### Q: 提示 "Python 未找到"？
A: 请安装 Python 3.9+，下载地址：https://www.python.org/downloads/
   - 安装时请勾选 "Add Python to PATH"

### Q: 提示 "FFmpeg 未找到"？
A: FFmpeg 是可选的，但推荐安装以获得完整的视频处理功能：
   - macOS: `brew install ffmpeg`
   - Windows: 下载 https://github.com/BtbN/FFmpeg-Builds/releases

### Q: 依赖安装失败？
A: 可能是网络问题，请尝试：
   1. 检查网络连接
   2. 使用 VPN 或切换网络
   3. 手动安装：`pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/`

### Q: 端口被占用？
A: 启动脚本会自动尝试其他端口（9090-9099）。如果仍然失败：
   1. 关闭占用端口的程序
   2. 或手动指定端口：`python web_server.py --port 8080`

### Q: 浏览器无法访问？
A: 请检查：
   1. 终端是否显示 "服务地址: http://127.0.0.1:9090"
   2. 浏览器是否设置了代理（需要排除 localhost）
   3. 尝试使用不同的浏览器

---

## 命令行参数

如果需要自定义启动选项，可以直接运行 Python：

```bash
python web_server.py --help

# 自定义端口
python web_server.py --port 8080

# 不自动打开浏览器
python web_server.py --no-browser

# 调试模式
python web_server.py --log-level debug
```

---

## 技术支持

- GitHub Issues: https://github.com/Doesking/easycut/issues
- 文档: README.md

---

**享受使用 EasyCut！** 🎬
