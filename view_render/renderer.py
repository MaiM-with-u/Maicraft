"""
方块缓存渲染模块
将 BlockCache 中的方块以等距投影渲染为二维图像，便于快速预览。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple, Dict, Set, Any

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64
import colorsys

from agent.block_cache.block_cache import BlockCache, Block, global_block_cache


@dataclass
class RenderConfig:
    image_width: int = 1024
    image_height: int = 768
    background_color: Tuple[int, int, int, int] = (180, 210, 255, 255)  # 淡蓝色背景
    block_size: int = 36  # 单位立方体基准尺寸（像素）
    draw_grid: bool = False
    face_colors: Dict[str, Tuple[int, int, int, int]] = None  # top, left, right
    vertical_scale: float = 1.0  # 垂直高度像素（每上升1格的像素高度 = block_size * vertical_scale）
    type_color_map: Dict[Any, Tuple[int, int, int]] = None  # 可选：类型 -> 基础RGB
    exclude_types: Set[Any] = None  # 需要排除渲染的方块类型（默认排除 air）
    # 轨迹配置
    trail_enabled: bool = True
    trail_max_points: int = 500
    trail_color: Tuple[int, int, int, int] = (255, 210, 0, 180)  # 半透明黄
    trail_width: int = 2

    def __post_init__(self) -> None:
        if self.face_colors is None:
            # 默认为石头风格的中性配色
            self.face_colors = {
                "top": (180, 180, 190, 255),
                "left": (150, 150, 160, 255),
                "right": (120, 120, 130, 255),
            }
        if self.type_color_map is None:
            self.type_color_map = {}
        if self.exclude_types is None:
            self.exclude_types = {"air", 0, "0", None}


class BlockCacheRenderer:
    def __init__(self, cache: Optional[BlockCache] = None, config: Optional[RenderConfig] = None) -> None:
        self.cache = cache or global_block_cache
        self.config = config or RenderConfig()
        # 玩家轨迹（世界坐标，渲染时投影）
        self._player_trail: List[Tuple[float, float, float]] = []
        # 最近一次渲染的图像
        self._last_image: Optional[Image.Image] = None

    # === 公共 API ===
    def render(self,
               center: Optional[Tuple[float, float, float]] = None,
               radius: Optional[float] = None,
               save_path: Optional[str] = None) -> Image.Image:
        """
        渲染当前缓存。
        - center+radius 提供则仅渲染该范围内方块。
        - save_path 提供则保存 PNG。
        返回 PIL.Image 对象。
        """
        blocks = self._collect_blocks(center=center, radius=radius)
        img = self._render_blocks(blocks, auto_center=center is None)
        if save_path:
            img.save(save_path, format="PNG")
        # 缓存最近一次渲染的图像
        try:
            self._last_image = img.copy()
        except Exception:
            self._last_image = img
        return img

    def render_to_base64(self,
                          center: Optional[Tuple[float, float, float]] = None,
                          radius: Optional[float] = None,
                          image_format: str = "PNG",
                          data_uri: bool = False,
                          compress_ratio: float = 0.25) -> str:
        """渲染并返回图像的Base64字符串。
        - image_format: "PNG" 或 "JPEG"
        - data_uri: True时返回 data URI 前缀
        - compress_ratio: 压缩比例，0.25表示压缩到原来的1/4大小
        """
        img = self.render(center=center, radius=radius, save_path=None)
        
        # 压缩图片到指定比例
        if compress_ratio != 1.0:
            new_width = int(img.width * compress_ratio)
            new_height = int(img.height * compress_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        buffer = BytesIO()
        fmt = image_format.upper()
        img.save(buffer, format=fmt)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        if data_uri:
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            return f"data:{mime};base64,{encoded}"
        return encoded

    def get_last_render_base64(self, image_format: str = "PNG", data_uri: bool = False, compress_ratio: float = 0.25) -> Optional[str]:
        """返回最近一次渲染图像的Base64字符串；若还未渲染则返回None。
        - compress_ratio: 压缩比例，0.25表示压缩到原来的1/4大小
        """
        if self._last_image is None:
            return None
        
        # 压缩图片到指定比例
        img = self._last_image
        if compress_ratio != 1.0:
            new_width = int(img.width * compress_ratio)
            new_height = int(img.height * compress_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        buffer = BytesIO()
        fmt = image_format.upper()
        img.save(buffer, format=fmt)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        if data_uri:
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            return f"data:{mime};base64,{encoded}"
        return encoded

    # === 内部方法 ===
    def _collect_blocks(self,
                        center: Optional[Tuple[float, float, float]],
                        radius: Optional[float]) -> List[Block]:
        if center is not None and radius is not None:
            cx, cy, cz = center
            blocks = self.cache.get_blocks_in_range(cx, cy, cz, radius)
        # 无范围限制则渲染全部
        else:
            blocks = list(self.cache._position_cache.values())  # 受控访问，仅用于渲染预览

        # 过滤掉空气与排除类型
        filtered: List[Block] = []
        for b in blocks:
            bt = b.block_type
            if bt in self.config.exclude_types:
                continue
            # 常见字符串标记
            if isinstance(bt, str) and bt.lower() == "air":
                continue
            filtered.append(b)
        return filtered

    def _render_blocks(self, blocks: Iterable[Block], auto_center: bool) -> Image.Image:
        cfg = self.config
        img = Image.new("RGBA", (cfg.image_width, cfg.image_height), cfg.background_color)
        draw = ImageDraw.Draw(img, "RGBA")
        # 保存当前图像用于半透明合成
        self._current_img = img

        # 基于邻居的简单遮挡剔除：若 +x、+y、+z 三方向均有方块，则认为该方块被完全遮挡
        occupied: Set[Tuple[int, int, int]] = set()
        for _b in blocks:
            occupied.add((int(_b.position.x), int(_b.position.y), int(_b.position.z)))

        visible_blocks: List[Block] = []
        for _b in blocks:
            _x, _y, _z = int(_b.position.x), int(_b.position.y), int(_b.position.z)
            if (
                (_x + 1, _y, _z) in occupied and
                (_x, _y + 1, _z) in occupied and
                (_x, _y, _z + 1) in occupied
            ):
                continue
            visible_blocks.append(_b)

        # 将世界坐标直接投影到等距坐标（不在世界坐标中做平移），避免小数平移引起的 round 抖动
        projected_raw: List[Tuple[int, int, float, Block]] = []
        min_px = 10**9
        max_px = -10**9
        min_py = 10**9
        max_py = -10**9
        for b in visible_blocks:
            sx, sy = self._iso_project(b.position.x, b.position.y, b.position.z)
            depth = b.position.x + b.position.y + b.position.z
            projected_raw.append((sx, sy, depth, b))
            if auto_center:
                if sx < min_px:
                    min_px = sx
                if sx > max_px:
                    max_px = sx
                if sy < min_py:
                    min_py = sy
                if sy > max_py:
                    max_py = sy

        # 排序：按深度由小到大（更远先画）
        projected_raw.sort(key=lambda t: t[2])

        # 计算将图像放在画布中心的屏幕平移量
        dx = cfg.image_width // 2
        dy = cfg.image_height // 2
        if auto_center and projected_raw:
            # 优先使用玩家位置居中（从 BlockCache 获取）
            player_positions = self.cache.get_player_positions()
            if player_positions:
                player_pos = player_positions[0].position
                px, py = self._iso_project(player_pos.x, player_pos.y, player_pos.z)
                dx -= px
                dy -= py
            else:
                # 回退：使用边界框居中
                center_x = (min_px + max_px) // 2
                center_y = (min_py + max_py) // 2
                dx -= center_x
                dy -= center_y

        # 视口尺寸
        img_w, img_h = cfg.image_width, cfg.image_height
        margin = 2

        for sx, sy, _h, b in projected_raw:
            bt_str = str(b.block_type).lower()
            face_colors = self._get_face_colors_for_type(b.block_type)
            # 叶子类：绿色半透明
            if "leaves" in bt_str or "leave" in bt_str or "leaf" in bt_str:
                green_base = (95, 159, 53)
                face_colors = {
                    "top": self._tone_rgba(green_base, 1.0, 0.55),
                    "left": self._tone_rgba(green_base, 0.85, 0.55),
                    "right": self._tone_rgba(green_base, 0.70, 0.55),
                }

            cxp = sx + dx
            cyp = sy + dy

            # 屏幕外裁剪：估算该方块在屏幕上的包围盒（与 _draw_cube 几何一致）
            tile_w = cfg.block_size
            tile_h = cfg.block_size // 2
            h = int(round(cfg.block_size * cfg.vertical_scale))
            minx = cxp - tile_w - 2
            maxx = cxp + tile_w + 2
            miny = cyp - tile_h - 2 - 1
            maxy = cyp + tile_h + h + 2
            if maxx < -margin or minx > img_w + margin or maxy < -margin or miny > img_h + margin:
                continue

            # 水体：3/4 高度半透明蓝色
            if "water" in bt_str:
                water_base = (52, 126, 232)
                alpha = 0.60
                water_colors = {
                    "top": self._tone_rgba(water_base, 1.0, alpha),
                    "left": self._tone_rgba(water_base, 0.85, alpha),
                    "right": self._tone_rgba(water_base, 0.70, alpha),
                }
                self._draw_cube(draw, cxp, cyp, cfg.block_size, cfg, water_colors)
            # 草方块特殊顶面
            elif "grass_block" in bt_str:
                self._draw_grass_block_cube(draw, cxp, cyp, cfg.block_size, cfg)
            # 蕨类/矮草用交叉平面
            elif ("fern" in bt_str) or ("shortgrass" in bt_str) or ("short_grass" in bt_str) or ("tall_grass" in bt_str) or ("tallgrass" in bt_str):
                # 使用绿色交叉面片
                green_rgba = (95, 159, 53, 255)
                self._draw_crossed_planes(draw, cxp, cyp, cfg.block_size, cfg, green_rgba)
            else:
                self._draw_cube(draw, cxp, cyp, cfg.block_size, cfg, face_colors)

        # 记录玩家位置并绘制运动轨迹
        try:
            if cfg.trail_enabled:
                # 从 BlockCache 获取玩家位置，而不是从 global_environment
                player_positions = self.cache.get_player_positions()
                if player_positions:
                    # 获取第一个玩家的位置（通常是主玩家）
                    ppos = player_positions[0].position
                    head_world = (ppos.x, ppos.y + 1, ppos.z)
                    if not self._player_trail or self._player_trail[-1] != head_world:
                        self._player_trail.append(head_world)
                        if len(self._player_trail) > cfg.trail_max_points:
                            self._player_trail = self._player_trail[-cfg.trail_max_points:]

                    if len(self._player_trail) >= 2:
                        pts: List[Tuple[int, int]] = []
                        for wx, wy, wz in self._player_trail:
                            sx, sy = self._iso_project(wx, wy, wz)
                            pts.append((sx + dx, sy + dy))
                        for i in range(1, len(pts)):
                            self._line(draw, pts[i-1], pts[i], cfg.trail_color, cfg.trail_width)
        except Exception:
            pass

        # 绘制玩家位置箭头（置于顶层）
        try:
            # 从 BlockCache 获取玩家位置
            player_positions = self.cache.get_player_positions()
            if player_positions:
                player_pos = player_positions[0].position
                # 使用玩家头部位置（y+1）作为箭头基准
                px, py = self._iso_project(player_pos.x, player_pos.y + 1, player_pos.z)
                self._draw_player_marker(draw, px + dx, py + dy, cfg.block_size)
        except Exception:
            pass

        # 绘制坐标轴方向标注（不包含图例说明）
        self._draw_coordinate_axes(draw, dx, dy, cfg)

        # 清理当前图像引用
        self._current_img = None
        return img

    # 等距投影（菱形格）：
    # 将方块中心 (x,y,z) 投影到 2D。这里采用常见 2:1 isometric。
    def _iso_project(self, x: float, y: float, z: float) -> Tuple[int, int]:
        s = self.config.block_size
        tile_w = s
        tile_h = s // 2
        # 严格 2:1 等距：顶面水平位移基于 tile_w/tile_h，竖直高度使用 s*vertical_scale
        iso_x = round((x - z) * tile_w)
        iso_y = round((x + z) * tile_h - y * (s * self.config.vertical_scale))
        return iso_x, iso_y

    def _draw_cube(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int, cfg: RenderConfig,
                   face_colors: Dict[str, Tuple[int, int, int, int]], height_override: Optional[int] = None) -> None:
        tile_w = s           # 菱形左右偏移
        tile_h = s // 2      # 菱形上下偏移（等距2:1）
        h = height_override if height_override is not None else int(round(s * cfg.vertical_scale))  # 侧面高度像素，需与 _iso_project 的 y 缩放一致
        overlap = 1
        edge = 1

        # 顶面四边形
        top = [
            (cx, cy - tile_h - edge),
            (cx + tile_w + edge, cy - edge),
            (cx, cy + tile_h + overlap),
            (cx - tile_w - edge, cy - edge),
        ]

        # 左侧面
        left = [
            (cx - tile_w - edge, cy - edge),
            (cx, cy + tile_h),
            (cx, cy + tile_h + h + overlap),
            (cx - tile_w - edge, cy + h + overlap - edge),
        ]

        # 右侧面
        right = [
            (cx + tile_w + edge, cy - edge),
            (cx, cy + tile_h),
            (cx, cy + tile_h + h + overlap),
            (cx + tile_w + edge, cy + h + overlap - edge),
        ]

        # 绘制顺序：先左后右最后顶，获得更自然的遮挡
        self._poly(draw, left, face_colors["left"]) 
        self._poly(draw, right, face_colors["right"]) 
        self._poly(draw, top, face_colors["top"]) 

    def _get_face_colors_for_type(self, block_type: Any) -> Dict[str, Tuple[int, int, int, int]]:
        """根据方块类型生成三面颜色。
        优先使用 RenderConfig.type_color_map 中配置；否则基于类型ID生成稳定的 HSV 色调。
        顶面最亮，右侧最暗。
        """
        cfg = self.config
        if block_type in cfg.type_color_map:
            r, g, b = cfg.type_color_map[block_type]
        else:
            bt = str(block_type).lower()
            # 优先匹配常见材料的固定配色
            if "log" in bt:
                # 棕色（木头）
                r, g, b = 121, 85, 58
            elif "dirt" in bt:
                # 淡棕（泥土）
                r, g, b = 160, 120, 80
            elif "andesite" in bt or "andestie" in bt:
                # 安山岩：比石头稍浅的灰
                r, g, b = 150, 150, 150
            elif "stone" in bt:
                # 灰色（石头）
                r, g, b = 130, 130, 130
            else:
                # 稳定色：类型ID映射到 [0,1) 的色相
                hue = (hash(str(block_type)) % 360) / 360.0
                s = 0.25
                v = 0.80
                r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, s, v)
                r, g, b = int(r_f * 255), int(g_f * 255), int(b_f * 255)

        def tone(rgb: Tuple[int, int, int], mul: float) -> Tuple[int, int, int, int]:
            rr = max(0, min(255, int(rgb[0] * mul)))
            gg = max(0, min(255, int(rgb[1] * mul)))
            bb = max(0, min(255, int(rgb[2] * mul)))
            return rr, gg, bb, 255

        return {
            "top": tone((r, g, b), 1.0),
            "left": tone((r, g, b), 0.85),
            "right": tone((r, g, b), 0.70),
        }

    def _apply_alpha(self, face_colors: Dict[str, Tuple[int, int, int, int]], alpha: float) -> Dict[str, Tuple[int, int, int, int]]:
        a = max(0, min(255, int(255 * alpha)))
        return {
            k: (v[0], v[1], v[2], a) for k, v in face_colors.items()
        }

    def _draw_crossed_planes(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int,
                              cfg: RenderConfig, color: Tuple[int, int, int, int]) -> None:
        # 两张互相垂直的立面，与世界 X/Z 轴对齐，并按等距投影呈斜向
        tile_w = s
        tile_h = s // 2
        h = int(round(s * cfg.vertical_scale))

        # 方向向量（等距）
        half_x = (tile_w // 2, tile_h // 2)    # X 轴方向的一半
        half_z = (-tile_w // 2, tile_h // 2)   # Z 轴方向的一半

        # 平面X：顶边端点为 center ± half_x
        x_top_left = (cx - half_x[0], cy - half_x[1])
        x_top_right = (cx + half_x[0], cy + half_x[1])
        x_bot_left = (x_top_left[0], x_top_left[1] + h)
        x_bot_right = (x_top_right[0], x_top_right[1] + h)
        plane_x = [x_top_left, x_top_right, x_bot_right, x_bot_left]

        # 平面Z：顶边端点为 center ± half_z
        z_top_left = (cx - half_z[0], cy - half_z[1])
        z_top_right = (cx + half_z[0], cy + half_z[1])
        z_bot_left = (z_top_left[0], z_top_left[1] + h)
        z_bot_right = (z_top_right[0], z_top_right[1] + h)
        plane_z = [z_top_left, z_top_right, z_bot_right, z_bot_left]

        self._poly(draw, plane_x, color)
        self._poly(draw, plane_z, color)

    def _draw_grass_block_cube(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int,
                               cfg: RenderConfig) -> None:
        tile_w = s
        tile_h = s // 2
        h = int(round(s * cfg.vertical_scale))

        # 基础颜色：顶部草绿，侧面为土的明暗
        grass_top = (95, 159, 53, 255)  # 草绿
        dirt_base = (160, 120, 80)      # 与 dirt 一致

        def tone(rgb: Tuple[int, int, int], mul: float, a: int = 255) -> Tuple[int, int, int, int]:
            rr = max(0, min(255, int(rgb[0] * mul)))
            gg = max(0, min(255, int(rgb[1] * mul)))
            bb = max(0, min(255, int(rgb[2] * mul)))
            return rr, gg, bb, a

        left_color = tone(dirt_base, 0.85)
        right_color = tone(dirt_base, 0.70)

        # 顶面：上边 1/4 绿色，下边 3/4 仍为绿色，但我们用一条水平带体现“上1/4”
        top_poly = [
            (cx, cy - tile_h - 1),
            (cx + tile_w + 1, cy - 1),
            (cx, cy + tile_h + 1),
            (cx - tile_w - 1, cy - 1),
        ]
        self._poly(draw, top_poly, grass_top)

        # 在顶面内画一条稍亮的上边带，近似“上1/4”为绿色高光
        band_height = max(1, tile_h // 4)
        highlight = (110, 180, 70, 255)
        band = [
            (cx, cy - tile_h - 1),
            (cx + tile_w + 1, cy - 1),
            (cx + tile_w, cy - 1 + band_height),
            (cx, cy - tile_h + band_height),
            (cx - tile_w, cy - 1 + band_height),
            (cx - tile_w - 1, cy - 1),
        ]
        self._poly(draw, band, highlight)

        # 左右侧面（基于土色）
        left = [
            (cx - tile_w - 1, cy - 1),
            (cx, cy + tile_h),
            (cx, cy + tile_h + h + 1),
            (cx - tile_w - 1, cy + h),
        ]
        right = [
            (cx + tile_w + 1, cy - 1),
            (cx, cy + tile_h),
            (cx, cy + tile_h + h + 1),
            (cx + tile_w + 1, cy + h),
        ]
        self._poly(draw, left, left_color)
        self._poly(draw, right, right_color)

    def _poly(self, draw: ImageDraw.ImageDraw, points: List[Tuple[int, int]], color: Tuple[int, int, int, int]) -> None:
        """绘制支持半透明合成的多边形。alpha<255 时在临时图层绘制并合成。"""
        if len(color) == 4 and color[3] < 255 and hasattr(self, "_current_img") and self._current_img is not None:
            try:
                w, h = self._current_img.size
                layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                layer_draw = ImageDraw.Draw(layer, "RGBA")
                layer_draw.polygon(points, fill=color)
                self._current_img.alpha_composite(layer)
            except (AttributeError, Exception):
                # 如果合成失败，回退到直接绘制
                draw.polygon(points, fill=color)
        else:
            draw.polygon(points, fill=color)

    def _line(self, draw: ImageDraw.ImageDraw, p1: Tuple[int, int], p2: Tuple[int, int],
              color: Tuple[int, int, int, int], width: int) -> None:
        if len(color) == 4 and color[3] < 255 and hasattr(self, "_current_img") and self._current_img is not None:
            try:
                w, h = self._current_img.size
                layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                layer_draw = ImageDraw.Draw(layer, "RGBA")
                layer_draw.line([p1, p2], fill=color, width=width)
                self._current_img.alpha_composite(layer)
            except (AttributeError, Exception):
                # 如果合成失败，回退到直接绘制
                draw.line([p1, p2], fill=color, width=width)
        else:
            draw.line([p1, p2], fill=color, width=width)

    def _tone_rgba(self, rgb: Tuple[int, int, int], mul: float, alpha: float) -> Tuple[int, int, int, int]:
        rr = max(0, min(255, int(rgb[0] * mul)))
        gg = max(0, min(255, int(rgb[1] * mul)))
        bb = max(0, min(255, int(rgb[2] * mul)))
        aa = max(0, min(255, int(255 * alpha)))
        return rr, gg, bb, aa

    def _draw_player_marker(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int) -> None:
        # 朝上的箭头，亮黄色，带描边
        size = max(10, int(s * 1.2))
        half = size // 2
        arrow = [
            (cx, cy - size),
            (cx + half, cy),
            (cx + half // 2, cy),
            (cx + half // 2, cy + size),
            (cx - half // 2, cy + size),
            (cx - half // 2, cy),
            (cx - half, cy),
        ]
        draw.polygon(arrow, fill=(255, 210, 0, 255))
        draw.line(arrow + [arrow[0]], fill=(20, 20, 20, 255), width=2)

    def _draw_coordinate_axes(self, draw: ImageDraw.ImageDraw, dx: int, dy: int, cfg: RenderConfig) -> None:
        """绘制坐标轴方向标注"""
        # 轴的长度（像素）
        axis_length = cfg.block_size * 3
        
        # 起始点（左下角，留出边距）
        margin = 50
        start_x = margin
        start_y = cfg.image_height - margin
        
        # 绘制X轴（红色，指向右）
        x_end_x = start_x + axis_length
        x_end_y = start_y
        draw.line([(start_x, start_y), (x_end_x, x_end_y)], fill=(255, 0, 0, 255), width=3)
        # X轴箭头
        self._draw_axis_arrow(draw, (x_end_x, x_end_y), (1, 0), (255, 0, 0, 255))
        # X轴标签
        self._draw_axis_label(draw, "X", (x_end_x + 6, x_end_y - 10), (255, 0, 0, 255))
        
        # 绘制Z轴（蓝色，指向左上方，等距投影）
        z_end_x = start_x - axis_length // 2
        z_end_y = start_y - axis_length // 4
        draw.line([(start_x, start_y), (z_end_x, z_end_y)], fill=(0, 0, 255, 255), width=3)
        # Z轴箭头
        self._draw_axis_arrow(draw, (z_end_x, z_end_y), (-0.5, -0.25), (0, 0, 255, 255))
        # Z轴标签
        self._draw_axis_label(draw, "Z", (z_end_x - 10, z_end_y - 14), (0, 0, 255, 255))
        
        # 绘制Y轴（绿色，指向上方）
        y_end_x = start_x
        y_end_y = start_y - axis_length
        draw.line([(start_x, start_y), (y_end_x, y_end_y)], fill=(0, 255, 0, 255), width=3)
        # Y轴箭头
        self._draw_axis_arrow(draw, (y_end_x, y_end_y), (0, -1), (0, 255, 0, 255))
        # Y轴标签
        self._draw_axis_label(draw, "Y", (y_end_x - 8, y_end_y - 18), (0, 255, 0, 255))
        
        # 绘制原点标记
        draw.ellipse([(start_x - 3, start_y - 3), (start_x + 3, start_y + 3)], 
                    fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=1)
        # 不绘制图例

    def _draw_axis_arrow(self, draw: ImageDraw.ImageDraw, pos: Tuple[int, int], 
                         direction: Tuple[float, float], color: Tuple[int, int, int, int]) -> None:
        """绘制轴箭头"""
        x, y = pos
        dx, dy = direction
        
        # 箭头大小
        arrow_size = 8
        
        # 计算箭头的两个端点
        perp_x, perp_y = -dy, dx  # 垂直方向
        
        # 箭头头部
        arrow_tip = (x, y)
        arrow_left = (int(x - arrow_size * dx + arrow_size * 0.5 * perp_x), 
                     int(y - arrow_size * dy + arrow_size * 0.5 * perp_y))
        arrow_right = (int(x - arrow_size * dx - arrow_size * 0.5 * perp_x), 
                      int(y - arrow_size * dy - arrow_size * 0.5 * perp_y))
        
        # 绘制箭头
        arrow_points = [arrow_tip, arrow_left, arrow_right]
        draw.polygon(arrow_points, fill=color)

    def _draw_axis_label(self, draw: ImageDraw.ImageDraw, label: str, pos: Tuple[int, int], 
                         color: Tuple[int, int, int, int]) -> None:
        """使用标准字体绘制轴标签，避免字体渲染异常"""
        x, y = pos
        try:
            font = ImageFont.load_default()
            draw.text((x, y), label, fill=color, font=font)
        except Exception:
            # 回退：若字体加载失败，使用小矩形代替
            draw.rectangle([(x, y), (x + 6, y + 6)], fill=color)

    def _draw_legend(self, draw: ImageDraw.ImageDraw, x: int, y: int, cfg: RenderConfig) -> None:
        """保留占位函数，但不绘制任何图例（按需求移除图例显示）"""
        return


__all__ = ["BlockCacheRenderer", "RenderConfig"]


