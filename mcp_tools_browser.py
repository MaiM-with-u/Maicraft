#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP工具浏览器脚本
用于获取和浏览现有的MCP工具及其参数信息
"""

import asyncio
import json
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from mcp_server.client import  global_mcp_client
    from utils.logger import get_logger
except ImportError as e:
    print(f"导入错误: {e}")  # 这里保持print，因为此时日志系统可能不可用
    print("请确保在项目根目录下运行此脚本")
    sys.exit(1)

# 设置日志系统并获取日志器
logger = get_logger("MCPToolsBrowser")


class MCPToolsBrowser:
    """MCP工具浏览器类"""
    
    def __init__(self):
        self.logger = get_logger("MCPToolsBrowser")

        self.connected = False
        
    async def connect(self) -> bool:
        """连接到MCP服务器"""
        try:
            # 使用新的连接管理功能
            self.connected = await global_mcp_client.connect(enable_auto_reconnect=False)

            if self.connected:
                self.logger.info("成功连接到MCP服务器")
                # 显示连接状态信息
                status = global_mcp_client.get_connection_status()
                self.logger.info(f"连接状态: {status['state']}")
                return True
            else:
                self.logger.error("连接MCP服务器失败")
                # 显示详细的错误信息
                status = global_mcp_client.get_connection_status()
                if status['health']['last_error']:
                    self.logger.error(f"错误详情: {status['health']['last_error']}")
                return False

        except Exception as e:
            self.logger.error(f"连接过程中发生错误: {e}")
            return False
    
    async def disconnect(self):
        """断开MCP连接"""
        if global_mcp_client and self.connected:
            await global_mcp_client.shutdown()
            self.connected = False
            self.logger.info("已断开MCP连接")

    def show_connection_status(self):
        """显示详细的连接状态信息"""
        if not global_mcp_client:
            print("MCP客户端未初始化")
            return

        status = global_mcp_client.get_connection_status()

        print("\n" + "="*60)
        print("MCP连接状态详情")
        print("="*60)
        print(f"当前状态: {status['state']}")
        print(f"是否连接: {'是' if status['is_connected'] else '否'}")

        print(f"\n健康状态:")
        print(f"  是否健康: {'是' if status['health']['is_healthy'] else '否'}")
        print(f"  连续失败次数: {status['health']['consecutive_failures']}")
        if status['health']['last_error']:
            print(f"  最后错误: {status['health']['last_error']}")
        if status['health']['last_success_time']:
            import time
            last_success = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['health']['last_success_time']))
            print(f"  最后成功时间: {last_success}")

        print(f"\n重连配置:")
        print(f"  重连启用: {'是' if status['reconnection']['enabled'] else '否'}")
        print(f"  最大重试次数: {status['reconnection']['max_attempts']}")
        print(f"  正在重连: {'是' if status['reconnection']['is_reconnecting'] else '否'}")

        print(f"\n配置文件: {status['config_file']}")
        print("="*60)
    
    async def get_tools_info(self) -> List[Dict[str, Any]]:
        """获取所有MCP工具的详细信息"""
        if not self.connected or not global_mcp_client:
            return []
        
        try:
            # 获取工具元数据
            tools_metadata = await global_mcp_client.get_tools_metadata()
            if not tools_metadata:
                return []
            
            tools_info = []
            for tool in tools_metadata:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description or "无描述",
                    "input_schema": tool.inputSchema or {},
                    "properties": {},
                    "required_fields": [],
                    "optional_fields": [],
                    "examples": []
                }
                
                # 解析输入模式
                if tool.inputSchema:
                    schema = tool.inputSchema
                    properties = schema.get("properties", {})
                    required_fields = schema.get("required", [])
                    
                    tool_info["properties"] = properties
                    tool_info["required_fields"] = required_fields
                    tool_info["optional_fields"] = [k for k in properties.keys() if k not in required_fields]
                    
                    # 生成示例参数
                    examples = self._generate_examples(properties, required_fields)
                    tool_info["examples"] = examples
                
                tools_info.append(tool_info)
            
            return tools_info
            
        except Exception as e:
            self.logger.error(f"获取工具信息失败: {e}")
            return []
    
    def _generate_examples(self, properties: Dict[str, Any], required_fields: List[str]) -> List[Dict[str, Any]]:
        """生成参数示例"""
        examples = []
        
        # 生成最小参数示例（只包含必需字段）
        if required_fields:
            min_example = {}
            for field in required_fields:
                if field in properties:
                    field_info = properties[field]
                    field_type = field_info.get("type", "string")
                    default_value = field_info.get("default")
                    
                    if default_value is not None:
                        min_example[field] = default_value
                    else:
                        min_example[field] = self._get_type_example(field_type)
            
            examples.append({
                "type": "最小参数（必需字段）",
                "params": min_example
            })
        
        # 生成完整参数示例（包含所有字段）
        if properties:
            full_example = {}
            for field, field_info in properties.items():
                field_type = field_info.get("type", "string")
                default_value = field_info.get("default")
                
                if default_value is not None:
                    full_example[field] = default_value
                else:
                    full_example[field] = self._get_type_example(field_type)
            
            examples.append({
                "type": "完整参数（所有字段）",
                "params": full_example
            })
        
        return examples
    
    def _get_type_example(self, field_type: str) -> Any:
        """根据字段类型生成示例值"""
        type_examples = {
            "string": "示例字符串",
            "integer": 42,
            "number": 3.14,
            "boolean": True,
            "array": ["示例1", "示例2"],
            "object": {"key": "value"}
        }
        return type_examples.get(field_type, "示例值")
    
    def display_tools_summary(self, tools_info: List[Dict[str, Any]]):
        """显示工具概览"""
        print("\n" + "="*80)
        print("MCP工具概览")
        print("="*80)
        print(f"总工具数量: {len(tools_info)}")
        
        if not tools_info:
            print("没有找到可用的MCP工具")
            return
        
        # 按类型分类工具
        query_tools = []
        action_tools = []
        
        for tool in tools_info:
            name = tool["name"].lower()
            if any(keyword in name for keyword in ["query", "get", "list", "find", "search"]):
                query_tools.append(tool)
            else:
                action_tools.append(tool)
        
        print(f"查询类工具: {len(query_tools)} 个")
        print(f"动作类工具: {len(action_tools)} 个")
        
        # 显示工具名称列表
        print("\n工具名称列表:")
        print("-" * 40)
        for i, tool in enumerate(tools_info, 1):
            tool_type = "查询" if tool in query_tools else "动作"
            print(f"{i:2d}. [{tool_type}] {tool['name']}")
    
    def display_tool_details(self, tool_info: Dict[str, Any]):
        """显示单个工具的详细信息"""
        print(f"\n{'='*60}")
        print(f"工具: {tool_info['name']}")
        print(f"{'='*60}")
        print(f"描述: {tool_info['description']}")
        
        # 显示参数信息
        properties = tool_info["properties"]
        required_fields = tool_info["required_fields"]
        optional_fields = tool_info["optional_fields"]
        
        if properties:
            print("\n参数信息:")
            print(f"必需参数 ({len(required_fields)} 个):")
            for field in required_fields:
                if field in properties:
                    self._display_field_info(field, properties[field], True)
            
            if optional_fields:
                print(f"\n可选参数 ({len(optional_fields)} 个):")
                for field in optional_fields:
                    if field in properties:
                        self._display_field_info(field, properties[field], False)
        else:
            print("\n参数信息: 无参数")
        
        # 显示示例
        examples = tool_info["examples"]
        if examples:
            print("\n参数示例:")
            for i, example in enumerate(examples, 1):
                print(f"\n{i}. {example['type']}:")
                params_json = json.dumps(example['params'], ensure_ascii=False, indent=2)
                print(f"   {params_json}")
    
    def _display_field_info(self, field_name: str, field_info: Dict[str, Any], is_required: bool):
        """显示字段信息"""
        field_type = field_info.get("type", "unknown")
        field_desc = field_info.get("description", "")
        default_value = field_info.get("default")
        
        required_mark = "[必需]" if is_required else "[可选]"
        print(f"  - {field_name} ({field_type}) {required_mark}")
        
        if field_desc:
            print(f"    描述: {field_desc}")
        
        if default_value is not None and not is_required:
            print(f"    默认值: {default_value}")
    
    async def display_interactive_menu(self, tools_info: List[Dict[str, Any]]):
        """显示交互式菜单（异步）"""
        while True:
            print("\n" + "-"*60)
            print("MCP工具浏览器 - 交互式菜单")
            print("-"*60)
            print("1. 显示工具概览")
            print("2. 浏览所有工具详细信息")
            print("3. 搜索工具")
            print("4. 按名称或编号查看工具")
            print("5. 执行工具并查看返回值")
            print("6. 导出工具信息到JSON文件")
            print("7. 显示连接状态详情")
            print("8. 退出")
            print("-"*60)
            
            try:
                choice = input("请选择操作 (1-8): ").strip()

                if choice == "1":
                    self.display_tools_summary(tools_info)

                elif choice == "2":
                    self.browse_all_tools(tools_info)

                elif choice == "3":
                    self.search_tools(tools_info)

                elif choice == "4":
                    await self.view_tool_by_name_or_id(tools_info)

                elif choice == "5":
                    await self.execute_tool_flow(tools_info)

                elif choice == "6":
                    self.export_tools_to_json(tools_info)

                elif choice == "7":
                    self.show_connection_status()

                elif choice == "8":
                    print("退出MCP工具浏览器")
                    break

                else:
                    print("无效选择，请输入1-8之间的数字")
                    
            except KeyboardInterrupt:
                print("\n\n用户中断，退出程序")
                break
            except Exception as e:
                print(f"操作过程中发生错误: {e}")
    
    def browse_all_tools(self, tools_info: List[Dict[str, Any]]):
        """浏览所有工具"""
        if not tools_info:
            print("没有可用的工具")
            return
        
        print(f"\n开始浏览 {len(tools_info)} 个工具...")
        
        for i, tool_info in enumerate(tools_info, 1):
            self.display_tool_details(tool_info)
            
            if i < len(tools_info):
                try:
                    input("\n按回车键继续查看下一个工具...")
                except KeyboardInterrupt:
                    print("\n用户中断浏览")
                    break
    
    def search_tools(self, tools_info: List[Dict[str, Any]]):
        """搜索工具"""
        if not tools_info:
            print("没有可用的工具")
            return
        
        search_term = input("请输入搜索关键词: ").strip().lower()
        if not search_term:
            print("搜索关键词不能为空")
            return
        
        matching_tools = []
        for tool in tools_info:
            # 在工具名称、描述和参数中搜索
            if (search_term in tool["name"].lower() or 
                search_term in tool["description"].lower() or
                any(search_term in field.lower() for field in tool["properties"].keys())):
                matching_tools.append(tool)
        
        if matching_tools:
            print(f"\n找到 {len(matching_tools)} 个匹配的工具:")
            for tool in matching_tools:
                print(f"  - {tool['name']}: {tool['description']}")
            
            # 显示详细信息
            for tool in matching_tools:
                self.display_tool_details(tool)
                try:
                    input("\n按回车键继续查看下一个匹配的工具...")
                except KeyboardInterrupt:
                    print("\n用户中断浏览")
                    break
        else:
            print(f"没有找到包含关键词 '{search_term}' 的工具")
    
    async def view_tool_by_name_or_id(self, tools_info: List[Dict[str, Any]]):
        """按名称或编号查看工具详细信息，并可选择执行工具"""
        if not tools_info:
            print("没有可用的工具")
            return
        
        while True:
            print(f"\n{'='*60}")
            print("按名称或编号查看工具")
            print(f"{'='*60}")
            print("支持以下输入方式:")
            print("1. 工具编号 (1-{})".format(len(tools_info)))
            print("2. 工具名称 (完整或部分)")
            print("3. 输入 'list' 显示所有工具列表")
            print("4. 输入 'back' 返回主菜单")
            print("5. 输入 'help' 显示帮助信息")
            print("-" * 60)
            
            # 显示工具列表供参考
            print("可用工具列表:")
            for i, tool in enumerate(tools_info, 1):
                tool_type = "查询" if any(keyword in tool["name"].lower() for keyword in ["query", "get", "list", "find", "search"]) else "动作"
                print(f"  {i:2d}. [{tool_type}] {tool['name']}")
            
            print("-" * 60)
            
            try:
                user_input = input("请输入工具编号、名称或命令: ").strip()
                
                if user_input.lower() == 'back':
                    print("返回主菜单...")
                    break
                elif user_input.lower() == 'list':
                    self.display_tools_summary(tools_info)
                    continue
                elif user_input.lower() == 'help':
                    self._show_view_tool_help()
                    continue
                elif not user_input:
                    print("❌ 输入不能为空，请重新输入")
                    continue
                
                # 尝试按编号查找
                if user_input.isdigit():
                    tool_id = int(user_input)
                    if 1 <= tool_id <= len(tools_info):
                        tool_info = tools_info[tool_id - 1]
                        print(f"\n✅ 找到工具 (编号 {tool_id}):")
                        self.display_tool_details(tool_info)
                        
                        # 询问是否继续查看其他工具
                        if not self._ask_continue_viewing():
                            break
                    else:
                        print(f"❌ 无效的工具编号，请输入 1-{len(tools_info)} 之间的数字")
                        continue
                
                # 按名称查找
                else:
                    matching_tools = self._find_tools_by_name(tools_info, user_input)
                    
                    if len(matching_tools) == 1:
                        # 只有一个匹配项，直接显示
                        tool_info = matching_tools[0]
                        print(f"\n✅ 找到工具: {tool_info['name']}")
                        self.display_tool_details(tool_info)
                        if self._ask_execute_tool():
                            await self._execute_single_tool(tool_info)
                        
                        # 询问是否继续查看其他工具
                        if not self._ask_continue_viewing():
                            break
                            
                    elif len(matching_tools) > 1:
                        # 多个匹配项，让用户选择
                        print(f"\n🔍 找到 {len(matching_tools)} 个匹配的工具:")
                        
                        # 显示匹配统计
                        query_count = sum(1 for tool in matching_tools if any(keyword in tool["name"].lower() for keyword in ["query", "get", "list", "find", "search"]))
                        action_count = len(matching_tools) - query_count
                        print(f"📊 匹配统计: 查询类 {query_count} 个, 动作类 {action_count} 个")
                        
                        for i, tool in enumerate(matching_tools, 1):
                            tool_type = "查询" if any(keyword in tool["name"].lower() for keyword in ["query", "get", "list", "find", "search"]) else "动作"
                            print(f"  {i}. [{tool_type}] {tool['name']}")
                        
                        choice_input = input("\n请选择要查看的工具编号: ").strip()
                        if choice_input.isdigit():
                            choice_id = int(choice_input)
                            if 1 <= choice_id <= len(matching_tools):
                                selected_tool = matching_tools[choice_id - 1]
                                print(f"\n✅ 查看工具: {selected_tool['name']}")
                                self.display_tool_details(selected_tool)

                                await self._execute_single_tool(selected_tool)
                                
                                # 询问是否继续查看其他工具
                                if not self._ask_continue_viewing():
                                    break
                            else:
                                print(f"❌ 无效的选择，请输入 1-{len(matching_tools)} 之间的数字")
                        else:
                            print("❌ 请输入有效的数字")
                            
                    else:
                        print(f"❌ 未找到名称包含 '{user_input}' 的工具")
                        print("💡 提示:")
                        print("  - 检查拼写是否正确")
                        print("  - 尝试使用部分名称")
                        print("  - 使用 'list' 命令查看所有可用工具")
                        print("  - 使用 'help' 命令查看帮助信息")
                        print(f"  - 当前共有 {len(tools_info)} 个可用工具")
                        continue
                        
            except KeyboardInterrupt:
                print("\n\n用户中断操作")
                break
            except Exception as e:
                print(f"❌ 操作过程中发生错误: {e}")
                continue
    
    def _show_view_tool_help(self):
        """显示查看工具的帮助信息"""
        print("\n" + "="*50)
        print("查看工具帮助信息")
        print("="*50)
        print("📋 支持的输入格式:")
        print("  • 数字: 直接输入工具编号 (如: 1, 5, 10)")
        print("  • 名称: 输入工具名称 (如: query_state, chat)")
        print("  • 部分名称: 输入名称的一部分 (如: query, mine)")
        print("  • 命令: 特殊命令")
        print("\n🔧 特殊命令:")
        print("  • list: 显示所有工具列表")
        print("  • back: 返回主菜单")
        print("  • help: 显示此帮助信息")
        print("\n💡 使用技巧:")
        print("  • 工具编号是最快的查找方式")
        print("  • 名称搜索支持模糊匹配")
        print("  • 可以连续查看多个工具")
        print("  • 随时可以返回主菜单")
        print("  • 支持中文输入 (是/否)")
        print("\n🚀 快速访问:")
        print("  • 输入 '1' 快速查看第一个工具")
        print("  • 输入 'query' 查找所有查询类工具")
        print("  • 输入 'mine' 查找挖掘相关工具")
        print("="*50)
    
    def _ask_continue_viewing(self) -> bool:
        """询问是否继续查看其他工具"""
        while True:
            try:
                continue_input = input("\n是否继续查看其他工具? (y/n): ").strip().lower()
                if continue_input in ['y', 'yes', '是', '']:
                    return True
                elif continue_input in ['n', 'no', '否']:
                    return False
                else:
                    print("请输入 y/是 或 n/否")
            except KeyboardInterrupt:
                print("\n用户中断，返回主菜单")
                return False
    
    def _find_tools_by_name(self, tools_info: List[Dict[str, Any]], search_term: str) -> List[Dict[str, Any]]:
        """根据名称查找工具（支持部分匹配和智能搜索）"""
        search_term = search_term.lower().strip()
        matching_tools = []
        
        # 精确匹配优先
        exact_matches = []
        # 部分匹配
        partial_matches = []
        # 描述匹配
        desc_matches = []
        
        for tool in tools_info:
            tool_name = tool["name"].lower()
            tool_desc = tool["description"].lower()
            
            # 精确匹配
            if search_term == tool_name:
                exact_matches.append(tool)
            # 开头匹配
            elif tool_name.startswith(search_term):
                partial_matches.append(tool)
            # 包含匹配
            elif search_term in tool_name:
                partial_matches.append(tool)
            # 描述匹配
            elif search_term in tool_desc:
                desc_matches.append(tool)
        
        # 按优先级排序：精确匹配 > 开头匹配 > 包含匹配 > 描述匹配
        matching_tools = exact_matches + partial_matches + desc_matches
        
        return matching_tools
    
    def export_tools_to_json(self, tools_info: List[Dict[str, Any]]):
        """导出工具信息到JSON文件"""
        if not tools_info:
            print("没有可用的工具信息可导出")
            return
        
        filename = input("请输入导出文件名 (默认: mcp_tools_info.json): ").strip()
        if not filename:
            filename = "mcp_tools_info.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(tools_info, f, ensure_ascii=False, indent=2)
            print(f"工具信息已成功导出到: {filename}")
        except Exception as e:
            print(f"导出失败: {e}")


    async def execute_tool_flow(self, tools_info: List[Dict[str, Any]]):
        """执行工具并查看返回值的完整流程"""
        if not tools_info:
            print("没有可用的工具")
            return
        
        print(f"\n{'='*60}")
        print("执行工具并查看返回值")
        print(f"{'='*60}")
        
        # 显示工具列表
        print("可用工具列表:")
        for i, tool in enumerate(tools_info, 1):
            tool_type = "查询" if any(keyword in tool["name"].lower() for keyword in ["query", "get", "list", "find", "search"]) else "动作"
            print(f"  {i:2d}. [{tool_type}] {tool['name']}")
        
        print("-" * 60)
        
        while True:
            try:
                user_input = input("请输入工具编号或名称 (输入 'back' 返回主菜单): ").strip()
                
                if user_input.lower() == 'back':
                    print("返回主菜单...")
                    break
                
                if not user_input:
                    print("❌ 输入不能为空，请重新输入")
                    continue
                
                # 尝试按编号查找
                if user_input.isdigit():
                    tool_id = int(user_input)
                    if 1 <= tool_id <= len(tools_info):
                        tool_info = tools_info[tool_id - 1]
                        await self._execute_single_tool(tool_info)
                        break
                    else:
                        print(f"❌ 无效的工具编号，请输入 1-{len(tools_info)} 之间的数字")
                        continue
                
                # 按名称查找
                else:
                    matching_tools = self._find_tools_by_name(tools_info, user_input)
                    
                    if len(matching_tools) == 1:
                        await self._execute_single_tool(matching_tools[0])
                        break
                    elif len(matching_tools) > 1:
                        print(f"\n🔍 找到 {len(matching_tools)} 个匹配的工具:")
                        for i, tool in enumerate(matching_tools, 1):
                            tool_type = "查询" if any(keyword in tool["name"].lower() for keyword in ["query", "get", "list", "find", "search"]) else "动作"
                            print(f"  {i}. [{tool_type}] {tool['name']}")
                        
                        choice_input = input("\n请选择要执行的工具编号: ").strip()
                        if choice_input.isdigit():
                            choice_id = int(choice_input)
                            if 1 <= choice_id <= len(matching_tools):
                                selected_tool = matching_tools[choice_id - 1]
                                await self._execute_single_tool(selected_tool)
                                break
                            else:
                                print(f"❌ 无效的选择，请输入 1-{len(matching_tools)} 之间的数字")
                        else:
                            print("❌ 请输入有效的数字")
                    else:
                        print(f"❌ 未找到名称包含 '{user_input}' 的工具")
                        print("💡 提示: 检查拼写或使用工具编号")
                        continue
                        
            except KeyboardInterrupt:
                print("\n\n用户中断操作")
                break
            except Exception as e:
                print(f"❌ 操作过程中发生错误: {e}")
                continue
    
    async def _execute_single_tool(self, tool_info: Dict[str, Any]):
        """执行单个工具并展示结果"""
        print(f"\n{'='*60}")
        print(f"执行工具: {tool_info['name']}")
        print(f"{'='*60}")
        print(f"描述: {tool_info['description']}")
        
        # 显示参数信息
        properties = tool_info["properties"]
        required_fields = tool_info["required_fields"]
        
        if properties:
            print("\n参数信息:")
            print(f"必需参数 ({len(required_fields)} 个):")
            for field in required_fields:
                if field in properties:
                    self._display_field_info(field, properties[field], True)
            
            optional_fields = [k for k in properties.keys() if k not in required_fields]
            if optional_fields:
                print(f"\n可选参数 ({len(optional_fields)} 个):")
                for field in optional_fields:
                    if field in properties:
                        self._display_field_info(field, properties[field], False)
        
        # 获取用户输入参数
        print(f"\n{'='*40}")
        print("参数输入")
        print(f"{'='*40}")
        
        # 生成示例参数
        examples = tool_info["examples"]
        if examples:
            print("参数示例:")
            for i, example in enumerate(examples, 1):
                print(f"\n{i}. {example['type']}:")
                params_json = json.dumps(example['params'], ensure_ascii=False, indent=2)
                print(f"   {params_json}")
        
        print("\n请输入参数 (JSON格式):")
        print("提示: 输入 'example' 使用第一个示例参数，输入 'min' 使用最小参数")
        
        while True:
            try:
                params_input = input("参数: ").strip()
                
                if params_input.lower() == 'example' and examples:
                    params_input = json.dumps(examples[0]['params'], ensure_ascii=False)
                    print(f"使用示例参数: {params_input}")
                elif params_input.lower() == 'min' and examples:
                    # 找到最小参数示例
                    min_example = None
                    for example in examples:
                        if "最小" in example['type'] or "必需" in example['type']:
                            min_example = example
                            break
                    if min_example:
                        params_input = json.dumps(min_example['params'], ensure_ascii=False)
                        print(f"使用最小参数: {params_input}")
                    else:
                        params_input = json.dumps(examples[0]['params'], ensure_ascii=False)
                        print(f"使用第一个示例参数: {params_input}")
                
                if not params_input:
                    print("❌ 参数不能为空，请重新输入")
                    continue
                
                # 解析JSON参数
                try:
                    if params_input.strip():
                        parsed_params = json.loads(params_input)
                    else:
                        parsed_params = {}
                    break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON格式错误: {e}")
                    print("请检查JSON格式，例如: {\"key\": \"value\"}")
                    continue
                    
            except KeyboardInterrupt:
                print("\n\n用户中断参数输入")
                return
            except Exception as e:
                print(f"❌ 参数输入错误: {e}")
                continue
        
        # 执行工具
        print(f"\n{'='*40}")
        print("执行工具中...")
        print(f"{'='*40}")
        
        try:

            
            # 使用工具适配器执行工具
            result = await global_mcp_client.call_tool_directly(tool_info['name'], parsed_params)
            
            print(f"执行结果: {result}")
            print(type(result))
            print(result.is_error)
            print(result.content)
            print(result.structured_content)
            print(result.data)
            
            # 展示执行结果
            await self._display_tool_result(tool_info['name'], result)
            
        except Exception as e:
            print(f"❌ 工具执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    async def _display_tool_result(self, tool_name: str, result):
        """展示工具执行结果"""
        print(f"\n{'='*60}")
        print(f"工具执行结果: {tool_name}")
        print(f"{'='*60}")
        
        if result.is_error:
            print("❌ 执行失败")
            if result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"错误信息: {content.text}")
        else:
            print("✅ 执行成功")
            print(json.dumps(result, ensure_ascii=False, indent=2, default=lambda o: getattr(o, '__dict__', str(o))))
        
        # 询问是否继续执行
        try:
            return True
        except KeyboardInterrupt:
            print("\n用户中断")
            return False

    def _safe_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """容错解析JSON文本为字典"""
        try:
            import dirtyjson
            return dirtyjson.loads(text)
        except Exception:
            try:
                return json.loads(text)
            except Exception as e:
                print(f"JSON解析失败: {e}")
                return None

    def _display_call_result(self, result: Any):
        """格式化展示 CallToolResult 返回值"""
        try:
            is_error = getattr(result, "is_error", False)
            print("\n" + ("结果: 失败" if is_error else "结果: 成功"))
            
            content = getattr(result, "content", None)
            if content:
                print("\n文本内容:")
                for i, item in enumerate(content, 1):
                    t = getattr(item, "type", "")
                    if t == "text":
                        txt = getattr(item, "text", "")
                        print(f"  [{i}] {txt}")
                    else:
                        # 其它类型简单序列化
                        try:
                            print(f"  [{i}] {json.dumps(item, ensure_ascii=False, default=lambda o: getattr(o, '__dict__', str(o)))}")
                        except Exception:
                            print(f"  [{i}] {item}")
            
            structured = getattr(result, "structured_content", None)
            if structured is not None:
                print("\n结构化数据:")
                print(json.dumps(structured, ensure_ascii=False, indent=2))
            
            data = getattr(result, "data", None)
            if data is not None:
                print("\n附加数据:")
                try:
                    print(json.dumps(data, ensure_ascii=False, indent=2))
                except Exception:
                    print(str(data))
        except Exception as e:
            print(f"展示结果时出错: {e}")


async def main():
    """主函数"""
    print("MCP工具浏览器启动中...")
    
    browser = MCPToolsBrowser()
    
    try:
        # 连接到MCP服务器
        print("正在连接MCP服务器...")
        if not await browser.connect():
            print("连接MCP服务器失败！")
            # 显示详细的连接状态和错误信息
            browser.show_connection_status()
            return
        
        # 获取工具信息
        print("正在获取MCP工具信息...")
        tools_info = await browser.get_tools_info()
        
        if not tools_info:
            print("没有找到可用的MCP工具")
            return
        
        # 显示工具概览
        browser.display_tools_summary(tools_info)
        
        # 显示交互式菜单
        await browser.display_interactive_menu(tools_info)
        
    except Exception as e:
        print(f"程序运行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 断开连接
        await browser.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"程序启动失败: {e}")
        import traceback
        traceback.print_exc()
