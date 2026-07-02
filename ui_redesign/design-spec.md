# SOE Auto Editor UI 重构设计规范

## 项目概述
SOE Auto Editor (EasyCut) 是一个AI自动视频剪辑平台，专注于国企宣传视频的自动制作。

## 重构目标
**视觉风格现代化**：更新色彩、字体、图标、动画等视觉元素，使其更符合现代剪辑软件风格。

## 参考风格
1. **剪映/CapCut**：现代化设计，适合短视频创作，操作简单直观
2. **Final Cut Pro**：苹果风格，简洁优雅，高效工作流

## 保留功能
1. 侧边栏导航
2. 模板选择系统
3. LUT调色系统
4. 多格式导出

## 当前设计系统分析

### 现有色彩方案
```css
/* 暗色主题 */
--bg-base: #07080d;
--bg-elevated: #0d0f17;
--bg-card: #11131e;
--bg-hover: #181b28;
--border: #1e2130;
--border-active: #4f46e5;
--text: #e8eaf0;
--text2: #7c8096;
--text3: #515570;
--accent: #6366f1;
--accent-glow: rgba(99,102,241,.25);
--accent-2: #a855f7;
--green: #22c55e;
--red: #ef4444;
--yellow: #f59e0b;
```

### 现有字体
- 系统字体栈：`-apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", sans-serif`

### 现有布局
- 固定侧边栏（220px）
- 主内容区域
- 卡片式布局
- 响应式设计

## 新设计方向

### 色彩方案（参考剪映/CapCut）
```css
/* 主色调：深蓝紫渐变 */
--primary: #6366f1;
--primary-light: #818cf8;
--primary-dark: #4f46e5;

/* 背景色：更深沉的暗色 */
--bg-base: #0a0a0f;
--bg-elevated: #12121a;
--bg-card: #1a1a25;
--bg-hover: #22222e;

/* 文字色：更清晰的对比 */
--text: #f0f0f5;
--text2: #a0a0b0;
--text3: #707080;

/* 强调色：更现代的渐变 */
--accent: linear-gradient(135deg, #6366f1, #a855f7);
--accent-glow: rgba(99,102,241,.3);

/* 状态色：更鲜艳 */
--success: #10b981;
--error: #ef4444;
--warning: #f59e0b;
```

### 字体系统
```css
/* 显示字体：更现代的无衬线 */
font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;

/* 代码字体：等宽字体 */
font-family: "SF Mono", "Fira Code", monospace;
```

### 布局系统
1. **侧边栏**：保持220px宽度，但更简洁的设计
2. **主内容区**：更大的间距，更好的呼吸感
3. **卡片系统**：更圆润的边框，更明显的层次
4. **响应式**：保持现有响应式断点

### 交互设计
1. **拖拽上传**：更直观的拖拽区域
2. **实时预览**：视频/照片处理时的实时反馈
3. **动画过渡**：平滑的页面切换和元素动画
4. **状态反馈**：更清晰的处理状态指示

## 设计原则

### 1. 简洁优先
- 减少视觉噪音
- 突出核心功能
- 保持界面清爽

### 2. 一致性
- 统一的色彩语言
- 一致的交互模式
- 统一的间距系统

### 3. 可访问性
- 足够的对比度
- 清晰的视觉层次
- 直观的操作反馈

### 4. 现代感
- 微妙的渐变效果
- 平滑的动画过渡
- 现代的图标设计

## 组件设计规范

### 按钮
```css
/* 主要按钮 */
.btn-primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-light));
  color: white;
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--accent-glow);
}
```

### 卡片
```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s ease;
}

.card:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}
```

### 输入框
```css
input, select, textarea {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  color: var(--text);
  transition: all 0.2s ease;
}

input:focus, select:focus, textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--accent-glow);
}
```

## 图标系统
- 使用Emoji作为临时图标（保持现有）
- 考虑引入专业图标库（如Lucide Icons）
- 保持图标风格一致

## 动画规范
- 页面切换：300ms ease-in-out
- 元素出现：200ms ease-out
- 悬停效果：150ms ease
- 加载动画：循环旋转

## 响应式断点
- 移动端：< 768px
- 平板：768px - 1024px
- 桌面：> 1024px

## 下一步行动
1. 创建新的HTML/CSS文件
2. 重构侧边栏设计
3. 更新卡片和表单样式
4. 添加动画效果
5. 测试响应式布局