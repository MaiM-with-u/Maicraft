import os
import json


class ActionsManager:
    def __init__(self):
        self.base_dir = os.path.join(os.path.dirname(__file__), "learnt_actions")
        self.record_path = os.path.join(self.base_dir, "all_learnt_actions.json")

    def get_all_learnt_actions(self):
        if not os.path.exists(self.record_path):
            return []
        try:
            with open(self.record_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception:
            return []

    def get_all_learnt_actions_string(self) -> str:
        records = self.get_all_learnt_actions()
        # 生成以描述为主体的展示文本
        lines = []
        for item in records:
            name = item.get("name", "").strip()
            # 获取/分割后的后一段
            name_last = name.split("/")[-1] if "/" in name else name
            lines.append(f"await {name_last}(bot)")
            detail = item.get("detail", "").strip()
            if detail:
                lines.append(f"#{detail}")
            lines.append("\n")
        return "\n".join(lines)
    
    
    