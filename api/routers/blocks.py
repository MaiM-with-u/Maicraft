"""
方块缓存管理REST API路由
提供方块查询和管理功能
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException

from ..models.responses import ApiResponse
from agent.block_cache.block_cache import global_block_cache
from agent.common.basic_class import BlockPosition

# 创建路由器
blocks_router = APIRouter(prefix="/api/blocks", tags=["blocks"])


@blocks_router.get("/stats", response_model=ApiResponse)
async def get_block_cache_stats():
    """获取方块缓存统计信息"""
    try:
        stats = global_block_cache.get_stats()

        return ApiResponse(
            isSuccess=True,
            message="获取方块缓存统计成功",
            data=stats
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"获取方块缓存统计失败: {str(e)}",
            data=None
        )


@blocks_router.get("/region", response_model=ApiResponse)
async def get_blocks_in_region(
    x: int = Query(..., description="区域中心X坐标"),
    z: int = Query(..., description="区域中心Z坐标"),
    radius: int = Query(16, description="搜索半径", ge=1, le=64)
):
    """获取指定区域内的方块"""
    try:
        center_pos = BlockPosition(x, 64, z)  # 使用默认Y坐标

        # 获取区域内的方块
        blocks = global_block_cache.get_blocks_in_radius(center_pos, radius)

        # 格式化方块数据
        block_list = []
        for position, block in blocks.items():
            block_data = {
                "position": {
                    "x": position.x,
                    "y": position.y,
                    "z": position.z
                },
                "type": block.block_type,
                "name": block.block_name,
                "last_updated": block.last_updated.isoformat() if block.last_updated else None,
                "update_count": block.update_count
            }

            # 计算距离中心点的距离
            distance = ((position.x - x) ** 2 + (position.z - z) ** 2) ** 0.5
            block_data["distance"] = round(distance, 2)

            block_list.append(block_data)

        # 按距离排序
        block_list.sort(key=lambda b: b["distance"])

        return ApiResponse(
            isSuccess=True,
            message="获取区域方块成功",
            data={
                "blocks": block_list,
                "total": len(block_list),
                "center": {"x": x, "z": z},
                "radius": radius
            }
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"获取区域方块失败: {str(e)}",
            data=None
        )


@blocks_router.get("/search", response_model=ApiResponse)
async def search_blocks(
    name: str = Query(..., description="方块名称，支持部分匹配"),
    limit: int = Query(50, description="返回结果数量限制", ge=1, le=200)
):
    """搜索特定类型的方块"""
    try:
        # 搜索方块
        found_blocks = global_block_cache.search_blocks_by_name(name, limit=limit)

        # 格式化结果
        block_list = []
        for position, block in found_blocks:
            block_data = {
                "position": {
                    "x": position.x,
                    "y": position.y,
                    "z": position.z
                },
                "type": block.block_type,
                "name": block.block_name,
                "last_updated": block.last_updated.isoformat() if block.last_updated else None,
                "update_count": block.update_count
            }
            block_list.append(block_data)

        return ApiResponse(
            isSuccess=True,
            message="搜索方块成功",
            data={
                "blocks": block_list,
                "total": len(block_list),
                "search_term": name,
                "limit": limit
            }
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"搜索方块失败: {str(e)}",
            data=None
        )


@blocks_router.get("/types", response_model=ApiResponse)
async def get_block_types():
    """获取缓存中的方块类型统计"""
    try:
        type_stats = global_block_cache.get_type_statistics()

        # 格式化类型统计数据
        types_data = []
        for block_type, stats in type_stats.items():
            types_data.append({
                "type": block_type,
                "count": stats["count"],
                "names": list(stats["names"]) if stats["names"] else []
            })

        # 按数量排序
        types_data.sort(key=lambda x: x["count"], reverse=True)

        return ApiResponse(
            isSuccess=True,
            message="获取方块类型统计成功",
            data={
                "types": types_data,
                "total_types": len(types_data)
            }
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"获取方块类型统计失败: {str(e)}",
            data=None
        )


@blocks_router.get("/position/{x}/{y}/{z}", response_model=ApiResponse)
async def get_block_at_position(x: int, y: int, z: int):
    """获取指定位置的方块信息"""
    try:
        position = BlockPosition(x, y, z)
        block = global_block_cache.get_block(x, y, z)

        if block:
            block_data = {
                "position": {
                    "x": position.x,
                    "y": position.y,
                    "z": position.z
                },
                "type": block.block_type,
                "name": block.block_name,
                "last_updated": block.last_updated.isoformat() if block.last_updated else None,
                "update_count": block.update_count,
                "exists": True
            }
        else:
            block_data = {
                "position": {"x": x, "y": y, "z": z},
                "exists": False,
                "message": "该位置的方块信息未被缓存"
            }

        return ApiResponse(
            isSuccess=True,
            message="获取位置方块信息成功",
            data=block_data
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"获取位置方块信息失败: {str(e)}",
            data=None
        )


@blocks_router.delete("/cache", response_model=ApiResponse)
async def clear_block_cache():
    """清空方块缓存"""
    try:
        # 注意：这里可能需要管理员权限验证
        cleared_count = global_block_cache.clear_cache()

        return ApiResponse(
            isSuccess=True,
            message="清空方块缓存成功",
            data={
                "cleared_blocks": cleared_count,
                "message": f"成功清除了 {cleared_count} 个方块缓存"
            }
        )
    except Exception as e:
        return ApiResponse(
            isSuccess=False,
            message=f"清空方块缓存失败: {str(e)}",
            data=None
        )
