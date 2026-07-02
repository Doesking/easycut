"""
EasyCut 易剪辑 v2.9 — AI 自动视频剪辑平台
大厂风格 · 暗色主题 · 风光摄影 · 智能剪辑

启动: python3.11 web_server.py
访问: http://127.0.0.1:8080
"""
import os, sys, json, asyncio, logging, uuid, time, io, base64, subprocess
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import asdict

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from PIL import Image
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))
from core.pipeline import AutoEditPipeline, EditRequest
from core.photo_enhancer import PhotoEnhancer, PRESET_LIBRARY, CATEGORY_NAMES, EnhanceParams

from core.jianying_exporter import JianyingDraftExporter
from core.subtitle import WhisperSubtitle
from core.speed_control import change_speed, SPEED_PRESETS
from core.pip_composer import pip_overlay, split_screen, PIP_POSITIONS, PIP_SIZES
from core.bg_remover import BackgroundRemover
from core.face_enhancer import FaceEnhancer
from core.auto_enhance import ai_auto_enhance, auto_crop, auto_level, auto_lens_correction
from core.keyframe_anim import apply_ken_burns, PRESETS as KB_PRESETS
from core.transitions import apply_transition_clip, apply_transition_between, apply_transition_chain, TRANSITIONS
from core.script_generator import ScriptGenerator, format_script_preview
from core.audio_mixer import mix_background_music, get_audio_info, adjust_audio_volume

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("EasyCut")

app = FastAPI(title="EasyCut 易剪辑", version="2.9.0")
tasks: Dict[str, Dict] = {}
photo_enhancer = PhotoEnhancer()
jianying_exporter = JianyingDraftExporter()
whisper_subtitle = WhisperSubtitle(model_size="medium")
bg_remover = BackgroundRemover()
face_enhancer = FaceEnhancer()
script_generator = ScriptGenerator()

for d in ["uploads", "output", "assets/music", "uploads/covers", "uploads/logos"]:
    Path(d).mkdir(parents=True, exist_ok=True)

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EasyCut 易剪辑 — AI 智能视频·照片处理</title>
<style>
/* ═══════ MODERN THEME V3 (参考剪映/CapCut + Final Cut Pro) ═══════ */
:root {
  /* 主色调：深蓝紫渐变 */
  --primary: #6366f1;
  --primary-light: #818cf8;
  --primary-dark: #4f46e5;
  --primary-glow: rgba(99, 102, 241, 0.3);
  
  /* 背景色：更深沉的暗色 */
  --bg-base: #0a0a0f;
  --bg-elevated: #12121a;
  --bg-card: #1a1a25;
  --bg-hover: #22222e;
  --bg-input: #16161f;
  
  /* 文字色：更清晰的对比 */
  --text: #f0f0f5;
  --text2: #a0a0b0;
  --text3: #707080;
  --text4: #505060;
  
  /* 边框色 */
  --border: #2a2a38;
  --border-active: #6366f1;
  
  /* 状态色 */
  --success: #10b981;
  --error: #ef4444;
  --warning: #f59e0b;
  --info: #3b82f6;
  
  /* 间距系统 */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 20px;
  --space-2xl: 24px;
  --space-3xl: 32px;
  
  /* 圆角系统 */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  
  /* 阴影系统 */
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.3);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.4);
  
  /* 动画系统 */
  --transition-fast: 0.15s ease;
  --transition-normal: 0.2s ease;
  --transition-slow: 0.3s ease;
  
  /* 侧边栏宽度 */
  --sidebar-width: 240px;
  --sidebar-collapsed: 72px;
}

/* ═══════ RESET & BASE ═══════ */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: "SF Pro Display", -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
  background: var(--bg-base);
  color: var(--text);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  line-height: 1.5;
}

/* ═══════ APP LAYOUT ═══════ */
.app {
  display: flex;
  min-height: 100vh;
}

/* ═══════ SIDEBAR ═══════ */
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: var(--bg-elevated);
  border-right: 1px solid var(--border);
  z-index: 100;
  display: flex;
  flex-direction: column;
  transition: width var(--transition-slow);
  overflow: hidden;
}

.sidebar-header {
  padding: var(--space-xl) var(--space-lg) var(--space-lg);
  border-bottom: 1px solid var(--border);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.sidebar-logo .icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, var(--primary), var(--primary-light));
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 800;
  color: #fff;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-normal);
}

.sidebar-logo .icon:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 12px var(--primary-glow);
}

.sidebar-logo .name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
}

.sidebar-ver {
  font-size: 11px;
  color: var(--text3);
  padding: 0 var(--space-lg);
  margin-top: var(--space-xs);
}

/* ═══════ NAVIGATION ═══════ */
.nav-section {
  margin-top: var(--space-xl);
  padding: 0 var(--space-sm);
}

.nav-label {
  padding: var(--space-xs) var(--space-md);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text3);
  font-weight: 600;
  margin-bottom: var(--space-xs);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  font-size: 14px;
  color: var(--text2);
  cursor: pointer;
  transition: all var(--transition-fast);
  border-radius: var(--radius-md);
  margin: var(--space-xs) 0;
  border: 1px solid transparent;
  position: relative;
  overflow: hidden;
}

.nav-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.1), transparent);
  transition: left 0.5s ease;
}

.nav-item:hover::before {
  left: 100%;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text);
  border-color: var(--border);
}

.nav-item.active {
  background: rgba(99, 102, 241, 0.1);
  color: var(--primary);
  font-weight: 600;
  border-color: rgba(99, 102, 241, 0.2);
}

.nav-item .badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: rgba(99, 102, 241, 0.15);
  color: var(--primary);
  margin-left: auto;
  font-weight: 600;
}

/* ═══════ SIDEBAR FOOTER ═══════ */
.sidebar-footer {
  margin-top: auto;
  padding: var(--space-lg);
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.theme-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: var(--bg-card);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all var(--transition-fast);
  color: var(--text2);
}

.theme-btn:hover {
  background: var(--bg-hover);
  color: var(--text);
  border-color: var(--primary);
  transform: rotate(180deg);
}

.kb-hint {
  font-size: 11px;
  color: var(--text3);
  font-weight: 500;
}

/* ═══════ MAIN CONTENT ═══════ */
.main {
  margin-left: var(--sidebar-width);
  flex: 1;
  padding: var(--space-2xl) var(--space-3xl);
  max-width: calc(100vw - var(--sidebar-width));
  transition: margin-left var(--transition-slow);
}

/* ═══════ PAGE HEADER ═══════ */
.page-header {
  margin-bottom: var(--space-2xl);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: var(--space-xs);
}

.page-header .subtitle {
  font-size: 14px;
  color: var(--text2);
  font-weight: 400;
}

/* ═══════ PANELS GRID ═══════ */
.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2xl);
}

@media (max-width: 1200px) {
  .panels {
    grid-template-columns: 1fr;
  }
}

.panel {
  display: none;
}

.panel.active {
  display: contents;
}

/* ═══════ CARDS ═══════ */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  margin-bottom: var(--space-lg);
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--primary), var(--primary-light));
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.card:hover {
  border-color: rgba(99, 102, 241, 0.3);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card:hover::before {
  opacity: 1;
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.card-header .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 8px var(--primary-glow);
  flex-shrink: 0;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.2); }
}

.card-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

/* ═══════ FORM ELEMENTS ═══════ */
input[type="text"],
input[type="file"],
input[type="number"],
textarea,
select {
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text);
  font-size: 14px;
  outline: none;
  font-family: inherit;
  transition: all var(--transition-fast);
  resize: vertical;
}

input:focus,
textarea:focus,
select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

input::placeholder,
textarea::placeholder {
  color: var(--text3);
}

select {
  appearance: none;
  cursor: pointer;
  padding-right: 36px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23707080' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
}

input[type="range"] {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--border);
  border-radius: 3px;
  outline: none;
  margin: var(--space-sm) 0;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
  border: 3px solid var(--bg-card);
  box-shadow: 0 0 8px var(--primary-glow);
  transition: all var(--transition-fast);
}

input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.1);
  box-shadow: 0 0 12px var(--primary-glow);
}

/* ═══════ BUTTONS ═══════ */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-xl);
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: inherit;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
}

.btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  transition: width 0.3s ease, height 0.3s ease;
}

.btn:active::after {
  width: 200%;
  height: 200%;
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary), var(--primary-light));
  color: #fff;
  box-shadow: 0 2px 8px var(--primary-glow);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px var(--primary-glow);
}

.btn-secondary {
  background: var(--bg-hover);
  color: var(--text2);
  border: 1px solid var(--border);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text);
  border-color: var(--primary);
}

.btn-sm {
  padding: var(--space-sm) var(--space-md);
  font-size: 12px;
  border-radius: var(--radius-sm);
}

.btn-row {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-md);
  flex-wrap: wrap;
}

/* ═══════ DROPZONE ═══════ */
.dropzone {
  border: 2px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-3xl);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-normal);
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg-input);
  position: relative;
}

.dropzone:hover,
.dropzone.drag-over {
  border-color: var(--primary);
  background: rgba(99, 102, 241, 0.05);
  box-shadow: 0 0 20px var(--primary-glow);
}

.dropzone.drag-over {
  animation: dropzone-pulse 1s infinite;
}

@keyframes dropzone-pulse {
  0%, 100% { box-shadow: 0 0 20px var(--primary-glow); }
  50% { box-shadow: 0 0 40px var(--primary-glow); }
}

.dropzone input {
  display: none;
}

.dropzone .dz-icon {
  font-size: 48px;
  opacity: 0.6;
  margin-bottom: var(--space-md);
  transition: all var(--transition-normal);
}

.dropzone:hover .dz-icon {
  opacity: 1;
  transform: scale(1.1);
}

.dropzone .dz-hint {
  font-size: 14px;
  color: var(--text2);
  margin-bottom: var(--space-xs);
}

.dropzone .dz-hint strong {
  color: var(--primary);
  font-weight: 600;
}

/* ═══════ PROGRESS ═══════ */
.progress-wrap {
  display: none;
  margin-top: var(--space-lg);
}

.progress-wrap.active {
  display: block;
}

.progress-bar {
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--primary-light));
  width: 0;
  transition: width var(--transition-slow);
  border-radius: 3px;
  box-shadow: 0 0 10px var(--primary-glow);
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: progress-shine 2s infinite;
}

@keyframes progress-shine {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-text {
  font-size: 12px;
  color: var(--text2);
  margin-top: var(--space-sm);
  display: flex;
  justify-content: space-between;
}

/* ═══════ RESULT ═══════ */
.result-card {
  display: none;
  margin-top: var(--space-xl);
}

.result-card.active {
  display: block;
  animation: fadeInUp 0.5s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-video {
  width: 100%;
  border-radius: var(--radius-lg);
  background: #000;
  box-shadow: var(--shadow-lg);
}

.download-links {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
  margin-top: var(--space-md);
}

.download-link {
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--primary);
  text-decoration: none;
  border: 1px solid rgba(99, 102, 241, 0.2);
  transition: all var(--transition-fast);
  font-weight: 500;
}

.download-link:hover {
  background: rgba(99, 102, 241, 0.1);
  border-color: var(--primary);
  transform: translateY(-2px);
}

/* ═══════ FILE LIST ═══════ */
.file-list {
  margin-top: var(--space-md);
  font-size: 12px;
  color: var(--text3);
}

.file-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--bg-input);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-xs);
  border: 1px solid var(--border);
  transition: all var(--transition-fast);
}

.file-item:hover {
  border-color: var(--primary);
  background: rgba(99, 102, 241, 0.05);
}

.file-item .file-icon {
  font-size: 16px;
  opacity: 0.7;
}

.file-item .file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-item .file-size {
  font-size: 11px;
  color: var(--text4);
}

.file-item .file-remove {
  cursor: pointer;
  color: var(--text3);
  transition: color var(--transition-fast);
}

.file-item .file-remove:hover {
  color: var(--error);
}

/* ═══════ VISUALIZATION ═══════ */
.visual-card {
  background: linear-gradient(135deg, var(--bg-card), var(--bg-elevated));
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  margin-bottom: var(--space-lg);
  position: relative;
  overflow: hidden;
  transition: all var(--transition-normal);
}

