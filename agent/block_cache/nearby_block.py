from agent.block_cache.block_cache import global_block_cache
from agent.environment.basic_info import BlockPosition

from utils.logger import get_logger

logger = get_logger("NearbyBlockManager")


class NearbyBlockManager:
    def __init__(self):
        self.block_cache = global_block_cache
    
    async def get_block_details_mix_str(self, position: BlockPosition, full_distance: int = 16, can_see_distance: int = 32):
        """
        获取方块详情字符串
        
        Args:
            position: 中心位置
            full_distance: 完全显示距离，此距离内显示所有方块
            can_see_distance: 可见显示距离，此距离内只显示可见方块
        """
        # 获取两个距离范围内的方块
        full_blocks = self.block_cache.get_blocks_in_range(position.x, position.y, position.z, full_distance)
        can_see_blocks = self.block_cache.get_blocks_in_range(position.x, position.y, position.z, can_see_distance)
        
        # 合并两个范围的方块，去重
        all_blocks = list({(block.position.x, block.position.y, block.position.z): block for block in full_blocks + can_see_blocks}.values())
        
        # 分组：key 为展示名称（空气 -> 无方块，其它直接用方块类型）
        grouped_positions = {}
        block_num = 0
        
        for block in all_blocks:
            # 跳过空气方块，不加入显示
            if block.block_type == "air":
                continue
            
            # 计算方块到中心的距离
            distance_to_center = ((block.position.x - position.x) ** 2 + 
                                 (block.position.y - position.y) ** 2 + 
                                 (block.position.z - position.z) ** 2) ** 0.5
            
            # 根据距离范围决定显示规则
            if distance_to_center <= full_distance:
                # 完全显示距离内显示所有方块
                pass
            elif distance_to_center <= can_see_distance:
                # 可见显示距离内只显示可见方块
                if not block.can_see:
                    continue
            else:
                # 超出范围，不显示
                continue
                
            block_num += 1
            key = block.block_type
            if key not in grouped_positions:
                grouped_positions[key] = []
            grouped_positions[key].append((block.position.x, block.position.y, block.position.z))
        
        # 组装输出：同类方块在同一行内以坐标列表形式展示
        parts = []
        for key, coords in grouped_positions.items():
            coord_str = self._format_coords_compact(coords)
            parts.append(f"{key}: {coord_str}")
        
        around_blocks_str = "\n".join(parts) + "\n"
        around_blocks_str += f"玩家所在位置: x={position.x}, y={position.y}, z={position.z}\n"
        around_blocks_str += f"玩家头部位置: x={position.x}, y={position.y+1}, z={position.z}\n"
        
        # 添加可放置方块位置检测
        placement_info = await self._get_placement_positions(position, distance=5)
        around_blocks_str += f"\n可放置方块位置:\n{placement_info}"
        
        # 添加可移动位置检测
        movement_info = await self._get_movement_positions(position, distance=5)
        around_blocks_str += f"\n可作为Move终点位置:\n{movement_info}"
        
        return around_blocks_str

    def _format_coords_compact(self, coords: list[tuple[int, int, int]]) -> str:
        """将 (x,y,z) 列表尽量压缩为区间表示。
        按三个轴向分别尝试：
        - 固定 (y,z)，合并 x 连续区间 → 输出形如 "(y=Y, z=Z): x=a ~ b, c"。
        - 固定 (x,z)，合并 y 连续区间。
        - 固定 (x,y)，合并 z 连续区间。
        选择字符数最少的结果；若压缩无收益则回退到逐点列出。
        """
        if not coords:
            return ""
        # 去重并排序，避免重复坐标影响展示
        unique = sorted(set(coords))
        # 原始逐点：按 (x,z,y) 顺序输出
        plain = ",".join([f"(x={x},z={z},y={y})" for x, y, z in unique])
        
        def build_ranges(values: list[int]) -> list[tuple[int, int]]:
            if not values:
                return []
            values = sorted(set(values))
            ranges: list[tuple[int, int]] = []
            start = prev = values[0]
            for v in values[1:]:
                if v == prev + 1:
                    prev = v
                    continue
                ranges.append((start, prev))
                start = prev = v
            ranges.append((start, prev))
            return ranges
        
        def fmt_ranges(label: str, values: list[int]) -> str:
            range_list = build_ranges(values)
            parts = []
            for s, e in range_list:
                if s == e:
                    parts.append(f"{label}={s}")
                else:
                    parts.append(f"{label}={s} ~ {e}")
            return ", ".join(parts)
        
        # 方案 A：固定 (y,z)，合并 x
        from collections import defaultdict
        by_yz: dict[tuple[int, int], list[int]] = defaultdict(list)
        for x, y, z in unique:
            by_yz[(y, z)].append(x)
        plan_a_items: list[str] = []
        for (y, z), xs in sorted(by_yz.items()):
            for s, e in build_ranges(xs):
                if s == e:
                    plan_a_items.append(f"(x={s},z={z},y={y})")
                else:
                    plan_a_items.append(f"(x={s}~{e},z={z},y={y})")
        plan_a = ",".join(plan_a_items)
        
        # 方案 B：固定 (x,z)，合并 y
        by_xz: dict[tuple[int, int], list[int]] = defaultdict(list)
        for x, y, z in unique:
            by_xz[(x, z)].append(y)
        plan_b_items: list[str] = []
        for (x, z), ys in sorted(by_xz.items()):
            for s, e in build_ranges(ys):
                if s == e:
                    plan_b_items.append(f"(x={x},z={z},y={s})")
                else:
                    plan_b_items.append(f"(x={x},z={z},y={s}~{e})")
        plan_b = ",".join(plan_b_items)
        
        # 方案 C：固定 (x,y)，合并 z
        by_xy: dict[tuple[int, int], list[int]] = defaultdict(list)
        for x, y, z in unique:
            by_xy[(x, y)].append(z)
        plan_c_items: list[str] = []
        for (x, y), zs in sorted(by_xy.items()):
            for s, e in build_ranges(zs):
                if s == e:
                    plan_c_items.append(f"(x={x},z={s},y={y})")
                else:
                    plan_c_items.append(f"(x={x},z={s}~{e},y={y})")
        plan_c = ",".join(plan_c_items)
        
        candidates = [plain, plan_a, plan_b, plan_c]
        # 进一步方案：按单轴做标题分组，减少标签重复
        def join_range_tokens(label: str, values: list[int]) -> str:
            parts = []
            for s, e in build_ranges(values):
                if s == e:
                    parts.append(f"{label}={s}")
                else:
                    parts.append(f"{label}={s}~{e}")
            return "|".join(parts)

        def plan_factored_by_z() -> str:
            from collections import defaultdict
            by_z: dict[int, list[tuple[int, int]]] = defaultdict(list)
            for x, y, z in unique:
                by_z[z].append((x, y))
            z_parts: list[str] = []
            for z, xys in sorted(by_z.items()):
                # y -> x ranges signature
                y_to_xsig: dict[int, str] = {}
                from collections import defaultdict as dd
                y_to_xs: dict[int, list[int]] = dd(list)
                for x, y in xys:
                    y_to_xs[y].append(x)
                for y, xs in y_to_xs.items():
                    xsig = join_range_tokens('x', xs)
                    y_to_xsig[y] = xsig
                # 合并相邻 y 且签名相同
                items: list[str] = []
                for y in sorted(y_to_xsig.keys()):
                    pass
                ys_sorted = sorted(y_to_xsig.keys())
                if not ys_sorted:
                    z_parts.append(f"z={z}:")
                    continue
                start_y = prev_y = ys_sorted[0]
                prev_sig = y_to_xsig[prev_y]
                def emit(seg_start: int, seg_end: int, sig: str):
                    # sig like "x=1~3|x=5" → 转为 "x=1~3|x=5" 保持
                    if seg_start == seg_end:
                        items.append(f"({sig},y={seg_start})")
                    else:
                        items.append(f"({sig},y={seg_start}~{seg_end})")
                for y in ys_sorted[1:]:
                    sig = y_to_xsig[y]
                    if y == prev_y + 1 and sig == prev_sig:
                        prev_y = y
                        continue
                    emit(start_y, prev_y, prev_sig)
                    start_y = prev_y = y
                    prev_sig = sig
                emit(start_y, prev_y, prev_sig)
                z_parts.append(f"z={z}: " + ",".join(items))
            return "; ".join(z_parts)

        def plan_factored_by_y() -> str:
            from collections import defaultdict
            by_y: dict[int, list[tuple[int, int]]] = defaultdict(list)
            for x, y, z in unique:
                by_y[y].append((x, z))
            y_parts: list[str] = []
            for y, xzs in sorted(by_y.items()):
                z_to_xsig: dict[int, str] = {}
                from collections import defaultdict as dd
                z_to_xs: dict[int, list[int]] = dd(list)
                for x, z in xzs:
                    z_to_xs[z].append(x)
                for z, xs in z_to_xs.items():
                    xsig = join_range_tokens('x', xs)
                    z_to_xsig[z] = xsig
                items: list[str] = []
                zs_sorted = sorted(z_to_xsig.keys())
                if not zs_sorted:
                    y_parts.append(f"y={y}:")
                    continue
                start_z = prev_z = zs_sorted[0]
                prev_sig = z_to_xsig[prev_z]
                def emit(seg_start: int, seg_end: int, sig: str):
                    if seg_start == seg_end:
                        items.append(f"({sig},z={seg_start})")
                    else:
                        items.append(f"({sig},z={seg_start}~{seg_end})")
                for z in zs_sorted[1:]:
                    sig = z_to_xsig[z]
                    if z == prev_z + 1 and sig == prev_sig:
                        prev_z = z
                        continue
                    emit(start_z, prev_z, prev_sig)
                    start_z = prev_z = z
                    prev_sig = sig
                emit(start_z, prev_z, prev_sig)
                y_parts.append(f"y={y}: " + ",".join(items))
            return "; ".join(y_parts)

        def plan_factored_by_x() -> str:
            from collections import defaultdict
            by_x: dict[int, list[tuple[int, int]]] = defaultdict(list)
            for x, y, z in unique:
                by_x[x].append((y, z))
            x_parts: list[str] = []
            for x, yzs in sorted(by_x.items()):
                z_to_ysig: dict[int, str] = {}
                from collections import defaultdict as dd
                z_to_ys: dict[int, list[int]] = dd(list)
                for y, z in yzs:
                    z_to_ys[z].append(y)
                for z, ys in z_to_ys.items():
                    ysig = join_range_tokens('y', ys)
                    z_to_ysig[z] = ysig
                items: list[str] = []
                zs_sorted = sorted(z_to_ysig.keys())
                if not zs_sorted:
                    x_parts.append(f"x={x}:")
                    continue
                start_z = prev_z = zs_sorted[0]
                prev_sig = z_to_ysig[prev_z]
                def emit(seg_start: int, seg_end: int, sig: str):
                    if seg_start == seg_end:
                        items.append(f"({sig},z={seg_start})")
                    else:
                        items.append(f"({sig},z={seg_start}~{seg_end})")
                for z in zs_sorted[1:]:
                    sig = z_to_ysig[z]
                    if z == prev_z + 1 and sig == prev_sig:
                        prev_z = z
                        continue
                    emit(start_z, prev_z, prev_sig)
                    start_z = prev_z = z
                    prev_sig = sig
                emit(start_z, prev_z, prev_sig)
                x_parts.append(f"x={x}: " + ",".join(items))
            return "; ".join(x_parts)

        plan_d = plan_factored_by_z()
        plan_e = plan_factored_by_y()
        plan_f = plan_factored_by_x()

        candidates.extend([plan_d, plan_e, plan_f])

        # 方案 G：三维盒子合并（x 连续 → 合并成条；同形 y 段在同 z 合并；再跨 z 合并同形）
        def plan_boxes() -> str:
            from collections import defaultdict
            # (y,z) -> list of x ranges
            by_yz: dict[tuple[int, int], list[int]] = defaultdict(list)
            for x, y, z in unique:
                by_yz[(y, z)].append(x)
            yz_to_runs: dict[tuple[int, int], list[tuple[int, int]]] = {}
            for (y, z), xs in by_yz.items():
                yz_to_runs[(y, z)] = build_ranges(xs)
            # 对每个 z，将相邻 y 且 run 集合相同的合并
            z_to_y_segments: dict[int, list[tuple[int, int, tuple[tuple[int, int], ...]]]] = {}
            zs = sorted({z for _, z in by_yz.keys()})
            for z in zs:
                ys = sorted({y for (y2, z2) in yz_to_runs.keys() if z2 == z and y2 is not None})
                segments: list[tuple[int, int, tuple[tuple[int, int], ...]]] = []
                if not ys:
                    z_to_y_segments[z] = segments
                    continue
                start_y = prev_y = ys[0]
                prev_runs = tuple(yz_to_runs.get((prev_y, z), []))
                for y in ys[1:]:
                    runs = tuple(yz_to_runs.get((y, z), []))
                    if y == prev_y + 1 and runs == prev_runs:
                        prev_y = y
                        continue
                    segments.append((start_y, prev_y, prev_runs))
                    start_y = prev_y = y
                    prev_runs = runs
                segments.append((start_y, prev_y, prev_runs))
                z_to_y_segments[z] = segments
            # 跨 z 合并：对每个 (y1,y2,runs) 在相邻 z 若相同则扩展
            # 先将每个 z 的段落索引为可比较键
            boxes: list[tuple[int, int, int, int, int, int]] = []  # (x1,x2,z1,z2,y1,y2)
            # 为了便于跨 z 合并，建立按键 (y1,y2,runs) -> 按 z 排序的 z 列表
            key_to_zlist: dict[tuple[int, int, tuple[tuple[int, int], ...]], list[int]] = defaultdict(list)
            for z, segs in z_to_y_segments.items():
                for (y1, y2, runs) in segs:
                    key_to_zlist[(y1, y2, runs)].append(z)
            # 对每个键的 z 列表合并连续 z，形成 z 区间
            for (y1, y2, runs), zlist in key_to_zlist.items():
                zlist = sorted(set(zlist))
                for z_start, z_end in build_ranges(zlist):
                    # 对于该 (y1,y2,z_start~z_end) 的每个 x-run 生成盒子
                    for x1, x2 in runs:
                        boxes.append((x1, x2, z_start, z_end, y1, y2))
            # 输出
            def fmt(a: int, b: int, label: str) -> str:
                if a == b:
                    return f"{label}={a}"
                return f"{label}={a}~{b}"
            items = []
            for x1, x2, z1, z2, y1, y2 in sorted(boxes):
                items.append(f"({fmt(x1,x2,'x')},{fmt(z1,z2,'z')},{fmt(y1,y2,'y')})")
            return ",".join(items)

        plan_g = plan_boxes()
        candidates.append(plan_g)
        # 选择字符最短的表示
        best = min(candidates, key=len)
        return best
    
    async def _get_placement_positions(self, position: BlockPosition, distance: int = 5):
        """检测可以放置方块的位置
        
        规则：
        1. 位置必须是空气、水或岩浆
        2. 周围6个相邻位置（上下左右前后）中至少有1个至多5个是固体方块
        3. 如果是水或岩浆，需要特别说明会挤占
        """
        # 获取周围5格内的所有方块
        around_blocks = self.block_cache.get_blocks_in_range(position.x, position.y, position.z, distance)
        
        # 创建位置到方块类型的映射
        block_map = {}
        for block in around_blocks:
            block_map[(block.position.x, block.position.y, block.position.z)] = block.block_type
        
        # 定义6个相邻方向（上下左右前后）
        adjacent_directions = [
            (0, 1, 0),   # 上
            (0, -1, 0),  # 下
            (1, 0, 0),   # 右
            (-1, 0, 0),  # 左
            (0, 0, 1),   # 前
            (0, 0, -1),  # 后
        ]
        
        # 检查每个位置是否可以放置方块
        placement_positions = []
        water_lava_positions = []
        
        for x in range(position.x - distance, position.x + distance + 1):
            for y in range(position.y - distance, position.y + distance + 1):
                for z in range(position.z - distance, position.z + distance + 1):
                    current_pos = (x, y, z)
                    current_block_type = block_map.get(current_pos)
                    
                    # 跳过未知方块（none）
                    if current_block_type is None:
                        continue
                    
                    # 只检查空气、水或岩浆位置
                    if current_block_type not in ["air", "water", "lava"]:
                        continue
                    
                    # 计算相邻固体方块数量
                    solid_adjacent_count = 0
                    for dx, dy, dz in adjacent_directions:
                        adj_pos = (x + dx, y + dy, z + dz)
                        adj_block_type = block_map.get(adj_pos)
                        
                        # 跳过未知方块
                        if adj_block_type is None:
                            continue
                        
                        # 检查是否为固体方块（非空气、水、岩浆）
                        if adj_block_type not in ["air", "water", "lava"]:
                            solid_adjacent_count += 1
                    
                    # 检查相邻固体方块数量是否在1-5之间
                    if 1 <= solid_adjacent_count <= 5:
                        if current_block_type == "air":
                            placement_positions.append((x, y, z))
                        elif current_block_type in ["water", "lava"]:
                            water_lava_positions.append((x, y, z, current_block_type))
        
        # 格式化输出
        result_parts = []
        
        if placement_positions:
            coord_str = self._format_coords_compact(placement_positions)
            result_parts.append(f"可直接放置: {coord_str}")
        
        if water_lava_positions:
            water_coords = [(x, y, z) for x, y, z, block_type in water_lava_positions if block_type == "water"]
            lava_coords = [(x, y, z) for x, y, z, block_type in water_lava_positions if block_type == "lava"]
            
            if water_coords:
                water_str = self._format_coords_compact(water_coords)
                result_parts.append(f"水位置(会挤占水方块): {water_str}")
            
            if lava_coords:
                lava_str = self._format_coords_compact(lava_coords)
                result_parts.append(f"岩浆位置(会挤占岩浆方块): {lava_str}")
        
        if not result_parts:
            return "无可用位置"
        
        return "\n".join(result_parts)
    
    async def _get_movement_positions(self, position: BlockPosition, distance: int = 5):
        """检测可以移动到的位置
        
        规则：
        1. 该位置必须为空气
        2. 该位置下方必须有方块（不为air或none）
        3. 该位置上方必须为空气（确保有足够空间站立）
        """
        # 获取周围5格内的所有方块
        around_blocks = self.block_cache.get_blocks_in_range(position.x, position.y, position.z, distance)
        
        # 创建位置到方块类型的映射
        block_map = {}
        for block in around_blocks:
            block_map[(block.position.x, block.position.y, block.position.z)] = block.block_type
        
        # 检查每个位置是否可以移动
        movement_positions = []
        
        for x in range(position.x - distance, position.x + distance + 1):
            for y in range(position.y - distance, position.y + distance + 1):
                for z in range(position.z - distance, position.z + distance + 1):
                    current_pos = (x, y, z)
                    current_block_type = block_map.get(current_pos)
                    
                    # 跳过未知方块
                    if current_block_type is None:
                        continue
                    
                    # 当前位置必须为空气
                    if current_block_type != "air":
                        continue
                    
                    # 检查下方是否有方块（不为air或none）
                    below_pos = (x, y - 1, z)
                    below_block_type = block_map.get(below_pos)
                    
                    # 跳过未知方块或空气
                    if below_block_type is None or below_block_type == "air":
                        continue
                    
                    # 检查上方是否为空气（确保有足够空间站立）
                    above_pos = (x, y + 1, z)
                    above_block_type = block_map.get(above_pos)
                    
                    # 跳过未知方块或非空气
                    if above_block_type is None or above_block_type != "air":
                        continue
                    
                    # 符合条件，可以移动到此位置
                    movement_positions.append((x, y, z))
        
        # 格式化输出
        if not movement_positions:
            return "无可用move位置"
        
        coord_str = self._format_coords_compact(movement_positions)
        return f"{coord_str}"
    
nearby_block_manager = NearbyBlockManager()