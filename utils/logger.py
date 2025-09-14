"""
增强的日志管理器
基于loguru实现，支持JSON格式输出和分级日志文件管理
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union
from loguru import logger as _logger


class LoggerManager:
    """增强的日志管理器类"""

    def __init__(self):
        self._initialized = False
        self._config = {}
        self._recent_logs = []  # 存储最近的日志记录
        self._max_recent_logs = 1000  # 最大保留的日志条数

    def configure(
        self,
        level: str = "INFO",
        enable_json: bool = False,
        log_to_file: bool = True,
        log_dir: str = "logs",
        rotation: str = "10 MB",  # 改为按大小轮转，更适合高频日志
        retention: str = "3 days",  # 缩短保留时间
        encoding: str = "utf-8",
        enable_hierarchical_logging: bool = True,
        max_recent_logs: int = 1000,  # 最大保留的最近日志条数
    ) -> None:
        """
        配置日志管理器

        Args:
            level: 日志级别
            enable_json: 是否启用JSON Lines格式文件输出（控制台始终为彩色格式）文件输出（控制台始终为彩色格式）
            log_to_file: 是否输出到文件
            log_dir: 日志目录
            rotation: 日志轮转策略（如"1 day", "100 MB"）
            retention: 日志保留策略（如"7 days", "10 files"）
            encoding: 文件编码
            enable_hierarchical_logging: 是否启用层次化日志记录
            max_recent_logs: 最大保留的最近日志条数
        """
        self._config = {
            "level": level.upper(),
            "enable_json": enable_json,
            "log_to_file": log_to_file,
            "log_dir": log_dir,
            "rotation": rotation,
            "retention": retention,
            "encoding": encoding,
            "enable_hierarchical_logging": enable_hierarchical_logging,
            "max_recent_logs": max_recent_logs,
        }

        # 设置最大保留日志条数
        self._max_recent_logs = max_recent_logs

        # 验证级别
        valid_levels = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}
        if self._config["level"] not in valid_levels:
            self._config["level"] = "INFO"

        self._setup_loguru()
        self._initialized = True

    def _setup_loguru(self) -> None:
        """设置loguru日志处理器"""
        # 清除所有现有处理器
        _logger.remove()

        level = self._config["level"]
        enable_json = self._config["enable_json"]
        log_to_file = self._config["log_to_file"]
        log_dir = self._config["log_dir"]
        rotation = self._config["rotation"]
        retention = self._config["retention"]
        encoding = self._config["encoding"]
        enable_hierarchical = self._config["enable_hierarchical_logging"]

        # 控制台输出 - 始终使用彩色格式
        console_format = "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <1}</level> | <cyan>{extra[module]}</cyan> - <level>{message}</level>"

        _logger.add(
            sys.stderr,
            level=level,
            format=console_format,
            colorize=True,
            enqueue=False,
            backtrace=False,
            diagnose=False,
        )

        # 添加内存缓存handler - 用于存储最近日志
        # 使用filter函数来拦截所有日志记录
        def memory_filter(record):
            # 将记录添加到内存缓存
            log_entry = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "level_no": record["level"].no,
                "module": record["extra"].get("module", ""),
                "message": record["message"],
                "file": f"{record['file'].name}:{record['line']}",
                "function": record["function"],
                "process": record["process"].id,
                "thread": record["thread"].id,
            }

            # 添加到缓存
            self._recent_logs.append(log_entry)

            # 限制缓存大小
            if len(self._recent_logs) > self._max_recent_logs:
                self._recent_logs.pop(0)  # 移除最旧的记录

            return True  # 允许记录继续处理

        _logger.add(
            lambda x: None,  # 空sink，因为我们只需要filter
            level=level,
            filter=memory_filter,
            enqueue=False,
        )

        if log_to_file:
            # 确保日志目录存在
            Path(log_dir).mkdir(exist_ok=True)

            # 文件输出配置
            base_config = {
                "rotation": rotation,
                "retention": retention,
                "encoding": encoding,
                "enqueue": True,
                "backtrace": True,
                "diagnose": True,
            }

            if enable_json:
                # JSON格式文件输出
                json_format = '{{"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}", "level": "{level}", "level_no": {level.no}, "module": "{extra[module]}", "message": "{message}", "file": "{file}", "line": {line}, "function": "{function}", "process": {process.id}, "thread": {thread.id}}}'

                _logger.add(
                    os.path.join(log_dir, "app.jsonl"),
                    format=json_format,
                    level=level,
                    **base_config
                )
            else:
                # 普通文本格式文件输出
                text_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[module]: <15} | {file}:{line} - {message}"

                if enable_hierarchical:
                    # 层次化日志记录：不同级别输出到不同文件，低级文件包含高级别日志
                    log_levels = [
                        ("debug", "DEBUG"),
                        ("info", "INFO"),
                        ("warning", "WARNING"),
                        ("error", "ERROR"),
                        ("critical", "CRITICAL")
                    ]

                    for file_prefix, min_level in log_levels:
                        _logger.add(
                            os.path.join(log_dir, f"{file_prefix}.log"),
                            format=text_format,
                            level=min_level,
                            filter=lambda record, level=min_level: record["level"].no >= _logger.level(level).no,
                            colorize=False,
                            **base_config
                        )
                else:
                    # 单一日志文件
                    _logger.add(
                        os.path.join(log_dir, "app.log"),
                        format=text_format,
                        level=level,
                        colorize=False,
                        **base_config
                    )

    def get_logger(self, name: str):
        """获取绑定了模块名的logger"""
        if not self._initialized:
            self.configure()  # 使用默认配置初始化
        return _logger.bind(module=name)

    def set_level(self, level: str) -> None:
        """动态设置日志级别"""
        self._config["level"] = level.upper()
        self._setup_loguru()

    def enable_json(self, enable: bool = True) -> None:
        """启用或禁用JSON Lines格式文件输出（控制台始终为彩色格式）"""
        self._config["enable_json"] = enable
        self._setup_loguru()

    def get_recent_logs(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        module: Optional[str] = None,
        message_contains: Optional[str] = None,
        since_minutes: Optional[int] = None
    ) -> list:
        """
        获取最近的日志记录，支持过滤

        Args:
            limit: 返回的最大记录数
            level: 过滤特定日志级别
            module: 过滤特定模块
            message_contains: 消息包含的字符串
            since_minutes: 获取最近N分钟内的日志

        Returns:
            list: 符合条件的日志记录列表
        """
        import datetime

        logs = self._recent_logs.copy()

        # 按时间过滤
        if since_minutes is not None:
            cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=since_minutes)
            logs = [
                log for log in logs
                if datetime.datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00')) > cutoff_time
            ]

        # 按级别过滤
        if level is not None:
            logs = [log for log in logs if log["level"].upper() == level.upper()]

        # 按模块过滤
        if module is not None:
            logs = [log for log in logs if module.lower() in log["module"].lower()]

        # 按消息内容过滤
        if message_contains is not None:
            logs = [
                log for log in logs
                if message_contains.lower() in log["message"].lower()
            ]

        # 返回最新的limit条记录
        return logs[-limit:] if limit > 0 else logs

    def get_log_stats(self) -> Dict[str, Any]:
        """
        获取日志统计信息

        Returns:
            dict: 包含各种统计信息的字典
        """
        if not self._recent_logs:
            return {
                "total_logs": 0,
                "level_counts": {},
                "module_counts": {},
                "time_range": None,
            }

        import datetime
        from collections import Counter

        logs = self._recent_logs
        level_counts = Counter(log["level"] for log in logs)
        module_counts = Counter(log["module"] for log in logs)

        # 计算时间范围
        timestamps = [
            datetime.datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
            for log in logs
        ]
        time_range = {
            "earliest": min(timestamps).isoformat(),
            "latest": max(timestamps).isoformat(),
        }

        return {
            "total_logs": len(logs),
            "level_counts": dict(level_counts),
            "module_counts": dict(module_counts.most_common(10)),  # 只显示前10个最活跃的模块
            "time_range": time_range,
            "max_capacity": self._max_recent_logs,
            "utilization_percent": round(len(logs) / self._max_recent_logs * 100, 1),
        }

    def clear_recent_logs(self) -> int:
        """
        清空最近日志缓存

        Returns:
            int: 清空的日志条数
        """
        count = len(self._recent_logs)
        self._recent_logs.clear()
        return count

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._config.copy()


# 全局日志管理器实例
_logger_manager = LoggerManager()


def get_logger(name: str):
    """返回带有模块名绑定的loguru logger。"""
    return _logger_manager.get_logger(name)


def setup_logging(level: Optional[str] = None) -> None:
    """根据配置设置全局日志级别。

    Args:
        level: 日志级别字符串，如 "DEBUG"、"INFO"、"WARNING"、"ERROR"。
    """
    try:
        config = {"level": level or "INFO"}
        _logger_manager.configure(**config)
    except Exception:
        # 出现异常时保持默认配置
        pass


def setup_advanced_logging(
    level: str = "INFO",
    enable_json: bool = False,
    log_to_file: bool = True,
    log_dir: str = "logs",
    rotation: str = "10 MB",  # 改为按大小轮转，更适合高频日志
    retention: str = "3 days",  # 缩短保留时间
    enable_hierarchical_logging: bool = True,
    max_recent_logs: int = 1000,  # 最大保留的最近日志条数
) -> None:
    """
    设置高级日志配置

    Args:
        level: 日志级别
        enable_json: 是否启用JSON Lines格式文件输出（控制台始终为彩色格式）
        log_to_file: 是否输出到文件
        log_dir: 日志目录
        rotation: 日志轮转策略
        retention: 日志保留策略
        enable_hierarchical_logging: 是否启用层次化日志记录
        max_recent_logs: 最大保留的最近日志条数
    """
    try:
        _logger_manager.configure(
            level=level,
            enable_json=enable_json,
            log_to_file=log_to_file,
            log_dir=log_dir,
            rotation=rotation,
            retention=retention,
            enable_hierarchical_logging=enable_hierarchical_logging,
            max_recent_logs=max_recent_logs,
        )
    except Exception:
        # 出现异常时保持默认配置
        pass


def cleanup_old_logs(log_dir: str = "logs", max_age_days: int = 7) -> int:
    """
    清理指定天数前的旧日志文件

    Args:
        log_dir: 日志目录路径
        max_age_days: 保留天数，超过此天数的文件将被删除

    Returns:
        int: 删除的文件数量
    """
    import time
    from pathlib import Path

    log_path = Path(log_dir)
    if not log_path.exists():
        return 0

    deleted_count = 0
    cutoff_time = time.time() - (max_age_days * 24 * 3600)

    # 清理所有日志文件（包括轮转的文件）
    for pattern in ["*.log*", "*.jsonl", "*.json"]:
        for log_file in log_path.glob(pattern):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except OSError:
                    pass  # 忽略删除失败的文件

    return deleted_count


def get_disk_usage(log_dir: str = "logs") -> dict:
    """
    获取日志目录的磁盘使用情况

    Args:
        log_dir: 日志目录路径

    Returns:
        dict: 包含文件数量、大小等信息的字典
    """
    from pathlib import Path

    log_path = Path(log_dir)
    if not log_path.exists():
        return {"file_count": 0, "total_size": 0, "total_size_mb": 0}

    total_size = 0
    file_count = 0

    # 查找所有日志相关文件
    for pattern in ["*.log*", "*.jsonl", "*.json"]:
        for log_file in log_path.glob(pattern):
            if log_file.is_file():
                total_size += log_file.stat().st_size
                file_count += 1

    return {
        "file_count": file_count,
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2)
    }


def get_recent_logs(
    limit: int = 100,
    level: Optional[str] = None,
    module: Optional[str] = None,
    message_contains: Optional[str] = None,
    since_minutes: Optional[int] = None
) -> list:
    """
    获取最近的日志记录，支持过滤

    Args:
        limit: 返回的最大记录数
        level: 过滤特定日志级别（如"ERROR", "INFO"）
        module: 过滤特定模块
        message_contains: 消息包含的字符串
        since_minutes: 获取最近N分钟内的日志

    Returns:
        list: 符合条件的日志记录列表

    Examples:
        # 获取最近10条错误日志
        errors = get_recent_logs(limit=10, level="ERROR")

        # 获取最近5分钟内包含"失败"的日志
        recent_failures = get_recent_logs(since_minutes=5, message_contains="失败")

        # 获取特定模块的日志
        module_logs = get_recent_logs(module="database", limit=50)
    """
    return _logger_manager.get_recent_logs(
        limit=limit,
        level=level,
        module=module,
        message_contains=message_contains,
        since_minutes=since_minutes
    )


def get_log_stats() -> Dict[str, Any]:
    """
    获取日志统计信息

    Returns:
        dict: 包含各种统计信息的字典

    Examples:
        stats = get_log_stats()
        print(f"总日志数: {stats['total_logs']}")
        print(f"内存使用率: {stats['utilization_percent']}%")
        print(f"各级别分布: {stats['level_counts']}")
    """
    return _logger_manager.get_log_stats()


def clear_recent_logs() -> int:
    """
    清空最近日志缓存

    Returns:
        int: 清空的日志条数

    Examples:
        cleared_count = clear_recent_logs()
        print(f"清空了 {cleared_count} 条日志记录")
    """
    return _logger_manager.clear_recent_logs()


def get_logger_manager() -> LoggerManager:
    """获取全局日志管理器实例"""
    return _logger_manager