.visual-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at top right, var(--primary-glow), transparent 70%);
  pointer-events: none;
  opacity: 0.3;
  transition: opacity var(--transition-normal);
}

.visual-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.visual-card:hover::after {
  opacity: 0.5;
}

.visual-card .visual-title {
  font-size: 13px;
  color: var(--text2);
  margin-bottom: var(--space-sm);
  font-weight: 500;
}

.visual-card .visual-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: var(--space-xs);
  transition: all var(--transition-normal);
}

.visual-card:hover .visual-value {
  color: var(--primary);
}

.visual-card .visual-change {
  font-size: 12px;
  color: var(--success);
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.visual-card .visual-change.negative {
  color: var(--error);
}

/* ═══════ STATS GRID ═══════ */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-lg);
  margin-bottom: var(--space-2xl);
}

/* ═══════ TOAST ═══════ */
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  padding: var(--space-md) var(--space-xl);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 550;
  opacity: 0;
  transform: translateX(100%);
  transition: all var(--transition-slow);
  pointer-events: none;
  box-shadow: var(--shadow-lg);
}

.toast.show {
  opacity: 1;
  transform: translateX(0);
}

.toast-success {
  background: var(--success);
  color: #fff;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.toast-error {
  background: var(--error);
  color: #fff;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

/* ═══════ LOADING ═══════ */
.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(10, 10, 15, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: var(--radius-lg);
  opacity: 0;
  visibility: hidden;
  transition: all var(--transition-normal);
}

.loading-overlay.active {
  opacity: 1;
  visibility: visible;
}

/* ═══════ TOOLTIP ═══════ */
.tooltip {
  position: relative;
  display: inline-block;
}

.tooltip .tooltip-text {
  visibility: hidden;
  width: 120px;
  background-color: var(--bg-elevated);
  color: var(--text);
  text-align: center;
  border-radius: var(--radius-sm);
  padding: var(--space-sm) var(--space-md);
  position: absolute;
  z-index: 1;
  bottom: 125%;
  left: 50%;
  margin-left: -60px;
  opacity: 0;
  transition: opacity var(--transition-fast);
  font-size: 11px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-md);
}

.tooltip .tooltip-text::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: var(--border) transparent transparent transparent;
}

.tooltip:hover .tooltip-text {
  visibility: visible;
  opacity: 1;
}

/* ═══════ RESPONSIVE ═══════ */
@media (max-width: 1024px) {
  :root {
    --sidebar-width: 72px;
  }
  
  .sidebar .name,
  .sidebar .nav-label,
  .sidebar .nav-item span:not(.nav-emoji),
  .sidebar .kb-hint,
  .sidebar .subtitle,
  .sidebar-ver {
    display: none;
  }
  
  .sidebar-logo {
    justify-content: center;
  }
  
  .nav-item {
    justify-content: center;
    padding: var(--space-md);
  }
  
  .main {
    padding: var(--space-xl);
  }
}

@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    z-index: 1000;
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
  
  .main {
    margin-left: 0;
    padding: var(--space-lg);
  }
  
  .panels {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-md);
  }
  
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}

/* ═══════ ANIMATIONS ═══════ */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.card {
  animation: fadeIn 0.3s ease-out;
}

.panel.active .card:nth-child(1) { animation-delay: 0.05s; }
.panel.active .card:nth-child(2) { animation-delay: 0.1s; }
.panel.active .card:nth-child(3) { animation-delay: 0.15s; }
.panel.active .card:nth-child(4) { animation-delay: 0.2s; }

/* ═══════ SCROLLBAR ═══════ */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-base);
}

::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text3);
}

/* ═══════ UTILITY CLASSES ═══════ */
.hidden { display: none !important; }
.visible { display: block !important; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.mt-1 { margin-top: var(--space-sm); }

/* ═══════ SCRIPT CARDS ═══════ */
.script-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.script-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--primary), var(--primary-light));
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.script-card:hover {
  border-color: var(--primary);
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.script-card:hover::before {
  opacity: 1;
}

.script-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-md);
}

.script-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: var(--space-xs);
}

.script-card-meta {
  display: flex;
  gap: var(--space-md);
  font-size: 12px;
  color: var(--text3);
  margin-bottom: var(--space-md);
}

.script-card-tag {
  display: inline-block;
  padding: 2px 8px;
  background: var(--primary-glow);
  color: var(--primary-light);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
}

.script-card-preview {
  font-size: 13px;
  color: var(--text2);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.script-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--space-lg);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border);
}

.script-card-actions {
  display: flex;
  gap: var(--space-sm);
}

.script-card-actions .btn {
  padding: 4px 10px;
  font-size: 12px;
}

/* Script Detail Sections */
.script-section {
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
}

.script-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-light);
  margin-bottom: var(--space-md);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.script-step {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--border);
}

.script-step:last-child {
  border-bottom: none;
}

.script-step-number {
  width: 24px;
  height: 24px;
  background: var(--primary);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.script-step-content {
  flex: 1;
}

.script-step-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: var(--space-xs);
}

.script-step-desc {
  font-size: 12px;
  color: var(--text2);
  line-height: 1.5;
}

.script-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.script-info-item {
  background: var(--bg-input);
  padding: var(--space-md);
  border-radius: var(--radius-md);
  text-align: center;
}

.script-info-label {
  font-size: 11px;
  color: var(--text3);
  margin-bottom: var(--space-xs);
}

.script-info-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}
.mt-2 { margin-top: var(--space-md); }
.mt-3 { margin-top: var(--space-lg); }
.mb-1 { margin-bottom: var(--space-sm); }
.mb-2 { margin-bottom: var(--space-md); }
.mb-3 { margin-bottom: var(--space-lg); }

/* ═══════ KEYBOARD SHORTCUTS HINT ═══════ */
.shortcut-hint {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-md) var(--space-xl);
  display: flex;
  gap: var(--space-xl);
  z-index: 1000;
  box-shadow: var(--shadow-lg);
  transition: all var(--transition-slow);
  opacity: 0;
  visibility: hidden;
}

.shortcut-hint.visible {
  opacity: 1;
  visibility: visible;
}

.shortcut-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 12px;
  color: var(--text2);
}

.shortcut-key {
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text);
}
</style>
</head>
<body data-theme="dark">
<div class="app">
<!-- ═══════ SIDEBAR ═══════ -->
<aside class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">
      <div class="icon">E</div>
      <span class="name">EasyCut</span>
    </div>
  </div>
  <div class="sidebar-ver">v3.0 · 易剪辑</div>
  <nav>
    <div class="nav-section">
      <div class="nav-label">工作模式</div>
      <div class="nav-item active" data-panel="video" onclick="switchPanel('video')">
        <span class="nav-emoji">🎬</span>
        <span>视频剪辑</span>
      </div>
      <div class="nav-item" data-panel="photo" onclick="switchPanel('photo')">
        <span class="nav-emoji">📷</span>
        <span>照片修图</span>
      </div>
      <div class="nav-item" data-panel="script" onclick="switchPanel('script')">
        <span class="nav-emoji">📝</span>
        <span>脚本策划</span>
      </div>
    </div>
    <div class="nav-section">
      <div class="nav-label">视频模板</div>
      <div class="nav-item" data-tpl="party_building" onclick="selectTemplate('party_building')">
        🏛 党建
        <span class="badge">默认</span>
      </div>
      <div class="nav-item" data-tpl="conference" onclick="selectTemplate('conference')">
        🎤 会议
      </div>
      <div class="nav-item" data-tpl="visit" onclick="selectTemplate('visit')">
        🏭 参观
      </div>
      <div class="nav-item" data-tpl="study" onclick="selectTemplate('study')">
        📚 学习
      </div>
      <div class="nav-item" data-tpl="landscape" onclick="selectTemplate('landscape')">
        🏔 风光
        <span class="badge">新</span>
      </div>
      <div class="nav-item" data-tpl="propaganda" onclick="selectTemplate('propaganda')">
        📢 宣传
        <span class="badge">新</span>
      </div>
    </div>
  </nav>
  <div class="sidebar-footer">
    <span class="kb-hint">⌘1 视频 ⌘2 照片</span>
    <button class="theme-btn" onclick="toggleTheme()" title="切换主题">🌓</button>
  </div>
</aside>

