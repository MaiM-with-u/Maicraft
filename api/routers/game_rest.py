"""
游戏状态REST API路由
提供游戏状态查询和管理功能
"""

from typing import Optional, List
from fastapi import APIRouter, Query

from ..models.responses import ApiResponse
from ..services.game_state_service import game_state_service
from ..utils.error_handlers import handle_route_error, create_success_response

# 创建路由器
game_rest_router = APIRouter(prefix="/api/environment", tags=["environment"])


@game_rest_router.get("/snapshot", response_model=ApiResponse)
async def get_environment_snapshot():
    """获取游戏环境快照"""
    try:
        data = game_state_service.get_environment_snapshot()
        return create_success_response(
            data=data,
            message="获取环境快照成功"
        )
    except Exception as e:
        return handle_route_error("get_environment_snapshot", e)


@game_rest_router.get("/player", response_model=ApiResponse)
async def get_player_info():
    """获取玩家信息"""
    try:
        data = game_state_service.get_player_info()
        return create_success_response(
            data=data,
            message="获取玩家信息成功"
        )
    except Exception as e:
        return handle_route_error("get_player_info", e)


@game_rest_router.get("/inventory", response_model=ApiResponse)
async def get_inventory_info():
    """获取物品栏信息"""
    try:
        data = game_state_service.get_inventory_info()
        return create_success_response(
            data=data,
            message="获取物品栏信息成功"
        )
    except Exception as e:
        return handle_route_error("get_inventory_info", e)


@game_rest_router.get("/world", response_model=ApiResponse)
async def get_world_info():
    """获取世界信息"""
    try:
        data = game_state_service.get_world_info()
        return create_success_response(
            data=data,
            message="获取世界信息成功"
        )
    except Exception as e:
        return handle_route_error("get_world_info", e)


@game_rest_router.get("/nearby/entities", response_model=ApiResponse)
async def get_nearby_entities(
    range_limit: int = Query(16, description="搜索范围", ge=1, le=64)
):
    """获取附近实体"""
    try:
        entities = game_state_service.get_nearby_entities(range_limit)
        return create_success_response(
            data={
                "entities": entities,
                "count": len(entities),
                "range": range_limit
            },
            message="获取附近实体成功"
        )
    except Exception as e:
        return handle_route_error("get_nearby_entities", e)
