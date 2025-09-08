#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 query_area_blocks 工具的脚本
专门测试该工具的参数配置和返回值解析
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from utils.logger import get_logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from mcp_server.client import global_mcp_client
    from agent.common.basic_class import BlockPosition
    from agent.block_cache.block_cache import global_block_cache
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录下运行此脚本")
    sys.exit(1)

logger = get_logger("TestQueryAreaBlocks")


class TestQueryAreaBlocks:
    """测试 query_area_blocks 工具的类"""
    
    def __init__(self):
        self.logger = get_logger("TestQueryAreaBlocks")
        self.connected = False
    
    async def connect(self) -> bool:
        """连接到MCP服务器"""
        try:
            self.connected = await global_mcp_client.connect()
            if self.connected:
                self.logger.info("成功连接到MCP服务器")
                return True
            else:
                self.logger.error("连接MCP服务器失败")
                return False
        except Exception as e:
            self.logger.error(f"连接过程中发生错误: {e}")
            return False
    
    async def disconnect(self):
        """断开MCP连接"""
        if global_mcp_client and self.connected:
            await global_mcp_client.disconnect()
            self.connected = False
            self.logger.info("已断开MCP连接")
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """调用工具"""
        try:
            result = await global_mcp_client.call_tool_directly(tool_name, params)
            if not result.is_error and result.content:
                content_text = result.content[0].text
                return json.loads(content_text)
            else:
                self.logger.error(f"{tool_name}调用失败: {result.content[0].text if result.content else 'Unknown error'}")
                return None
        except Exception as e:
            self.logger.error(f"调用{tool_name}时发生异常: {e}")
            return None
    
    async def test_basic_query(self):
        """测试基本查询功能"""
        print("\n" + "="*60)
        print("测试1: 基本查询功能")
        print("="*60)
        
        # 使用固定坐标进行测试
        params = {
            "startX": 100,
            "startY": 64,
            "startZ": 100,
            "endX": 105,
            "endY": 68,
            "endZ": 105
        }
        
        print(f"调用参数: {params}")
        result = await self.call_tool("query_area_blocks", params)
        
        if result:
            self._analyze_result(result, "基本查询")
        else:
            print("❌ 基本查询失败")
    
    async def test_compression_mode(self):
        """测试压缩模式"""
        print("\n" + "="*60)
        print("测试2: 压缩模式")
        print("="*60)
        
        params = {
            "startX": 100,
            "startY": 64,
            "startZ": 100,
            "endX": 105,
            "endY": 68,
            "endZ": 105,
            "compressionMode": True,
            "includeBlockCounts": True
        }
        
        print(f"调用参数: {params}")
        result = await self.call_tool("query_area_blocks", params)
        
        if result:
            self._analyze_result(result, "压缩模式")
        else:
            print("❌ 压缩模式测试失败")
    
    async def test_relative_coords(self):
        """测试相对坐标"""
        print("\n" + "="*60)
        print("测试3: 相对坐标")
        print("="*60)
        
        params = {
            "startX": -5,
            "startY": -2,
            "startZ": -5,
            "endX": 5,
            "endY": 2,
            "endZ": 5,
            "useRelativeCoords": True
        }
        
        print(f"调用参数: {params}")
        result = await self.call_tool("query_area_blocks", params)
        
        if result:
            self._analyze_result(result, "相对坐标")
        else:
            print("❌ 相对坐标测试失败")
    
    async def test_large_area(self):
        """测试大区域查询"""
        print("\n" + "="*60)
        print("测试4: 大区域查询")
        print("="*60)
        
        params = {
            "startX": 90,
            "startY": 60,
            "startZ": 90,
            "endX": 110,
            "endY": 70,
            "endZ": 110,
            "maxBlocks": 10000,
            "compressionMode": True
        }
        
        print(f"调用参数: {params}")
        result = await self.call_tool("query_area_blocks", params)
        
        if result:
            self._analyze_result(result, "大区域查询")
        else:
            print("❌ 大区域查询失败")
    
    async def test_edge_cases(self):
        """测试边界情况"""
        print("\n" + "="*60)
        print("测试5: 边界情况")
        print("="*60)
        
        # 测试单个方块
        params = {
            "startX": 100,
            "startY": 64,
            "startZ": 100,
            "endX": 100,
            "endY": 64,
            "endZ": 100
        }
        
        print(f"调用参数 (单个方块): {params}")
        result = await self.call_tool("query_area_blocks", params)
        
        if result:
            self._analyze_result(result, "单个方块")
        else:
            print("❌ 单个方块查询失败")
    
    def _analyze_result(self, result: Dict[str, Any], test_name: str):
        """分析查询结果"""
        print(f"\n✅ {test_name} 成功")
        print(f"请求ID: {result.get('request_id', 'N/A')}")
        print(f"耗时: {result.get('elapsed_ms', 0)}ms")
        
        data = result.get("data", {})
        
        # 分析方块数量统计
        if "blockCounts" in data:
            block_counts = data["blockCounts"]
            if isinstance(block_counts, dict):
                print(f"方块种类数: {len(block_counts)}")
                print(f"总方块数: {sum(block_counts.values())}")
                print("方块统计:")
                for block_type, count in sorted(block_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  - {block_type}: {count}")
            elif isinstance(block_counts, list):
                print(f"方块统计列表: {len(block_counts)} 项")
                for i, block_stat in enumerate(block_counts[:10]):
                    if isinstance(block_stat, dict):
                        block_type = block_stat.get("name", "unknown")
                        count = block_stat.get("count", 0)
                        print(f"  - {block_type}: {count}")
                    else:
                        print(f"  - 项 {i+1}: {block_stat}")
            else:
                print(f"方块统计格式: {type(block_counts)} - {block_counts}")
        
        # 分析压缩方块数据
        if "compressedBlocks" in data:
            compressed_blocks = data["compressedBlocks"]
            print(f"压缩方块组数: {len(compressed_blocks)}")
            
            # 分析每个方块组
            total_blocks = 0
            for i, block_data in enumerate(compressed_blocks[:5]):  # 只显示前5个
                block_type = block_data.get("name", "unknown")
                can_see = block_data.get("canSee", False)
                positions = block_data.get("positions", [])
                total_blocks += len(positions)
                print(f"  方块组 {i+1}: {block_type}, 可见: {can_see}, 位置数: {len(positions)}")
            
            if len(compressed_blocks) > 5:
                print(f"  ... 还有 {len(compressed_blocks) - 5} 个方块组")
            
            print(f"总方块数 (压缩模式): {total_blocks}")
        
        # 分析原始方块数据
        if "blocks" in data:
            blocks = data["blocks"]
            print(f"原始方块数: {len(blocks)}")
            
            # 显示前几个方块
            for i, block in enumerate(blocks[:5]):
                pos = block.get("position", {})
                block_type = block.get("name", "unknown")
                print(f"  方块 {i+1}: {block_type} at ({pos.get('x', 0)}, {pos.get('y', 0)}, {pos.get('z', 0)})")
            
            if len(blocks) > 5:
                print(f"  ... 还有 {len(blocks) - 5} 个方块")
        
        # 分析查询范围
        if "queryRange" in data:
            query_range = data["queryRange"]
            print(f"查询范围: {query_range}")
        
        # 测试数据完整性
        self._test_data_integrity(data)
    
    def _test_data_integrity(self, data: Dict[str, Any]):
        """测试数据完整性"""
        print("\n📊 数据完整性检查:")
        
        # 检查必要字段
        required_fields = ["queryRange"]
        for field in required_fields:
            if field in data:
                print(f"  ✅ {field}: 存在")
            else:
                print(f"  ❌ {field}: 缺失")
        
        # 检查方块数据格式
        if "compressedBlocks" in data:
            compressed_blocks = data["compressedBlocks"]
            if isinstance(compressed_blocks, list):
                print(f"  ✅ compressedBlocks: 列表格式，{len(compressed_blocks)} 项")
                
                # 检查每个压缩方块的结构
                for i, block in enumerate(compressed_blocks[:3]):
                    if isinstance(block, dict):
                        has_name = "name" in block
                        has_positions = "positions" in block
                        has_can_see = "canSee" in block
                        print(f"    方块组 {i+1}: name={has_name}, positions={has_positions}, canSee={has_can_see}")
                    else:
                        print(f"    方块组 {i+1}: ❌ 不是字典格式")
            else:
                print(f"  ❌ compressedBlocks: 不是列表格式")
        
        if "blocks" in data:
            blocks = data["blocks"]
            if isinstance(blocks, list):
                print(f"  ✅ blocks: 列表格式，{len(blocks)} 项")
            else:
                print(f"  ❌ blocks: 不是列表格式")
    
    async def test_with_block_cache(self):
        """测试与方块缓存的集成"""
        print("\n" + "="*60)
        print("测试6: 方块缓存集成")
        print("="*60)
        
        # 获取玩家当前位置附近区域
        params = {
            "startX": 95,
            "startY": 62,
            "startZ": 95,
            "endX": 105,
            "endY": 67,
            "endZ": 105,
            "compressionMode": True
        }
        
        print(f"调用参数: {params}")
        result = await self.call_tool("query_area_blocks", params)
        
        if result:
            data = result.get("data", {})
            compressed_blocks = data.get("compressedBlocks", [])
            
            print(f"查询到 {len(compressed_blocks)} 个方块组")
            
            # 模拟 environment_updater 中的处理逻辑
            updated_count = 0
            for block_data in compressed_blocks:
                block_type = block_data.get("name", "")
                can_see = block_data.get("canSee", False)
                positions = block_data.get("positions", [])
                
                print(f"处理方块: {block_type}, 可见: {can_see}, 位置数: {len(positions)}")
                
                # 更新到方块缓存
                for pos in positions:
                    x = pos.get("x", 0)
                    y = pos.get("y", 0)
                    z = pos.get("z", 0)
                    
                    block_pos = BlockPosition(x=x, y=y, z=z)
                    cached_block = global_block_cache.add_block(block_type, can_see, block_pos)
                    updated_count += 1
            
            print(f"✅ 已更新 {updated_count} 个方块到缓存")
            
            # 测试缓存查询
            print(f"\n🔍 测试缓存查询:")
            test_pos = BlockPosition(x=100, y=64, z=100)
            cached_block = global_block_cache.get_block(test_pos.x, test_pos.y, test_pos.z)
            if cached_block:
                print(f"  位置 ({test_pos.x}, {test_pos.y}, {test_pos.z}): {cached_block.block_type}, 可见: {cached_block.can_see}")
            else:
                print(f"  位置 ({test_pos.x}, {test_pos.y}, {test_pos.z}): 未找到")
        else:
            print("❌ 方块缓存集成测试失败")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始测试 query_area_blocks 工具")
        print("="*80)
        
        if not self.connected:
            print("❌ 未连接到MCP服务器")
            return
        
        try:
            # 运行所有测试
            await self.test_basic_query()
            await self.test_compression_mode()
            await self.test_relative_coords()
            await self.test_large_area()
            await self.test_edge_cases()
            await self.test_with_block_cache()
            
            print("\n" + "="*80)
            print("✅ 所有测试完成")
            print("="*80)
            
        except Exception as e:
            self.logger.error(f"测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
    
    async def interactive_test(self):
        """交互式测试 - 让用户自定义参数"""
        print("\n" + "="*80)
        print("🎯 交互式测试 - 自定义查询参数")
        print("="*80)
        
        while True:
            try:
                print("\n请输入查询参数:")
                
                # 获取坐标参数
                print("\n📍 坐标设置:")
                print("输入格式: x y z (例如: 100 64 100)")
                start_coords = self._get_input_coords("起始坐标", "100 64 100")
                end_coords = self._get_input_coords("结束坐标", "105 68 105")
                
                # 获取可选参数
                print("\n⚙️ 可选参数设置:")
                use_relative = self._get_input_bool("使用相对坐标", False)
                max_blocks = self._get_input_int("最大方块数量", 5000)
                compression_mode = self._get_input_bool("启用压缩模式", False)
                include_counts = self._get_input_bool("包含方块统计", True)
                
                # 构建参数字典
                params = {
                    "startX": start_coords[0],
                    "startY": start_coords[1],
                    "startZ": start_coords[2],
                    "endX": end_coords[0],
                    "endY": end_coords[1],
                    "endZ": end_coords[2]
                }
                
                # 添加可选参数（如果用户设置了非默认值）
                if use_relative:
                    params["useRelativeCoords"] = use_relative
                if max_blocks != 5000:
                    params["maxBlocks"] = max_blocks
                if compression_mode:
                    params["compressionMode"] = compression_mode
                if include_counts != True:
                    params["includeBlockCounts"] = include_counts
                
                print("\n📋 调用参数:")
                print(json.dumps(params, indent=2, ensure_ascii=False))
                
                # 执行查询
                print("\n🔍 执行查询...")
                result = await self.call_tool("query_area_blocks", params)
                
                if result:
                    self._analyze_result(result, "自定义查询")
                    await self._detailed_analysis(result)
                else:
                    print("❌ 查询失败")
                
                # 询问是否继续
                if not self._get_input_bool("\n是否继续测试", False):
                    break
                    
            except KeyboardInterrupt:
                print("\n\n用户中断")
                break
            except Exception as e:
                print(f"\n❌ 测试过程中发生错误: {e}")
                import traceback
                traceback.print_exc()
                break
    
    def _get_input_int(self, prompt: str, default: int) -> int:
        """获取整数输入"""
        while True:
            try:
                value = input(f"{prompt} (默认: {default}): ").strip()
                if not value:
                    return default
                return int(value)
            except ValueError:
                print("❌ 请输入有效的整数")
    
    def _get_input_bool(self, prompt: str, default: bool) -> bool:
        """获取布尔值输入"""
        while True:
            value = input(f"{prompt} (默认: {'是' if default else '否'}): ").strip().lower()
            if not value:
                return default
            if value in ['y', 'yes', '是', 'true', '1']:
                return True
            if value in ['n', 'no', '否', 'false', '0']:
                return False
            print("❌ 请输入 y/是 或 n/否")
    
    def _get_input_coords(self, prompt: str, default: str) -> tuple:
        """获取坐标输入，支持 x y z 格式"""
        while True:
            value = input(f"{prompt} (默认: {default}): ").strip()
            if not value:
                # 使用默认值
                coords = default.split()
                return int(coords[0]), int(coords[1]), int(coords[2])
            
            try:
                coords = value.split()
                if len(coords) != 3:
                    print("❌ 请输入3个坐标值，用空格分隔 (例如: 100 64 100)")
                    continue
                
                x, y, z = int(coords[0]), int(coords[1]), int(coords[2])
                return x, y, z
            except ValueError:
                print("❌ 坐标必须是整数，请重新输入")
            except Exception as e:
                print(f"❌ 输入格式错误: {e}")
                print("请使用格式: x y z (例如: 100 64 100)")
    
    async def _detailed_analysis(self, result: Dict[str, Any]):
        """详细分析查询结果"""
        print("\n" + "="*60)
        print("🔍 详细分析")
        print("="*60)
        
        # 首先检查整个结果的结构
        print(f"📋 结果结构概览:")
        print(f"  结果键: {list(result.keys())}")
        
        data = result.get("data", {})
        print(f"  数据键: {list(data.keys())}")
        
        # 打印完整的数据结构以了解实际格式
        print(f"\n📋 完整数据结构:")
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        
        # 检查是否有任何数据
        if not data:
            print("❌ 没有找到数据")
            return
        
        # 尝试识别不同的数据结构
        print(f"\n🔍 数据结构分析:")
        
        # 检查各种可能的数据字段
        possible_fields = [
            'blocks', 'compressedBlocks', 'blockCounts', 'queryRange',
            'startX', 'startY', 'startZ', 'endX', 'endY', 'endZ',
            'positions', 'blockData', 'results', 'items'
        ]
        
        found_fields = []
        for field in possible_fields:
            if field in data:
                found_fields.append(field)
                print(f"  ✅ 找到字段: {field} (类型: {type(data[field]).__name__})")
        
        if not found_fields:
            print(f"  ❌ 未找到预期的数据字段")
            print(f"  💡 实际字段: {list(data.keys())}")
        
        # 分析具体的数据内容
        print(f"\n📊 数据内容分析:")
        
        # 1. 检查是否有直接的方块数据
        if 'blocks' in data:
            blocks = data['blocks']
            print(f"  直接方块数据: {len(blocks)} 项")
            self._analyze_blocks_data(blocks)
        
        # 2. 检查压缩方块数据
        if 'compressedBlocks' in data:
            compressed_blocks = data['compressedBlocks']
            print(f"  压缩方块数据: {len(compressed_blocks)} 组")
            self._analyze_compressed_blocks(compressed_blocks)
        
        # 3. 检查方块计数
        if 'blockCounts' in data:
            block_counts = data['blockCounts']
            print(f"  方块计数数据: {type(block_counts).__name__}")
            self._analyze_block_counts(block_counts)
        
        # 4. 检查是否有位置数据
        if 'positions' in data:
            positions = data['positions']
            print(f"  位置数据: {len(positions)} 个位置")
        
        # 5. 检查查询范围
        range_fields = ['startX', 'startY', 'startZ', 'endX', 'endY', 'endZ']
        if any(field in data for field in range_fields):
            print(f"  查询范围字段:")
            for field in range_fields:
                if field in data:
                    print(f"    {field}: {data[field]}")
        
        # 6. 检查是否有其他可能包含数据的重要字段
        for key, value in data.items():
            if isinstance(value, (list, dict)) and len(value) > 0:
                if key not in ['blocks', 'compressedBlocks', 'blockCounts', 'positions']:
                    print(f"  📦 其他数据字段 '{key}': {type(value).__name__} 包含 {len(value)} 项")
                    if isinstance(value, list) and len(value) > 0:
                        print(f"    第一项类型: {type(value[0]).__name__}")
                        if isinstance(value[0], dict):
                            print(f"    第一项键: {list(value[0].keys())}")
        
        # 性能分析
        elapsed_ms = result.get("elapsed_ms", 0)
        print(f"\n⚡ 性能分析:")
        print(f"  查询耗时: {elapsed_ms}ms")
        
        # 生成总结
        print(f"\n📋 总结:")
        print(f"  查询状态: 成功")
        print(f"  数据字段数: {len(data)}")
        print(f"  主要数据类型: {', '.join(found_fields)}")
    
    def _analyze_blocks_data(self, blocks):
        """分析方块数据"""
        if not isinstance(blocks, list):
            print(f"    ⚠️ 方块数据不是列表格式: {type(blocks)}")
            return
        
        print(f"    方块详情 (共 {len(blocks)} 个):")
        block_types = {}
        y_levels = {}
        
        # 显示所有方块
        for i, block in enumerate(blocks):
            if isinstance(block, dict):
                block_type = block.get('name', 'unknown')
                position = block.get('position', {})
                can_see = block.get('canSee', 'N/A')
                print(f"      {i+1:3d}. {block_type:<15} 可见:{can_see} 位置:{position}")
                
                # 统计方块类型
                block_types[block_type] = block_types.get(block_type, 0) + 1
                
                # 统计Y轴分布
                if isinstance(position, dict):
                    y = position.get('y', 0)
                    y_levels[y] = y_levels.get(y, 0) + 1
        
        print(f"\n    方块类型统计: {len(block_types)} 种")
        print(f"    ┌{'─'*40}┬{'─'*10}┐")
        print(f"    │{'方块类型':<40}│{'数量':>10}│")
        print(f"    ├{'─'*40}┼{'─'*10}┤")
        for block_type, count in sorted(block_types.items(), key=lambda x: x[1], reverse=True):
            print(f"    │{block_type:<40}│{count:>10}│")
        print(f"    └{'─'*40}┴{'─'*10}┘")
        
        if y_levels:
            print(f"\n    Y轴分布: {len(y_levels)} 层")
            print(f"    ┌{'─'*10}┬{'─'*10}┐")
            print(f"    │{'Y坐标':<10}│{'方块数':>10}│")
            print(f"    ├{'─'*10}┼{'─'*10}┤")
            for y in sorted(y_levels.keys()):
                print(f"    │{y:<10}│{y_levels[y]:>10}│")
            print(f"    └{'─'*10}┴{'─'*10}┘")
    
    def _analyze_compressed_blocks(self, compressed_blocks):
        """分析压缩方块数据"""
        if not isinstance(compressed_blocks, list):
            print(f"    ⚠️ 压缩方块数据不是列表格式: {type(compressed_blocks)}")
            return
        
        total_blocks = 0
        visible_blocks = 0
        block_types = {}
        
        print(f"    压缩方块详情 (共 {len(compressed_blocks)} 组):")
        
        # 显示所有压缩方块组
        for i, block_group in enumerate(compressed_blocks):
            if isinstance(block_group, dict):
                block_type = block_group.get('name', 'unknown')
                can_see = block_group.get('canSee', False)
                positions = block_group.get('positions', [])
                
                print(f"      组 {i+1:3d}. {block_type:<15} 可见:{can_see} 位置数:{len(positions)}")
                
                # 显示前5个位置作为示例
                if positions:
                    sample_positions = positions[:5]
                    position_str = ", ".join([f"({p.get('x',0)},{p.get('y',0)},{p.get('z',0)})" for p in sample_positions])
                    if len(positions) > 5:
                        position_str += f" ... 还有 {len(positions) - 5} 个位置"
                    print(f"           位置示例: {position_str}")
                
                total_blocks += len(positions)
                if can_see:
                    visible_blocks += len(positions)
                
                block_types[block_type] = block_types.get(block_type, 0) + len(positions)
        
        print(f"\n    压缩方块统计:")
        print(f"    ┌{'─'*20}┬{'─'*10}┬{'─'*10}┬{'─'*10}┐")
        print(f"    │{'方块类型':<20}│{'总数量':>10}│{'可见数':>10}│{'不可见':>10}│")
        print(f"    ├{'─'*20}┼{'─'*10}┼{'─'*10}┼{'─'*10}┤")
        
        for block_type, total_count in sorted(block_types.items(), key=lambda x: x[1], reverse=True):
            # 计算可见数量（需要重新遍历，因为之前只统计了总数）
            visible_count = 0
            for block_group in compressed_blocks:
                if isinstance(block_group, dict) and block_group.get('name') == block_type:
                    if block_group.get('canSee', False):
                        visible_count += len(block_group.get('positions', []))
            
            invisible_count = total_count - visible_count
            print(f"    │{block_type:<20}│{total_count:>10}│{visible_count:>10}│{invisible_count:>10}│")
        
        print(f"    └{'─'*20}┴{'─'*10}┴{'─'*10}┴{'─'*10}┘")
        print(f"    总方块数: {total_blocks}")
        print(f"    可见方块: {visible_blocks} ({visible_blocks/total_blocks*100:.1f}%)" if total_blocks > 0 else "    可见方块: 0")
        print(f"    不可见方块: {total_blocks - visible_blocks} ({(total_blocks-visible_blocks)/total_blocks*100:.1f}%)" if total_blocks > 0 else "    不可见方块: 0")
    
    def _analyze_block_counts(self, block_counts):
        """分析方块计数数据"""
        if isinstance(block_counts, dict):
            total = sum(block_counts.values())
            print(f"    字典格式: {len(block_counts)} 种方块, 总计 {total} 个")
            print(f"    ┌{'─'*40}┬{'─'*10}┬{'─'*10}┐")
            print(f"    │{'方块类型':<40}│{'数量':>10}│{'百分比':>10}│")
            print(f"    ├{'─'*40}┼{'─'*10}┼{'─'*10}┤")
            for block_type, count in sorted(block_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total * 100) if total > 0 else 0
                print(f"    │{block_type:<40}│{count:>10}│{percentage:>9.1f}%│")
            print(f"    └{'─'*40}┴{'─'*10}┴{'─'*10}┘")
            
        elif isinstance(block_counts, list):
            print(f"    列表格式: {len(block_counts)} 项")
            total = 0
            dict_items = []
            list_items = []
            
            # 分析列表中的每一项
            for i, item in enumerate(block_counts):
                if isinstance(item, dict):
                    block_type = item.get('name', 'unknown')
                    count = item.get('count', 0)
                    dict_items.append((block_type, count))
                    total += count
                    print(f"      {i+1:3d}. {block_type:<20} 数量: {count}")
                else:
                    list_items.append((i+1, item))
                    print(f"      {i+1:3d}. {item}")
            
            print(f"\n    字典项统计:")
            if dict_items:
                print(f"    ┌{'─'*30}┬{'─'*10}┬{'─'*10}┐")
                print(f"    │{'方块类型':<30}│{'数量':>10}│{'百分比':>10}│")
                print(f"    ├{'─'*30}┼{'─'*10}┼{'─'*10}┤")
                for block_type, count in sorted(dict_items, key=lambda x: x[1], reverse=True):
                    percentage = (count / total * 100) if total > 0 else 0
                    print(f"    │{block_type:<30}│{count:>10}│{percentage:>9.1f}%│")
                print(f"    └{'─'*30}┴{'─'*10}┴{'─'*10}┘")
            
            print(f"\n    总计: {total} 个方块")
            
        else:
            print(f"    未知格式: {type(block_counts)}")
            print(f"    值: {block_counts}")
        
        # 2. 方块统计详细分析
        if "blockCounts" in data:
            block_counts = data["blockCounts"]
            print(f"\n📊 方块统计详细分析:")
            
            if isinstance(block_counts, dict):
                total_count = sum(block_counts.values())
                print(f"  总方块数: {total_count}")
                print(f"  方块种类: {len(block_counts)}")
                
                # 按数量排序
                sorted_blocks = sorted(block_counts.items(), key=lambda x: x[1], reverse=True)
                
                print(f"\n  📈 前10种最多方块:")
                for i, (block_type, count) in enumerate(sorted_blocks[:10], 1):
                    percentage = (count / total_count) * 100 if total_count > 0 else 0
                    print(f"    {i:2d}. {block_type:<20} {count:>6} ({percentage:5.1f}%)")
                
                # 稀有方块
                rare_blocks = [item for item in sorted_blocks if item[1] <= 3]
                if rare_blocks:
                    print(f"\n  💎 稀有方块 (≤3个):")
                    for i, (block_type, count) in enumerate(rare_blocks[:10], 1):
                        print(f"    {i}. {block_type}: {count}")
                
            elif isinstance(block_counts, list):
                print(f"  列表项数: {len(block_counts)}")
                total_count = 0
                for block_stat in block_counts:
                    if isinstance(block_stat, dict):
                        count = block_stat.get("count", 0)
                        total_count += count
                print(f"  估算总方块数: {total_count}")
        
        # 3. 压缩方块详细分析
        if "compressedBlocks" in data:
            compressed_blocks = data["compressedBlocks"]
            print(f"\n🗜️ 压缩方块详细分析:")
            print(f"  压缩组数: {len(compressed_blocks)}")
            
            # 分析可见性
            visible_blocks = 0
            invisible_blocks = 0
            block_type_groups = {}
            
            for block_data in compressed_blocks:
                if isinstance(block_data, dict):
                    block_type = block_data.get("name", "unknown")
                    can_see = block_data.get("canSee", False)
                    positions = block_data.get("positions", [])
                    
                    if can_see:
                        visible_blocks += len(positions)
                    else:
                        invisible_blocks += len(positions)
                    
                    if block_type not in block_type_groups:
                        block_type_groups[block_type] = {"visible": 0, "invisible": 0}
                    
                    if can_see:
                        block_type_groups[block_type]["visible"] += len(positions)
                    else:
                        block_type_groups[block_type]["invisible"] += len(positions)
            
            total_compressed = visible_blocks + invisible_blocks
            print(f"  总压缩方块数: {total_compressed}")
            print(f"  可见方块: {visible_blocks} ({visible_blocks/total_compressed*100:.1f}%)")
            print(f"  不可见方块: {invisible_blocks} ({invisible_blocks/total_compressed*100:.1f}%)")
            
            # 按可见性分析
            print(f"\n  👁️ 方块可见性分析:")
            for block_type, counts in sorted(block_type_groups.items(), 
                                          key=lambda x: x[1]["visible"] + x[1]["invisible"], 
                                          reverse=True)[:10]:
                total = counts["visible"] + counts["invisible"]
                visible_pct = counts["visible"] / total * 100 if total > 0 else 0
                print(f"    {block_type:<15} 可见:{counts['visible']:>3} 不可见:{counts['invisible']:>3} "
                      f"({visible_pct:>4.1f}% 可见)")
        
        # 4. 原始方块数据分析
        if "blocks" in data:
            blocks = data["blocks"]
            print(f"\n📦 原始方块数据分析:")
            print(f"  原始方块数: {len(blocks)}")
            
            # 分析Y轴分布
            y_distribution = {}
            for block in blocks:
                if isinstance(block, dict):
                    pos = block.get("position", {})
                    y = pos.get("y", 0)
                    y_distribution[y] = y_distribution.get(y, 0) + 1
            
            if y_distribution:
                print(f"  📊 Y轴分布:")
                for y in sorted(y_distribution.keys()):
                    print(f"    Y={y}: {y_distribution[y]} 个方块")
        
        # 5. 性能分析
        elapsed_ms = result.get("elapsed_ms", 0)
        print(f"\n⚡ 性能分析:")
        print(f"  查询耗时: {elapsed_ms}ms")
        
        # 计算效率指标
        if "blockCounts" in data:
            block_counts = data["blockCounts"]
            if isinstance(block_counts, dict):
                total_blocks = sum(block_counts.values())
                if elapsed_ms > 0:
                    blocks_per_ms = total_blocks / elapsed_ms
                    print(f"  查询效率: {blocks_per_ms:.1f} 方块/毫秒")
        
        # 6. 生成可视化报告
        print(f"\n📋 可视化报告:")
        self._generate_visual_report(data)
    
    def _generate_visual_report(self, data: Dict[str, Any]):
        """生成可视化报告"""
        try:
            # 简单的文本可视化
            if "blockCounts" in data:
                block_counts = data["blockCounts"]
                if isinstance(block_counts, dict):
                    # 创建一个简单的条形图
                    print(f"  📊 方块分布图:")
                    sorted_blocks = sorted(block_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                    
                    max_count = max(count for _, count in sorted_blocks) if sorted_blocks else 1
                    
                    for block_type, count in sorted_blocks:
                        bar_length = int((count / max_count) * 30)  # 最大30个字符
                        bar = "█" * bar_length
                        print(f"    {block_type:<12} {bar} {count}")
                    
                    print(f"    {'-' * 40}")
                    print(f"    总计: {sum(block_counts.values())} 个方块")
            
        except Exception as e:
            print(f"  生成可视化报告时出错: {e}")
    
    async def save_results_to_file(self, result: Dict[str, Any], filename: str = None):
        """保存结果到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"query_area_blocks_result_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 结果已保存到: {filename}")
            return True
        except Exception as e:
            print(f"\n❌ 保存文件失败: {e}")
            return False


async def main():
    """主函数"""
    print("query_area_blocks 工具测试脚本启动中...")
    
    tester = TestQueryAreaBlocks()
    
    try:
        # 连接到MCP服务器
        print("正在连接MCP服务器...")
        if not await tester.connect():
            print("连接MCP服务器失败，请检查:")
            print("1. Minecraft服务器是否正在运行")
            print("2. 是否开启了局域网模式（端口25565）")
            print("3. Maicraft MCP服务器是否已启动")
            return
        
        # 显示菜单
        while True:
            print("\n" + "="*60)
            print("🎮 query_area_blocks 测试工具")
            print("="*60)
            print("1. 运行所有预设测试")
            print("2. 自定义参数测试")
            print("3. 退出")
            print("-"*60)
            
            choice = input("请选择操作 (1-3): ").strip()
            
            if choice == "1":
                await tester.run_all_tests()
            elif choice == "2":
                await tester.interactive_test()
            elif choice == "3":
                print("退出程序")
                break
            else:
                print("❌ 无效选择，请输入1-3之间的数字")
        
    except Exception as e:
        print(f"程序运行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 断开连接
        await tester.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"程序启动失败: {e}")
        import traceback
        traceback.print_exc()