<!-- ═══════ MAIN CONTENT ═══════ -->
<main class="main">
<!-- ──────── VIDEO PANEL ──────── -->
<div class="panel active" id="panel-video">
  <div class="page-header">
    <div>
      <h2>🎬 视频智能剪辑</h2>
      <div class="subtitle">拖拽视频 → AI自动剪辑 → 多格式导出</div>
    </div>
    <div class="btn-row" style="margin: 0;">
      <button class="btn btn-secondary btn-sm" onclick="switchPanel('photo')">📷 照片修图</button>
    </div>
  </div>
  
  <!-- 统计卡片 -->
  <div class="stats-grid">
    <div class="visual-card">
      <div class="visual-title">今日处理</div>
      <div class="visual-value" id="todayCount">0</div>
      <div class="visual-change">
        <span>↑</span>
        <span>+12% 较昨日</span>
      </div>
    </div>
    <div class="visual-card">
      <div class="visual-title">平均处理时间</div>
      <div class="visual-value" id="avgTime">0s</div>
      <div class="visual-change">
        <span>↓</span>
        <span>-8% 较昨日</span>
      </div>
    </div>
    <div class="visual-card">
      <div class="visual-title">成功率</div>
      <div class="visual-value" id="successRate">0%</div>
      <div class="visual-change">
        <span>↑</span>
        <span>+2% 较昨日</span>
      </div>
    </div>
    <div class="visual-card">
      <div class="visual-title">LUT预设</div>
      <div class="visual-value" id="lutCount">0</div>
      <div class="visual-change">
        <span>→</span>
        <span>可用预设</span>
      </div>
    </div>
  </div>
  
  <div class="panels">
    <!-- 左侧：上传区域 -->
    <div>
      <div class="card">
        <div class="card-header">
          <span class="dot"></span>
          <h3>上传视频素材</h3>
        </div>
        <div class="dropzone" id="videoDropzone">
          <div class="dz-icon">📤</div>
          <div class="dz-hint">
            <strong>拖拽视频到此处</strong> 或点击选择
          </div>
          <input type="file" id="videoInput" accept="video/*" multiple>
        </div>
        <div class="file-list" id="fileList"></div>
        
        <div class="progress-wrap" id="progressWrap">
          <div class="progress-bar">
            <div class="progress-fill" id="progressFill"></div>
          </div>
          <div class="progress-text">
            <span id="progressStage">准备中...</span>
            <span id="progressPct">0%</span>
          </div>
        </div>
        
        <div class="result-card" id="resultCard">
          <video class="result-video" id="resultVideo" controls></video>
          <div class="download-links" id="downloadLinks"></div>
        </div>
      </div>
    </div>
    
    <!-- 右侧：设置区域 -->
    <div>
      <div class="card">
        <div class="card-header">
          <span class="dot"></span>
          <h3>剪辑设置</h3>
        </div>
        
        <!-- 模板选择 -->
        <div style="margin-bottom: var(--space-lg);">
          <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">视频模板</div>
          <select id="templateSelect" onchange="selectTemplate(this.value)">
            <option value="party_building">🏛 党建</option>
            <option value="conference">🎤 会议</option>
            <option value="visit">🏭 参观</option>
            <option value="study">📚 学习</option>
            <option value="landscape">🏔 风光摄影</option>
            <option value="propaganda">📢 宣传视频</option>
          </select>
        </div>
        
        <!-- 标题输入 -->
        <div style="margin-bottom: var(--space-lg);">
          <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">视频标题</div>
          <input type="text" id="titleInput" placeholder="输入视频标题（可选）">
        </div>
        
        <!-- 风格描述 -->
        <div style="margin-bottom: var(--space-lg);">
          <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">剪辑风格</div>
          <textarea id="styleInput" rows="2" placeholder="描述想要的剪辑风格：大气磅礴、冷色调、快节奏..."></textarea>
        </div>
        
        <!-- 分辨率和帧率 -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); margin-bottom: var(--space-lg);">
          <div>
            <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">分辨率</div>
            <select id="resolutionSelect">
              <option value="1920x1080">1080p</option>
              <option value="3840x2160">4K</option>
              <option value="1280x720">720p</option>
            </select>
          </div>
          <div>
            <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">帧率</div>
            <select id="fpsSelect">
              <option value="30">30 fps</option>
              <option value="25">25 fps</option>
              <option value="60">60 fps</option>
            </select>
          </div>
        </div>
        
        <!-- 导出格式 -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); margin-bottom: var(--space-lg);">
          <div>
            <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">导出格式</div>
            <select id="formatSelect">
              <option value="mp4">MP4</option>
              <option value="mov">MOV</option>
              <option value="mp4,mov">MP4 + MOV</option>
              <option value="mp4,xml">MP4 + 剪映XML</option>
              <option value="mp4,draft">MP4 + 剪映草稿</option>
            </select>
          </div>
          <div>
            <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">宽银幕</div>
            <select id="letterboxSelect">
              <option value="off">标准 16:9</option>
              <option value="2.35:1">电影 2.35:1</option>
              <option value="1.85:1">宽银幕 1.85:1</option>
            </select>
          </div>
        </div>
        
        <!-- 调色风格 -->
        <div style="margin-bottom: var(--space-lg);">
          <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">调色风格</div>
          <div style="display: flex; gap: var(--space-sm); align-items: center;">
            <select id="colorPresetSelect" style="flex: 1;">
              <optgroup label="── 传统调色 ──">
                <option value="warm_red">🔴 暖红（党建）</option>
                <option value="professional">💼 商务专业</option>
                <option value="bright">✨ 明亮清新</option>
                <option value="warm">🌡 暖色调</option>
              </optgroup>
              <optgroup label="── 影视飓风 LUT ──">
                <option value="yingshi_cinematic">🎬 电影感</option>
                <option value="yingshi_fresh">🌿 清新</option>
                <option value="yingshi_vintage">📼 复古</option>
                <option value="yingshi_cyberpunk">🌃 赛博朋克</option>
                <option value="yingshi_natural">🏔 自然</option>
              </optgroup>
              <optgroup label="── 新增影视飓风 LUT ──">
                <option value="ysjf_cinematic_film">🎬 电影感自然</option>
                <option value="ysjf_teal_orange">🎨 青橙电影调</option>
                <option value="ysjf_golden_hour">🌇 金色时刻暖调</option>
                <option value="ysjf_moody_cinematic">🌑 暗调电影感</option>
                <option value="ysjf_vintage_film">📼 复古胶片感</option>
              </optgroup>
              <optgroup label="── 通用 LUT ──">
                <option value="film_emulation">🎞 胶片模拟</option>
                <option value="landscape">🌄 风景优化</option>
                <option value="portrait">👤 人像优化</option>
                <option value="vlog">📹 Vlog风格</option>
                <option value="dark_moody">🌑 暗调氛围</option>
                <option value="warm_sunset">🌅 暖色日落</option>
                <option value="bw_noir">⬛ 黑白电影</option>
              </optgroup>
              <optgroup label="── 风光摄影 ──">
                <option value="nature_cinematic">🌲 电影感自然</option>
                <option value="golden_hour">🌇 金色时刻</option>
                <option value="moody_forest">🌲 暗调森林</option>
                <option value="teal_orange">🎨 青橙电影</option>
              </optgroup>
            </select>
            <div class="tooltip">
              <button class="btn btn-secondary btn-sm" onclick="previewLUT()" title="预览LUT效果">👁</button>
              <span class="tooltip-text">预览LUT效果</span>
            </div>
            <div class="tooltip">
              <button class="btn btn-secondary btn-sm" onclick="uploadLUT()" title="上传自定义LUT">📤</button>
              <span class="tooltip-text">上传自定义LUT</span>
            </div>
            <div class="tooltip">
              <button class="btn btn-secondary btn-sm" onclick="refreshLUTs()" title="刷新LUT列表">🔄</button>
              <span class="tooltip-text">刷新LUT列表</span>
            </div>
          </div>
          <div id="lutUploadStatus" style="display: none; margin-top: var(--space-sm); padding: var(--space-sm); background: var(--bg-input); border-radius: var(--radius-sm); font-size: 12px;"></div>
          <div id="lutStats" style="display: none; margin-top: var(--space-xs); font-size: 11px; color: var(--text3);"></div>
        </div>
        
        <!-- 开始剪辑按钮 -->
        <button class="btn btn-primary" onclick="startEdit()" style="width: 100%;">
          🚀 开始自动剪辑
        </button>
        
        <div id="videoLoading" style="display: none; text-align: center; margin-top: var(--space-md);">
          <span class="spinner"></span>
          <span style="margin-left: var(--space-sm); font-size: 13px; color: var(--text2);">处理中...</span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ──────── PHOTO PANEL ──────── -->
<div class="panel" id="panel-photo">
  <div class="page-header">
    <div>
      <h2>📷 照片智能修图</h2>
      <div class="subtitle">AI诊断 · 大师风格 · 手动精调</div>
    </div>
    <div class="btn-row" style="margin: 0;">
      <button class="btn btn-secondary btn-sm" onclick="switchPanel('video')">🎬 视频剪辑</button>
    </div>
  </div>
  
  <div class="panels">
    <!-- 左侧：上传和预览 -->
    <div>
      <div class="card">
        <div class="card-header">
          <span class="dot"></span>
          <h3>上传照片</h3>
        </div>
        <div class="dropzone" id="photoDropzone">
          <div class="dz-icon">🖼</div>
          <div class="dz-hint">
            <strong>拖拽照片到此处</strong> 或点击选择
          </div>
          <input type="file" id="photoInput" accept="image/*">
        </div>
        <div id="detectResult"></div>
      </div>
      
      <div class="card" id="previewCard" style="display: none;">
        <div class="card-header">
          <span class="dot"></span>
          <h3>预览</h3>
          <span id="compareHint" style="font-size: 11px; color: var(--primary); margin-left: auto; display: none;">← 拖动对比 →</span>
        </div>
        <div class="compare-container" id="compareContainer" style="display: none; position: relative; width: 100%; overflow: hidden; border-radius: var(--radius-md); border: 2px solid var(--primary);">
          <div id="compareAfterWrap" style="width: 100%;">
            <img id="compareAfter" style="width: 100%; display: block;" src="" alt="修图后">
          </div>
          <div id="compareBefore" style="position: absolute; top: 0; left: 0; width: 50%; height: 100%; overflow: hidden; border-right: 3px solid var(--primary);">
            <img id="compareOriginal" style="display: block; height: 100%; object-fit: cover; position: absolute; top: 0; left: 0;" src="" alt="原图">
          </div>
          <div id="compareHandle" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 40px; height: 40px; background: var(--primary); border-radius: 50%; cursor: ew-resize; z-index: 5; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 12px rgba(0,0,0,0.4);">
            <span style="color: #fff; font-size: 16px;">↔</span>
          </div>
          <div id="compareLabel" style="position: absolute; top: 10px; left: 50%; transform: translateX(-50%); background: var(--primary); color: #fff; padding: 4px 12px; border-radius: var(--radius-sm); font-size: 12px; pointer-events: none; z-index: 3; font-weight: 600;">原图 ← 50% → 修图</div>
        </div>
        <div id="previewSimple">
          <img id="previewImg" src="" alt="预览" style="width: 100%; border-radius: var(--radius-md);">
        </div>
        <div class="btn-row">
          <button class="btn btn-secondary btn-sm" onclick="toggleCompare()">↔ 对比</button>
          <button class="btn btn-secondary btn-sm" onclick="resetPhotoView()">🔄 原图</button>
          <button class="btn btn-secondary btn-sm" onclick="showEnhanced()">✨ 效果</button>
          <a id="dlEnhanced" class="btn btn-primary btn-sm" style="display: none;" download>⬇ 下载</a>
        </div>
      </div>
    </div>
    
    <!-- 右侧：修图工具 -->
    <div>
      <div class="card">
        <div class="card-header">
          <span class="dot"></span>
          <h3>风格描述</h3>
        </div>
        <input type="text" id="photoStyleRequest" placeholder="描述想要的风格：日系小清新、森山大道、电影感青橙色调...">
        <div style="font-size: 11px; color: var(--text3); margin-top: var(--space-xs);">支持自然语言 → 自动匹配预设</div>
      </div>
      
      <div class="card">
        <div class="card-header">
          <span class="dot"></span>
          <h3>🎨 风格画廊</h3>
        </div>
        <div id="styleGallery"></div>
      </div>
      
      <div class="card">
        <div class="card-header">
          <span class="dot"></span>
          <h3>🤖 一键智能</h3>
        </div>
        <div class="btn-row" style="flex-wrap: wrap; gap: var(--space-sm);">
          <button class="btn btn-secondary btn-sm" onclick="autoEnhancePhoto('crop')">✂ 自动裁剪</button>
          <button class="btn btn-secondary btn-sm" onclick="autoEnhancePhoto('level')">📐 自动水平</button>
          <button class="btn btn-secondary btn-sm" onclick="autoEnhancePhoto('lens')">🔍 抗畸变</button>
          <button class="btn btn-primary btn-sm" onclick="autoEnhancePhoto('all')">✨ AI一键优化</button>
        </div>
      </div>
      
      <div class="card">
        <div class="card-header">
          <span class="dot"></span>
          <h3>👤 人像美颜</h3>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md);">
          <div>
            <div style="font-size: 11px; color: var(--text3);">瘦脸</div>
            <input type="range" id="faceSlim" min="0" max="10" value="0" step="1" oninput="$('faceSlimVal').textContent=(this.value*10)+'%'">
            <span id="faceSlimVal" style="font-size: 10px; color: var(--primary);">0%</span>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--text3);">收下颌</div>
            <input type="range" id="faceJaw" min="0" max="10" value="0" step="1" oninput="$('faceJawVal').textContent=(this.value*10)+'%'">
            <span id="faceJawVal" style="font-size: 10px; color: var(--primary);">0%</span>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--text3);">磨皮</div>
            <input type="range" id="faceSmooth" min="0" max="15" value="0" step="1" oninput="$('faceSmoothVal').textContent=this.value">
            <span id="faceSmoothVal" style="font-size: 10px; color: var(--primary);">0</span>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--text3);">大眼</div>
            <input type="range" id="faceEye" min="0" max="5" value="0" step="1" oninput="$('faceEyeVal').textContent=(100+this.value*5)+'%'">
            <span id="faceEyeVal" style="font-size: 10px; color: var(--primary);">100%</span>
          </div>
        </div>
        <button class="btn btn-primary" onclick="applyFaceEnhance()" style="width: 100%; margin-top: var(--space-md);">👤 应用美颜</button>
      </div>
      
      <div class="card">
        <div class="card-header">
          <span class="dot"></span>
          <h3>✂ 抠图去背景</h3>
        </div>
        <div class="btn-row">
          <button class="btn btn-secondary btn-sm" onclick="removeBg('auto')">🎯 AI智能抠图</button>
          <button class="btn btn-secondary btn-sm" onclick="removeBg('logo')">🏷 Logo抠图</button>
          <button class="btn btn-secondary btn-sm" onclick="removeBg('white')">⬜ 去白底</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ──────── SCRIPT PANEL ──────── -->
<div class="panel" id="panel-script">
  <div class="page-header">
    <div>
      <h2>📝 脚本策划</h2>
      <div class="subtitle">AI生成脚本 → 拍摄 → 按脚本剪辑 → 导出剪映精修</div>
    </div>
    <button class="btn btn-primary" onclick="showScriptGenerator()">✨ 生成新脚本</button>
  </div>
  
  <!-- 脚本卡片列表 -->
  <div id="scriptList" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--space-lg);">
    <!-- 空状态提示 -->
    <div id="scriptEmptyState" style="grid-column: 1 / -1; text-align: center; padding: 60px 20px;">
      <div style="font-size: 48px; margin-bottom: var(--space-lg);">📝</div>
      <h3 style="color: var(--text); margin-bottom: var(--space-sm);">还没有脚本</h3>
      <p style="color: var(--text3); margin-bottom: var(--space-xl);">点击"生成新脚本"开始创建您的第一个视频脚本</p>
      <button class="btn btn-primary" onclick="showScriptGenerator()">✨ 生成新脚本</button>
    </div>
  </div>
</div>

