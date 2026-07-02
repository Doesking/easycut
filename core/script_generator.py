"""
脚本策划模块 — AI 脚本生成 & 脚本引导剪辑

功能：
1. 根据主题生成结构化视频脚本（场景/镜头/旁白/配乐）
2. 保存/加载/管理脚本
3. 脚本引导剪辑：按脚本结构匹配视频片段
4. 导出剪映草稿
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class Shot:
    """单个镜头"""
    shot_id: str = ""
    description: str = ""          # 镜头描述
    camera_movement: str = ""      # 运镜方式：固定/推/拉/摇/移/跟
    duration: float = 5.0          # 建议时长(秒)
    angle: str = ""                # 角度：平视/俯拍/仰拍/特写
    notes: str = ""                # 拍摄备注


@dataclass
class Scene:
    """场景"""
    scene_id: str = ""
    title: str = ""                # 场景标题
    description: str = ""          # 场景描述
    narration: str = ""            # 旁白/解说词
    shots: List[Shot] = field(default_factory=list)
    duration: float = 15.0         # 建议总时长(秒)
    mood: str = ""                 # 情绪：庄重/温暖/激昂/沉稳
    bgm_suggestion: str = ""       # 配乐建议
    transition: str = "fade"       # 转场方式
    content_tags: List[str] = field(default_factory=list)  # 内容标签


@dataclass
class Script:
    """完整脚本"""
    script_id: str = ""
    title: str = ""                # 视频标题
    topic: str = ""                # 主题
    category: str = ""             # 类别：宣传/党建/会议/学习/风光
    target_duration: float = 180   # 目标时长(秒)
    total_duration: float = 0      # 实际总时长
    scenes: List[Scene] = field(default_factory=list)
    overview: str = ""             # 整体概述
    style_notes: str = ""          # 风格说明
    music_style: str = ""          # 整体配乐风格
    created_at: str = ""
    updated_at: str = ""
    status: str = "draft"          # draft/ready/editing/done


# ═══════ 脚本模板库 ═══════

SCRIPT_TEMPLATES = {
    "宣传": {
        "name": "宣传教育片",
        "description": "树新风·廉政·政绩观 — 党委团委宣传",
        "default_scenes": [
            {
                "title": "开篇引入",
                "description": "以宏观视角引入主题，展示组织风貌或标志性场景",
                "narration": "（开篇语，点明主题，如：'风清气正，方能行稳致远...'）",
                "mood": "庄重",
                "duration": 15,
                "shots": [
                    {"description": "组织大楼/标志外景", "camera": "缓慢推进", "angle": "平视", "duration": 5},
                    {"description": "党旗/团旗特写", "camera": "固定", "angle": "仰拍", "duration": 3},
                    {"description": "会议现场全景", "camera": "摇镜", "angle": "俯拍", "duration": 7},
                ],
                "transition": "fade_from_black",
                "bgm": "庄重弦乐，缓慢渐入",
                "tags": ["开场", "外景", "标志"]
            },
            {
                "title": "问题提出",
                "description": "阐述当前形势与需要解决的问题，引出主题重要性",
                "narration": "（阐述背景，如：'在新时代背景下，如何树立正确的政绩观...'）",
                "mood": "沉稳",
                "duration": 20,
                "shots": [
                    {"description": "领导讲话近景", "camera": "固定", "angle": "平视", "duration": 8},
                    {"description": "与会人员认真记录", "camera": "缓慢平移", "angle": "平视", "duration": 6},
                    {"description": "文件/材料特写", "camera": "固定", "angle": "俯拍", "duration": 6},
                ],
                "transition": "dissolve",
                "bgm": "低沉思考性配乐",
                "tags": ["讲话", "会议", "文件"]
            },
            {
                "title": "案例展示",
                "description": "通过正面典型案例展示良好作风与成效",
                "narration": "（案例描述，如：'XX同志扎根基层三十年，用实际行动诠释了...'）",
                "mood": "温暖",
                "duration": 25,
                "shots": [
                    {"description": "工作现场实拍", "camera": "跟拍", "angle": "平视", "duration": 8},
                    {"description": "人物采访近景", "camera": "固定", "angle": "平视", "duration": 10},
                    {"description": "成果展示/数据图表", "camera": "缓慢推进", "angle": "平视", "duration": 7},
                ],
                "transition": "dissolve",
                "bgm": "温暖感人配乐",
                "tags": ["案例", "采访", "成果"]
            },
            {
                "title": "警示教育",
                "description": "反面案例警示，强调纪律红线",
                "narration": "（警示语，如：'然而，也有少数干部...'）",
                "mood": "严肃",
                "duration": 15,
                "shots": [
                    {"description": "纪律文件/条例特写", "camera": "固定", "angle": "俯拍", "duration": 5},
                    {"description": "会议讨论场景", "camera": "缓慢平移", "angle": "平视", "duration": 5},
                    {"description": "警示教育活动现场", "camera": "摇镜", "angle": "平视", "duration": 5},
                ],
                "transition": "fade",
                "bgm": "低沉严肃配乐",
                "tags": ["警示", "纪律", "文件"]
            },
            {
                "title": "讨论交流",
                "description": "集体学习讨论，畅谈心得体会",
                "narration": "（讨论摘要，如：'与会人员纷纷表示...'）",
                "mood": "积极",
                "duration": 20,
                "shots": [
                    {"description": "座谈会全景", "camera": "缓慢摇镜", "angle": "平视", "duration": 7},
                    {"description": "发言者近景", "camera": "固定", "angle": "平视", "duration": 8},
                    {"description": "互动交流场景", "camera": "平移", "angle": "平视", "duration": 5},
                ],
                "transition": "dissolve",
                "bgm": "积极向上配乐",
                "tags": ["讨论", "发言", "交流"]
            },
            {
                "title": "高潮升华",
                "description": "集体宣誓/签署承诺/表彰先进，情感升华",
                "narration": "（升华语，如：'让我们以实际行动，践行初心使命...'）",
                "mood": "激昂",
                "duration": 15,
                "shots": [
                    {"description": "集体宣誓/签署仪式", "camera": "缓慢推进", "angle": "平视", "duration": 5},
                    {"description": "表彰颁奖场景", "camera": "固定", "angle": "平视", "duration": 5},
                    {"description": "全体合影", "camera": "缓慢拉远", "angle": "平视", "duration": 5},
                ],
                "transition": "crossfade",
                "bgm": "激昂弦乐渐强",
                "tags": ["仪式", "表彰", "合影"]
            },
            {
                "title": "结尾收束",
                "description": "总结展望，点题收束",
                "narration": "（结尾语，如：'风清气正，行稳致远。让我们...'）",
                "mood": "庄重",
                "duration": 10,
                "shots": [
                    {"description": "外景全景/航拍", "camera": "缓慢拉远", "angle": "俯拍", "duration": 5},
                    {"description": "组织标志/旗帜", "camera": "固定", "angle": "平视", "duration": 5},
                ],
                "transition": "fade_to_black",
                "bgm": "庄重弦乐渐弱",
                "tags": ["结尾", "外景", "标志"]
            }
        ]
    },
    "会议": {
        "name": "会议纪实",
        "description": "会议记录与纪实",
        "default_scenes": [
            {
                "title": "会场全景",
                "description": "展示会议场地全貌",
                "narration": "",
                "mood": "庄重",
                "duration": 8,
                "shots": [
                    {"description": "会场外景", "camera": "固定", "angle": "平视", "duration": 4},
                    {"description": "会场内全景", "camera": "缓慢摇镜", "angle": "俯拍", "duration": 4},
                ],
                "transition": "fade_from_black",
                "bgm": "轻柔背景音乐",
                "tags": ["会场", "全景"]
            },
            {
                "title": "领导讲话",
                "description": "主要领导发言",
                "narration": "",
                "mood": "庄重",
                "duration": 30,
                "shots": [
                    {"description": "讲话者中景", "camera": "固定", "angle": "平视", "duration": 15},
                    {"description": "讲话者近景", "camera": "固定", "angle": "平视", "duration": 15},
                ],
                "transition": "cut",
                "bgm": "无/极轻",
                "tags": ["讲话", "领导"]
            },
            {
                "title": "会议讨论",
                "description": "与会人员交流讨论",
                "narration": "",
                "mood": "积极",
                "duration": 20,
                "shots": [
                    {"description": "发言人近景", "camera": "固定", "angle": "平视", "duration": 10},
                    {"description": "与会人员全景", "camera": "缓慢平移", "angle": "平视", "duration": 10},
                ],
                "transition": "dissolve",
                "bgm": "轻柔背景音乐",
                "tags": ["讨论", "交流"]
            },
            {
                "title": "会议成果",
                "description": "签署协议/合影留念",
                "narration": "",
                "mood": "温暖",
                "duration": 12,
                "shots": [
                    {"description": "签署/颁奖场景", "camera": "固定", "angle": "平视", "duration": 6},
                    {"description": "全体合影", "camera": "缓慢拉远", "angle": "平视", "duration": 6},
                ],
                "transition": "fade_to_black",
                "bgm": "温暖收尾音乐",
                "tags": ["签署", "合影"]
            }
        ]
    },
    "学习": {
        "name": "学习培训",
        "description": "学习培训纪实",
        "default_scenes": [
            {
                "title": "培训现场",
                "description": "培训场地与参与者",
                "narration": "",
                "mood": "庄重",
                "duration": 10,
                "shots": [
                    {"description": "培训现场全景", "camera": "缓慢摇镜", "angle": "俯拍", "duration": 5},
                    {"description": "参与者近景", "camera": "固定", "angle": "平视", "duration": 5},
                ],
                "transition": "fade_from_black",
                "bgm": "轻柔学习氛围音乐",
                "tags": ["培训", "现场"]
            },
            {
                "title": "学习过程",
                "description": "授课/研讨/实操",
                "narration": "",
                "mood": "专注",
                "duration": 30,
                "shots": [
                    {"description": "讲师授课", "camera": "固定", "angle": "平视", "duration": 10},
                    {"description": "学员认真听讲", "camera": "缓慢平移", "angle": "平视", "duration": 10},
                    {"description": "互动研讨", "camera": "固定", "angle": "平视", "duration": 10},
                ],
                "transition": "dissolve",
                "bgm": "专注学习配乐",
                "tags": ["授课", "听讲", "研讨"]
            },
            {
                "title": "学习成果",
                "description": "结业/总结/合影",
                "narration": "",
                "mood": "温暖",
                "duration": 10,
                "shots": [
                    {"description": "结业仪式", "camera": "固定", "angle": "平视", "duration": 5},
                    {"description": "合影留念", "camera": "缓慢拉远", "angle": "平视", "duration": 5},
                ],
                "transition": "fade_to_black",
                "bgm": "温暖收尾音乐",
                "tags": ["结业", "合影"]
            }
        ]
    }
}


class ScriptGenerator:
    """脚本生成器"""

    def __init__(self, scripts_dir: str = "scripts"):
        self.scripts_dir = Path(scripts_dir)
        self.scripts_dir.mkdir(exist_ok=True)

    def generate(self, topic: str, category: str = "宣传",
                 target_duration: float = 180,
                 custom_requirements: str = "") -> Script:
        """根据主题生成脚本"""
        template = SCRIPT_TEMPLATES.get(category, SCRIPT_TEMPLATES["宣传"])

        script_id = f"script_{int(time.time())}"
        scenes = []

        for i, scene_def in enumerate(template["default_scenes"]):
            shots = []
            for j, shot_def in enumerate(scene_def.get("shots", [])):
                shots.append(Shot(
                    shot_id=f"{i+1}_{j+1}",
                    description=shot_def.get("description", ""),
                    camera_movement=shot_def.get("camera", "固定"),
                    duration=shot_def.get("duration", 5.0),
                    angle=shot_def.get("angle", "平视"),
                    notes=""
                ))

            # 根据主题自定义旁白
            narration = scene_def.get("narration", "")
            narration = narration.replace("XX", topic) if narration else ""

            scenes.append(Scene(
                scene_id=str(i + 1),
                title=scene_def.get("title", f"场景{i+1}"),
                description=scene_def.get("description", ""),
                narration=narration,
                shots=shots,
                duration=scene_def.get("duration", 15.0),
                mood=scene_def.get("mood", ""),
                bgm_suggestion=scene_def.get("bgm", ""),
                transition=scene_def.get("transition", "fade"),
                content_tags=scene_def.get("tags", [])
            ))

        total_duration = sum(s.duration for s in scenes)

        # 根据目标时长调整各场景
        if total_duration > 0:
            ratio = target_duration / total_duration
            for scene in scenes:
                scene.duration = round(scene.duration * ratio, 1)
                for shot in scene.shots:
                    shot.duration = round(shot.duration * ratio, 1)

        script = Script(
            script_id=script_id,
            title=f"{topic} — {template['name']}",
            topic=topic,
            category=category,
            target_duration=target_duration,
            total_duration=sum(s.duration for s in scenes),
            scenes=scenes,
            overview=f"本片以「{topic}」为主题，{template['description']}。",
            style_notes=f"参考{template['name']}风格，严肃庄重，内容与形式结合",
            music_style="庄重/温暖/激昂（随场景变化）",
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            status="draft"
        )

        return script

    def save(self, script: Script) -> str:
        """保存脚本"""
        script.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        path = self.scripts_dir / f"{script.script_id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(script), f, ensure_ascii=False, indent=2)
        return str(path)

    def load(self, script_id: str) -> Optional[Script]:
        """加载脚本"""
        path = self.scripts_dir / f"{script_id}.json"
        if not path.exists():
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self._dict_to_script(data)

    def list_scripts(self) -> List[Dict]:
        """列出所有脚本"""
        scripts = []
        for path in sorted(self.scripts_dir.glob("*.json"), reverse=True):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                scripts.append({
                    "script_id": data.get("script_id", ""),
                    "title": data.get("title", ""),
                    "topic": data.get("topic", ""),
                    "category": data.get("category", ""),
                    "status": data.get("status", "draft"),
                    "scene_count": len(data.get("scenes", [])),
                    "total_duration": data.get("total_duration", 0),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                })
            except Exception:
                continue
        return scripts

    def delete(self, script_id: str) -> bool:
        """删除脚本"""
        path = self.scripts_dir / f"{script_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def update_scene(self, script_id: str, scene_id: str,
                     updates: Dict) -> Optional[Script]:
        """更新场景"""
        script = self.load(script_id)
        if not script:
            return None
        for scene in script.scenes:
            if scene.scene_id == scene_id:
                for key, value in updates.items():
                    if hasattr(scene, key):
                        setattr(scene, key, value)
                break
        script.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save(script)
        return script

    def get_editing_plan(self, script: Script,
                         video_scenes: List[Dict]) -> Dict:
        """根据脚本和视频场景生成剪辑计划

        Args:
            script: 脚本对象
            video_scenes: 视频场景列表，每个场景包含 {path, start, end, duration, ...}

        Returns:
            剪辑计划 {clips: [{scene_id, video_path, start, end, transition, ...}]}
        """
        plan = {"clips": [], "total_duration": 0}
        video_idx = 0

        for scene in script.scenes:
            scene_clips = []
            remaining_duration = scene.duration

            for shot in scene.shots:
                if video_idx >= len(video_scenes):
                    break

                vs = video_scenes[video_idx]
                clip_duration = min(shot.duration, vs.get("duration", shot.duration))

                scene_clips.append({
                    "scene_id": scene.scene_id,
                    "shot_id": shot.shot_id,
                    "video_path": vs.get("path", ""),
                    "start": vs.get("start", 0),
                    "end": vs.get("start", 0) + clip_duration,
                    "duration": clip_duration,
                    "transition": scene.transition,
                    "camera_movement": shot.camera_movement,
                })

                remaining_duration -= clip_duration
                video_idx += 1

                if remaining_duration <= 0:
                    break

            plan["clips"].extend(scene_clips)
            plan["total_duration"] += sum(c["duration"] for c in scene_clips)

        return plan

    @staticmethod
    def _dict_to_script(data: Dict) -> Script:
        """字典转Script对象"""
        scenes = []
        for s in data.get("scenes", []):
            shots = [Shot(**sh) for sh in s.get("shots", [])]
            scenes.append(Scene(
                scene_id=s.get("scene_id", ""),
                title=s.get("title", ""),
                description=s.get("description", ""),
                narration=s.get("narration", ""),
                shots=shots,
                duration=s.get("duration", 15.0),
                mood=s.get("mood", ""),
                bgm_suggestion=s.get("bgm_suggestion", ""),
                transition=s.get("transition", "fade"),
                content_tags=s.get("content_tags", [])
            ))
        return Script(
            script_id=data.get("script_id", ""),
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            category=data.get("category", ""),
            target_duration=data.get("target_duration", 180),
            total_duration=data.get("total_duration", 0),
            scenes=scenes,
            overview=data.get("overview", ""),
            style_notes=data.get("style_notes", ""),
            music_style=data.get("music_style", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            status=data.get("status", "draft")
        )


# ═══════ 预览格式化 ═══════

def format_script_preview(script: Script) -> str:
    """格式化脚本为可读文本"""
    lines = [
        f"# {script.title}",
        f"",
        f"**主题：** {script.topic}",
        f"**类别：** {script.category}",
        f"**目标时长：** {script.target_duration}秒",
        f"**风格：** {script.style_notes}",
        f"**配乐：** {script.music_style}",
        f"",
        f"## 概述",
        f"{script.overview}",
        f"",
        f"## 场景列表",
        f""
    ]

    for scene in script.scenes:
        lines.append(f"### 场景 {scene.scene_id}: {scene.title}")
        lines.append(f"- **描述：** {scene.description}")
        lines.append(f"- **时长：** {scene.duration}秒")
        lines.append(f"- **情绪：** {scene.mood}")
        lines.append(f"- **转场：** {scene.transition}")
        lines.append(f"- **配乐：** {scene.bgm_suggestion}")
        if scene.narration:
            lines.append(f"- **旁白：** {scene.narration}")
        lines.append(f"")
        lines.append(f"**镜头列表：**")
        for shot in scene.shots:
            lines.append(f"  {shot.shot_id}. {shot.description} | {shot.camera_movement} | {shot.angle} | {shot.duration}秒")
        lines.append(f"")

    return "\n".join(lines)
