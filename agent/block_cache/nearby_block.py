from agent.block_cache.block_cache import global_block_cache
from agent.common.basic_class import BlockPosition

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
            if block.block_type == "air" or block.block_type == "cave_air":
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
        around_blocks_str += f"\n**可放置方块位置**:\n{placement_info}"
        
        # 添加可移动位置检测
        # movement_info = await self._get_movement_positions(position, distance=5)
        # around_blocks_str += f"\n可作为Move终点位置:\n{movement_info}"
        
        return around_blocks_str

    def _format_coords_compact(self, coords: list[tuple[int, int, int]]) -> str:
        """将 (x,y,z) 列表压缩为统一的格式：()包裹，逗号分隔，xxx-xxxx范围"""
        if not coords:
            return ""
        
        # 去重并排序
        unique = sorted(set(coords))
        
        # 如果坐标很少，直接输出
        if len(unique) <= 2:
            return ",".join([f"(x={x},y={y},z={z})" for x, y, z in unique])
        
        # 尝试不同的压缩策略，选择最简洁的
        strategies = [
            self._format_by_height,      # 按高度(y)分组
            self._format_by_layer,       # 按层(z)分组  
            self._format_by_column,      # 按列(x)分组
        ]
        
        best_format = None
        best_length = float('inf')
        
        for strategy in strategies:
            try:
                result = strategy(unique)
                if len(result) < best_length:
                    best_format = result
                    best_length = len(result)
            except:
                continue
        
        # 如果所有压缩策略都不好，使用原始格式
        plain = ",".join([f"(x={x},y={y},z={z})" for x, y, z in unique])
        return best_format if best_format and len(best_format) < len(plain) else plain
    
    def _format_by_height(self, coords: list[tuple[int, int, int]]) -> str:
        """按高度(y)分组格式化"""
        from collections import defaultdict
        by_y = defaultdict(list)
        for x, y, z in coords:
            by_y[y].append((x, z))
        
        parts = []
        for y in sorted(by_y.keys()):
            points = by_y[y]
            if len(points) == 1:
                x, z = points[0]
                parts.append(f"(x={x},y={y},z={z})")
            else:
                # 按x,z坐标排序并分组
                xz_list = sorted(points)
                xz_str = self._format_xz_pairs(xz_list)
                parts.append(f"({xz_str},y={y})")
        
        return ",".join(parts)
    
    def _format_by_layer(self, coords: list[tuple[int, int, int]]) -> str:
        """按层(z)分组格式化"""
        from collections import defaultdict
        by_z = defaultdict(list)
        for x, y, z in coords:
            by_z[z].append((x, y))
        
        parts = []
        for z in sorted(by_z.keys()):
            points = by_z[z]
            if len(points) == 1:
                x, y = points[0]
                parts.append(f"(x={x},y={y},z={z})")
            else:
                # 按x,y坐标排序并分组
                xy_list = sorted(points)
                xy_str = self._format_xy_pairs(xy_list)
                parts.append(f"({xy_str},z={z})")
        
        return ",".join(parts)
    
    def _format_by_column(self, coords: list[tuple[int, int, int]]) -> str:
        """按列(x)分组格式化"""
        from collections import defaultdict
        by_x = defaultdict(list)
        for x, y, z in coords:
            by_x[x].append((y, z))
        
        parts = []
        for x in sorted(by_x.keys()):
            points = by_x[x]
            if len(points) == 1:
                y, z = points[0]
                parts.append(f"(x={x},y={y},z={z})")
            else:
                # 按y,z坐标排序并分组
                yz_list = sorted(points)
                yz_str = self._format_yz_pairs(yz_list)
                parts.append(f"({yz_str},x={x})")
        
        return ",".join(parts)
    
    def _format_xz_pairs(self, xz_pairs: list[tuple[int, int]]) -> str:
        """格式化x,z坐标对"""
        if len(xz_pairs) <= 2:
            x_parts = []
            z_parts = []
            for x, z in xz_pairs:
                x_parts.append(str(x))
                z_parts.append(str(z))
            x_str = self._compress_range([int(x) for x in x_parts])
            z_str = self._compress_range([int(z) for z in z_parts])
            return f"x={x_str},z={z_str}"
        
        # 尝试按x坐标分组
        from collections import defaultdict
        by_x = defaultdict(list)
        for x, z in xz_pairs:
            by_x[x].append(z)
        
        x_parts = []
        z_parts = []
        for x in sorted(by_x.keys()):
            x_parts.append(str(x))
            zs = sorted(by_x[x])
            z_parts.extend([str(z) for z in zs])
        
        x_str = self._compress_range([int(x) for x in x_parts])
        z_str = self._compress_range([int(z) for z in z_parts])
        return f"x={x_str},z={z_str}"
    
    def _format_xy_pairs(self, xy_pairs: list[tuple[int, int]]) -> str:
        """格式化x,y坐标对"""
        if len(xy_pairs) <= 2:
            x_parts = []
            y_parts = []
            for x, y in xy_pairs:
                x_parts.append(str(x))
                y_parts.append(str(y))
            x_str = self._compress_range([int(x) for x in x_parts])
            y_str = self._compress_range([int(y) for y in y_parts])
            return f"x={x_str},y={y_str}"
        
        # 尝试按x坐标分组
        from collections import defaultdict
        by_x = defaultdict(list)
        for x, y in xy_pairs:
            by_x[x].append(y)
        
        x_parts = []
        y_parts = []
        for x in sorted(by_x.keys()):
            x_parts.append(str(x))
            ys = sorted(by_x[x])
            y_parts.extend([str(y) for y in ys])
        
        x_str = self._compress_range([int(x) for x in x_parts])
        y_str = self._compress_range([int(y) for y in y_parts])
        return f"x={x_str},y={y_str}"
    
    def _format_yz_pairs(self, yz_pairs: list[tuple[int, int]]) -> str:
        """格式化y,z坐标对"""
        if len(yz_pairs) <= 2:
            y_parts = []
            z_parts = []
            for y, z in yz_pairs:
                y_parts.append(str(y))
                z_parts.append(str(z))
            y_str = self._compress_range([int(y) for y in y_parts])
            z_str = self._compress_range([int(z) for z in z_parts])
            return f"y={y_str},z={z_str}"
        
        # 尝试按y坐标分组
        from collections import defaultdict
        by_y = defaultdict(list)
        for y, z in yz_pairs:
            by_y[y].append(z)
        
        y_parts = []
        z_parts = []
        for y in sorted(by_y.keys()):
            y_parts.append(str(y))
            zs = sorted(by_y[y])
            z_parts.extend([str(z) for z in zs])
        
        y_str = self._compress_range([int(y) for y in y_parts])
        z_str = self._compress_range([int(z) for z in z_parts])
        return f"y={y_str},z={z_str}"
    
    def _compress_range(self, numbers: list[int]) -> str:
        """压缩数字范围为区间表示，使用xxx-xxxx格式"""
        if not numbers:
            return ""
        
        numbers = sorted(set(numbers))
        if len(numbers) == 1:
            return str(numbers[0])
        
        # 找出连续的区间
        ranges = []
        start = numbers[0]
        prev = numbers[0]
        
        for num in numbers[1:]:
            if num == prev + 1:
                prev = num
            else:
                ranges.append((start, prev))
                start = prev = num
        
        ranges.append((start, prev))
        
        # 构建压缩字符串
        parts = []
        for s, e in ranges:
            if s == e:
                parts.append(str(s))
            else:
                parts.append(f"{s}~{e}")

        return ",".join(parts)
    
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
                    if current_block_type not in ["air", "water", "lava","cave_air"]:
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
                        if adj_block_type not in ["air", "water", "lava", "cave_air"]:
                            solid_adjacent_count += 1
                    
                    # 检查相邻固体方块数量是否在1-5之间
                    if 1 <= solid_adjacent_count <= 5:
                        if current_block_type == "air" or current_block_type == "cave_air":
                            placement_positions.append((x, y, z))
                        elif current_block_type in ["water", "lava"]:
                            water_lava_positions.append((x, y, z, current_block_type))
        
        # 格式化输出
        result_parts = []
        
        if placement_positions:
            coord_str = self._format_coords_compact(placement_positions)
            result_parts.append(f"可place_block: {coord_str}")
        
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
                    if current_block_type != "air" and current_block_type != "cave_air":
                        continue
                    
                    # 检查下方是否有方块（不为air或none）
                    below_pos = (x, y - 1, z)
                    below_block_type = block_map.get(below_pos)
                    
                    # 跳过未知方块或空气
                    if below_block_type is None or below_block_type == "air" or below_block_type == "cave_air":
                        continue
                    
                    # 检查上方是否为空气（确保有足够空间站立）
                    above_pos = (x, y + 1, z)
                    above_block_type = block_map.get(above_pos)
                    
                    # 跳过未知方块或非空气
                    if above_block_type is None or above_block_type != "air" or above_block_type != "cave_air":
                        continue
                    
                    # 符合条件，可以移动到此位置
                    movement_positions.append((x, y, z))
        
        # 格式化输出
        if not movement_positions:
            return "无可用move位置"
        
        coord_str = self._format_coords_compact(movement_positions)
        return f"{coord_str}"
    
    async def get_visible_blocks_str(self, position: BlockPosition, distance: int = 32) -> str:
            """
            只返回附近可见方块的字符串
            
            Args:
                position: 中心位置
                distance: 可见方块的搜索距离
            """
            # 获取距离范围内的方块
            if not position:
                return ""
            
            blocks = self.block_cache.get_blocks_in_range(position.x, position.y, position.z, distance)
            
            # 过滤只保留可见方块
            visible_blocks = []
            for block in blocks:
                # 跳过空气方块
                if block.block_type == "air" or block.block_type == "cave_air":
                    continue
                
                # 只保留可见方块
                if block.can_see:
                    visible_blocks.append(block)
            
            # 按方块类型分组
            grouped_positions = {}
            block_num = 0
            
            for block in visible_blocks:
                block_num += 1
                key = block.block_type
                if key not in grouped_positions:
                    grouped_positions[key] = []
                grouped_positions[key].append((block.position.x, block.position.y, block.position.z))
            
            # 组装输出：同类方块在同一行内以坐标列表形式展示
            parts = []
            # logger.info(grouped_positions)
            for key, coords in grouped_positions.items():
                coord_str = self._format_coords_compact(coords)
                parts.append(f"{key}: {coord_str}")
            
            if not parts:
                result_str = f"视野内无可见方块\n"
            else:
                result_str = "\n".join(parts) + "\n"
            
            result_str += f"玩家所在位置: x={position.x}, y={position.y}, z={position.z}\n玩家头部位置: x={position.x}, y={position.y+1}, z={position.z}\n"
            # result_str += f"搜索距离: {distance}格\n"
            result_str += f"可见方块数量: {block_num}\n"
            
            # 添加可放置方块位置检测
            placement_info = await self._get_placement_positions(position, distance=5)
            result_str += f"\n**可放置方块位置**:\n{placement_info}"
            
            return result_str
    
    async def get_visible_blocks_list(self, position: BlockPosition, distance: int = 32) -> list[dict]:
        """
        只返回附近可见方块的列表
        
        Args:
            position: 中心位置
            distance: 可见方块的搜索距离
            
        Returns:
            包含可见方块信息的字典列表，每个字典包含位置和类型信息
        """
        # 获取距离范围内的方块
        blocks = self.block_cache.get_blocks_in_range(position.x, position.y, position.z, distance)
        
        # 过滤只保留可见方块
        visible_blocks = []
        for block in blocks:
            # 跳过空气方块
            if block.block_type == "air" or block.block_type == "cave_air":
                continue
            
            # 只保留可见方块
            if block.can_see:
                visible_blocks.append({
                    "x": block.position.x,
                    "y": block.position.y,
                    "z": block.position.z,
                    "type": block.block_type
                })
        
        return visible_blocks

nearby_block_manager = NearbyBlockManager()