<!-- ═══════ SCRIPT GENERATOR MODAL ═══════ -->
<div id="scriptGeneratorModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 1002; align-items: center; justify-content: center;">
  <div style="background: var(--bg-card); padding: var(--space-2xl); border-radius: var(--radius-lg); max-width: 600px; width: 90vw;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-xl);">
      <h3 style="color: var(--text);">✨ AI 脚本生成</h3>
      <button class="btn btn-secondary btn-sm" onclick="closeScriptGenerator()">✕</button>
    </div>
    
    <div style="margin-bottom: var(--space-lg);">
      <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">视频主题 *</div>
      <input type="text" id="scriptTopic" placeholder="输入视频主题：廉政教育、树新风、正确政绩观...">
    </div>
    <div style="margin-bottom: var(--space-lg);">
      <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">视频类别</div>
      <select id="scriptCategory">
        <option value="宣传">📢 宣传教育片</option>
        <option value="会议">🎤 会议纪实</option>
        <option value="学习">📚 学习培训</option>
        <option value="党建">🏛️ 党建专题</option>
        <option value="风光">🌄 风光展示</option>
      </select>
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-lg); margin-bottom: var(--space-lg);">
      <div>
        <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">目标时长</div>
        <select id="scriptDuration">
          <option value="60">1分钟</option>
          <option value="120">2分钟</option>
          <option value="180" selected>3分钟</option>
          <option value="300">5分钟</option>
          <option value="600">10分钟</option>
        </select>
      </div>
      <div>
        <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">风格偏好</div>
        <select id="scriptStyle">
          <option value="正式">正式严谨</option>
          <option value="温情">温情叙事</option>
          <option value="活力">活力动感</option>
          <option value="纪实">纪实风格</option>
        </select>
      </div>
    </div>
    <div style="margin-bottom: var(--space-xl);">
      <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">补充要求（可选）</div>
      <textarea id="scriptRequirements" rows="3" placeholder="如：需要加入采访环节、重点突出XX内容、包含数据展示..."></textarea>
    </div>
    
    <div style="display: flex; gap: var(--space-md);">
      <button class="btn btn-primary" onclick="generateScript()" style="flex: 1;">✨ 开始生成</button>
      <button class="btn btn-secondary" onclick="closeScriptGenerator()">取消</button>
    </div>
    
    <div id="scriptGenLoading" style="display: none; text-align: center; margin-top: var(--space-lg);">
      <div class="spinner"></div>
      <div style="font-size: 13px; color: var(--text2); margin-top: var(--space-sm);">AI正在生成脚本，请稍候...</div>
    </div>
  </div>
</div>
</main>
</div>

<!-- ═══════ TOAST ═══════ -->
<div class="toast" id="toast"></div>

<!-- ═══════ LUT PREVIEW MODAL ═══════ -->
<div id="lutPreviewModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center;">
  <div style="background: var(--bg-card); padding: var(--space-2xl); border-radius: var(--radius-lg); max-width: 90vw; max-height: 90vh; overflow: auto;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-lg);">
      <h3 style="color: var(--text);">LUT预览</h3>
      <button class="btn btn-secondary btn-sm" onclick="closeLutPreview()">✕ 关闭</button>
    </div>
    <div id="lutPreviewContent" style="text-align: center;">
      <div class="spinner"></div>
      <p style="margin-top: var(--space-md); color: var(--text2);">正在生成预览...</p>
    </div>
  </div>
</div>

<!-- ═══════ SCRIPT DETAIL MODAL ═══════ -->
<div id="scriptDetailModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 1001; align-items: center; justify-content: center;">
  <div style="background: var(--bg-card); padding: var(--space-2xl); border-radius: var(--radius-lg); max-width: 800px; max-height: 90vh; overflow: auto; width: 90vw;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-xl); border-bottom: 1px solid var(--border); padding-bottom: var(--space-lg);">
      <h3 id="scriptDetailTitle" style="color: var(--text); font-size: 18px;">脚本详情</h3>
      <button class="btn btn-secondary btn-sm" onclick="closeScriptDetail()">✕ 关闭</button>
    </div>
    <div id="scriptDetailContent" style="line-height: 1.8;">
      <!-- 动态内容 -->
    </div>
    <div style="display: flex; gap: var(--space-md); margin-top: var(--space-xl); border-top: 1px solid var(--border); padding-top: var(--space-lg);">
      <button class="btn btn-primary" onclick="exportScript()">📥 导出脚本</button>
      <button class="btn btn-secondary" onclick="closeScriptDetail()">关闭</button>
    </div>
  </div>
</div>

<!-- ═══════ KEYBOARD SHORTCUTS HINT ═══════ -->
<div class="shortcut-hint" id="shortcutHint">
  <div class="shortcut-item">
    <span class="shortcut-key">⌘1</span>
    <span>视频剪辑</span>
  </div>
  <div class="shortcut-item">
    <span class="shortcut-key">⌘2</span>
    <span>照片修图</span>
  </div>
  <div class="shortcut-item">
    <span class="shortcut-key">⌘3</span>
    <span>脚本策划</span>
  </div>
  <div class="shortcut-item">
    <span class="shortcut-key">⌘D</span>
    <span>切换主题</span>
  </div>
</div>

<script>
// ═══════ UTILITY FUNCTIONS ═══════
function $(id) { return document.getElementById(id); }

function showToast(message, type = 'success') {
  const toast = $('toast');
  toast.textContent = message;
  toast.className = `toast toast-${type} show`;
  setTimeout(() => toast.className = 'toast', 3000);
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ═══════ PANEL SWITCHING ═══════
function switchPanel(panel) {
  // Update nav items
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.panel === panel);
  });
  
  // Update panels
  document.querySelectorAll('.panel').forEach(p => {
    p.classList.toggle('active', p.id === `panel-${panel}`);
  });
  
  // Show keyboard shortcuts hint
  showShortcutHint();
}

// ═══════ TEMPLATE SELECTION ═══════
function selectTemplate(template) {
  document.querySelectorAll('.nav-item[data-tpl]').forEach(item => {
    item.classList.toggle('active', item.dataset.tpl === template);
  });
  $('templateSelect').value = template;
  
  // 自动切换到视频剪辑面板
  switchPanel('video');
  
  // 显示模板选择提示
  const tplNames = {
    'party_building': '党建宣传',
    'conference': '会议记录',
    'visit': '参观访问',
    'study': '学习培训',
    'landscape': '风光摄影',
    'propaganda': '宣传视频'
  };
  showToast(`已选择「${tplNames[template] || template}」模板`, 'success');
}

// ═══════ THEME TOGGLE ═══════
function toggleTheme() {
  const body = document.body;
  const current = body.getAttribute('data-theme');
  body.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark');
  showToast(`已切换到${current === 'dark' ? '浅色' : '深色'}主题`, 'success');
}

// ═══════ FILE UPLOAD HANDLING ═══════
let uploadedFiles = [];

function handleFileUpload(files) {
  const fileList = $('fileList');
  fileList.innerHTML = '';
  
  uploadedFiles = Array.from(files);
  
  uploadedFiles.forEach((file, index) => {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.innerHTML = `
      <span class="file-icon">🎬</span>
      <span class="file-name">${file.name}</span>
      <span class="file-size">${formatFileSize(file.size)}</span>
      <span class="file-remove" onclick="removeFile(${index})">✕</span>
    `;
    fileList.appendChild(fileItem);
  });
  
  if (uploadedFiles.length > 0) {
    showToast(`已选择 ${uploadedFiles.length} 个文件`, 'success');
  }
}

function removeFile(index) {
  uploadedFiles.splice(index, 1);
  handleFileUpload(uploadedFiles);
}

// ═══════ VIDEO EDITING ═══════
function startEdit() {
  if (uploadedFiles.length === 0) {
    showToast('请先上传视频文件', 'error');
    return;
  }
  
  const progressWrap = $('progressWrap');
  const progressFill = $('progressFill');
  const progressStage = $('progressStage');
  const progressPct = $('progressPct');
  const videoLoading = $('videoLoading');
  const resultCard = $('resultCard');
  
  progressWrap.classList.add('active');
  videoLoading.style.display = 'block';
  resultCard.classList.remove('active');
  
  // 模拟处理进度
  let progress = 0;
  const stages = ['分析视频...', '场景检测...', '内容分类...', '评分选择...', '生成剪辑...', '应用调色...', '渲染导出...'];
  let stageIndex = 0;
  
  const interval = setInterval(() => {
    progress += Math.random() * 15;
    if (progress >= 100) {
      progress = 100;
      clearInterval(interval);
      
      setTimeout(() => {
        progressWrap.classList.remove('active');
        videoLoading.style.display = 'none';
        resultCard.classList.add('active');
        
        // 模拟结果视频
        $('resultVideo').src = 'test_video.mp4';
        $('downloadLinks').innerHTML = `
          <a class="download-link" href="#" download>⬇ 下载 MP4</a>
          <a class="download-link" href="#" download>⬇ 下载 MOV</a>
          <a class="download-link" href="#" download>⬇ 剪映XML</a>
        `;
        
        showToast('视频处理完成！', 'success');
        updateStats();
      }, 500);
    }
    
    progressFill.style.width = progress + '%';
    progressPct.textContent = Math.round(progress) + '%';
    
    if (progress > (stageIndex + 1) * (100 / stages.length)) {
      stageIndex = Math.min(stageIndex + 1, stages.length - 1);
      progressStage.textContent = stages[stageIndex];
    }
  }, 200);
}

// ═══════ LUT FUNCTIONS ═══════
function previewLUT() {
  const lutName = $('colorPresetSelect').value;
  if (!lutName) {
    showToast('请先选择一个LUT', 'error');
    return;
  }
  
  const modal = $('lutPreviewModal');
  const content = $('lutPreviewContent');
  
  modal.style.display = 'flex';
  content.innerHTML = '<div class="spinner"></div><p style="margin-top: var(--space-md); color: var(--text2);">正在生成预览...</p>';
  
  // 模拟LUT预览生成
  setTimeout(() => {
    content.innerHTML = `
      <div style="background: linear-gradient(135deg, #1a1a25, #2a2a38); padding: var(--space-2xl); border-radius: var(--radius-md); margin-bottom: var(--space-lg);">
        <h4 style="color: var(--text); margin-bottom: var(--space-md);">LUT: ${lutName}</h4>
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-md);">
          <div style="background: #ff6b6b; height: 60px; border-radius: var(--radius-sm);"></div>
          <div style="background: #4ecdc4; height: 60px; border-radius: var(--radius-sm);"></div>
          <div style="background: #45b7d1; height: 60px; border-radius: var(--radius-sm);"></div>
          <div style="background: #96ceb4; height: 60px; border-radius: var(--radius-sm);"></div>
          <div style="background: #ffeaa7; height: 60px; border-radius: var(--radius-sm);"></div>
        </div>
        <p style="color: var(--text2); margin-top: var(--space-md); font-size: 12px;">LUT预览示例 - 实际效果将应用到视频中</p>
      </div>
    `;
  }, 1000);
}

function closeLutPreview() {
  $('lutPreviewModal').style.display = 'none';
}

function uploadLUT() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.cube';
  input.onchange = function() {
    const file = this.files[0];
    if (file) {
      showToast(`正在上传LUT: ${file.name}`, 'success');
      // 模拟上传
      setTimeout(() => {
        showToast('LUT上传成功！', 'success');
        refreshLUTs();
      }, 1500);
    }
  };
  input.click();
}

function refreshLUTs() {
  showToast('正在刷新LUT列表...', 'success');
  // 模拟刷新
  setTimeout(() => {
    $('lutStats').style.display = 'block';
    $('lutStats').textContent = '系统LUT: 17个, 用户LUT: 0个';
    showToast('LUT列表已刷新', 'success');
  }, 1000);
}

// ═══════ PHOTO FUNCTIONS ═══════
function autoEnhancePhoto(type) {
  showToast(`${type}功能正在处理...`, 'success');
  // 模拟处理
  setTimeout(() => {
    showToast(`${type}处理完成！`, 'success');
  }, 1500);
}

function applyFaceEnhance() {
  showToast('美颜功能正在处理...', 'success');
  setTimeout(() => {
    showToast('美颜处理完成！', 'success');
  }, 1500);
}

