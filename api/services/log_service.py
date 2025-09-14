"""
日志业务逻辑服务
处理日志相关的业务逻辑
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from utils.logger import get_logger_manager


class LogService:
    """日志服务类"""

    def __init__(self):
        self.logger = get_logger_manager()

    def get_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        config = self.logger.get_config()
        return {
            "level": config.get("level", "INFO")
        }

    def update_level(self, level: str) -> Dict[str, Any]:
        """更新日志级别"""
        valid_levels = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        if level.upper() not in valid_levels:
            raise ValueError(f"无效的日志级别: {level}")

        self.logger.set_level(level.upper())
        return {
            "message": f"日志级别已更新为 {level.upper()}"
        }

    def get_recent_logs(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        module: Optional[str] = None,
        message_contains: Optional[str] = None,
        since_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取最近的日志记录"""
        if limit < 1 or limit > 1000:
            limit = 100

        logs = self.logger.get_recent_logs(
            limit=limit,
            level=level,
            module=module,
            message_contains=message_contains,
            since_minutes=since_minutes
        )

        # 转换时间戳格式为毫秒级时间戳
        formatted_logs = []
        for log in logs:
            try:
                timestamp = int(datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00')).timestamp() * 1000)
                formatted_logs.append({
                    "timestamp": timestamp,
                    "level": log["level"],
                    "module": log["module"],
                    "message": log["message"],
                    "file": log.get("file", ""),
                    "line": log.get("line", 0)
                })
            except Exception:
                formatted_logs.append({
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "level": log["level"],
                    "module": log["module"],
                    "message": log["message"],
                    "file": log.get("file", ""),
                    "line": log.get("line", 0)
                })

        return {
            "logs": formatted_logs,
            "total": len(formatted_logs),
            "has_more": len(logs) == limit
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        stats = self.logger.get_log_stats()

        # 转换时间戳格式
        if stats["time_range"]["earliest"]:
            stats["time_range"]["earliest"] = int(datetime.fromisoformat(stats["time_range"]["earliest"].replace('Z', '+00:00')).timestamp() * 1000)
        if stats["time_range"]["latest"]:
            stats["time_range"]["latest"] = int(datetime.fromisoformat(stats["time_range"]["latest"].replace('Z', '+00:00')).timestamp() * 1000)

        return stats

    def clear_logs(self) -> Dict[str, Any]:
        """清空日志缓存"""
        cleared_count = self.logger.clear_recent_logs()
        return {
            "message": f"已清空 {cleared_count} 条日志记录",
            "cleared_count": cleared_count
        }
