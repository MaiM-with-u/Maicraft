"""
事件注册表 - 自动扫描注册事件类，消除手动配置
"""

from typing import Dict, Type, Any, Callable, Set
import importlib
import pkgutil
import inspect
from utils.logger import get_logger

# 获取当前模块的日志器
logger = get_logger("EventRegistry")


class EventRegistry:
    """事件注册表，管理事件类型到事件类的映射"""

    def __init__(self):
        self._event_classes: Dict[str, Type] = {}
        self._raw_data_handlers: Dict[str, Callable] = {}

    def register_event_class(self, event_type: str, event_class: Type) -> None:
        """注册事件类"""
        self._event_classes[event_type] = event_class

    def register_raw_data_handler(self, event_type: str, handler: Callable) -> None:
        """注册原始数据处理器"""
        self._raw_data_handlers[event_type] = handler

    def get_event_class(self, event_type: str) -> Type:
        """获取事件类"""
        return self._event_classes.get(event_type)

    def get_raw_data_handler(self, event_type: str) -> Callable:
        """获取原始数据处理器"""
        return self._raw_data_handlers.get(event_type)

    def create_event(self, event_type: str, **kwargs) -> Any:
        """创建事件实例"""
        event_class = self.get_event_class(event_type)
        if event_class:
            return event_class(**kwargs)
        return None

    def create_event_from_raw_data(self, event_data_item: Dict[str, Any]) -> Any:
        """从原始数据创建事件"""
        event_type = event_data_item.get("type", "")
        handler = self.get_raw_data_handler(event_type)
        if handler:
            return handler(event_data_item)
        return None

    def get_registered_event_types(self) -> Set[str]:
        """获取所有已注册的事件类型"""
        return set(self._event_classes.keys())

    def get_registered_count(self) -> int:
        """获取已注册的事件类数量"""
        return len(self._event_classes)


# 全局事件注册表实例
event_registry = EventRegistry()


def _convert_class_name_to_event_type(event_class_name: str) -> str:
    """
    将事件类名转换为事件类型 - 生成正确的camelCase格式
    ChatEvent -> chat
    PlayerJoinedEvent -> playerJoined
    EntityHurtEvent -> entityHurt
    """
    if not event_class_name.endswith("Event"):
        return event_class_name.lower()

    # 移除Event后缀
    name = event_class_name[:-5]

    # 特殊情况：如果是单单词，直接转小写
    if name.isupper():
        return name.lower()

    # 使用正则表达式进行驼峰转换，保持camelCase格式
    # 找到所有大写字母的位置
    words = []
    current_word = []

    for i, char in enumerate(name):
        if i == 0:
            # 第一个字符总是小写
            current_word.append(char.lower())
        elif char.isupper():
            # 如果当前是大写字母
            if current_word and name[i - 1].islower():
                # 前一个是小写，说明是大写单词的开始，先保存当前单词
                words.append("".join(current_word))
                current_word = [char.lower()]
            else:
                # 前一个是大写或当前是连续大写，直接添加
                current_word.append(char.lower())
        else:
            # 小写字母直接添加
            current_word.append(char)

    # 添加最后一个单词
    if current_word:
        words.append("".join(current_word))

    # 重新组合：第一个单词全小写，其他单词首字母大写
    if not words:
        return name.lower()

    result = words[0].lower()  # 第一个单词全小写
    for word in words[1:]:
        if word:
            result += word[0].upper() + word[1:].lower()

    return result


def auto_discover_and_register_events(package_name: str = "agent.events.impl") -> None:
    """
    自动扫描并注册指定包下的所有事件类

    Args:
        package_name: 要扫描的包名，默认为 "agent.events.impl"
    """
    try:
        # 动态导入包
        package = importlib.import_module(package_name)

        # 获取包的路径
        package_path = package.__path__ if hasattr(package, "__path__") else None
        if package_path:
            # 使用pkgutil扫描包中的所有模块
            for importer, modname, ispkg in pkgutil.iter_modules(
                package_path, f"{package_name}."
            ):
                if not ispkg and modname.endswith("_event"):
                    try:
                        # 导入模块
                        module = importlib.import_module(modname)

                        # 扫描模块中的所有类
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            # 检查是否是BaseEvent的子类（但不是BaseEvent本身）
                            from .base_event import BaseEvent

                            if (
                                inspect.isclass(obj)
                                and issubclass(obj, BaseEvent)
                                and obj is not BaseEvent
                            ):
                                # 转换为事件类型
                                event_type = _convert_class_name_to_event_type(
                                    obj.__name__
                                )

                                # 注册事件类
                                event_registry.register_event_class(event_type, obj)

                                # 注册原始数据处理器
                                if hasattr(obj, "from_raw_data"):
                                    event_registry.register_raw_data_handler(
                                        event_type, obj.from_raw_data
                                    )

                                logger.info(
                                    f"自动注册事件类: {obj.__name__} -> {event_type}"
                                )

                    except Exception as e:
                        logger.warning(f"跳过模块 {modname}: {e}")

    except Exception as e:
        logger.error(f"自动发现事件类失败: {e}")


def manual_register_event(event_type: str, event_class: Type) -> None:
    """
    手动注册事件类（用于特殊情况）

    Args:
        event_type: 事件类型字符串
        event_class: 事件类
    """
    event_registry.register_event_class(event_type, event_class)
    if hasattr(event_class, "from_raw_data"):
        event_registry.register_raw_data_handler(event_type, event_class.from_raw_data)


def register_all_events() -> None:
    """注册所有事件类型（自动发现 + 手动补充）"""
    logger.info("开始自动发现和注册事件类...")

    # 自动发现并注册事件类
    auto_discover_and_register_events("agent.events.impl")

    # 输出统计信息
    registered_count = event_registry.get_registered_count()
    registered_types = event_registry.get_registered_event_types()

    logger.info("事件注册完成:")
    logger.info(f"已注册事件类型数量: {registered_count}")
    logger.info(f"已注册的事件类型: {sorted(registered_types)}")

    if registered_count == 0:
        logger.warning("未发现任何事件类，请检查 agent.events.impl 包结构")