function removeBg(type) {
  showToast(`${type}抠图正在处理...`, 'success');
  setTimeout(() => {
    showToast('抠图处理完成！', 'success');
  }, 2000);
}

function toggleCompare() {
  showToast('对比功能开发中', 'success');
}

function resetPhotoView() {
  showToast('已重置为原图', 'success');
}

function showEnhanced() {
  showToast('显示增强效果', 'success');
}

// ═══════ SCRIPT FUNCTIONS ═══════
let scripts = []; // 存储所有生成的脚本

function showScriptGenerator() {
  $('scriptGeneratorModal').style.display = 'flex';
}

function closeScriptGenerator() {
  $('scriptGeneratorModal').style.display = 'none';
  $('scriptGenLoading').style.display = 'none';
}

function generateScript() {
  const topic = $('scriptTopic').value;
  if (!topic) {
    showToast('请输入视频主题', 'error');
    return;
  }
  
  const loading = $('scriptGenLoading');
  loading.style.display = 'block';
  
  // 模拟脚本生成
  setTimeout(() => {
    loading.style.display = 'none';
    closeScriptGenerator();
    
    const category = $('scriptCategory').value;
    const duration = $('scriptDuration').value;
    const style = $('scriptStyle').value;
    const requirements = $('scriptRequirements').value;
    
    // 生成详细的脚本内容
    const script = generateDetailedScript(topic, category, duration, style, requirements);
    scripts.unshift(script); // 添加到列表开头
    
    // 更新脚本列表
    renderScriptList();
    showToast('脚本生成完成！', 'success');
  }, 2500);
}

function generateDetailedScript(topic, category, duration, style, requirements) {
  const id = 'script_' + Date.now();
  const now = new Date();
  const dateStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
  const durationMin = Math.floor(duration / 60);
  
  // 根据类别生成不同的场景描述
  const sceneTemplates = {
    '宣传': {
      scenes: ['开篇展示', '领导讲话', '工作成果', '群众采访', '总结展望'],
      music: '激昂向上的背景音乐',
      transitions: ['淡入淡出', '滑动切换', '缩放转场']
    },
    '会议': {
      scenes: ['会场全景', '主持人开场', '主题报告', '分组讨论', '总结发言'],
      music: '庄重典雅的背景音乐',
      transitions: ['直接切换', '交叉溶解', '推拉转场']
    },
    '学习': {
      scenes: ['学习场景', '讲师讲解', '案例展示', '互动环节', '学习成果'],
      music: '轻松舒缓的背景音乐',
      transitions: ['柔和过渡', '翻页效果', '渐显渐隐']
    },
    '党建': {
      scenes: ['党旗展示', '活动场景', '党员风采', '群众参与', '成果展示'],
      music: '红色经典背景音乐',
      transitions: ['庄重切换', '主题过渡', '场景融合']
    },
    '风光': {
      scenes: ['全景航拍', '细节特写', '时间流逝', '四季变换', '日出日落'],
      music: '自然舒缓的背景音乐',
      transitions: ['流畅过渡', '自然切换', '渐变转场']
    }
  };
  
  const template = sceneTemplates[category] || sceneTemplates['宣传'];
  
  return {
    id,
    topic,
    category,
    duration: parseInt(duration),
    durationMin,
    style,
    requirements,
    date: dateStr,
    createdAt: now.toISOString(),
    overview: `本片为${category}类视频，主题为「${topic}」，时长约${durationMin}分钟，采用${style}风格。`,
    summary: `通过${template.scenes.length}个主要场景，全面展示${topic}的核心内容和重要意义。`,
    scenes: template.scenes.map((scene, index) => ({
      name: scene,
      startTime: Math.floor((duration / template.scenes.length) * index),
      endTime: Math.floor((duration / template.scenes.length) * (index + 1)),
      description: `拍摄${scene}相关内容，展示${topic}的${['引入', '核心', '成果', '反馈', '升华'][index] || '特色'}部分。`,
      shots: [
        { type: '全景', desc: `展示${scene}的整体环境` },
        { type: '中景', desc: `捕捉${scene}的主要内容` },
        { type: '特写', desc: `突出${scene}的细节亮点` }
      ],
      narration: `在${scene}部分，需要配合解说词说明${topic}的相关内容。`,
      tips: `建议使用稳定器拍摄，注意光线和构图。`
    })),
    music: template.music,
    transitions: template.transitions,
    equipment: ['摄像机/手机', '三脚架', '稳定器', '麦克风', '灯光'],
    postProduction: ['调色处理', '字幕添加', '音效混合', '转场优化', '最终渲染']
  };
}

function renderScriptList() {
  const list = $('scriptList');
  const emptyState = $('scriptEmptyState');
  
  if (scripts.length === 0) {
    emptyState.style.display = 'block';
    return;
  }
  
  emptyState.style.display = 'none';
  
  // 清除旧的脚本卡片（保留空状态提示）
  list.querySelectorAll('.script-card').forEach(card => card.remove());
  
  scripts.forEach((script, index) => {
    const card = document.createElement('div');
    card.className = 'script-card';
    card.style.animationDelay = `${index * 0.05}s`;
    card.innerHTML = `
      <div class="script-card-header">
        <div>
          <div class="script-card-title">《${script.topic}》</div>
          <div class="script-card-meta">
            <span>📅 ${script.date}</span>
            <span>⏱ ${script.durationMin}分钟</span>
            <span>🎬 ${script.scenes.length}个场景</span>
          </div>
        </div>
        <span class="script-card-tag">${script.category}</span>
      </div>
      <div class="script-card-preview">${script.overview}</div>
      <div class="script-card-footer">
        <span style="font-size: 12px; color: var(--text3);">风格: ${script.style}</span>
        <div class="script-card-actions">
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); viewScriptDetail('${script.id}')">查看详情</button>
          <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); useScript('${script.id}')">使用脚本</button>
        </div>
      </div>
    `;
    card.onclick = () => viewScriptDetail(script.id);
    list.appendChild(card);
  });
}

function viewScriptDetail(scriptId) {
  const script = scripts.find(s => s.id === scriptId);
  if (!script) return;
  
  $('scriptDetailTitle').textContent = `《${script.topic}》拍摄脚本`;
  
  const content = $('scriptDetailContent');
  content.innerHTML = `
    <!-- 基本信息 -->
    <div class="script-info-grid">
      <div class="script-info-item">
        <div class="script-info-label">类别</div>
        <div class="script-info-value">${script.category}</div>
      </div>
      <div class="script-info-item">
        <div class="script-info-label">时长</div>
        <div class="script-info-value">${script.durationMin}分钟</div>
      </div>
      <div class="script-info-item">
        <div class="script-info-label">风格</div>
        <div class="script-info-value">${script.style}</div>
      </div>
      <div class="script-info-item">
        <div class="script-info-label">场景数</div>
        <div class="script-info-value">${script.scenes.length}个</div>
      </div>
    </div>
    
    <!-- 脚本概述 -->
    <div class="script-section">
      <div class="script-section-title">📋 脚本概述</div>
      <p style="color: var(--text2); font-size: 13px; line-height: 1.8;">${script.overview}</p>
      <p style="color: var(--text2); font-size: 13px; line-height: 1.8; margin-top: var(--space-sm);">${script.summary}</p>
      ${script.requirements ? `<p style="color: var(--text3); font-size: 12px; margin-top: var(--space-sm); font-style: italic;">补充要求: ${script.requirements}</p>` : ''}
    </div>
    
    <!-- 分场景脚本 -->
    <div class="script-section">
      <div class="script-section-title">🎬 分场景脚本</div>
      ${script.scenes.map((scene, index) => `
        <div style="background: var(--bg-input); border-radius: var(--radius-md); padding: var(--space-lg); margin-bottom: var(--space-md);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-md);">
            <h4 style="color: var(--text); font-size: 14px;">场景 ${index + 1}: ${scene.name}</h4>
            <span style="font-size: 12px; color: var(--text3);">${formatTime(scene.startTime)} - ${formatTime(scene.endTime)}</span>
          </div>
          <p style="color: var(--text2); font-size: 13px; margin-bottom: var(--space-md);">${scene.description}</p>
          
          <div style="margin-bottom: var(--space-md);">
            <div style="font-size: 12px; color: var(--primary-light); margin-bottom: var(--space-sm);">📷 镜头设计</div>
            ${scene.shots.map(shot => `
              <div style="display: flex; gap: var(--space-sm); margin-bottom: var(--space-xs); font-size: 12px;">
                <span style="color: var(--text); min-width: 40px;">${shot.type}:</span>
                <span style="color: var(--text2);">${shot.desc}</span>
              </div>
            `).join('')}
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-md); font-size: 12px;">
            <div>
              <span style="color: var(--primary-light);">🎤 解说词:</span>
              <span style="color: var(--text2);"> ${scene.narration}</span>
            </div>
            <div>
              <span style="color: var(--primary-light);">💡 拍摄提示:</span>
              <span style="color: var(--text2);"> ${scene.tips}</span>
            </div>
          </div>
        </div>
      `).join('')}
    </div>
    
    <!-- 音乐与转场 -->
    <div class="script-section">
      <div class="script-section-title">🎵 音乐与转场</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-lg);">
        <div>
          <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">背景音乐</div>
          <p style="color: var(--text2); font-size: 13px;">${script.music}</p>
        </div>
        <div>
          <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">转场效果</div>
          <div style="display: flex; flex-wrap: wrap; gap: var(--space-xs);">
            ${script.transitions.map(t => `<span class="script-card-tag">${t}</span>`).join('')}
          </div>
        </div>
      </div>
    </div>
    
    <!-- 设备与后期 -->
    <div class="script-section">
      <div class="script-section-title">📹 拍摄设备与后期制作</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-lg);">
        <div>
          <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">所需设备</div>
          <div style="display: flex; flex-wrap: wrap; gap: var(--space-xs);">
            ${script.equipment.map(e => `<span style="background: var(--bg-hover); padding: 4px 8px; border-radius: var(--radius-sm); font-size: 12px; color: var(--text2);">${e}</span>`).join('')}
          </div>
        </div>
        <div>
          <div style="font-size: 12px; color: var(--text3); margin-bottom: var(--space-sm);">后期制作</div>
          <div style="display: flex; flex-wrap: wrap; gap: var(--space-xs);">
            ${script.postProduction.map(p => `<span style="background: var(--bg-hover); padding: 4px 8px; border-radius: var(--radius-sm); font-size: 12px; color: var(--text2);">${p}</span>`).join('')}
          </div>
        </div>
      </div>
    </div>
  `;
  
  $('scriptDetailModal').style.display = 'flex';
}

function closeScriptDetail() {
  $('scriptDetailModal').style.display = 'none';
}

function useScript(scriptId) {
  const script = scripts.find(s => s.id === scriptId);
  if (!script) return;
  
  // 切换到视频剪辑面板，并设置模板
  selectTemplate(script.category === '党建' ? 'party_building' : 
                 script.category === '会议' ? 'conference' :
                 script.category === '学习' ? 'study' : 'propaganda');
  showToast(`已应用「${script.topic}」脚本`, 'success');
}

function exportScript() {
  showToast('脚本导出功能开发中...', 'info');
}

