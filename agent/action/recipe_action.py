import json
import os
from typing import Any
from collections import Counter
from utils.logger import get_logger
from .name_map import ITEM_NAME_MAP


class RecipeFinder:
    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
        self.logger = get_logger("RecipeFinder")
        # 载入补充合成表
        self._supplement_recipes = self._load_supplement_recipes()
        
        # 物品别名映射表，将常用别名映射成标准名称
    
    def _normalize_item_name(self, item_name: Any) -> str:
        """
        将物品名称标准化，将别名映射成标准名称
        
        Args:
            item_name: 输入的物品名称（可能是别名）。允许任意类型，非字符串将被安全转换。
            
        Returns:
            标准化的物品名称
        """
        # 仅当为字符串时才进行 strip/lower，其他类型直接字符串化返回
        if isinstance(item_name, str):
            normalized = item_name.strip().lower()
        else:
            return str(item_name)
        
        # 查找映射
        if normalized in ITEM_NAME_MAP:
            return ITEM_NAME_MAP[normalized]
        
        # 如果没有找到映射，返回原名称
        return item_name
    
    async def find_recipe(self, item_name: str) -> str:
        """
        通过 MCP 工具获取物品的合成表并翻译成可读格式
        
        Args:
            item_name: 物品名称
            
        Returns:
            可读的合成表描述
        """
        if not self.mcp_client:
            return "错误：MCP 客户端未初始化"
        
        try:
            # 标准化物品名称
            normalized_name = self._normalize_item_name(item_name)
            if normalized_name != item_name:
                self.logger.info(f"[RecipeFinder] 物品名称标准化: '{item_name}' -> '{normalized_name}'")
            
            # 获取所有配方（MCP + 本地补充）
            all_recipes = []
            
            # 1. 获取无需工作台的配方
            no_table_recipes = await self._get_recipes_structured(normalized_name, False)
            if no_table_recipes:
                all_recipes.extend([(recipe, False) for recipe in no_table_recipes])
            
            # 2. 获取需要工作台的配方
            with_table_recipes = await self._get_recipes_structured(normalized_name, True)
            if with_table_recipes:
                all_recipes.extend([(recipe, True) for recipe in with_table_recipes])
            
            if not all_recipes:
                self.logger.warning(f"[RecipeFinder] 未找到 {item_name} 的合成表")
                return f"未找到 {item_name} 的合成表"
            
            # 格式化所有配方
            formatted_parts = []
            for recipe, use_table in all_recipes:
                if recipe:  # 过滤空配方
                    formatted = self._format_recipes(normalized_name, [recipe], use_table)
                    if formatted:
                        formatted_parts.append(formatted)
            
            if not formatted_parts:
                self.logger.warning(f"[RecipeFinder] 所有配方均为空")
                return f"未找到 {item_name} 的有效合成表"
            
            # 合并所有配方描述
            return "\n\n".join(formatted_parts)
            
        except Exception as e:
            error_msg = f"获取合成表时发生错误：{str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    async def _parse_recipe_result(self, result, item_name: str = "", use_crafting_table: bool = False) -> str:
        """
        解析 MCP 工具返回的合成表结果
        
        Args:
            result: MCP 工具返回的结果
            item_name: 物品名称，用于格式化输出
            
        Returns:
            可读的合成表描述
        """
        try:
            # 从结果中提取文本内容
            if hasattr(result, 'content') and result.content:
                result_text = ""
                for content in result.content:
                    if hasattr(content, 'text'):
                        result_text += content.text
                
                # 尝试解析 JSON 结果
                try:
                    result_json = json.loads(result_text)
                    
                    # 检查是否成功
                    if isinstance(result_json, dict):
                        if result_json.get("ok") is True:
                            data = result_json.get("data", {})
                            recipes = data.get("recipes", [])
                            # 提示可能在 data 或顶层
                            tips = data.get("tips") or result_json.get("tips", "")
                            
                            # 判断 recipes 是否为空或所有配方均无材料
                            def _is_empty_recipe(r: Any) -> bool:
                                if isinstance(r, dict):
                                    ings = r.get("ingredients")
                                    return isinstance(ings, list) and len(ings) == 0
                                if isinstance(r, list):
                                    return len(r) == 0
                                return False
                            if not recipes or all(_is_empty_recipe(r) for r in recipes):
                                return ""
                            
                            
                            # 生成可读的合成表描述
                            recipe_description = self._format_recipes(item_name, recipes, use_crafting_table)
                            
                            # 添加提示信息
                            if tips:
                                recipe_description += f"\n提示：{tips}"
                            
                            return recipe_description
                        else:
                            self.logger.error(f"获取合成表失败：\n{result_json}")
                            return ""
                    else:
                        return f"返回结果格式错误：{result_text}"
                        
                except json.JSONDecodeError:
                    # 如果不是 JSON 格式，直接返回文本内容
                    return f"合成表信息：{result_text}"
            else:
                return "未获取到合成表信息"
                
        except Exception as e:
            error_msg = f"解析合成表结果时发生错误：{str(e)}"
            self.logger.error(error_msg)
            return error_msg
    
    def _format_recipes(self, item_name: str, recipes: list, use_crafting_table: bool = False) -> str:
        """
        格式化合成表为可读格式
        
        Args:
            item_name: 物品名称
            recipes: 合成表列表
            
        Returns:
            格式化的合成表描述
        """
        if not recipes:
            return f"❌ 未找到 {item_name} 的合成表"
        
        formatted_recipes = []
        
        for i, recipe in enumerate(recipes, 1):
            self.logger.info(f"[RecipeFinder] 合成表：{recipe}")
            
            # 新格式：recipe 可能是 { "ingredients": [...], "requiresCraftingTable": true }
            if isinstance(recipe, dict) and "ingredients" in recipe:
                ingredients = recipe.get("ingredients", [])
            elif isinstance(recipe, list):
                ingredients = recipe
            else:
                # 回退：将其视为单一材料
                ingredients = [recipe]

            # 处理材料列表
            materials = []
            for material in ingredients:
                if isinstance(material, dict):
                    name_value = material.get("name", "未知材料")
                    name = self._normalize_item_name(name_value)
                    count = material.get("count", 1)
                else:
                    name = self._normalize_item_name(material)
                    count = 1

                if isinstance(count, (int, float)) and count > 1:
                    materials.append(f"{name} × {int(count)}")
                else:
                    materials.append(name)

            recipe_str = " + ".join(materials)
            formatted_recipes.append(f"{i}. {recipe_str}")
        
        # 构建最终的合成表描述
        recipe_text = f"\n查询得到：{item_name} 的合成表：\n"
        if use_crafting_table:
            recipe_text += "使用工作台合成：\n"
        recipe_text += "\n".join(formatted_recipes)
        
        return recipe_text
    
    async def _get_recipes_structured(self, item_name: str, use_crafting_table: bool = False) -> list:
        """
        查询并返回结构化的配方列表（每个配方为材料列表）。
        获取 MCP 配方与本地补充配方，进行去重合并。
        返回示例：[[{"name": "oak_log", "count": 1}], ...]
        """
        all_recipes: list = []
        # 获取 MCP 配方
        if self.mcp_client:
            try:
                args = {"item": item_name}
                if use_crafting_table:
                    args["useCraftingTable"] = True
                result = await self.mcp_client.call_tool_directly("query_recipe", args)
                if not result.is_error and getattr(result, "content", None):
                    text = "".join([getattr(c, "text", "") for c in result.content])
                    try:
                        data = json.loads(text)
                        if isinstance(data, dict) and data.get("ok"):
                            d = data.get("data", {})
                            rec = d.get("recipes", [])
                            # 统一成材料列表
                            normalized = []
                            for r in rec:
                                if isinstance(r, dict) and "ingredients" in r:
                                    normalized.append(r.get("ingredients", []))
                                elif isinstance(r, list):
                                    normalized.append(r)
                            all_recipes.extend(normalized)
                    except Exception:
                        pass
            except Exception:
                pass
        
        # 获取本地补充配方
        entry = self._supplement_recipes.get(item_name)
        if entry:
            key = "withTable" if use_crafting_table else "withoutTable"
            rec = entry.get(key, [])
            if isinstance(rec, list):
                all_recipes.extend(rec)
        
        # 去重合并（基于材料内容的哈希）
        def recipe_hash(recipe: list) -> str:
            if not isinstance(recipe, list):
                return str(recipe)
            # 标准化材料名称并排序，生成哈希
            materials = []
            for ing in recipe:
                if isinstance(ing, dict):
                    name = self._normalize_item_name(ing.get("name", ""))
                    count = int(ing.get("count", 1))
                    materials.append(f"{name}:{count}")
                else:
                    name = self._normalize_item_name(ing)
                    materials.append(f"{name}:1")
            return "|".join(sorted(materials))
        
        unique_recipes = []
        seen_hashes = set()
        for recipe in all_recipes:
            hash_val = recipe_hash(recipe)
            if hash_val not in seen_hashes:
                seen_hashes.add(hash_val)
                unique_recipes.append(recipe)
        
        self.logger.info(f"[RecipeFinder] 获取到 {item_name} 的配方：\n{unique_recipes}\n")
        
        return unique_recipes

    async def check_craft_feasibility(self, target_item: str, quantity: int, use_crafting_table: bool, inventory: list) -> tuple:
        """
        检查是否可以合成目标物品。
        Args:
            target_item: 目标物品名称
            quantity: 需要的数量
            use_crafting_table: 是否使用工作台
            inventory: 当前物品栏（参考 environment.py 的结构）
        Returns:
            (can_craft: bool, required: Dict[str,int], message: str)
        """
        if quantity <= 0:
            return True, {}, "数量为0，无需合成"

        target = self._normalize_item_name(target_item)

        # 统计物品栏数量
        bag = Counter()
        if isinstance(inventory, list):
            for it in inventory:
                if isinstance(it, dict):
                    name = self._normalize_item_name(it.get("name", ""))
                    if name:
                        bag[name] += int(it.get("count", 0))

        # 已有目标物品直接抵扣
        need_qty = max(0, int(quantity) - bag.get(target, 0))
        if need_qty == 0:
            return True, {}, f"背包已有 {target} x{quantity}，可以直接使用"

        # 递归展开所需基础材料
        visited = set()

        async def expand(name: str, qty: int, depth: int = 0) -> Counter:
            # 防止循环依赖
            key = (name, use_crafting_table)
            if depth > 10 or key in visited:
                c = Counter()
                c[name] += qty
                return c
            visited.add(key)

            recs = await self._get_recipes_structured(name, use_crafting_table)
            if not recs:
                c = Counter()
                c[name] += qty
                return c

            best: Counter | None = None
            for r in recs:
                accum = Counter()
                if isinstance(r, list):
                    for ing in r:
                        if isinstance(ing, dict):
                            ing_name = self._normalize_item_name(ing.get("name", "未知材料"))
                            ing_count = int(ing.get("count", 1)) * qty
                        else:
                            ing_name = self._normalize_item_name(ing)
                            ing_count = 1 * qty
                        sub = await expand(ing_name, ing_count, depth + 1)
                        accum.update(sub)
                if best is None or sum(accum.values()) < sum(best.values()):
                    best = accum
            return best or Counter()

        required_counter = await expand(target, need_qty)

        # 对照背包计算缺口
        missing = {}
        for name, cnt in required_counter.items():
            have = bag.get(name, 0)
            lack = max(0, cnt - have)
            if lack > 0:
                missing[name] = lack

        can_craft = len(missing) == 0

        # 生成说明文本
        lines = []
        lines.append(f"目标：{target} x{quantity}（使用工作台：{use_crafting_table}）")
        if need_qty != quantity:
            lines.append(f"已有：{bag.get(target, 0)}，仍需合成：{need_qty}")
        if required_counter:
            lines.append("所需基础材料：")
            for n, c in sorted(required_counter.items()):
                lines.append(f"  - {n} x{c}（背包有 {bag.get(n,0)}）")
        if missing:
            lines.append("缺少材料：")
            for n, c in sorted(missing.items()):
                lines.append(f"  - {n} x{c}")
        else:
            lines.append("材料充足，可以进行合成")

        return can_craft, dict(required_counter), "\n".join(lines)

    async def _plan_crafting_steps(self, target_item: str, quantity: int, has_table_nearby: bool, inventory: list) -> list[tuple[str, int, bool]]:
        """
        基于当前库存生成递归合成计划（简单可靠版本）。
        返回步骤列表 [(item, count, use_crafting_table)]。
        假设材料充足；请在调用前使用 check_craft_feasibility 校验。
        """
        bag = Counter()
        for it in inventory or []:
            if isinstance(it, dict):
                name = self._normalize_item_name(it.get("name", ""))
                if name:
                    bag[name] += int(it.get("count", 0))

        steps: list[tuple[str, int, bool]] = []


        async def choose_recipes(item: str, mode: bool) -> list:
            recs = await self._get_recipes_structured(item, mode)
            if not recs and mode is True:
                # 回退到无需工作台配方（在有工作台时也可用）
                recs = await self._get_recipes_structured(item, False)
            return recs

        async def try_craft_item(item: str, qty: int, depth: int = 0) -> bool:
            """尝试合成单个物品，返回是否成功"""
            # 递归深度限制，防止过深嵌套导致栈爆或死循环
            MAX_NESTING_DEPTH = 128
            if depth >= MAX_NESTING_DEPTH:
                self.logger.warning(f"[DEBUG] 递归深度达到上限 {MAX_NESTING_DEPTH}，停止并视为失败：{item} x{qty}")
                return False

            need = max(0, qty - bag.get(item, 0))
            if need <= 0:
                # 直接使用现有库存
                bag[item] -= qty
                return True
            
            self.logger.info(f"[DEBUG] 尝试合成 {item} x{need}，当前库存: {bag.get(item, 0)}")
            
            # 尝试找到可用配方
            recs = await choose_recipes(item, has_table_nearby)
            if not recs:
                # 如果优先模式没有配方，尝试另一种模式
                recs = await choose_recipes(item, not has_table_nearby)
            
            # 过滤掉空配方
            valid_recs = []
            for r in recs:
                ings = r if isinstance(r, list) else r.get("ingredients", [])
                if ings:  # 只保留有材料的配方
                    valid_recs.append(r)
            
            if not valid_recs:
                self.logger.warning(f"[DEBUG] {item} 没有找到任何有效配方，作为叶子材料处理")
                # 叶子材料，检查库存是否足够
                if bag.get(item, 0) >= qty:
                    self.logger.info(f"[DEBUG] {item} 在库存中存在，直接使用")
                    bag[item] -= qty
                    return True
                else:
                    self.logger.warning(f"[DEBUG] {item} 无法合成且库存不足，合成失败")
                    return False
            
            self.logger.info(f"[DEBUG] {item} 找到 {len(valid_recs)} 个有效配方")
            
            # 选成本最小的配方
            best = None
            best_cost = None
            for i, r in enumerate(valid_recs):
                ings = r if isinstance(r, list) else r.get("ingredients", [])
                cost = sum(int(ing.get("count", 1)) if isinstance(ing, dict) else 1 for ing in ings)
                self.logger.info(f"[DEBUG] 配方 {i+1}: 成本={cost}, 材料={ings}")
                if best is None or cost < best_cost:
                    best = ings
                    best_cost = cost
            
            self.logger.info(f"[DEBUG] 选择配方: {best}, 成本: {best_cost}")
            
            # 检查材料是否足够，不足时尝试递归合成
            can_craft = True
            self.logger.info(f"[DEBUG] 检查配方材料: {best}")
            for ing in best or []:
                if isinstance(ing, dict):
                    ing_name = self._normalize_item_name(ing.get("name", "未知材料"))
                    ing_count = int(ing.get("count", 1)) * need
                else:
                    ing_name = self._normalize_item_name(ing)
                    ing_count = 1 * need
                
                self.logger.info(f"[DEBUG] 检查材料 {ing_name}: 需要 {ing_count}, 库存 {bag.get(ing_name, 0)}")
                
                if bag.get(ing_name, 0) < ing_count:
                    # 材料不足，尝试递归合成
                    missing_qty = ing_count - bag.get(ing_name, 0)
                    self.logger.info(f"[DEBUG] 材料 {ing_name} 不足，尝试递归合成 {missing_qty} 个")
                    if not await try_craft_item(ing_name, missing_qty, depth + 1):
                        # 递归合成失败，说明这个材料无法合成
                        self.logger.warning(f"[DEBUG] 递归合成 {ing_name} 失败")
                        can_craft = False
                        break
                    else:
                        self.logger.info(f"[DEBUG] 递归合成 {ing_name} 成功")
                else:
                    self.logger.info(f"[DEBUG] 材料 {ing_name} 充足")
            
            if can_craft:
                # 材料足够，记录合成步骤
                actual_mode = has_table_nearby
                if not await choose_recipes(item, has_table_nearby):
                    actual_mode = not has_table_nearby
                
                self.logger.info(f"[DEBUG] 配方可行，记录合成步骤: {item} x{need} (模式: {actual_mode})")
                steps.append((item, need, actual_mode))
                
                # 消耗材料
                for ing in best or []:
                    if isinstance(ing, dict):
                        ing_name = self._normalize_item_name(ing.get("name", "未知材料"))
                        ing_count = int(ing.get("count", 1)) * need
                    else:
                        ing_name = self._normalize_item_name(ing)
                        ing_count = 1 * need
                    bag[ing_name] -= ing_count
                    self.logger.info(f"[DEBUG] 消耗材料 {ing_name}: -{ing_count}")
                
                # 增加合成后的物品
                bag[item] += need
                self.logger.info(f"[DEBUG] 增加物品 {item}: +{need}")
                return True
            
            # 如果当前配方无法合成，尝试其他配方
            if len(valid_recs) > 1:
                self.logger.info(f"[DEBUG] 尝试替代配方...")
                for alt_recipe in valid_recs:
                    if alt_recipe == best:
                        continue  # 跳过已经尝试过的配方
                    
                    ings = alt_recipe if isinstance(alt_recipe, list) else alt_recipe.get("ingredients", [])
                    if not ings:
                        continue
                    
                    self.logger.info(f"[DEBUG] 尝试替代配方: {ings}")
                    
                    # 检查替代配方的材料
                    alt_can_craft = True
                    for ing in ings:
                        if isinstance(ing, dict):
                            ing_name = self._normalize_item_name(ing.get("name", "未知材料"))
                            ing_count = int(ing.get("count", 1)) * need
                        else:
                            ing_name = self._normalize_item_name(ing)
                            ing_count = 1 * need
                        
                        self.logger.info(f"[DEBUG] 替代配方材料 {ing_name}: 需要 {ing_count}, 库存 {bag.get(ing_name, 0)}")
                        
                        if bag.get(ing_name, 0) < ing_count:
                            # 尝试递归合成
                            missing_qty = ing_count - bag.get(ing_name, 0)
                            self.logger.info(f"[DEBUG] 替代配方材料 {ing_name} 不足，尝试递归合成 {missing_qty} 个")
                            if not await try_craft_item(ing_name, missing_qty, depth + 1):
                                self.logger.warning(f"[DEBUG] 替代配方递归合成 {ing_name} 失败")
                                alt_can_craft = False
                                break
                            else:
                                self.logger.info(f"[DEBUG] 替代配方递归合成 {ing_name} 成功")
                        else:
                            self.logger.info(f"[DEBUG] 替代配方材料 {ing_name} 充足")
                    
                    if alt_can_craft:
                        # 替代配方可行，记录合成步骤
                        actual_mode = has_table_nearby
                        if not await choose_recipes(item, has_table_nearby):
                            actual_mode = not has_table_nearby
                        
                        self.logger.info(f"[DEBUG] 替代配方可行，记录合成步骤: {item} x{need} (模式: {actual_mode})")
                        steps.append((item, need, actual_mode))
                        
                        # 消耗材料
                        for ing in ings:
                            if isinstance(ing, dict):
                                ing_name = self._normalize_item_name(ing.get("name", "未知材料"))
                                ing_count = int(ing.get("count", 1)) * need
                            else:
                                ing_name = self._normalize_item_name(ing)
                                ing_count = 1 * need
                            bag[ing_name] -= ing_count
                            self.logger.info(f"[DEBUG] 消耗替代配方材料 {ing_name}: -{ing_count}")
                        
                        # 增加合成后的物品
                        bag[item] += need
                        self.logger.info(f"[DEBUG] 增加物品 {item}: +{need}")
                        return True
            else:
                self.logger.info(f"[DEBUG] 没有替代配方可尝试")
            
            self.logger.warning(f"[DEBUG] {item} 所有配方都无法合成")
            return False

        # 主循环：不断尝试合成直到完成或达到阈值
        target_norm = self._normalize_item_name(target_item)

        if await try_craft_item(target_norm, quantity, 0):
            return steps

    def _load_supplement_recipes(self) -> dict:
        """从同目录的 extra_recipes.json 载入补充合成表。失败时返回空字典。"""
        try:
            current_dir = os.path.dirname(__file__)
            file_path = os.path.join(current_dir, "extra_recipes.json")
            if not os.path.exists(file_path):
                return {}
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            self.logger.error(f"加载补充合成表失败：{e}")
        return {}

    def _format_recipes_from_supplement(self, normalized_name: str) -> str:
        """当 MCP 无结果时，从补充表生成格式化文本。"""
        entry = self._supplement_recipes.get(normalized_name)
        if not entry:
            return ""

        parts = []
        # without table
        recipes_without = entry.get("withoutTable", [])
        if recipes_without:
            text = self._format_recipes(normalized_name, recipes_without, False)
            parts.append(text)
        # with table
        recipes_with = entry.get("withTable", [])
        if recipes_with:
            text = self._format_recipes(normalized_name, recipes_with, True)
            parts.append(text)

        return "\n\n".join([p for p in parts if p])

    def set_mcp_client(self, mcp_client):
        """设置 MCP 客户端实例"""
        self.mcp_client = mcp_client

    async def craft_item_smart(self, item: str, count: int, inventory: list, block_position: Any) -> tuple[bool, str]:
        """
        智能合成：根据周围是否有工作台与材料情况，决定合成与返回总结。
        返回 (是否成功, 总结字符串)
        """
        try:
            if not self.mcp_client:
                return False, "错误：MCP 客户端未初始化"

            item_norm = self._normalize_item_name(item)

            # 检查周围10格是否有工作台
            from agent.block_cache.block_cache import global_block_cache
            has_table_nearby = False
            if block_position is not None:
                blocks = global_block_cache.get_blocks_in_range(block_position.x, block_position.y, block_position.z, 10)
                for b in blocks:
                    if b.block_type == "crafting_table":
                        has_table_nearby = True
                        break

            # 函数：判断某模式下是否存在配方
            async def has_recipe(use_table: bool) -> bool:
                recs = await self._get_recipes_structured(item_norm, use_table)
                # 过滤空配方
                def _is_empty(r: Any) -> bool:
                    if isinstance(r, dict):
                        ings = r.get("ingredients")
                        return isinstance(ings, list) and len(ings) == 0
                    if isinstance(r, list):
                        return len(r) == 0
                    return False
                return bool(recs and not all(_is_empty(r) for r in recs))

            # 工具结果解析器：返回 (ok, readable_msg)
            def parse_craft_result_text(result_text: Any, prefix: str) -> tuple[bool, str]:
                try:
                    payload = json.loads(result_text) if isinstance(result_text, str) else result_text
                except Exception:
                    payload = result_text

                if isinstance(payload, dict):
                    ok_flag = bool(payload.get("ok") is True)
                    if ok_flag:
                        data_obj = payload.get("data", {}) or {}
                        item_name = data_obj.get("item", item_norm)
                        count_val = data_obj.get("count", count)
                        return True, f"{prefix}成功合成：{item_name} x{count_val}"
                    # 失败细节
                    err_code = payload.get("error_code") or payload.get("code")
                    err_msg = payload.get("error_message") or payload.get("error") or payload.get("message")
                    req_id = payload.get("request_id") or payload.get("requestId")
                    detail_parts = ["合成失败"]
                    if err_msg:
                        detail_parts.append(f"原因：{err_msg}")
                    if err_code:
                        detail_parts.append(f"错误码：{err_code}")
                    if req_id:
                        detail_parts.append(f"请求ID：{req_id}")
                    return False, f"{prefix}{'；'.join(detail_parts)}"

                # 非预期格式
                return False, f"{prefix}合成失败：返回格式异常：{str(payload)}"

            # 分支 1：附近没有工作台
            if not has_table_nearby:
                has_recipe_no_table = await has_recipe(False)
                if has_recipe_no_table:
                    can, required, msg = await self.check_craft_feasibility(item_norm, count, False, inventory)
                    if can:
                        # 生成并逐步执行合成路径（无需工作台优先）
                        steps = await self._plan_crafting_steps(item_norm, count, False, inventory)
                        logs: list[str] = ["附近无工作台。按步骤合成："]
                        for step_item, step_count, step_use_table in steps:
                            if step_use_table:
                                args = {"item": step_item, "count": step_count}
                            else:
                                args = {"item": step_item, "count": step_count, "without_crafting_table": True}
                            call_result = await self.mcp_client.call_tool_directly("craft_item", args)
                            result_text = "".join([getattr(c, "text", "") for c in getattr(call_result, "content", [])]) if hasattr(call_result, 'content') else str(call_result)
                            ok_step, detail = parse_craft_result_text(result_text, "")
                            logs.append(f"- {('工作台' if step_use_table else '手工')} {step_item} x{step_count} -> {'成功' if ok_step else detail}")
                            if not ok_step:
                                return False, "\n".join(logs + ["\n" + msg])
                        return True, "\n".join(logs + ["\n" + msg])
                    else:
                        return False, f"附近无工作台，但存在无需工作台的配方；材料不足。\n{msg}"
                else:
                    # 没有无需工作台的配方
                    has_recipe_with_table = await has_recipe(True)
                    if has_recipe_with_table:
                        can_with, required_with, msg_with = await self.check_craft_feasibility(item_norm, count, True, inventory)
                        if can_with:
                            return False, f"附近无工作台；若找到工作台即可合成。\n{msg_with}"
                        else:
                            return False, f"附近无工作台；即便在工作台也材料不足，需要收集材料并找到工作台。\n{msg_with}"
                    else:
                        return False, "附近无工作台；此物品无可用合成表。"

            # 分支 2：附近有工作台
            else:
                has_recipe_with_table = await has_recipe(True)
                if has_recipe_with_table:
                    can_with, required_with, msg_with = await self.check_craft_feasibility(item_norm, count, True, inventory)
                    if can_with:
                        # 生成并逐步执行合成路径（优先使用工作台配方）
                        steps = await self._plan_crafting_steps(item_norm, count, True, inventory)
                        logs: list[str] = ["附近有工作台。按步骤合成："]
                        for step_item, step_count, step_use_table in steps:
                            args = {"item": step_item, "count": step_count}
                            call_result = await self.mcp_client.call_tool_directly("craft_item", args)
                            result_text = "".join([getattr(c, "text", "") for c in getattr(call_result, "content", [])]) if hasattr(call_result, 'content') else str(call_result)
                            ok_step, detail = parse_craft_result_text(result_text, "")
                            logs.append(f"- {('工作台' if step_use_table else '手工')} {step_item} x{step_count} -> {'成功' if ok_step else detail}")
                            if not ok_step:
                                return False, "\n".join(logs + ["\n" + msg_with])
                        return True, "\n".join(logs + ["\n" + msg_with])
                    else:
                        return False, f"附近有工作台，但材料不足。\n{msg_with}"
                else:
                    return False, "附近有工作台，但该物品无可用合成表，无法合成"

        except Exception as e:
            self.logger.error(f"craft_item_smart 发生异常：{e}")
            return False, f"执行异常：{e}"
    
    

recipe_finder = RecipeFinder()