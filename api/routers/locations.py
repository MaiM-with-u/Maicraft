"""
位置管理REST API路由
提供位置点查询和管理功能
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..models.responses import UnifiedApiResponse
from agent.environment.locations import global_location_points
from agent.common.basic_class import BlockPosition

# 创建路由器
locations_router = APIRouter(prefix="/api/locations", tags=["locations"])


class LocationData(BaseModel):
    """位置点数据模型"""
    name: str
    info: str
    position: Dict[str, float]  # {"x": float, "y": float, "z": float}


class LocationUpdate(BaseModel):
    """位置点更新模型"""
    info: Optional[str] = None
    position: Optional[Dict[str, float]] = None


@locations_router.get("", response_model=UnifiedApiResponse)
async def get_all_locations():
    """获取所有位置点"""
    try:
        locations = []
        for name, info, position in global_location_points.location_list:
            locations.append({
                "name": name,
                "info": info,
                "position": {
                    "x": position.x,
                    "y": position.y,
                    "z": position.z
                },
                "created_time": None,  # 暂时不支持
                "visit_count": 0  # 暂时不支持
            })

        return {
            "code": "SUCCESS",
            "success": True,
            "message": "获取位置点列表成功",
            "data": {
                "locations": locations,
                "total": len(locations)
            }
        }
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message": f"获取位置点列表失败: {str(e)}",
            "error_code": "OPERATION_FAILED",
            "data": None
        }


@locations_router.get("/stats", response_model=UnifiedApiResponse)
async def get_location_stats():
    """获取位置统计信息"""
    try:
        total_locations = len(global_location_points.location_list)

        # 统计位置类型（暂时不支持）
        type_stats = {}

        return {
            "code": "SUCCESS",
            "success": True,
            "message": "获取位置统计成功",
            "data": {
                "total_locations": total_locations,
                "type_distribution": type_stats,
                "most_visited": None,  # 暂时不支持
                "recently_added": None  # 暂时不支持
            }
        }
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message": f"获取位置统计失败: {str(e)}",
            "data": None
        }


@locations_router.post("", response_model=UnifiedApiResponse)
async def add_location(location: LocationData):
    """添加新位置点"""
    try:
        # 验证位置数据
        if not all(k in location.position for k in ["x", "y", "z"]):
            raise HTTPException(status_code=400, detail="位置数据必须包含x、y、z坐标")

        # 创建BlockPosition对象
        position = BlockPosition(
            x=location.position["x"],
            y=location.position["y"],
            z=location.position["z"]
        )

        # 添加位置点
        final_name = global_location_points.add_location(
            location.name,
            location.info,
            position
        )

        return {
            "code": "SUCCESS",
            "success": True,
            "message": "添加位置点成功",
            "data": {
                "name": final_name,
                "info": location.info,
                "position": location.position
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message": f"添加位置点失败: {str(e)}",
            "data": None
        }


@locations_router.get("/{name}", response_model=UnifiedApiResponse)
async def get_location(name: str):
    """获取指定位置点"""
    try:
        for loc_name, info, position in global_location_points.location_list:
            if loc_name == name:
                return {
                    "code": "SUCCESS",
            "success": True,
            "message": "获取位置点成功",
            "data": {
                        "name": loc_name,
                        "info": info,
                        "position": {
                            "x": position.x,
                            "y": position.y,
                            "z": position.z
                        }
                    }
                }

        # 位置点不存在
        return {
            "code": "ERROR",
            "success": False,
            "message": "位置点不存在",
            "data": None
        }
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message": f"获取位置点失败: {str(e)}",
            "data": None
        }


@locations_router.put("/{name}", response_model=UnifiedApiResponse)
async def update_location(name: str, update: LocationUpdate):
    """更新位置点信息"""
    try:
        # 检查位置点是否存在
        location_exists = any(loc[0] == name for loc in global_location_points.location_list)
        if not location_exists:
            return {
                "code": "ERROR",
            "success": False,
                "message": "位置点不存在",
                "data": None
            }

        # 更新信息
        if update.info is not None:
            success = global_location_points.edit_location(name, update.info)
            if not success:
                return {
                    "code": "ERROR",
            "success": False,
                    "message": "更新位置点信息失败",
                    "data": None
                }

        # 注意：位置更新暂时不支持，因为原始实现中没有这个功能
        if update.position is not None:
            return {
                "code": "ERROR",
            "success": False,
                "message": "位置坐标更新暂不支持",
                "data": None
            }

        # 获取更新后的位置点信息
        for loc_name, info, position in global_location_points.location_list:
            if loc_name == name:
                return {
                    "code": "SUCCESS",
            "success": True,
                    "message": "更新位置点成功",
                    "data": {
                        "name": loc_name,
                        "info": info,
                        "position": {
                            "x": position.x,
                            "y": position.y,
                            "z": position.z
                        }
                    }
                }

    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message": f"更新位置点失败: {str(e)}",
            "data": None
        }


@locations_router.delete("/{name}", response_model=UnifiedApiResponse)
async def delete_location(name: str):
    """删除位置点"""
    try:
        # 检查位置点是否存在
        location_exists = False
        location_data = None

        for loc_name, info, position in global_location_points.location_list:
            if loc_name == name:
                location_exists = True
                location_data = {
                    "name": loc_name,
                    "info": info,
                    "position": {
                        "x": position.x,
                        "y": position.y,
                        "z": position.z
                    }
                }
                break

        if not location_exists:
            return {
                "code": "ERROR",
            "success": False,
                "message": "位置点不存在",
                "data": None
            }

        # 删除位置点
        global_location_points.remove_location(name)

        return {
            "code": "SUCCESS",
            "success": True,
            "message": "删除位置点成功",
            "data": location_data
        }
    except Exception as e:
        return {
            "code": "ERROR",
            "success": False,
            "message": f"删除位置点失败: {str(e)}",
            "data": None
        }
