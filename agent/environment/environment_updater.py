"""
环境信息更新器
使用新的拆分后的查询工具来更新Minecraft环境信息
"""

import asyncio
import time
import traceback
from typing import Callable, Optional, Dict, Any
from datetime import datetime
from utils.logger import get_logger
from agent.environment.environment import global_environment
import json
from agent.block_cache.block_cache import global_block_cache

class EnvironmentUpdater:
    """环境信息定期更新器"""
    
    def __init__(self, 
                 mcp_client,
                 update_interval: int = 0.2,
                 ):
        """
        初始化环境更新器
        
        Args:
            agent: MaicraftAgent实例，用于调用查询工具
            update_interval: 更新间隔（秒），默认3秒
            auto_start: 是否自动开始更新，默认False
        """
        self.mcp_client = mcp_client
        self.update_interval = update_interval
        self.logger = get_logger("EnvironmentUpdater")
        
        # 更新状态
        self.is_running = False
        self.is_paused = False
        
        # 异步任务控制
        self._update_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        
        # 统计信息
        self.update_count = 0
        self.last_update_time: Optional[datetime] = None
        self.last_update_duration = 0.0
        self.average_update_duration = 0.0
        self.total_update_duration = 0.0
        
        # 事件处理相关
        self.last_processed_tick: int = 0  # 记录最后处理的事件 gameTick
        
    
    def start(self) -> bool:
        """启动环境更新器"""
        if self.is_running:
            self.logger.warning("[EnvironmentUpdater] 更新器已在运行中")
            return False
        
        try:
            self._stop_event.clear()
            self._pause_event.clear()
            self.is_running = True
            self.is_paused = False
            
            # 使用asyncio.create_task启动异步更新循环
            try:
                # 如果已有事件循环，直接创建任务
                self._update_task = asyncio.create_task(self._update_loop())
                self.logger.info(f"[EnvironmentUpdater] 在现有事件循环中启动成功，更新间隔: {self.update_interval}秒")
            except RuntimeError:
                # 如果没有运行中的事件循环，记录错误
                self.logger.error("[EnvironmentUpdater] 无法获取运行中的事件循环")
                self.is_running = False
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 启动失败: {e}")
            self.is_running = False
            return False
    
    def stop(self) -> bool:
        """停止环境更新器"""
        if not self.is_running:
            self.logger.warning("[EnvironmentUpdater] 更新器未在运行")
            return False
        
        try:
            self.logger.info("[EnvironmentUpdater] 正在停止更新器...")
            self._stop_event.set()
            
            # 停止异步任务
            if self._update_task and not self._update_task.done():
                self._update_task.cancel()
                self.logger.info("[EnvironmentUpdater] 异步任务已取消")
            
            self.is_running = False
            self.is_paused = False
            self.logger.info("[EnvironmentUpdater] 已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 停止失败: {e}")
            return False
    
    
    async def _update_loop(self):
        """更新循环的主逻辑（异步版本）"""
        self.logger.info(f"[EnvironmentUpdater] 异步更新循环已启动，间隔: {self.update_interval}秒")
        
        while not self._stop_event.is_set():
            try:
                # 检查是否暂停
                if self._pause_event.is_set():
                    await asyncio.sleep(0.1)  # 暂停时短暂休眠
                    continue
                
                await self.perform_update()
                
                # 等待下次更新
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"[EnvironmentUpdater] 更新循环异常: {e}")
                await asyncio.sleep(1)  # 出错时等待1秒再继续
        
        self.logger.info("[EnvironmentUpdater] 异步更新循环已结束")

            
        
    
    
    async def perform_update(self):
        """执行单次环境更新（异步版本）"""
        try:
            
            
            # 使用新的拆分后的查询工具获取环境数据
            environment_data = await self._gather_environment_data()
            
            if environment_data:
                # 更新全局环境信息
                try:
                    
                    global_environment.update_from_observation(environment_data)
                    # self.logger.info(f"[EnvironmentUpdater] 全局环境信息已更新，最后更新: {global_environment.last_update}")
                except Exception as e:
                    self.logger.error(f"[EnvironmentUpdater] 更新全局环境信息失败: {e}")
                    self.logger.error(traceback.format_exc())
                
                self.logger.debug(f"[EnvironmentUpdater] 环境更新完成")
            else:
                self.logger.warning("[EnvironmentUpdater] 环境更新未返回结果")
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 环境更新失败: {e}")
            raise

    async def _gather_environment_data(self) -> Optional[Dict[str, Any]]:
        """使用新的查询工具收集环境数据"""
        try:
            # 并行调用所有查询工具
            tasks = [
                self._call_query_game_state(),
                self._call_query_player_status(),
                self._call_query_recent_events(),
                self._call_query_surroundings("players"),
                self._call_query_surroundings("entities"),
                self._call_query_surroundings("blocks")
            ]
            
            # 等待所有查询完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 记录每个查询工具的结果类型，用于调试
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.warning(f"[EnvironmentUpdater] 查询工具 {i} 返回异常: {result}")
            
            # 合并结果
            combined_data = {
                "ok": True,
                "data": {},
                "request_id": "",
                "elapsed_ms": 0
            }
            
            
            # 处理游戏状态
            if isinstance(results[0], dict) and results[0].get("ok"):
                try:
                    game_state = results[0].get("data", {})
                    combined_data["data"].update(game_state)
                    combined_data["request_id"] = results[0].get("request_id", "")
                    combined_data["elapsed_ms"] = max(combined_data["elapsed_ms"], results[0].get("elapsed_ms", 0))
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理游戏状态数据时出错: {e}")
            
            # 处理玩家状态
            if isinstance(results[1], dict) and results[1].get("ok"):
                try:
                    player_status = results[1].get("data", {})
                    
                    # 新格式的玩家状态包含了更多信息，直接更新
                    combined_data["data"].update(player_status)
                    
                    # 处理物品栏信息（新格式中物品栏在player_status中）
                    if "inventory" in player_status:
                        combined_data["data"]["inventory"] = player_status["inventory"]
                    
                    # 处理光标信息
                    if "blockAtEntityCursor" in player_status:
                        combined_data["data"]["blockAtCursor"] = player_status["blockAtEntityCursor"]
                    if "entityAtCursor" in player_status:
                        combined_data["data"]["entityAtCursor"] = player_status["entityAtCursor"]
                    
                    # 处理手持物品信息
                    if "heldItem" in player_status:
                        combined_data["data"]["heldItem"] = player_status["heldItem"]
                    if "usingHeldItem" in player_status:
                        combined_data["data"]["usingHeldItem"] = player_status["usingHeldItem"]
                    
                    # 处理装备信息
                    if "equipment" in player_status:
                        combined_data["data"]["equipment"] = player_status["equipment"]
                    
                    # 处理其他新字段
                    for field in ["gamemode", "velocity", "armor", "isSleeping", "onGround", "yaw", "pitch", "biome"]:
                        if field in player_status:
                            combined_data["data"][field] = player_status[field]
                    
                    combined_data["elapsed_ms"] = max(combined_data["elapsed_ms"], results[1].get("elapsed_ms", 0))
                    self.logger.debug("[EnvironmentUpdater] 玩家状态数据更新成功")
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理玩家状态数据时出错: {e}")
                    self.logger.warning(traceback.format_exc())
            
            # 处理最近事件
            if isinstance(results[2], dict) and results[2].get("ok"):
                try:
                    recent_events = results[2].get("data", {})
                    # 根据工具返回的数据结构，events 字段直接包含事件列表
                    new_events = recent_events.get("events", [])
                    
                    # 更新 last_processed_tick 为最新的事件 tick
                    old_tick = self.last_processed_tick  # 在条件块外定义
                    if new_events:
                        # 找到最大的 gameTick 值
                        max_tick = max(event.get("gameTick", 0) for event in new_events if event.get("gameTick") is not None)
                        # 每次获取后都更新 last_processed_tick 为最新事件的 gameTick
                        self.last_processed_tick = max_tick + 5
                        # self.logger.info(f"[EnvironmentUpdater] 更新 last_processed_tick: {old_tick} -> {self.last_processed_tick}")
                
                    # 将新事件添加到现有事件列表中，而不是替换
                    combined_data["data"]["recentEvents"] = new_events
                    # 同时保存统计信息
                    combined_data["data"]["recentEventsStats"] = recent_events.get("stats", {})
                    combined_data["data"]["supportedEventTypes"] = recent_events.get("supportedEventTypes", [])
                    combined_data["elapsed_ms"] = max(combined_data["elapsed_ms"], results[2].get("elapsed_ms", 0))
                    self.logger.debug(f"[EnvironmentUpdater] 最近事件数据更新成功")
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理最近事件数据时出错: {e}")
                    combined_data["data"]["recentEvents"] = []
                    combined_data["data"]["recentEventsStats"] = {}
                    combined_data["data"]["supportedEventTypes"] = []
            
            # 处理周围环境 - 玩家
            if isinstance(results[3], dict) and results[3].get("ok"):
                try:
                    nearby_players = results[3].get("data", {}).get("players", {})
                    if isinstance(nearby_players, dict) and "list" in nearby_players:
                        combined_data["data"]["nearbyPlayers"] = nearby_players.get("list", [])
                    else:
                        # 如果players不是预期的结构，设置为空列表
                        combined_data["data"]["nearbyPlayers"] = []
                    combined_data["elapsed_ms"] = max(combined_data["elapsed_ms"], results[3].get("elapsed_ms", 0))
                    self.logger.debug("[EnvironmentUpdater] 周围玩家数据更新成功")
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理周围玩家数据时出错: {e}")
                    combined_data["data"]["nearbyPlayers"] = []
            
            # 处理周围环境 - 实体
            if isinstance(results[4], dict) and results[4].get("ok"):
                try:
                    nearby_entities = results[4].get("data", {}).get("entities", {})
                    if isinstance(nearby_entities, dict) and "list" in nearby_entities:
                        combined_data["data"]["nearbyEntities"] = nearby_entities.get("list", [])
                    else:
                        # 如果entities不是预期的结构，设置为空列表
                        combined_data["data"]["nearbyEntities"] = []
                    combined_data["elapsed_ms"] = max(combined_data["elapsed_ms"], results[4].get("elapsed_ms", 0))
                    self.logger.debug("[EnvironmentUpdater] 周围实体数据更新成功")
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理周围实体数据时出错: {e}")
                    combined_data["data"]["nearbyEntities"] = []
                    
            
            # 处理周围方块缓存器
            if isinstance(results[5], dict) and results[5].get("ok"):
                try:
                    blocks = results[5].get("data", {}).get("blocks", {})
                    global_block_cache.update_from_blocks(blocks)
                    self.logger.debug("[EnvironmentUpdater] 周围方块数据更新成功")
                except Exception as e:
                    self.logger.warning(f"[EnvironmentUpdater] 处理周围方块数据时出错: {e}")
                    self.logger.warning(traceback.format_exc())
            
            return combined_data
            
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 收集环境数据时发生异常: {e}")
            return None
        
    async def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用工具"""
        try:
            result = await self.mcp_client.call_tool_directly(tool_name, params)
            if not result.is_error and result.content:
                content_text = result.content[0].text
                return json.loads(content_text)
            else:
                self.logger.error(f"[EnvironmentUpdater] {tool_name}调用失败: {result.content[0].text if result.content else 'Unknown error'}")
                return None
        except Exception as e:
            self.logger.error(f"[EnvironmentUpdater] 调用{tool_name}时发生异常: {e}")
            return None

    async def _call_query_game_state(self) -> Optional[Dict[str, Any]]:
        """调用query_game_state工具"""
        return await self._call_tool("query_game_state", {})

    async def _call_query_player_status(self, include_inventory: bool = False) -> Optional[Dict[str, Any]]:
        """调用query_player_status工具"""
        # 新的格式已经包含了物品栏信息，所以不需要额外参数
        return await self._call_tool("query_player_status", {"includeInventory":True})

    async def _call_query_recent_events(self) -> Optional[Dict[str, Any]]:
        """调用query_recent_events工具"""
        return await self._call_tool("query_recent_events", {"sinceTick": self.last_processed_tick})

    async def _call_query_surroundings(self, env_type: str) -> Optional[Dict[str, Any]]:
        """调用query_surroundings工具"""
        return await self._call_tool("query_surroundings", {"type": env_type,"range":5,"useAbsoluteCoords":True})
    
    def reset_event_tracking(self):
        """重置事件跟踪，清空 last_processed_tick"""
        self.last_processed_tick = 0
        self.logger.info("[EnvironmentUpdater] 事件跟踪已重置，last_processed_tick 设为 0")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
    
    def __del__(self):
        """析构函数，确保线程被正确清理"""
        if self.is_running:
            try:
                self.stop()
            except:
                pass
