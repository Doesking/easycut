"""
议程匹配器：根据会议议程自动识别场景是否匹配当前议程项
"""
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgendaItem:
    """议程项"""
    time: str           # "09:00" 或 "9:00"
    title: str          # "开幕式"
    keywords: List[str]  # 关键词
    expected_scenes: List[str]  # 预期场景类型
    duration_min: float = 5  # 预期时长(分钟)


class AgendaMatcher:
    """议程匹配器"""

    SCENE_AGENDA_MAP = {
        "speech": ["讲话", "发言", "报告", "致辞", "演讲", "汇报"],
        "meeting": ["会议", "讨论", "座谈", "交流", "研讨会"],
        "group_photo": ["合影", "留念", "集体照"],
        "flag_ceremony": ["升旗", "开幕", "仪式"],
        "document_sign": ["签约", "签署", "签订"],
        "handshake": ["握手", "会见", "接见", "会晤"],
        "award": ["颁奖", "表彰", "授牌", "授勋"],
        "visit": ["参观", "考察", "视察", "调研"],
        "study": ["学习", "培训", "讲座", "授课"],
    }

    def __init__(self):
        pass

    def parse_agenda(self, text: str) -> List[AgendaItem]:
        """解析议程文本"""
        items = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            # 解析格式: "09:00 开幕式" 或 "09:00-09:30 开幕式" 或 "1. 开幕式"
            time_str = ""
            title = line

            # 尝试匹配时间
            import re
            time_match = re.match(r'(\d{1,2}:\d{2}(?:-\d{1,2}:\d{2})?)\s*(.+)', line)
            if time_match:
                time_str = time_match.group(1)
                title = time_match.group(2)
            else:
                # 尝试匹配编号
                num_match = re.match(r'(\d+)[\.\、\)]\s*(.+)', line)
                if num_match:
                    title = num_match.group(2)

            # 生成关键词和预期场景
            keywords = self._extract_keywords(title)
            expected = self._predict_scenes(title)

            items.append(AgendaItem(
                time=time_str,
                title=title,
                keywords=keywords,
                expected_scenes=expected,
            ))

        logger.info(f"解析议程: {len(items)}项")
        return items

    def _extract_keywords(self, title: str) -> List[str]:
        """从标题提取关键词"""
        keywords = []
        for kw in ["开幕", "讲话", "发言", "报告", "致辞", "讨论", "交流",
                    "签约", "合影", "参观", "考察", "颁奖", "表彰", "闭幕",
                    "总结", "培训", "学习", "座谈", "会见", "调研"]:
            if kw in title:
                keywords.append(kw)
        return keywords

    def _predict_scenes(self, title: str) -> List[str]:
        """预测议程项对应的场景类型"""
        expected = []
        for scene_type, kws in self.SCENE_AGENDA_MAP.items():
            for kw in kws:
                if kw in title:
                    if scene_type not in expected:
                        expected.append(scene_type)
        return expected if expected else ["meeting"]

    def match_scenes_to_agenda(
        self, scenes: List, agenda: List[AgendaItem]
    ) -> List[Dict]:
        """
        将检测到的场景匹配到议程项

        返回: [{agenda_item, scenes: [...], match_score: float}, ...]
        """
        matched = []

        for item in agenda:
            item_scenes = []
            for scene in scenes:
                score = self._match_score(scene, item)
                if score > 0.3:
                    item_scenes.append({
                        "scene": scene,
                        "score": score,
                    })

            # 按匹配分数排序
            item_scenes.sort(key=lambda x: x["score"], reverse=True)

            matched.append({
                "agenda": item,
                "scenes": item_scenes,
                "match_count": len(item_scenes),
                "best_score": item_scenes[0]["score"] if item_scenes else 0,
            })

        return matched

    def _match_score(self, scene, agenda: AgendaItem) -> float:
        """计算场景与议程的匹配分数"""
        score = 0.0

        # 场景类型匹配
        if scene.category in agenda.expected_scenes:
            score += 0.6
        elif scene.category == "general":
            score += 0.3

        # 关键词匹配（如果场景有文字识别的话）
        # 这里用分类置信度作为补充
        if hasattr(scene, 'category_confidence'):
            score += scene.category_confidence * 0.2

        return min(score, 1.0)

    def generate_timeline_plan(
        self, matched_agenda: List[Dict], target_duration: float
    ) -> List[Dict]:
        """
        根据议程匹配结果生成时间线剪辑计划

        每个议程项分配相应的时长，按时间顺序排列
        """
        plan = []
        total_items = len(matched_agenda)

        # 计算每个议程项的时长
        remaining = target_duration
        for i, item in enumerate(matched_agenda):
            agenda = item["agenda"]
            scenes = item["scenes"]

            # 根据场景数量和议程项权重分配时长
            weight = agenda.duration_min / sum(a["agenda"].duration_min
                                                for a in matched_agenda)
            allocated = target_duration * weight

            # 选取最佳匹配场景
            selected_scenes = []
            acc_dur = 0
            for s in scenes:
                if acc_dur >= allocated:
                    break
                dur = s["scene"].duration
                selected_scenes.append(s["scene"])
                acc_dur += dur

            plan.append({
                "agenda_title": agenda.title,
                "agenda_time": agenda.time,
                "scenes": selected_scenes,
                "allocated_duration": allocated,
                "actual_duration": acc_dur,
                "match_quality": item["best_score"],
            })

        return plan
