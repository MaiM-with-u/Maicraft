"""
事件发射器 - 实现类似mineflayer的bot.on/bot.once事件监听机制
"""

import asyncio
import logging
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Listener:
    """监听器包装类"""

    callback: Callable
    event_type: str
    is_once: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __eq__(self, other) -> bool:
        if isinstance(other, Listener):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)


class ListenerHandle:
    """监听器句柄，用于管理监听器的生命周期"""

    def __init__(self, emitter: "EventEmitter", listener: Listener):
        self._emitter = emitter
        self._listener = listener
        self._removed = False

    def remove(self) -> bool:
        """移除监听器"""
        if not self._removed:
            success = self._emitter.off(
                self._listener.event_type, self._listener.callback
            )
            self._removed = success
            return success
        return False

    @property
    def is_removed(self) -> bool:
        """检查监听器是否已被移除"""
        return self._removed

    @property
    def event_type(self) -> str:
        """获取监听的事件类型"""
        return self._listener.event_type


class EventEmitter:
    """事件发射器，负责管理监听器和事件分发"""

    def __init__(self, max_listeners: int = 200):  # 提高默认限制
        self._listeners: Dict[str, List[Listener]] = {}
        self._once_listeners: Dict[str, List[Listener]] = {}
        self._max_listeners = max_listeners
        self._listener_count: Dict[str, int] = {}

        # 性能统计
        self._stats = {
            "total_emitted": 0,
            "total_listeners_called": 0,
            "avg_emit_time": 0.0,
            "max_emit_time": 0.0,
            "errors": 0,
        }

    def _check_listener_limit(self, event_type: str) -> bool:
        """检查监听器数量是否超过限制"""
        current_count = self._listener_count.get(event_type, 0)
        if current_count >= self._max_listeners:
            logger.warning(f"监听器数量超过限制 {self._max_listeners}: {event_type}")
            return False
        return True

    async def emit(self, event: "BaseEvent") -> None:
        """分发事件给所有相关监听器"""
        import time

        start_time = time.time()

        event_type = event.type

        # 获取所有监听器
        listeners = self._listeners.get(event_type, []) + self._once_listeners.get(
            event_type, []
        )

        if not listeners:
            return

        # 更新统计信息
        self._stats["total_emitted"] += 1

        # 限制并发数量，避免创建过多协程
        semaphore = asyncio.Semaphore(50)  # 限制最大并发数

        async def call_with_semaphore(listener):
            async with semaphore:
                await self._safe_call_listener(listener, event)

        tasks = [
            asyncio.create_task(call_with_semaphore(listener)) for listener in listeners
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 清理一次性监听器
        if event_type in self._once_listeners:
            self._stats["total_listeners_called"] += len(
                self._once_listeners[event_type]
            )
            del self._once_listeners[event_type]
            self._listener_count[event_type] = self._listener_count.get(
                event_type, 0
            ) - len(listeners)

        # 更新性能统计
        elapsed = time.time() - start_time
        self._stats["total_listeners_called"] += len(listeners)
        self._stats["avg_emit_time"] = (
            self._stats["avg_emit_time"] * (self._stats["total_emitted"] - 1) + elapsed
        ) / self._stats["total_emitted"]
        self._stats["max_emit_time"] = max(self._stats["max_emit_time"], elapsed)

    async def _safe_call_listener(self, listener: Listener, event: "BaseEvent") -> None:
        """安全调用监听器，隔离异常"""
        try:
            if asyncio.iscoroutinefunction(listener.callback):
                await listener.callback(event)
            else:
                # 同步回调也在线程池中执行，避免阻塞事件循环
                await asyncio.get_event_loop().run_in_executor(
                    None, listener.callback, event
                )
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"事件监听器执行失败 [{listener.event_type}]: {e}")
            logger.error(f"监听器ID: {listener.id}, 回调: {listener.callback}")
            import traceback

            logger.error(f"异常详情: {traceback.format_exc()}")

    def on(self, event_type: str, callback: Callable) -> ListenerHandle:
        """注册持续监听器"""
        if not self._check_listener_limit(event_type):
            raise ValueError(f"监听器数量超过限制: {event_type}")

        # 检查是否已存在相同的回调
        existing_listeners = self._listeners.get(event_type, [])
        for existing in existing_listeners:
            if existing.callback == callback:
                logger.warning(f"重复注册监听器: {event_type}")
                return ListenerHandle(self, existing)

        listener = Listener(callback=callback, event_type=event_type, is_once=False)

        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

        self._listener_count[event_type] = self._listener_count.get(event_type, 0) + 1

        logger.debug(f"注册持续监听器: {event_type} -> {listener.id}")
        return ListenerHandle(self, listener)

    def once(self, event_type: str, callback: Callable) -> ListenerHandle:
        """注册一次性监听器"""
        if not self._check_listener_limit(event_type):
            raise ValueError(f"监听器数量超过限制: {event_type}")

        listener = Listener(callback=callback, event_type=event_type, is_once=True)

        if event_type not in self._once_listeners:
            self._once_listeners[event_type] = []
        self._once_listeners[event_type].append(listener)

        self._listener_count[event_type] = self._listener_count.get(event_type, 0) + 1

        logger.debug(f"注册一次性监听器: {event_type} -> {listener.id}")
        return ListenerHandle(self, listener)

    def off(self, event_type: str, callback: Optional[Callable] = None) -> bool:
        """移除监听器"""
        removed = False

        # 从持续监听器中移除
        if event_type in self._listeners:
            if callback is None:
                # 移除所有该类型的持续监听器
                count = len(self._listeners[event_type])
                self._listeners[event_type].clear()
                self._listener_count[event_type] = (
                    self._listener_count.get(event_type, 0) - count
                )
                removed = count > 0
            else:
                # 移除特定的监听器
                original_length = len(self._listeners[event_type])
                self._listeners[event_type] = [
                    l for l in self._listeners[event_type] if l.callback != callback
                ]
                removed_count = original_length - len(self._listeners[event_type])
                if removed_count > 0:
                    self._listener_count[event_type] = (
                        self._listener_count.get(event_type, 0) - removed_count
                    )
                    removed = True

                # 如果没有监听器了，清理字典
                if not self._listeners[event_type]:
                    del self._listeners[event_type]

        # 从一次性监听器中移除
        if event_type in self._once_listeners:
            if callback is None:
                count = len(self._once_listeners[event_type])
                self._once_listeners[event_type].clear()
                self._listener_count[event_type] = (
                    self._listener_count.get(event_type, 0) - count
                )
                removed = removed or (count > 0)
            else:
                original_length = len(self._once_listeners[event_type])
                self._once_listeners[event_type] = [
                    l
                    for l in self._once_listeners[event_type]
                    if l.callback != callback
                ]
                removed_count = original_length - len(self._once_listeners[event_type])
                if removed_count > 0:
                    self._listener_count[event_type] = (
                        self._listener_count.get(event_type, 0) - removed_count
                    )
                    removed = True

                if not self._once_listeners[event_type]:
                    del self._once_listeners[event_type]

        if removed:
            logger.debug(f"移除监听器: {event_type}, callback: {callback}")

        return removed

    def remove_all_listeners(self, event_type: Optional[str] = None) -> int:
        """移除所有监听器"""
        total_removed = 0

        if event_type is None:
            # 移除所有类型的监听器
            for et in list(self._listeners.keys()):
                total_removed += self.remove_all_listeners(et)
            for et in list(self._once_listeners.keys()):
                if et not in self._listeners:  # 避免重复计算
                    total_removed += self.remove_all_listeners(et)
        else:
            # 移除指定类型的监听器
            removed_from_regular = len(self._listeners.get(event_type, []))
            removed_from_once = len(self._once_listeners.get(event_type, []))

            if event_type in self._listeners:
                del self._listeners[event_type]
            if event_type in self._once_listeners:
                del self._once_listeners[event_type]

            total_removed = removed_from_regular + removed_from_once
            self._listener_count[event_type] = 0

        return total_removed

    def listener_count(self, event_type: str) -> int:
        """获取指定事件类型的监听器数量"""
        return self._listener_count.get(event_type, 0)

    def event_names(self) -> List[str]:
        """获取所有已注册监听器的事件类型"""
        return list(set(self._listeners.keys()) | set(self._once_listeners.keys()))

    def get_listeners_info(self) -> Dict[str, List[Dict]]:
        """获取监听器信息（用于调试）"""
        info = {}

        for event_type, listeners in self._listeners.items():
            info[event_type] = [
                {"id": l.id, "created_at": l.created_at.isoformat(), "is_once": False}
                for l in listeners
            ]

        for event_type, listeners in self._once_listeners.items():
            if event_type not in info:
                info[event_type] = []
            info[event_type].extend(
                [
                    {
                        "id": l.id,
                        "created_at": l.created_at.isoformat(),
                        "is_once": True,
                    }
                    for l in listeners
                ]
            )

        return info

    def get_performance_stats(self) -> Dict:
        """获取性能统计信息"""
        return self._stats.copy()

    def get_monitoring_metrics(self) -> Dict:
        """获取监控指标"""
        return {
            "active_listeners": sum(self._listener_count.values()),
            "event_types": len(self.event_names()),
            "performance_stats": self.get_performance_stats(),
            "listener_counts": self._listener_count.copy(),
        }
