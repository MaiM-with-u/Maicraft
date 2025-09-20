"""
容器管理REST API路由
提供容器查询和管理功能
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException

from ..models.responses import UnifiedApiResponse
from agent.container_cache.container_cache import global_container_cache
from agent.common.basic_class import BlockPosition

# 创建路由器
containers_router = APIRouter(prefix="/api/containers", tags=["containers"])


@containers_router.get("", response_model=UnifiedApiResponse)
async def get_containers(
    container_type: str = Query("all", description="容器类型: all, chest, furnace"),
    range_limit: float = Query(32.0, description="搜索范围", ge=1.0, le=128.0)
):
    """获取容器列表"""
    try:
        # 获取玩家当前位置作为搜索中心
        from agent.environment.environment import global_environment
        center_position = global_environment.position

        if not center_position:
            return {
                "code": "ERROR",
            "success": False,
                "message":"无法获取玩家位置信息",
                "data":None
            }

        center_block_pos = BlockPosition(center_position)

        # 获取附近的容器
        containers = global_container_cache.get_nearby_containers_with_verify(
            center_block_pos,
            range_limit
        )

        # 过滤容器类型
        if container_type != "all":
            containers = [
                container for container in containers
                if container.container_type == container_type
            ]

        # 格式化容器数据
        container_list = []
        for container in containers:
            container_data = {
                "position": {
                    "x": container.position.x,
                    "y": container.position.y,
                    "z": container.position.z
                },
                "type": container.container_type,
                "inventory": container.inventory or {},
                "verified": True  # 已经过验证
            }

            # 添加熔炉特定信息
            if container.container_type == "furnace" and container.furnace_slots:
                container_data["furnace_slots"] = container.furnace_slots

            container_list.append(container_data)

        return {
            "code": "SUCCESS",
            "success": True,
            "message":"获取容器列表成功",
            "data":{
                "containers": container_list,
                "total": len(container_list),
                "center_position": {
                    "x": center_block_pos.x,
                    "y": center_block_pos.y,
                    "z": center_block_pos.z
                },
                "range": range_limit,
                "type_filter": container_type
            }
        }
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message":f"获取容器列表失败: {str(e)}",
            "data":None
        }


@containers_router.get("/verify/{x}/{y}/{z}", response_model=UnifiedApiResponse)
async def verify_container(x: int, y: int, z: int):
    """验证容器存在"""
    try:
        position = BlockPosition(x, y, z)

        # 首先检查缓存中是否有这个容器
        container_info = global_container_cache.get_container_info(position)

        if not container_info:
            return {
                "code": "SUCCESS",
            "success": True,
                "message":"容器验证完成",
                "data":{
                    "exists": False,
                    "position": {"x": x, "y": y, "z": z},
                    "reason": "容器不在缓存中"
                }
            }

        # 验证容器实际存在
        exists = global_container_cache.verify_container_exists(
            position,
            container_info.container_type
        )

        if not exists:
            # 如果容器不存在，从缓存中移除
            global_container_cache.remove_container_from_cache(position)

        result_data = {
            "exists": exists,
            "position": {"x": x, "y": y, "z": z},
            "type": container_info.container_type,
            "verified": True
        }

        if exists:
            result_data.update({
                "inventory": container_info.inventory or {},
                "furnace_slots": container_info.furnace_slots or {}
            })

        return {
            "code": "SUCCESS",
            "success": True,
            "message":"容器验证完成",
            "data":result_data
        }
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message":f"验证容器失败: {str(e)}",
            "data":None
        }


@containers_router.delete("/invalid", response_model=UnifiedApiResponse)
async def clean_invalid_containers():
    """清理无效容器"""
    try:
        # 清理所有无效容器
        removed_count = global_container_cache.clean_invalid_containers()

        return {
            "code": "SUCCESS",
            "success": True,
            "message":"清理无效容器完成",
            "data":{
                "removed_count": removed_count,
                "message": f"成功清理了 {removed_count} 个不存在的容器"
            }
        }
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message":f"清理无效容器失败: {str(e)}",
            "data":None
        }


@containers_router.get("/stats", response_model=UnifiedApiResponse)
async def get_container_stats():
    """获取容器统计信息"""
    try:
        chest_count = len(global_container_cache.chest_cache)
        furnace_count = len(global_container_cache.furnace_cache)
        total_count = chest_count + furnace_count

        # 计算总物品数量
        total_items = 0
        for container in list(global_container_cache.chest_cache.values()) + list(global_container_cache.furnace_cache.values()):
            if container.inventory:
                total_items += sum(container.inventory.values())
            if container.furnace_slots:
                for slot_items in container.furnace_slots.values():
                    if isinstance(slot_items, dict):
                        total_items += sum(slot_items.values())

        return {
            "code": "SUCCESS",
            "success": True,
            "message":"获取容器统计成功",
            "data":{
                "total_containers": total_count,
                "chest_count": chest_count,
                "furnace_count": furnace_count,
                "total_items": total_items,
                "cache_info": global_container_cache.get_cache_info()
            }
        }
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message":f"获取容器统计失败: {str(e)}",
            "data":None
        }