function formatTime(seconds) {
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

// ═══════ STATS UPDATE ═══════
function updateStats() {
  // 模拟更新统计数据
  $('todayCount').textContent = Math.floor(Math.random() * 10) + 1;
  $('avgTime').textContent = Math.floor(Math.random() * 30 + 10) + 's';
  $('successRate').textContent = Math.floor(Math.random() * 10 + 90) + '%';
  $('lutCount').textContent = '17';
}

// ═══════ KEYBOARD SHORTCUTS ═══════
function showShortcutHint() {
  const hint = $('shortcutHint');
  hint.classList.add('visible');
  setTimeout(() => hint.classList.remove('visible'), 3000);
}

// ═══════ INITIALIZATION ═══════
document.addEventListener('DOMContentLoaded', function() {
  // Set initial template
  selectTemplate('party_building');
  
  // Load LUT presets
  setTimeout(refreshLUTs, 1000);
  
  // Update stats
  updateStats();
  
  // Setup file upload handlers
  $('videoInput').addEventListener('change', function(e) {
    handleFileUpload(e.target.files);
  });
  
  $('photoInput').addEventListener('change', function(e) {
    if (e.target.files.length > 0) {
      showToast(`已选择照片: ${e.target.files[0].name}`, 'success');
      $('previewCard').style.display = 'block';
      $('previewImg').src = URL.createObjectURL(e.target.files[0]);
    }
  });
  
  // Setup drag and drop
  const videoDropzone = $('videoDropzone');
  videoDropzone.addEventListener('dragover', function(e) {
    e.preventDefault();
    this.classList.add('drag-over');
  });
  
  videoDropzone.addEventListener('dragleave', function(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
  });
  
  videoDropzone.addEventListener('drop', function(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  });
  
  videoDropzone.addEventListener('click', function() {
    $('videoInput').click();
  });
  
  const photoDropzone = $('photoDropzone');
  photoDropzone.addEventListener('dragover', function(e) {
    e.preventDefault();
    this.classList.add('drag-over');
  });
  
  photoDropzone.addEventListener('dragleave', function(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
  });
  
  photoDropzone.addEventListener('drop', function(e) {
    e.preventDefault();
    this.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
      $('photoInput').files = e.dataTransfer.files;
      showToast(`已选择照片: ${e.dataTransfer.files[0].name}`, 'success');
      $('previewCard').style.display = 'block';
      $('previewImg').src = URL.createObjectURL(e.dataTransfer.files[0]);
    }
  });
  
  photoDropzone.addEventListener('click', function() {
    $('photoInput').click();
  });
  
  // Setup keyboard shortcuts
  document.addEventListener('keydown', function(e) {
    if (e.metaKey || e.ctrlKey) {
      switch(e.key) {
        case '1':
          e.preventDefault();
          switchPanel('video');
          break;
        case '2':
          e.preventDefault();
          switchPanel('photo');
          break;
        case '3':
          e.preventDefault();
          switchPanel('script');
          break;
        case 'd':
        case 'D':
          e.preventDefault();
          toggleTheme();
          break;
      }
    }
  });
  
  // Show keyboard shortcuts hint on first load
  setTimeout(showShortcutHint, 2000);
});

