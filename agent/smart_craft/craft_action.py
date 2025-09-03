import json
import os
from typing import Any, List
from collections import Counter
from utils.logger import get_logger
from .name_map import ITEM_NAME_MAP
from agent.environment.inventory_utils import Item
from .recipe_class import RawRecipe
from mcp_server.client import global_mcp_client


class RecipeFinder:
    def __init__(self):
        self.mcp_client = global_mcp_client
        self.logger = get_logger("RecipeFinder")
        
        # 物品别名映射表，将常用别名映射成标准名称
        self.conversion_pairs = self._load_conversion_pairs()

    def _load_conversion_pairs(self) -> dict:
        """
        加载转化对配置：
        文件结构示例：
        {
          "conversion_pairs": [
            {"items": ["coal", "coal_block"], "priority": "coal", "ratio": {"coal_to_coal_block": 0.111...}}
          ]
        }
        返回结构：{ item_name: {"pair_items": [...], "priority": str, "ratio": dict } }
        """
        try:
            config_path = os.path.join(os.path.dirname(__file__), "conversion_pairs.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                out: dict = {}
                for pair in (data.get("conversion_pairs") or []):
                    items = pair.get("items") or []
                    priority = pair.get("priority")
                    ratio = pair.get("ratio") or {}
                    for nm in items:
                        out[self._normalize_item_name(nm)] = {
                            "pair_items": [self._normalize_item_name(x) for x in items],
                            "priority": self._normalize_item_name(priority) if priority else None,
                            "ratio": ratio,
                        }
                return out
        except Exception as e:
            self.logger.warning(f"加载转化对配置失败: {e}")
        return {}

    def _is_priority_item(self, item_name: str) -> bool:
        item_norm = self._normalize_item_name(item_name)
        info = self.conversion_pairs.get(item_norm)
        return bool(info and info.get("priority") == item_norm)

    def _get_pair_items(self, item_name: str) -> set[str]:
        item_norm = self._normalize_item_name(item_name)
        info = self.conversion_pairs.get(item_norm) or {}
        return set(info.get("pair_items") or [])
    
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
    

    async def _get_raw_recipes(self, item_name: str, use_crafting_table: bool = False) -> list[RawRecipe]:
        """
        使用 query_raw_recipe 查询并返回 RawRecipe 列表（保留 inShape/ingredients 等结构）。
        """
        if not self.mcp_client:
            return []
        try:
            args = {"item": item_name, "useCraftingTable": bool(use_crafting_table)}
            result = await self.mcp_client.call_tool_directly("query_raw_recipe", args)
            if getattr(result, "is_error", False) or not getattr(result, "content", None):
                return []
            text = "".join([getattr(c, "text", "") for c in result.content])
            try:
                payload = json.loads(text) if text else {}
            except Exception:
                payload = {}
            rr_list = RawRecipe.from_query_raw_recipe(payload)
            # 若工具未标注 requiresTable，则用调用参数补齐
            for r in rr_list:
                if getattr(r, "requires_table", None) is None:
                    r.requires_table = bool(use_crafting_table)
            return rr_list
        except Exception:
            return []

    @staticmethod
    def _raw_recipe_to_tool_payload(rr: RawRecipe) -> dict:
        """
        将 RawRecipe 转换为 craft_with_recipe 所需的 recipe 对象结构。
        仅包含 id/metadata/count 字段。
        """
        def item_to_payload(item) -> dict | None:
            if not item:
                return None
            return {
                "id": getattr(item, "id", None),
                "metadata": getattr(item, "metadata", None),
                "count": getattr(item, "count", 1),
                "name": getattr(item, "name", None),
            }

        def shape_to_payload(shape):
            if not shape:
                return None
            out = []
            for row in shape:
                new_row = []
                for cell in row:
                    new_row.append(None if cell is None else item_to_payload(cell))
                out.append(new_row)
            return out

        payload = {
            "result": item_to_payload(getattr(rr, "result", None)),
            "requiresTable": bool(getattr(rr, "requires_table", False)),
        }
        
        # 只有当字段存在且不为空时才添加到payload中
        if getattr(rr, "in_shape", None):
            payload["inShape"] = shape_to_payload(rr.in_shape)
        if getattr(rr, "out_shape", None):
            payload["outShape"] = shape_to_payload(rr.out_shape)
        if getattr(rr, "ingredients", None) and len(rr.ingredients) > 0:
            payload["ingredients"] = [item_to_payload(x) for x in rr.ingredients]
        if getattr(rr, "delta", None) and len(rr.delta) > 0:
            payload["delta"] = [item_to_payload(x) for x in rr.delta]
        
        return payload
    
    
    async def _get_missing_materials_info(self, target_item: str, quantity: int, has_table_nearby: bool, inventory: List[Item]) -> str:
        """
        获取合成失败时的具体材料缺失信息，分析所有可能的合成配方
        """
        try:
            # 构建库存计数器
            bag = Counter()
            for it in inventory or []:
                name = self._normalize_item_name(it.name)
                bag[name] += int(it.count)

            # 获取所有可能的配方（包括工作台和手工配方）
            all_recipes = []
            
            # 获取工作台配方
            if has_table_nearby:
                table_recipes = await self._get_raw_recipes(target_item, True)
                all_recipes.extend([(rr, True) for rr in table_recipes])
            
            # 获取手工配方
            hand_recipes = await self._get_raw_recipes(target_item, False)
            all_recipes.extend([(rr, False) for rr in hand_recipes])
            
            if not all_recipes:
                return "该物品无可用合成配方"
            
            # 分析所有配方
            recipe_analysis = []
            
            for rr, use_table in all_recipes:
                # 提取材料信息
                def extract_ings(rr: RawRecipe):
                    empty_names = {"empty", "air", ""}
                    if getattr(rr, "ingredients", None):
                        lst = []
                        for x in rr.ingredients:
                            nm = (getattr(x, "name", "") or "").strip().lower()
                            if nm in empty_names:
                                continue
                            cnt = abs(int(getattr(x, "count", 1)))
                            if cnt <= 0:
                                continue
                            lst.append({"name": getattr(x, "name", "未知材料"), "count": cnt})
                        return lst
                    # 从 in_shape 聚合
                    in_shape = getattr(rr, "in_shape", None)
                    if not in_shape:
                        return []
                    tally = {}
                    for row in in_shape:
                        for cell in row:
                            if cell is None:
                                continue
                            nm = (getattr(cell, "name", "") or "").strip().lower()
                            if nm in empty_names:
                                continue
                            key = (cell.id, cell.name, cell.metadata)
                            if key not in tally:
                                tally[key] = {"name": cell.name, "count": 0}
                            tally[key]["count"] += max(1, abs(int(getattr(cell, "count", 1))))
                    return [{"name": v["name"], "count": v["count"]} for v in tally.values()]
                
                ings = extract_ings(rr)
                if not ings:
                    continue
                
                # 计算需要的材料数量
                per_batch_out = int(getattr(getattr(rr, "result", None), "count", 1)) if getattr(rr, "result", None) else 1
                if per_batch_out <= 0:
                    per_batch_out = 1
                import math
                batches_needed = int(math.ceil(quantity / per_batch_out))
                
                # 检查每种材料
                missing_materials = []
                total_needed = {}
                
                for ing in ings:
                    if isinstance(ing, dict):
                        ing_name = self._normalize_item_name(ing.get("name", "未知材料"))
                        ing_count = int(ing.get("count", 1)) * batches_needed
                    else:
                        ing_name = self._normalize_item_name(ing)
                        ing_count = 1 * batches_needed
                    
                    # 累计总需求
                    if ing_name not in total_needed:
                        total_needed[ing_name] = 0
                    total_needed[ing_name] += ing_count
                    
                    available = bag.get(ing_name, 0)
                    if available < ing_count:
                        missing = ing_count - available
                        missing_materials.append(f"{ing_name} x{missing}")
                
                # 记录这个配方的分析结果
                recipe_type = "工作台" if use_table else "手工"
                if missing_materials:
                    recipe_analysis.append({
                        "type": recipe_type,
                        "missing": missing_materials,
                        "total_needed": total_needed,
                        "per_batch": per_batch_out,
                        "batches": batches_needed
                    })
                else:
                    recipe_analysis.append({
                        "type": recipe_type,
                        "missing": [],
                        "total_needed": total_needed,
                        "per_batch": per_batch_out,
                        "batches": batches_needed,
                        "status": "材料充足"
                    })
            
            # 生成综合报告
            if not recipe_analysis:
                return "配方存在但无法解析材料需求"
            
            # 检查是否有材料充足的配方
            feasible_recipes = [r for r in recipe_analysis if r.get("status") == "材料充足"]
            if feasible_recipes:
                return "存在材料充足的配方，但合成计划生成失败"
            
            # 生成所有缺少材料的汇总报告
            all_missing = {}
            for recipe in recipe_analysis:
                for missing_item in recipe["missing"]:
                    # 解析缺少的物品名称和数量
                    if " x" in missing_item:
                        item_name, count_str = missing_item.rsplit(" x", 1)
                        try:
                            count = int(count_str)
                            if item_name not in all_missing:
                                all_missing[item_name] = 0
                            all_missing[item_name] = max(all_missing[item_name], count)
                        except ValueError:
                            all_missing[missing_item] = 1
                    else:
                        all_missing[missing_item] = 1
            
            # 生成详细报告
            report_lines = ["合成失败分析："]
            
            # 添加总体缺少材料汇总
            # if all_missing:
            #     missing_summary = [f"{item} x{count}" for item, count in all_missing.items()]
            #     report_lines.append(f"总体缺少材料：{', '.join(missing_summary)}")
            
            # 添加各配方的详细分析
            for i, recipe in enumerate(recipe_analysis, 1):
                # report_lines.append(f"\n配方{i}（{recipe['type']}）：")
                report_lines.append(f"\n配方{i}：")
                if recipe.get("status") == "材料充足":
                    # report_lines.append(f"  ✓ 材料充足，每批次产出：{recipe['per_batch']}，需要批次：{recipe['batches']}")
                    report_lines.append("  ✓ 材料充足")
                else:
                    report_lines.append(f"  ✗ 缺少材料：{', '.join(recipe['missing'])}")
                    # report_lines.append(f"    每批次产出：{recipe['per_batch']}，需要批次：{recipe['batches']}")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            return f"分析材料需求时出错：{e}"
    
    
    async def _plan_crafting_steps(self, target_item: str, quantity: int, has_table_nearby: bool, inventory: List[Item]) -> list[tuple[str, int, bool, dict]]:
        """
        基于当前库存生成递归合成计划（简单可靠版本）。
        返回步骤列表 [(item, count, use_crafting_table)]。
        假设材料充足；请在调用前使用 check_craft_feasibility 校验。
        """
        if not inventory:
            self.logger.warning("[DEBUG] 库存为空，无法生成合成计划")
            return []

        steps: list[tuple[str, int, bool, dict]] = []


        async def choose_recipes(item: str, mode: bool) -> list[RawRecipe]:
            recs = await self._get_raw_recipes(item, mode)
            self.logger.info(f"[DEBUG] 获取原始配方：item={item}, mode={'table' if mode else 'hand'}, count={len(recs)}")
            if not recs and mode is True:
                # 回退到无需工作台配方（在有工作台时也可用）
                recs = await self._get_raw_recipes(item, False)
                self.logger.info(f"[DEBUG] 回退到无需工作台配方，count={len(recs)}")
            return recs

        async def try_craft_item(item: str, qty: int, depth: int = 0) -> bool:
            """尝试合成单个物品，返回是否成功"""
            # 递归深度限制，防止过深嵌套导致栈爆或死循环
            MAX_NESTING_DEPTH = 128
            if depth >= MAX_NESTING_DEPTH:
                self.logger.warning(f"[DEBUG] 递归深度达到上限 {MAX_NESTING_DEPTH}，停止并视为失败：{item} x{qty}")
                return False

            # 忽略现有库存，始终按请求数量进行合成
            need = int(qty)
            
            self.logger.info(f"[DEBUG] 尝试合成 {item} x{need}（忽略现有库存）")
            
            # 尝试找到可用配方
            recs = await choose_recipes(item, has_table_nearby)
            if not recs:
                # 如果优先模式没有配方，尝试另一种模式
                recs = await choose_recipes(item, not has_table_nearby)
            
            # 过滤掉空配方（只保留有 ingredients 或 inShape 的）
            def extract_ings(rr: RawRecipe):
                empty_names = {"empty", "air", ""}
                if getattr(rr, "ingredients", None):
                    lst = []
                    for x in rr.ingredients:
                        nm = (getattr(x, "name", "") or "").strip().lower()
                        if nm in empty_names:
                            continue
                        cnt = abs(int(getattr(x, "count", 1)))
                        if cnt <= 0:
                            continue
                        lst.append({"name": getattr(x, "name", "未知材料"), "count": cnt})
                    return lst
                # 从 in_shape 聚合
                in_shape = getattr(rr, "in_shape", None)
                if not in_shape:
                    return []
                tally = {}
                for row in in_shape:
                    for cell in row:
                        if cell is None:
                            continue
                        nm = (getattr(cell, "name", "") or "").strip().lower()
                        if nm in empty_names:
                            continue
                        key = (cell.id, cell.name, cell.metadata)
                        if key not in tally:
                            tally[key] = {"name": cell.name, "count": 0}
                        tally[key]["count"] += max(1, abs(int(getattr(cell, "count", 1))))
                # 虽然这里返回 dict 形式仅用于成本估算与日志，执行时使用 rr 原始结构
                return [{"name": v["name"], "count": v["count"]} for v in tally.values()]

            valid_recs: list[tuple[RawRecipe, list]] = []
            for rr in recs:
                ings = extract_ings(rr)
                self.logger.info(f"[DEBUG] 候选配方材料数：{len(ings)}，requires_table={getattr(rr, 'requires_table', False)}")
                if ings:
                    valid_recs.append((rr, ings))
            
            if not valid_recs:
                self.logger.warning(f"[DEBUG] {item} 没有找到任何有效配方，作为叶子材料处理")
                # 叶子材料，检查库存是否足够
                # 每次检查都从头开始计算库存，防止前面的步骤影响
                current_bag = Counter()
                for it in inventory or []:
                    name = self._normalize_item_name(it.name)
                    current_bag[name] += int(it.count)

                # 优先物品：如果该物品属于转化对，且本身是优先项，则直接视为叶子物品（不递归）
                if self._is_priority_item(item):
                    self.logger.info(f"[DEBUG] {item} 是转化对优先物品，跳过递归，视为叶子物品")
                    return current_bag.get(item, 0) >= qty

                if current_bag.get(item, 0) >= qty:
                    self.logger.info(f"[DEBUG] {item} 在库存中存在，直接使用")
                    return True
                else:
                    self.logger.warning(f"[DEBUG] {item} 无法合成且库存不足，合成失败")
                    return False
            
            self.logger.info(f"[DEBUG] {item} 找到 {len(valid_recs)} 个有效配方")
            
            # 选成本最小的配方
            best = None
            best_cost = None
            best_rr = None
            for i, (rr, ings) in enumerate(valid_recs):
                cost = sum(int(ing.get("count", 1)) if isinstance(ing, dict) else 1 for ing in ings)
                self.logger.info(f"[DEBUG] 配方 {i+1}: 成本={cost}, 材料={ings}")
                if best is None or cost < best_cost:
                    best = ings
                    best_cost = cost
                    best_rr = rr
            
            self.logger.info(f"[DEBUG] 选择配方: {best}, 成本: {best_cost}")
            
            # 计算单次配方产量，用于批次换算
            try:
                per_batch_out = int(getattr(getattr(best_rr, "result", None), "count", 1)) if best_rr else 1
                if per_batch_out <= 0:
                    per_batch_out = 1
            except Exception:
                per_batch_out = 1
            import math
            batches_needed = int(math.ceil(need / per_batch_out))

            # 检查材料是否足够，不足时尝试递归合成（按批次需求）
            can_craft = True
            self.logger.info(f"[DEBUG] 检查配方材料: {best}，单次产量={per_batch_out}，批次={batches_needed}")
            for ing in best or []:
                if isinstance(ing, dict):
                    ing_name = self._normalize_item_name(ing.get("name", "未知材料"))
                    per_ing = int(ing.get("count", 1))
                else:
                    ing_name = self._normalize_item_name(ing)
                    per_ing = 1
                ing_count = per_ing * batches_needed
                
                # 每次检查都从头开始计算库存，防止前面的步骤影响
                current_bag = Counter()
                for it in inventory or []:
                    name = self._normalize_item_name(it.name)
                    current_bag[name] += int(it.count)
                
                self.logger.info(f"[DEBUG] 检查材料 {ing_name}: 需要 {ing_count}, 库存 {current_bag.get(ing_name, 0)}")

                # 若目标 item 是转化对中的优先物品，且当前原料属于其转化对成员
                # 当库存不足时，不再递归合成该原料，避免在优先物品之间循环互转
                if self._is_priority_item(item) and ing_name in self._get_pair_items(item):
                    if current_bag.get(ing_name, 0) < ing_count:
                        self.logger.info(f"[DEBUG] {item} 为优先物品，且 {ing_name} 属于同一转化对；库存不足时不递归该原料")
                        can_craft = False
                        break
                
                if current_bag.get(ing_name, 0) < ing_count:
                    # 材料不足，尝试递归合成
                    missing_qty = ing_count - current_bag.get(ing_name, 0)
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
                recipe_payload = self._raw_recipe_to_tool_payload(best_rr) if best_rr else {}
                steps.append((item, need, actual_mode, recipe_payload))
                
                # 不再模拟消耗和增加材料，因为每次检查都从头开始
                self.logger.info(f"[DEBUG] 记录合成步骤: {item} x{need}，不模拟材料变化")
                return True
            
            # 如果当前配方无法合成，尝试其他配方
            if len(valid_recs) > 1:
                self.logger.info("[DEBUG] 尝试替代配方...")
                for rr, ings in valid_recs:
                    if ings == best:
                        continue  # 跳过已经尝试过的配方
                    if not ings:
                        continue
                    
                    self.logger.info(f"[DEBUG] 尝试替代配方: {ings}")

                    # 计算该替代配方的单次产量与批次数
                    try:
                        alt_per_batch_out = int(getattr(getattr(rr, "result", None), "count", 1)) if rr else 1
                        if alt_per_batch_out <= 0:
                            alt_per_batch_out = 1
                    except Exception:
                        alt_per_batch_out = 1
                    import math
                    alt_batches_needed = int(math.ceil(need / alt_per_batch_out))
                    self.logger.info(f"[DEBUG] 替代配方单次产量={alt_per_batch_out}，需要批次={alt_batches_needed}")

                    # 检查替代配方的材料（按批次需求折算）
                    alt_can_craft = True
                    for ing in ings:
                        if isinstance(ing, dict):
                            ing_name = self._normalize_item_name(ing.get("name", "未知材料"))
                            per_ing = int(ing.get("count", 1))
                        else:
                            ing_name = self._normalize_item_name(ing)
                            per_ing = 1

                        ing_count = per_ing * alt_batches_needed

                        # 每次检查都从头开始计算库存，防止前面的步骤影响
                        current_bag = Counter()
                        for it in inventory or []:
                            name = self._normalize_item_name(it.name)
                            current_bag[name] += int(it.count)

                        self.logger.info(f"[DEBUG] 替代配方材料 {ing_name}: 需要 {ing_count}, 库存 {current_bag.get(ing_name, 0)}")

                        if current_bag.get(ing_name, 0) < ing_count:
                            # 尝试递归合成
                            missing_qty = ing_count - current_bag.get(ing_name, 0)
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
                        recipe_payload = self._raw_recipe_to_tool_payload(rr)
                        steps.append((item, need, actual_mode, recipe_payload))
                        
                        # 不再模拟消耗和增加材料，因为每次检查都从头开始
                        self.logger.info(f"[DEBUG] 记录替代配方合成步骤: {item} x{need}，不模拟材料变化")
                        return True
            else:
                self.logger.info("[DEBUG] 没有替代配方可尝试")
            
            self.logger.warning(f"[DEBUG] {item} 所有配方都无法合成")
            return False

        # 主循环：不断尝试合成直到完成或达到阈值
        target_norm = self._normalize_item_name(target_item)

        if await try_craft_item(target_norm, quantity, 0):
            return steps
        # 规划失败返回空列表，避免上层对 None 取 len 报错
        return []

    async def craft_item_smart(self, item: str, count: int, inventory: List[Item], block_position: Any) -> tuple[bool, str]:
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

            # 函数：判断某模式下是否存在配方（使用 RawRecipe）
            async def has_recipe(use_table: bool) -> bool:
                recs = await self._get_raw_recipes(item_norm, use_table)
                if not recs:
                    return False
                def rr_has_ingredients(rr: RawRecipe) -> bool:
                    if getattr(rr, "ingredients", None):
                        return len(rr.ingredients) > 0
                    in_shape = getattr(rr, "in_shape", None)
                    if in_shape:
                        for row in in_shape:
                            for cell in row:
                                if cell is not None:
                                    return True
                    return False
                return any(rr_has_ingredients(r) for r in recs)

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
                    # 生成并逐步执行合成路径（无需工作台优先）
                    steps = await self._plan_crafting_steps(item_norm, count, False, inventory)
                    logs: list[str] = ["附近无工作台。按步骤合成："]
                    self.logger.info(f"[Craft] 计划步骤数：{len(steps)}")
                    
                    # 检查是否成功生成了合成步骤
                    if not steps:
                        # 尝试获取具体的材料缺失信息
                        missing_info = await self._get_missing_materials_info(item_norm, count, False, inventory)
                        return False, f"附近无工作台，但无法生成合成计划：{missing_info}"
                    
                    for step_item, step_count, step_use_table, recipe_payload in steps:
                        # 将需要的物品数量转换为执行次数（批次）
                        try:
                            res = recipe_payload.get("result") if isinstance(recipe_payload, dict) else None
                            per_batch = int(res.get("count", 1)) if isinstance(res, dict) else 1
                            per_batch = per_batch if per_batch > 0 else 1
                        except Exception:
                            per_batch = 1
                        import math
                        exec_batches = int(math.ceil(step_count / per_batch))
                        args = {"recipe": recipe_payload, "count": exec_batches}
                        if not step_use_table:
                            args["withoutCraftingTable"] = True
                        self.logger.info(f"[Craft] 准备执行：{'工作台' if step_use_table else '手工'} {step_item} x{step_count}，调用参数：{args}")
                        call_result = await self.mcp_client.call_tool_directly("craft_with_recipe", args)
                        result_text = "".join([getattr(c, "text", "") for c in getattr(call_result, "content", [])]) if hasattr(call_result, 'content') else str(call_result)
                        ok_step, detail = parse_craft_result_text(result_text, "")
                        self.logger.info(f"[Craft] 执行结果：{'成功' if ok_step else '失败'}；返回：{result_text}")
                        logs.append(f"- {('工作台' if step_use_table else '手工')} {step_item} x{step_count} -> {'成功' if ok_step else detail}")
                        if not ok_step:
                            return False, "\n".join(logs)
                    return True, "\n".join(logs)
                else:
                    # 没有无需工作台的配方
                    has_recipe_with_table = await has_recipe(True)
                    if has_recipe_with_table:
                        return False, "附近无工作台；若找到工作台即可合成。"
                    else:
                        return False, "附近无工作台；此物品无可用合成表。"

            # 分支 2：附近有工作台
            else:
                has_recipe_with_table = await has_recipe(True)
                if has_recipe_with_table:
                    # 生成并逐步执行合成路径（优先使用工作台配方）
                    steps = await self._plan_crafting_steps(item_norm, count, True, inventory)
                    logs: list[str] = ["附近有工作台。按步骤合成："]
                    self.logger.info(f"[Craft] 计划步骤数：{len(steps)}")
                    
                    # 检查是否成功生成了合成步骤
                    if not steps:
                        # 尝试获取具体的材料缺失信息
                        missing_info = await self._get_missing_materials_info(item_norm, count, True, inventory)
                        return False, f"附近有工作台，但无法生成合成计划：{missing_info}"
                    
                    for step_item, step_count, step_use_table, recipe_payload in steps:
                        # 将需要的物品数量转换为执行次数（批次）
                        try:
                            res = recipe_payload.get("result") if isinstance(recipe_payload, dict) else None
                            per_batch = int(res.get("count", 1)) if isinstance(res, dict) else 1
                            per_batch = per_batch if per_batch > 0 else 1
                        except Exception:
                            per_batch = 1
                        import math
                        exec_batches = int(math.ceil(step_count / per_batch))
                        args = {"recipe": recipe_payload, "count": exec_batches}
                        if not step_use_table:
                            args["withoutCraftingTable"] = True
                        self.logger.info(f"[Craft] 准备执行：{'工作台' if step_use_table else '手工'} {step_item} x{step_count}，调用参数：{args}")
                        call_result = await self.mcp_client.call_tool_directly("craft_with_recipe", args)
                        result_text = "".join([getattr(c, "text", "") for c in getattr(call_result, "content", [])]) if hasattr(call_result, 'content') else str(call_result)
                        ok_step, detail = parse_craft_result_text(result_text, "")
                        self.logger.info(f"[Craft] 执行结果：{'成功' if ok_step else '失败'}；返回：{result_text}")
                        logs.append(f"- {('工作台' if step_use_table else '手工')} {step_item} x{step_count} -> {'成功' if ok_step else detail}")
                        if not ok_step:
                            return False, "\n".join(logs)
                    return True, "\n".join(logs)
                else:
                    return False, "附近有工作台，但该物品无可用合成表，无法合成"

        except Exception as e:
            self.logger.error(f"craft_item_smart 发生异常：{e}")
            return False, f"执行异常：{e}"
    
    

recipe_finder = RecipeFinder()