// ═══════ PLACEHOLDER FUNCTIONS ═══════
function loadLUTPresets() {
  console.log('Loading LUT presets...');
}
</script>
</body>
</html>"""


# API (unchanged from v2.0)
# ═══════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index(): return HTML_PAGE


@app.post("/api/upload")
async def upload(
    videos: List[UploadFile] = File(...),
    cover: Optional[UploadFile] = File(None),
    logo: Optional[UploadFile] = File(None),
    music: Optional[UploadFile] = File(None),
    template: str = Form("party_building"),
    style_description: str = Form(""),
    agenda_text: str = Form(""),
    title: str = Form(""), subtitle: str = Form(""),
    organization: str = Form(""), date_text: str = Form(""),
    logo_position: str = Form("top_right"),
    logo_remove_bg: str = Form("0"),
    export_capcut: str = Form("0"),
    export_formats: str = Form("mp4"),
    resolution: str = Form("1080p"),
    fps: str = Form("30"),
    letterbox: str = Form("0"),
    color_preset: str = Form("warm_red"),
):
    task_id = str(uuid.uuid4())[:8]
    saved = []

    for f in videos:
        sp = Path("uploads") / f"{task_id}_{f.filename}"
        sp.write_bytes(await f.read())
        saved.append(str(sp.absolute()))

    cover_path = logo_path = music_path = None
    if cover:
        cp = Path("uploads/covers") / f"{task_id}_{cover.filename}"
        cp.write_bytes(await cover.read()); cover_path = str(cp.absolute())
    if logo:
        lp = Path("uploads/logos") / f"{task_id}_{logo.filename}"
        lp.write_bytes(await logo.read()); logo_path = str(lp.absolute())
    if music:
        mp = Path("assets/music") / f"{task_id}_{music.filename}"
        mp.write_bytes(await music.read()); music_path = str(mp.absolute())

    output_path = str((Path("output") / f"{template}_{task_id}.mp4").absolute())

    tasks[task_id] = {
        "status": "uploaded", "percent": 10,
        "message": f"已上传 {len(saved)} 个视频", "input_paths": saved,
        "template": template, "style_description": style_description,
        "agenda_text": agenda_text, "title": title, "subtitle": subtitle,
        "organization": organization, "date_text": date_text,
        "cover_path": cover_path, "logo_path": logo_path,
        "logo_position": logo_position,
        "logo_remove_bg": logo_remove_bg == "1",
        "music_path": music_path,
        "export_capcut": export_capcut == "1",
        "export_formats": [f.strip() for f in export_formats.split(",") if f.strip()],
        "resolution": resolution, "fps": int(fps),
        "letterbox": letterbox == "1",
        "color_preset": color_preset,
        "output_path": output_path, "elapsed": 0, "scenes": "--",
    }
    asyncio.create_task(_run_edit(task_id))
    return JSONResponse({"success": True, "task_id": task_id})


async def _run_edit(task_id: str):
    t = tasks.get(task_id); t0 = time.time()
    if not t: return
    try:
        pipeline = AutoEditPipeline(str(Path(__file__).parent / "config.yaml"))
        request = EditRequest(
            input_paths=t["input_paths"], template=t["template"],
            title=t["title"], subtitle=t["subtitle"],
            organization=t["organization"], date_text=t["date_text"],
            output_path=t["output_path"],
            style_description=t["style_description"],
            agenda_text=t["agenda_text"],
            cover_image=t.get("cover_path"),
            logo_path=t.get("logo_path"),
            logo_position=t.get("logo_position", "top_right"),
            logo_remove_bg=t.get("logo_remove_bg", False),
            music_path=t.get("music_path"),
            color_tone=t.get("color_preset", "warm_red"),
            export_capcut_timeline=t.get("export_capcut", False),
            export_formats=t.get("export_formats", ["mp4"]),
            export_resolution=t.get("resolution", "1080p"),
            export_fps=t.get("fps", 30),
        )
        result = await pipeline.execute(request)
        elapsed = round(time.time() - t0, 1)
        if result.success:
            exported_files = []
            for fmt, path in result.metadata.get("exported_formats", {}).items():
                if path and os.path.exists(path) and path != t["output_path"]:
                    exported_files.append(path)
            t.update({
                "status": "completed", "percent": 100,
                "message": f"✅ 完成! {result.duration:.1f}秒",
                "duration": round(result.duration, 1),
                "scenes_detected": result.scenes_detected,
                "scenes_selected": result.scenes_selected,
                "elapsed": elapsed, "scenes": f"{result.scenes_selected}/{result.scenes_detected}",
                "output_path": result.output_path, "exported_files": exported_files,
            })
        else:
            t.update({"status": "failed", "error": result.error, "elapsed": elapsed})
    except Exception as e:
        logger.error(f"Task error: {e}", exc_info=True)
        t.update({"status": "failed", "error": str(e)})


@app.get("/api/progress/{task_id}")
async def progress(task_id: str):
    t = tasks.get(task_id)
    if not t: return JSONResponse({"status": "not_found"})
    return JSONResponse({k: t.get(k) for k in [
        "status","percent","message","elapsed","scenes","duration",
        "scenes_detected","scenes_selected","output_path","exported_files","error"
    ]})


@app.get("/api/download/{task_id}")
async def download(task_id: str):
    t = tasks.get(task_id)
    if not t or t.get("status") != "completed": return JSONResponse({"error": "not ready"}, 404)
    return FileResponse(t["output_path"], media_type="video/mp4",
                        filename=os.path.basename(t["output_path"]))


@app.get("/api/download-file/{path:path}")
async def download_file(path: str):
    p = Path(path)
    if not p.exists(): return JSONResponse({"error": "not found"}, 404)
    return FileResponse(str(p), filename=p.name)


@app.get("/api/health")
async def health(): return {"status": "ok", "version": "2.8.0", "name": "EasyCut 易剪辑"}


@app.get("/api/color-presets")
async def color_presets():
    """获取所有可用的调色预设（包括传统预设、系统LUT预设和用户LUT预设）"""
    try:
        from core.color_grade import ColorGrader
        from core.lut_loader import get_global_lut_presets
        
        # 初始化调色引擎
        grader = ColorGrader()
        
        # 获取传统预设
        presets = grader.list_presets()
        traditional_presets = {
            name: info.get("description", name) 
            for name, info in presets.items() 
            if info.get("type") == "parameter"
        }
        
        # 获取系统LUT预设
        system_lut_presets = grader.list_lut_presets()
        
        # 获取用户上传的LUT预设
        user_lut_presets = []
        lut_dir = Path("uploads/luts")
        if lut_dir.exists():
            from core.lut_loader import LUTLoader
            loader = LUTLoader()
            for file_path in lut_dir.glob("*.cube"):
                try:
                    lut_data = loader.load_cube_file(str(file_path))
                    if lut_data:
                        user_lut_presets.append({
                            "name": file_path.stem,
                            "title": lut_data.title,
                            "size": lut_data.size,
                            "description": f"用户上传: {lut_data.title}",
                            "is_user_upload": True
                        })
                except Exception as e:
                    logger.warning(f"读取用户LUT文件失败 {file_path}: {e}")
                    continue
        
        # 合并所有LUT预设
        all_lut_presets = []
        for p in system_lut_presets:
            all_lut_presets.append({
                "name": p["name"],
                "title": p["title"],
                "size": p["size"],
                "description": p.get("description", p["title"]),
                "is_user_upload": False
            })
        
        all_lut_presets.extend(user_lut_presets)
        
        return JSONResponse({
            "traditional": traditional_presets,
            "lut": all_lut_presets,
            "total": len(presets) + len(all_lut_presets),
            "system_lut_count": len(system_lut_presets),
            "user_lut_count": len(user_lut_presets)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.post("/api/upload-lut")
async def upload_lut(
    lut_file: UploadFile = File(...),
    name: str = Form(""),
    description: str = Form("")
):
    """上传自定义LUT文件"""
    try:
        # 验证文件类型
        if not lut_file.filename.lower().endswith('.cube'):
            return JSONResponse({"error": "只支持.cube格式的LUT文件"}, 400)
        
        # 读取文件内容
        content = await lut_file.read()
        
        # 验证文件大小（最大10MB）
        if len(content) > 10 * 1024 * 1024:
            return JSONResponse({"error": "LUT文件过大，最大支持10MB"}, 400)
        
        # 生成唯一文件名
        import uuid
        task_id = str(uuid.uuid4())[:8]
        filename = f"{task_id}_{lut_file.filename}"
        
        # 保存文件
        lut_dir = Path("uploads/luts")
        lut_dir.mkdir(exist_ok=True)
        lut_path = lut_dir / filename
        lut_path.write_bytes(content)
        
        # 验证LUT文件格式
        from core.lut_loader import LUTLoader
        loader = LUTLoader()
        lut_data = loader.load_cube_file(str(lut_path))
        
        if not lut_data:
            # 删除无效文件
            lut_path.unlink()
            return JSONResponse({"error": "无效的LUT文件格式"}, 400)
        
        # 使用用户提供的名称或默认名称
        preset_name = name if name else lut_data.title
        if not preset_name:
            preset_name = os.path.splitext(lut_file.filename)[0]
        
        # 清理名称（只保留字母、数字、下划线、连字符）
        import re
        preset_name = re.sub(r'[^\w\-]', '_', preset_name)
        preset_name = re.sub(r'_+', '_', preset_name).strip('_')
        
        # 添加到全局LUT预设管理器
        from core.lut_loader import get_global_lut_presets
        lut_presets = get_global_lut_presets()
        success = lut_presets.add_preset(preset_name, str(lut_path))
        
        if not success:
            return JSONResponse({"error": "添加LUT预设失败"}, 500)
        
        return JSONResponse({
            "success": True,
            "preset_name": preset_name,
            "title": lut_data.title,
            "size": lut_data.size,
            "file_path": str(lut_path.absolute()),
            "message": f"LUT '{preset_name}' 上传成功"
        })
        
    except Exception as e:
        logger.error(f"LUT上传失败: {e}", exc_info=True)
        return JSONResponse({"error": f"上传失败: {str(e)}"}, 500)


@app.get("/api/user-luts")
async def user_luts():
    """获取用户上传的LUT文件列表"""
    try:
        lut_dir = Path("uploads/luts")
        if not lut_dir.exists():
            return JSONResponse({"luts": []})
        
        luts = []
        from core.lut_loader import LUTLoader
        loader = LUTLoader()
        
        for file_path in lut_dir.glob("*.cube"):
            try:
                lut_data = loader.load_cube_file(str(file_path))
                if lut_data:
                    luts.append({
                        "name": file_path.stem,
                        "title": lut_data.title,
                        "size": lut_data.size,
                        "file_path": str(file_path.absolute()),
                        "file_size": file_path.stat().st_size
                    })
            except Exception as e:
                logger.warning(f"读取LUT文件失败 {file_path}: {e}")
                continue
        
        return JSONResponse({"luts": luts})
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/lut-cache-stats")
async def lut_cache_stats():
    """获取LUT缓存统计信息"""
    try:
        from core.lut_loader import LUTLoader
        stats = LUTLoader.get_cache_stats()
        return JSONResponse({
            "success": True,
            "stats": stats,
            "message": f"缓存命中率: {stats['hit_rate']:.1%}, 内存使用: {stats['memory_usage_mb']:.1f}MB"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.post("/api/lut-cache-clear")
async def lut_cache_clear():
    """清除LUT缓存"""
    try:
        from core.lut_loader import LUTLoader
        LUTLoader.clear_global_cache()
        return JSONResponse({
            "success": True,
            "message": "LUT缓存已清除"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/lut-preview/{lut_name}")
async def lut_preview(lut_name: str):
    """生成LUT预览图像"""
    try:
        # 查找LUT文件
        lut_path = None
        
        # 首先检查系统LUT目录
        system_lut_dir = Path("assets/luts")
        if system_lut_dir.exists():
            for file_path in system_lut_dir.glob("*.cube"):
                if file_path.stem == lut_name:
                    lut_path = file_path
                    break
        
        # 如果没找到，检查用户上传目录
        if not lut_path:
            user_lut_dir = Path("uploads/luts")
            if user_lut_dir.exists():
                for file_path in user_lut_dir.glob("*.cube"):
                    if file_path.stem == lut_name:
                        lut_path = file_path
                        break
        
        if not lut_path:
            return JSONResponse({"error": f"LUT '{lut_name}' 未找到"}, 404)
        
        # 生成预览图像
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # 创建测试图像（渐变色块）
        width, height = 400, 200
        img = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(img)
        
        # 绘制渐变色块
        for x in range(width):
            for y in range(height):
                # 创建彩色渐变
                r = int(255 * x / width)
                g = int(255 * y / height)
                b = int(255 * (1 - x / width))
                draw.point((x, y), fill=(r, g, b))
        
        # 应用LUT（简化版本，实际应用需要更复杂的实现）
        # 这里我们创建一个带有LUT信息的预览图
        
        # 添加文字信息
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # 绘制LUT名称
        draw.text((10, 10), f"LUT: {lut_name}", fill="white", font=font)
        draw.text((10, 30), f"文件: {lut_path.name}", fill="white", font=font)
        
        # 绘制示例颜色块
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
        for i, color in enumerate(colors):
            x = 10 + i * 60
            y = 60
            draw.rectangle([x, y, x + 50, y + 50], fill=color)
            draw.text((x, y + 55), f"R:{color[0]} G:{color[1]} B:{color[2]}", fill="white", font=font)
        
        # 转换为字节流
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return StreamingResponse(
            img_byte_arr,
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=lut_preview_{lut_name}.png"}
        )
        
    except Exception as e:
        logger.error(f"LUT预览生成失败: {e}", exc_info=True)
        return JSONResponse({"error": f"预览生成失败: {str(e)}"}, 500)



@app.post("/api/photo/detect")
async def photo_detect(photo: UploadFile = File(...)):
    """识别照片类型"""
    try:
        img = Image.open(io.BytesIO(await photo.read()))
        result = photo_enhancer.detect_type(img)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/photo/presets")
async def photo_presets(type: str = ""):
    """获取照片类型对应的修图预设"""
    all_cats = photo_enhancer.all_categories()
    # 如果没有指定类型或类型为空，返回全部类别
    if not type or type == "general":
        return JSONResponse(all_cats)
    cat_name = CATEGORY_NAMES.get(type, "通用")
    result = {}
    if "通用" in all_cats:
        result["通用"] = all_cats["通用"]
    if cat_name in all_cats:
        result[cat_name] = all_cats[cat_name]
    return JSONResponse(result)


@app.post("/api/photo/enhance")
async def photo_enhance(
    photo: UploadFile = File(...),
    category: str = Form("通用"),
    preset: str = Form("一键增强"),
    style_request: str = Form(""),
    params: str = Form(""),
):
    """执行照片修图"""
    try:
        img = Image.open(io.BytesIO(await photo.read()))

        # 确定使用的参数
        enhance_params = None

        # 1. 自然语言风格请求
        if style_request:
            parsed = photo_enhancer.parse_style_request(style_request)
            if parsed:
                for cat, presets in PRESET_LIBRARY.items():
                    if parsed in presets:
                        enhance_params = presets[parsed]
                        break

        # 2. 手动参数（JSON）
        if params and not enhance_params:
            try:
                raw = json.loads(params)
                enhance_params = EnhanceParams(**{k: v/100 if k in ('brightness','contrast','saturation','sharpness') else v for k,v in raw.items()})
            except Exception:
                pass

        # 3. 预设
        if not enhance_params:
            enhance_params = photo_enhancer.get_params(category, preset)

        # 4. 兜底
        if not enhance_params:
            enhance_params = EnhanceParams()

        # 执行增强
        enhanced = photo_enhancer.enhance(img, enhance_params)

        # 返回 base64
        buf = io.BytesIO()
        enhanced.save(buf, format="JPEG", quality=92)
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        return JSONResponse({"success": True, "image": img_b64})
    except Exception as e:
        logger.error(f"Photo enhance error: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, 500)


# ═══════════════════════════════════════════
# 照片诊断 API
# ═══════════════════════════════════════════

@app.post("/api/photo/diagnose")
async def photo_diagnose(photo: UploadFile = File(...)):
    """照片诊断：识别问题 + 推荐方案"""
    try:
        img = Image.open(io.BytesIO(await photo.read()))
        detect = photo_enhancer.detect_type(img)
        diagnosis = photo_enhancer.diagnose(detect, img)
        return JSONResponse({"success": True, "detection": detect, "diagnosis": diagnosis})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


# ═══════════════════════════════════════════
# 剪映草稿导出 API
# ═══════════════════════════════════════════

@app.post("/api/export/jianying")
async def export_jianying(task_id: str = Form(...), project_name: str = Form("EasyCut_Project")):
    """将已完成剪辑导出为剪映草稿工程"""
    task = tasks.get(task_id)
    if not task:
        return JSONResponse({"success": False, "error": "任务不存在"}, 404)
    if task.get("status") != "done":
        return JSONResponse({"success": False, "error": "任务尚未完成"}, 400)

    try:
        result = task.get("result", {})
        # 从编辑计划构建剪映草稿
        clips = []
        for seg in result.get("segments", []):
            clips.append({
                "path": seg.get("source_path", ""),
                "start": 0,
                "duration": seg.get("duration", 3.0),
                "fade_in": True,
            })

        draft_path = jianying_exporter.export(
            project_name=project_name,
            video_clips=clips,
            music_path=result.get("music_path"),
            title_text=result.get("title", ""),
            width=result.get("width", 1920),
            height=result.get("height", 1080),
            fps=result.get("fps", 30),
        )
        return JSONResponse({"success": True, "draft_path": draft_path, "project_name": project_name})
    except Exception as e:
        logger.error(f"剪映导出失败: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, 500)


# ═══════════════════════════════════════════
# 字幕生成 API
# ═══════════════════════════════════════════

@app.post("/api/subtitle/generate")
async def subtitle_generate(
    task_id: str = Form(...),
    language: str = Form("auto"),
    model_size: str = Form("medium"),
    fontsize: int = Form(20),
    fontcolor: str = Form("white"),
    burn: str = Form("false"),
    format: str = Form("srt"),
):
    """从视频生成字幕"""
    try:
        task = tasks.get(task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"}, 404)

        output_path = task.get("output_path", "")
        if not output_path or not os.path.exists(output_path):
            return JSONResponse({"success": False, "error": "视频文件不存在"}, 404)

        # 提取音频
        audio_path = os.path.join("uploads", f"{task_id}_audio.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", output_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path
        ], capture_output=True, timeout=60)

        if not os.path.exists(audio_path):
            return JSONResponse({"success": False, "error": "音频提取失败"}, 500)

        # 转录
        ws = WhisperSubtitle(
            model_size=model_size,
            device="auto",
            compute_type="auto",
        )
        lang = None if language == "auto" else language
        segments = ws.transcribe(audio_path, language=lang)

        # 生成字幕文件
        if format == "vtt":
            content = ws.to_vtt(segments)
            ext = "vtt"
        elif format == "ass":
            content = ws.to_ass(segments)
            ext = "ass"
        else:
            content = ws.to_srt(segments)
            ext = "srt"

        srt_path = os.path.join("uploads", f"{task_id}.{ext}")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 烧录字幕
        subtitle_url = f"/api/download-file/{task_id}.{ext}"
        burned_url = None
        if burn.lower() in ("true", "1", "yes") and ext == "srt":
            burned_path = os.path.join("output", f"{task_id}_subtitled.mp4")
            from core.subtitle import burn_subtitles
            success = burn_subtitles(
                output_path, srt_path, burned_path,
                fontsize=fontsize, fontcolor=fontcolor,
            )
            if success:
                burned_url = f"/api/download-file/{task_id}_subtitled.mp4"

        # 清理
        try:
            os.remove(audio_path)
        except OSError:
            pass

        return JSONResponse({
            "success": True,
            "segments": segments,
            "segment_count": len(segments),
            "subtitle_url": subtitle_url,
            "burned_url": burned_url,
        })
    except Exception as e:
        logger.error(f"Subtitle generation error: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, 500)


# ═══════════════════════════════════════════
# 变速 & 画中画 API
# ═══════════════════════════════════════════

@app.post("/api/speed")
async def api_speed(
    task_id: str = Form(...),
    speed: float = Form(1.0),
):
    """变速处理"""
    try:
        task = tasks.get(task_id)
        if not task:
            return JSONResponse({"success": False, "error": "任务不存在"}, 404)

        output_path = task.get("output_path", "")
        if not output_path or not os.path.exists(output_path):
            return JSONResponse({"success": False, "error": "视频文件不存在"}, 404)

        new_path = output_path.replace(".mp4", f"_speed_{speed}x.mp4")
        ok = change_speed(output_path, new_path, speed=speed)
        if not ok:
            return JSONResponse({"success": False, "error": "变速处理失败"}, 500)

        return JSONResponse({
            "success": True,
            "output_url": f"/api/download-file/{os.path.basename(new_path)}",
            "speed": speed,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.post("/api/pip")
async def api_pip(
    task_id: str = Form(...),
    pip_task_id: str = Form(""),
    pip_file: Optional[UploadFile] = File(None),
    position: str = Form("bottom_right"),
    pip_size: str = Form("small"),
    mode: str = Form("pip"),
):
    """画中画/分屏处理"""
    try:
        task = tasks.get(task_id)
        if not task:
            return JSONResponse({"success": False, "error": "主任务不存在"}, 404)

        output_path = task.get("output_path", "")
        if not output_path or not os.path.exists(output_path):
            return JSONResponse({"success": False, "error": "主视频不存在"}, 404)

        # 获取 PIP 视频
        pip_path = None
        if pip_task_id:
            pip_task = tasks.get(pip_task_id)
            if pip_task:
                pip_path = pip_task.get("output_path", "")
        elif pip_file:
            pip_path = os.path.join("uploads", f"pip_{uuid.uuid4().hex[:8]}_{pip_file.filename}")
            content = await pip_file.read()
            with open(pip_path, "wb") as f:
                f.write(content)

        if not pip_path or not os.path.exists(pip_path):
            return JSONResponse({"success": False, "error": "PIP视频不存在"}, 400)

        # 处理
        new_path = output_path.replace(".mp4", f"_{mode}.mp4")
        if mode == "pip":
            ok = pip_overlay(output_path, pip_path, new_path, position=position, pip_size=pip_size)
        elif mode in ("left_right", "top_bottom"):
            ok = split_screen(output_path, pip_path, new_path, layout=mode)
        else:
            ok = pip_overlay(output_path, pip_path, new_path, position=position, pip_size=pip_size)

        if not ok:
            return JSONResponse({"success": False, "error": "叠加处理失败"}, 500)

        return JSONResponse({
            "success": True,
            "output_url": f"/api/download-file/{os.path.basename(new_path)}",
            "mode": mode,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


# ═══════════════════════════════════════════
# 抠图 / 人像 / 自动增强 API
# ═══════════════════════════════════════════

@app.post("/api/photo/bg-remove")
async def api_bg_remove(
    photo: UploadFile = File(...),
    mode: str = Form("auto"),
):
    """抠图：去除背景 → 透明PNG"""
    try:
        content = await photo.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if mode == "white":
            rgba = bg_remover.remove_background_white(img)
        elif mode == "logo":
            rgba = bg_remover.remove_logo_background(img)
        else:
            rgba = bg_remover.remove_background(img)

        b64 = bg_remover.image_to_base64(rgba)
        return JSONResponse({"success": True, "image": b64})
    except Exception as e:
        logger.error(f"BG remove error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.post("/api/photo/face-enhance")
async def api_face_enhance(
    photo: UploadFile = File(...),
    slim_face: float = Form(0),
    slim_jawline: float = Form(0),
    smooth_skin: int = Form(0),
    enlarge_eyes: float = Form(0),
):
    """人像美颜：瘦脸/收下颌/磨皮/大眼"""
    try:
        content = await photo.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        opts = {
            "slim_face": slim_face,
            "slim_jawline": slim_jawline,
            "smooth_skin": smooth_skin,
            "enlarge_eyes": enlarge_eyes,
        }
        result = face_enhancer.enhance_portrait(img, opts)

        _, buf = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 92])
        b64 = base64.b64encode(buf.tobytes()).decode()
        return JSONResponse({"success": True, "image": b64})
    except Exception as e:
        logger.error(f"Face enhance error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.post("/api/photo/auto-enhance")
async def api_auto_enhance(
    photo: UploadFile = File(...),
    mode: str = Form("all"),
):
    """自动增强：裁剪/水平/畸变/一键AI"""
    try:
        content = await photo.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        report = {}

        if mode == "crop":
            result = auto_crop(img)
            report["action"] = "智能裁剪"
        elif mode == "level":
            result = auto_level(img)
            report["action"] = "水平校正"
        elif mode == "lens":
            result = auto_lens_correction(img)
            report["action"] = "抗畸变"
        else:
            result, report = ai_auto_enhance(img)

        _, buf = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 92])
        b64 = base64.b64encode(buf.tobytes()).decode()
        return JSONResponse({"success": True, "image": b64, "report": report})
    except Exception as e:
        logger.error(f"Auto enhance error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, 500)


# ═══════════════════════════════════════════
# 关键帧 / 转场 / 音频 API
# ═══════════════════════════════════════════

@app.post("/api/ken-burns")
async def api_ken_burns(
    video: UploadFile = File(...),
    preset: str = Form("ken_burns_slow"),
):
    """Ken Burns 推拉摇移效果"""
    try:
        content = await video.read()
        in_path = f"uploads/_kb_{uuid.uuid4().hex[:8]}.mp4"
        out_path = f"output/_kb_{uuid.uuid4().hex[:8]}.mp4"
        with open(in_path, "wb") as f:
            f.write(content)

        ok = apply_ken_burns(in_path, out_path, preset=preset)
        if ok:
            return JSONResponse({"success": True, "output": f"/download/{Path(out_path).name}"})
        return JSONResponse({"success": False, "error": "Ken Burns failed"}, 500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.get("/api/ken-burns/presets")
async def api_ken_burns_presets():
    """返回 Ken Burns 预设列表"""
    presets = {k: {"name": v["name"]} for k, v in KB_PRESETS.items()}
    return JSONResponse({"success": True, "presets": presets})


@app.post("/api/transition")
async def api_transition(
    video: UploadFile = File(...),
    transition: str = Form("fade"),
    duration: float = Form(0.5),
):
    """应用转场特效"""
    try:
        content = await video.read()
        in_path = f"uploads/_tr_{uuid.uuid4().hex[:8]}.mp4"
        out_path = f"output/_tr_{uuid.uuid4().hex[:8]}.mp4"
        with open(in_path, "wb") as f:
            f.write(content)

        ok = apply_transition_clip(in_path, out_path, transition, duration)
        if ok:
            return JSONResponse({"success": True, "output": f"/download/{Path(out_path).name}"})
        return JSONResponse({"success": False, "error": "Transition failed"}, 500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.get("/api/transitions")
async def api_transitions():
    """返回转场预设列表"""
    items = {k: {"name": v["name"]} for k, v in TRANSITIONS.items()}
    return JSONResponse({"success": True, "transitions": items})


@app.post("/api/audio/mix")
async def api_audio_mix(
    video: UploadFile = File(...),
    music: UploadFile = File(...),
    music_volume: float = Form(0.3),
    fade_in: float = Form(1.0),
    fade_out: float = Form(2.0),
):
    """叠加背景音乐"""
    try:
        vid_content = await video.read()
        mus_content = await music.read()
        vid_path = f"uploads/_mix_v_{uuid.uuid4().hex[:8]}.mp4"
        mus_path = f"uploads/_mix_m_{uuid.uuid4().hex[:8]}.mp3"
        out_path = f"output/_mix_{uuid.uuid4().hex[:8]}.mp4"
        with open(vid_path, "wb") as f: f.write(vid_content)
        with open(mus_path, "wb") as f: f.write(mus_content)

        ok = mix_background_music(vid_path, mus_path, out_path, music_volume, fade_in, fade_out)
        if ok:
            return JSONResponse({"success": True, "output": f"/download/{Path(out_path).name}"})
        return JSONResponse({"success": False, "error": "Audio mix failed"}, 500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.post("/api/audio/volume")
async def api_audio_volume(
    video: UploadFile = File(...),
    volume: float = Form(1.0),
):
    """调整音量"""
    try:
        content = await video.read()
        in_path = f"uploads/_vol_{uuid.uuid4().hex[:8]}.mp4"
        out_path = f"output/_vol_{uuid.uuid4().hex[:8]}.mp4"
        with open(in_path, "wb") as f: f.write(content)

        ok = adjust_audio_volume(in_path, out_path, volume)
        if ok:
            return JSONResponse({"success": True, "output": f"/download/{Path(out_path).name}"})
        return JSONResponse({"success": False, "error": "Volume adjust failed"}, 500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.post("/api/transition-chain")
async def api_transition_chain(
    clips: str = Form(...),
    transition: str = Form("dissolve"),
    duration: float = Form(0.5),
):
    """多片段转场拼接（JSON 数组传入路径列表）"""
    try:
        clip_list = json.loads(clips)
        out_path = f"output/_tc_{uuid.uuid4().hex[:8]}.mp4"
        ok = apply_transition_chain(clip_list, out_path, transition, duration)
        if ok:
            return JSONResponse({"success": True, "output": f"/download/{Path(out_path).name}"})
        return JSONResponse({"success": False, "error": "Transition chain failed"}, 500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


# ═══════════════════════════════════════════
# 脚本策划 API
# ═══════════════════════════════════════════

@app.post("/api/script/generate")
async def api_script_generate(
    topic: str = Form(...),
    category: str = Form("宣传"),
    target_duration: float = Form(180),
    custom_requirements: str = Form(""),
):
    """生成脚本"""
    try:
        script = script_generator.generate(topic, category, target_duration, custom_requirements)
        path = script_generator.save(script)
        return JSONResponse({
            "success": True,
            "script_id": script.script_id,
            "script": asdict(script),
            "preview": format_script_preview(script),
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.get("/api/script/list")
async def api_script_list():
    """列出所有脚本"""
    scripts = script_generator.list_scripts()
    return JSONResponse({"success": True, "scripts": scripts})


@app.get("/api/script/{script_id}")
async def api_script_get(script_id: str):
    """获取脚本详情"""
    script = script_generator.load(script_id)
    if not script:
        return JSONResponse({"success": False, "error": "脚本不存在"}, 404)
    return JSONResponse({
        "success": True,
        "script": asdict(script),
        "preview": format_script_preview(script),
    })


@app.post("/api/script/update")
async def api_script_update(
    script_id: str = Form(...),
    scene_id: str = Form(...),
    narration: str = Form(""),
    description: str = Form(""),
    duration: float = Form(0),
):
    """更新场景"""
    try:
        updates = {}
        if narration:
            updates["narration"] = narration
        if description:
            updates["description"] = description
        if duration > 0:
            updates["duration"] = duration
        script = script_generator.update_scene(script_id, scene_id, updates)
        if not script:
            return JSONResponse({"success": False, "error": "脚本或场景不存在"}, 404)
        return JSONResponse({"success": True, "script": asdict(script)})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.post("/api/script/save")
async def api_script_save(
    script_id: str = Form(...),
    title: str = Form(""),
    style_notes: str = Form(""),
    music_style: str = Form(""),
):
    """保存脚本元信息"""
    try:
        script = script_generator.load(script_id)
        if not script:
            return JSONResponse({"success": False, "error": "脚本不存在"}, 404)
        if title:
            script.title = title
        if style_notes:
            script.style_notes = style_notes
        if music_style:
            script.music_style = music_style
        script_generator.save(script)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.post("/api/script/{script_id}/status")
async def api_script_status(script_id: str, status: str = Form(...)):
    """更新脚本状态"""
    try:
        script = script_generator.load(script_id)
        if not script:
            return JSONResponse({"success": False, "error": "脚本不存在"}, 404)
        script.status = status
        script_generator.save(script)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, 500)


@app.delete("/api/script/{script_id}")
async def api_script_delete(script_id: str):
    """删除脚本"""
    ok = script_generator.delete(script_id)
    return JSONResponse({"success": ok})


@app.get("/api/script/categories")
async def api_script_categories():
    """获取脚本类别列表"""
    from core.script_generator import SCRIPT_TEMPLATES
    cats = []
    for key, tpl in SCRIPT_TEMPLATES.items():
        cats.append({"id": key, "name": tpl["name"], "description": tpl["description"]})
    return JSONResponse({"success": True, "categories": cats})


if __name__ == "__main__":
    import argparse
    import webbrowser
    import threading

    parser = argparse.ArgumentParser(description="EasyCut 易剪辑 v2.9")
    parser.add_argument("--port", type=int, default=9090, help="服务端口 (默认: 9090)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"])
    args = parser.parse_args()

    # 检查端口是否可用
    import socket
    def check_port(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return True
            except OSError:
                return False

    port = args.port
    if not check_port(port):
        for p in range(9090, 9100):
            if check_port(p):
                port = p
                break
        else:
            print(f"错误: 无法找到可用端口 (尝试了 9090-9099)")
            exit(1)

    # 显示启动信息
    print(rf"""
╔══════════════════════════════════════════════════════════════╗
║           🎬 EasyCut 易剪辑  v2.9                           ║
║       AI 智能视频剪辑 · 大厂品质                             ║
║                                                              ║
║  🌐 服务地址: http://127.0.0.1:{port:<24}║
║                                                              ║
║  📋 功能模块:                                                ║
║     • 视频剪辑: 党建 / 会议 / 参观 / 学习 / 风光 / 宣传     ║
║     • 照片修图: 30+ 预设 / 人脸美颜 / 背景去除               ║
║     • 脚本策划: AI 生成拍摄脚本                              ║
║     • 调色系统: 25 个预设 / 自定义 LUT                       ║
║                                                              ║
║  ⌨️  快捷键: ⌘1 视频剪辑 / ⌘2 照片修图 / ⌘3 脚本策划       ║
║  ⏹️  停止服务: Ctrl+C                                        ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 自动打开浏览器
    if not args.no_browser:
        def open_browser():
            import time
            time.sleep(1.5)  # 等待服务器启动
            webbrowser.open(f"http://127.0.0.1:{port}")

        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

    # 启动服务器
    uvicorn.run(app, host=args.host, port=port, log_level=args.log_level)
