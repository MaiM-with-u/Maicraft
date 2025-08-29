"""
方块缓存渲染模块
将 BlockCache 中的方块以等距投影渲染为二维图像，便于快速预览。
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple, Dict, Set, Any
import numpy as np

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64
import colorsys
import math

from agent.block_cache.block_cache import BlockCache, CachedBlock, global_block_cache
from agent.environment.environment import global_environment


@dataclass
class Vector3:
    """3D向量"""
    x: float
    y: float
    z: float
    
    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    
    def normalize(self):
        length = self.length()
        if length > 0:
            return Vector3(self.x / length, self.y / length, self.z / length)
        return Vector3(0, 0, 0)
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other):
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

@dataclass
class Camera:
    """相机系统"""
    position: Vector3          # 相机位置
    target: Vector3           # 目标点（看向的位置）
    up: Vector3              # 向上向量
    fov_degrees: float       # 视野角度
    near_plane: float        # 近裁剪面
    far_plane: float         # 远裁剪面
    
    def get_view_matrix(self):
        """计算视图矩阵"""
        # 计算相机的局部坐标系
        forward = (self.target - self.position).normalize()  # Z轴（向前）
        right = forward.cross(self.up).normalize()          # X轴（向右）
        up = right.cross(forward).normalize()               # Y轴（向上）
        
        # 视图矩阵（世界坐标到相机坐标的变换）
        view_matrix = np.array([
            [right.x, right.y, right.z, -right.dot(self.position)],
            [up.x, up.y, up.z, -up.dot(self.position)],
            [-forward.x, -forward.y, -forward.z, forward.dot(self.position)],
            [0, 0, 0, 1]
        ])
        return view_matrix
    
    def get_projection_matrix(self, aspect_ratio):
        """计算投影矩阵"""
        fov_rad = math.radians(self.fov_degrees)
        f = 1.0 / math.tan(fov_rad / 2.0)
        
        projection_matrix = np.array([
            [f / aspect_ratio, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (self.far_plane + self.near_plane) / (self.near_plane - self.far_plane), 
             (2 * self.far_plane * self.near_plane) / (self.near_plane - self.far_plane)],
            [0, 0, -1, 0]
        ])
        return projection_matrix

@dataclass
class Block3D:
    """3D空间中的方块"""
    position: Vector3
    block_type: str
    
    def get_vertices(self):
        """获取立方体的8个顶点"""
        x, y, z = self.position.x, self.position.y, self.position.z
        return [
            Vector3(x, y, z),         # 0: 左后下
            Vector3(x+1, y, z),       # 1: 右后下
            Vector3(x+1, y, z+1),     # 2: 右前下
            Vector3(x, y, z+1),       # 3: 左前下
            Vector3(x, y+1, z),       # 4: 左后上
            Vector3(x+1, y+1, z),     # 5: 右后上
            Vector3(x+1, y+1, z+1),   # 6: 右前上
            Vector3(x, y+1, z+1),     # 7: 左前上
        ]
    
    def get_faces(self):
        """获取立方体的6个面（顶点索引）"""
        return [
            ([0, 1, 2, 3], "bottom"),   # 底面
            ([4, 7, 6, 5], "top"),      # 顶面
            ([0, 4, 5, 1], "back"),     # 后面 (-z)
            ([2, 6, 7, 3], "front"),    # 前面 (+z)
            ([0, 3, 7, 4], "left"),     # 左面 (-x)
            ([1, 5, 6, 2], "right"),    # 右面 (+x)
        ]

class Renderer3D:
    """3D渲染管道"""
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.blocks: List[Block3D] = []
        self.camera = Camera(
            position=Vector3(0, 2, 5),
            target=Vector3(0, 0, 0),
            up=Vector3(0, 1, 0),
            fov_degrees=90,
            near_plane=0.1,
            far_plane=100.0
        )
    
    def add_block(self, block: Block3D):
        """添加方块到3D空间"""
        self.blocks.append(block)
    
    def clear_blocks(self):
        """清空所有方块"""
        self.blocks.clear()
    
    def world_to_screen(self, world_pos: Vector3):
        """将3D世界坐标转换为2D屏幕坐标"""
        # 转换为齐次坐标
        world_pos_4d = np.array([world_pos.x, world_pos.y, world_pos.z, 1.0])
        
        # 应用视图变换
        view_matrix = self.camera.get_view_matrix()
        view_pos = view_matrix @ world_pos_4d
        
        # 应用投影变换
        aspect_ratio = self.width / self.height
        projection_matrix = self.camera.get_projection_matrix(aspect_ratio)
        clip_pos = projection_matrix @ view_pos
        
        # 透视除法
        if clip_pos[3] != 0:
            ndc_pos = clip_pos[:3] / clip_pos[3]
        else:
            return None  # 点在相机后面
        
        # NDC到屏幕坐标
        screen_x = int((ndc_pos[0] + 1) * 0.5 * self.width)
        screen_y = int((1 - ndc_pos[1]) * 0.5 * self.height)  # Y轴翻转
        depth = ndc_pos[2]
        
        return (screen_x, screen_y, depth)
    
    def is_face_visible(self, face_vertices: List[Vector3]):
        """背面剔除：检查面是否朝向相机"""
        if len(face_vertices) < 3:
            return False
        
        # 计算面的法向量
        v1 = face_vertices[1] - face_vertices[0]
        v2 = face_vertices[2] - face_vertices[0]
        normal = v1.cross(v2).normalize()
        
        # 从面中心到相机的向量
        face_center = Vector3(0, 0, 0)
        for v in face_vertices:
            face_center = face_center + v
        face_center = face_center * (1.0 / len(face_vertices))
        
        to_camera = (self.camera.position - face_center).normalize()
        
        # 如果法向量与到相机的向量夹角小于90度，则面朝向相机
        return normal.dot(to_camera) > 0
    
    def is_block_in_frustum(self, block_pos: Vector3) -> bool:
        """检查方块是否在视锥内（简化的视锥剔除）"""
        # 计算方块到相机的向量
        to_block = block_pos - self.camera.position
        
        # 计算相机朝向
        forward = (self.camera.target - self.camera.position).normalize()
        
        # 点积检查方块是否在相机前方
        if to_block.dot(forward) < self.camera.near_plane:
            return False
        
        # 距离检查
        if to_block.length() > self.camera.far_plane:
            return False
        
        # 简化的FOV检查（可以进一步优化）
        distance = to_block.length()
        if distance > 0:
            # 角度检查
            angle = math.acos(max(-1, min(1, to_block.dot(forward) / distance)))
            fov_rad = math.radians(self.camera.fov_degrees)
            if angle > fov_rad / 2 * 1.2:  # 稍微放宽一点避免边界问题
                return False
        
        return True
    
    def render_to_image(self):
        """渲染3D场景到2D图像"""
        img = Image.new("RGBA", (self.width, self.height), (16, 16, 20, 255))
        draw = ImageDraw.Draw(img)
        
        # 收集所有需要绘制的面
        face_list = []
        
        for block in self.blocks:
            # 视锥剔除：跳过不在视野内的方块
            if not self.is_block_in_frustum(block.position):
                continue
                
            vertices = block.get_vertices()
            faces = block.get_faces()
            
            # 计算每个面的屏幕坐标和深度
            for face_indices, face_name in faces:
                face_vertices_3d = [vertices[i] for i in face_indices]
                
                # 背面剔除
                if not self.is_face_visible(face_vertices_3d):
                    continue
                
                # 转换为屏幕坐标
                face_vertices_2d = []
                face_depth = 0
                valid_face = True
                
                for vertex in face_vertices_3d:
                    screen_pos = self.world_to_screen(vertex)
                    if screen_pos is None:
                        valid_face = False
                        break
                    face_vertices_2d.append((screen_pos[0], screen_pos[1]))
                    face_depth += screen_pos[2]
                
                if valid_face:
                    face_depth /= len(face_vertices_3d)  # 平均深度
                    face_list.append((face_depth, face_vertices_2d, face_name, block.block_type))
        
        # 按深度排序（远到近）
        face_list.sort(key=lambda x: x[0], reverse=True)
        
        # 绘制每个面
        for depth, vertices_2d, face_name, block_type in face_list:
            self._draw_face_2d(draw, vertices_2d, face_name, block_type)
        
        # 绘制准星
        self._draw_crosshair_2d(draw)
        
        return img
    
    def _draw_face_2d(self, draw: ImageDraw.ImageDraw, vertices_2d: List[Tuple[int, int]], 
                      face_name: str, block_type: str):
        """在2D空间中绘制一个面"""
        # 获取面的颜色
        color = self._get_face_color(block_type, face_name)
        
        # 绘制多边形
        if len(vertices_2d) >= 3:
            draw.polygon(vertices_2d, fill=color, outline=self._darken_color(color))
    
    def _get_face_color(self, block_type: str, face_name: str):
        """获取面的颜色"""
        # 扩展的颜色映射
        color_map = {
            "grass_block": {
                "top": (95, 159, 53, 255),      # 草绿色顶面
                "bottom": (134, 96, 67, 255),   # 土色底面
                "front": (134, 96, 67, 255),    # 土色侧面
                "back": (134, 96, 67, 255),
                "left": (134, 96, 67, 255),
                "right": (134, 96, 67, 255),
            },
            "stone": {
                "top": (125, 125, 125, 255),
                "bottom": (100, 100, 100, 255),
                "front": (110, 110, 110, 255),
                "back": (105, 105, 105, 255),
                "left": (115, 115, 115, 255),
                "right": (108, 108, 108, 255),
            },
            "dirt": {
                "top": (134, 96, 67, 255),
                "bottom": (120, 85, 60, 255),
                "front": (125, 90, 63, 255),
                "back": (122, 87, 61, 255),
                "left": (130, 93, 65, 255),
                "right": (127, 91, 64, 255),
            },
            "water": {
                "top": (52, 126, 232, 180),     # 半透明水面
                "bottom": (42, 106, 202, 180),
                "front": (47, 116, 217, 180),
                "back": (45, 111, 210, 180),
                "left": (50, 121, 227, 180),
                "right": (48, 118, 220, 180),
            },
            "wood": {
                "top": (160, 130, 75, 255),     # 木头颜色
                "bottom": (140, 110, 65, 255),
                "front": (150, 120, 70, 255),
                "back": (145, 115, 68, 255),
                "left": (155, 125, 72, 255),
                "right": (152, 122, 71, 255),
            },
            "sand": {
                "top": (237, 201, 175, 255),    # 沙子颜色
                "bottom": (220, 185, 160, 255),
                "front": (230, 195, 170, 255),
                "back": (225, 190, 165, 255),
                "left": (235, 200, 175, 255),
                "right": (232, 197, 172, 255),
            },
        }
        
        # 默认颜色（灰色系）
        default_colors = {
            "top": (150, 150, 150, 255),
            "bottom": (120, 120, 120, 255),
            "front": (135, 135, 135, 255),
            "back": (130, 130, 130, 255),
            "left": (140, 140, 140, 255),
            "right": (132, 132, 132, 255),
        }
        
        # 查找颜色
        block_type_clean = block_type.lower().replace("minecraft:", "")
        block_colors = color_map.get(block_type_clean, default_colors)
        return block_colors.get(face_name, default_colors[face_name])
    
    def _darken_color(self, color: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """使颜色变暗，用于边框"""
        factor = 0.7
        return (
            int(color[0] * factor),
            int(color[1] * factor),
            int(color[2] * factor),
            color[3]
        )
    
    def _draw_crosshair_2d(self, draw: ImageDraw.ImageDraw):
        """绘制2D准星"""
        center_x = self.width // 2
        center_y = self.height // 2
        size = 10
        color = (255, 255, 255, 200)
        
        # 水平线
        draw.line([(center_x - size, center_y), (center_x + size, center_y)], fill=color, width=2)
        # 垂直线
        draw.line([(center_x, center_y - size), (center_x, center_y + size)], fill=color, width=2)

def create_test_scene():
    """创建一个测试场景来验证3D渲染系统"""
    renderer = Renderer3D(800, 600)
    
    # 设置相机位置
    renderer.camera.position = Vector3(5, 3, 5)
    renderer.camera.target = Vector3(0, 0, 0)
    renderer.camera.fov_degrees = 75
    
    # 添加一些测试方块
    test_blocks = [
        Block3D(Vector3(0, 0, 0), "grass_block"),
        Block3D(Vector3(1, 0, 0), "stone"),
        Block3D(Vector3(0, 1, 0), "dirt"),
        Block3D(Vector3(-1, 0, 0), "grass_block"),
        Block3D(Vector3(0, 0, 1), "stone"),
        Block3D(Vector3(0, 0, -1), "dirt"),
    ]
    
    for block in test_blocks:
        renderer.add_block(block)
    
    return renderer.render_to_image()

def setup_first_person_camera(renderer_3d: Renderer3D, player_pos, player_height: float = 1.6, fov: float = 90.0):
    """设置第一人称相机参数"""
    if player_pos:
        # 相机位置在玩家眼睛高度
        camera_pos = Vector3(player_pos.x, player_pos.y + player_height, player_pos.z)
        # 朝向-x方向
        target_pos = Vector3(player_pos.x - 1, player_pos.y + player_height, player_pos.z)
        
        renderer_3d.camera.position = camera_pos
        renderer_3d.camera.target = target_pos
        renderer_3d.camera.up = Vector3(0, 1, 0)
        renderer_3d.camera.fov_degrees = fov
        renderer_3d.camera.near_plane = 0.1
        renderer_3d.camera.far_plane = 50.0

def test_3d_rendering():
    """测试3D渲染系统的函数"""
    print("Testing 3D rendering system...")
    
    try:
        # 创建测试场景
        test_image = create_test_scene()
        
        # 保存测试图像
        test_image.save("test_3d_render.png")
        print("✅ 3D rendering test successful! Image saved as 'test_3d_render.png'")
        
        return True
    except Exception as e:
        print(f"❌ 3D rendering test failed: {e}")
        return False

@dataclass
class RenderConfig:
    image_width: int = 1024
    image_height: int = 768
    background_color: Tuple[int, int, int, int] = (16, 16, 20, 255)
    block_size: int = 16  # 单位立方体基准尺寸（像素）
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
    # 第一人称视角配置
    render_mode: str = "isometric" # "isometric" or "first_person"
    player_height: float = 1.6 # 玩家眼睛高度
    fov_horizontal: float = 90.0 # 水平视野角度 (degrees)
    fov_vertical: float = 60.0 # 垂直视野角度 (degrees)
    view_distance: float = 10.0 # 视野距离

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
                          data_uri: bool = False) -> str:
        """渲染并返回图像的Base64字符串。
        - image_format: "PNG" 或 "JPEG"
        - data_uri: True时返回 data URI 前缀
        """
        img = self.render(center=center, radius=radius, save_path=None)
        buffer = BytesIO()
        fmt = image_format.upper()
        img.save(buffer, format=fmt)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        if data_uri:
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            return f"data:{mime};base64,{encoded}"
        return encoded

    def get_last_render_base64(self, image_format: str = "PNG", data_uri: bool = False) -> Optional[str]:
        """返回最近一次渲染图像的Base64字符串；若还未渲染则返回None。"""
        if self._last_image is None:
            return None
        buffer = BytesIO()
        fmt = image_format.upper()
        self._last_image.save(buffer, format=fmt)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        if data_uri:
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            return f"data:{mime};base64,{encoded}"
        return encoded

    # === 内部方法 ===
    def _collect_blocks(self,
                        center: Optional[Tuple[float, float, float]],
                        radius: Optional[float]) -> List[CachedBlock]:
        if center is not None and radius is not None:
            cx, cy, cz = center
            blocks = self.cache.get_blocks_in_range(cx, cy, cz, radius)
        # 无范围限制则渲染全部
        else:
            blocks = list(self.cache._position_cache.values())  # 受控访问，仅用于渲染预览

        # 过滤掉空气与排除类型
        filtered: List[CachedBlock] = []
        for b in blocks:
            bt = b.block_type
            if bt in self.config.exclude_types:
                continue
            # 常见字符串标记
            if isinstance(bt, str) and bt.lower() == "air":
                continue
            filtered.append(b)
        return filtered

    def _render_blocks(self, blocks: Iterable[CachedBlock], auto_center: bool) -> Image.Image:
        cfg = self.config
        
        # 根据渲染模式选择渲染方法
        if cfg.render_mode == "first_person":
            return self._render_first_person(blocks)
        else:
            return self._render_isometric(blocks, auto_center)

    def _render_isometric(self, blocks: Iterable[CachedBlock], auto_center: bool) -> Image.Image:
        """等距投影渲染方法"""
        cfg = self.config
        img = Image.new("RGBA", (cfg.image_width, cfg.image_height), cfg.background_color)
        draw = ImageDraw.Draw(img, "RGBA")
        # 保存当前图像用于半透明合成
        self._current_img = img

        # 基于邻居的简单遮挡剔除：若 +x、+y、+z 三方向均有方块，则认为该方块被完全遮挡
        occupied: Set[Tuple[int, int, int]] = set()
        for _b in blocks:
            occupied.add((int(_b.position.x), int(_b.position.y), int(_b.position.z)))

        visible_blocks: List[CachedBlock] = []
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
        projected_raw: List[Tuple[int, int, float, CachedBlock]] = []
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
            # 优先使用玩家位置居中
            player_pos = getattr(global_environment, "position", None)
            if player_pos is not None:
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
                ppos = getattr(global_environment, "position", None)
                if ppos is not None:
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
            player_pos = getattr(global_environment, "position", None)
            if player_pos is not None:
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

    def _render_first_person(self, blocks: Iterable[CachedBlock]) -> Image.Image:
        """第一人称渲染方法 - 使用3D渲染管道"""
        cfg = self.config
        
        # 创建3D渲染器
        renderer_3d = Renderer3D(cfg.image_width, cfg.image_height)
        
        # 设置第一人称相机
        player_pos = global_environment.get('player_pos')
        if not player_pos:
            # 如果没有玩家位置，回退到等距投影
            return self._render_isometric(blocks, True)
        
        setup_first_person_camera(renderer_3d, player_pos, cfg.player_height, cfg.fov_horizontal)
        
        # 过滤可见方块（视距范围内）
        camera_pos = renderer_3d.camera.position
        visible_blocks = []
        
        for block in blocks:
            # 计算距离
            dx = block.position.x - camera_pos.x
            dy = block.position.y - camera_pos.y
            dz = block.position.z - camera_pos.z
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            # 只添加视距范围内的方块
            if distance <= cfg.view_distance:
                block_3d = Block3D(
                    position=Vector3(block.position.x, block.position.y, block.position.z),
                    block_type=str(block.block_type)
                )
                renderer_3d.add_block(block_3d)
        
        # 渲染3D场景到2D图像
        return renderer_3d.render_to_image()

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

    def _draw_first_person_block(self, draw: ImageDraw.ImageDraw, block_x: int, block_y: int, block_z: int,
                                  face_colors: Dict[str, Tuple[int, int, int, int]]) -> None:
        """第一人称视角下的方块绘制 - 真正的透视投影"""
        # 获取玩家位置和视角参数
        from .renderer import global_environment
        player_pos = global_environment.get('player_pos')
        if not player_pos:
            return
            
        eye_x = player_pos.x
        eye_y = player_pos.y + self.config.player_height
        eye_z = player_pos.z
        
        # 立方体的8个顶点（1x1x1的标准立方体）
        vertices_3d = [
            # 底面四个顶点 (y = block_y)
            (block_x, block_y, block_z),         # 0: 左后下
            (block_x + 1, block_y, block_z),     # 1: 右后下  
            (block_x + 1, block_y, block_z + 1), # 2: 右前下
            (block_x, block_y, block_z + 1),     # 3: 左前下
            # 顶面四个顶点 (y = block_y + 1)
            (block_x, block_y + 1, block_z),     # 4: 左后上
            (block_x + 1, block_y + 1, block_z), # 5: 右后上
            (block_x + 1, block_y + 1, block_z + 1), # 6: 右前上
            (block_x, block_y + 1, block_z + 1), # 7: 左前上
        ]
        
        # 将3D顶点投影到2D屏幕坐标
        vertices_2d = []
        for vx, vy, vz in vertices_3d:
            screen_x, screen_y = self._project_3d_to_2d(vx, vy, vz, eye_x, eye_y, eye_z)
            vertices_2d.append((screen_x, screen_y))
        
        # 定义立方体的6个面（顶点索引）
        faces = [
            ([0, 1, 2, 3], face_colors["bottom"]),  # 底面
            ([4, 7, 6, 5], face_colors["top"]),     # 顶面  
            ([0, 4, 5, 1], face_colors["back"]),    # 后面 (-z方向)
            ([2, 6, 7, 3], face_colors["front"]),   # 前面 (+z方向)
            ([0, 3, 7, 4], face_colors["left"]),    # 左面 (-x方向)
            ([1, 5, 6, 2], face_colors["right"]),   # 右面 (+x方向)
        ]
        
        # 计算面的深度并排序（从远到近绘制）
        face_depths = []
        for face_indices, color in faces:
            # 计算面中心的Z深度（相对于玩家）
            center_z = sum((vertices_3d[i][2] - eye_z) for i in face_indices) / 4
            center_x = sum((vertices_3d[i][0] - eye_x) for i in face_indices) / 4
            depth = math.sqrt(center_x*center_x + center_z*center_z)
            face_depths.append((depth, face_indices, color))
        
        # 按深度排序（远的先画）
        face_depths.sort(key=lambda x: x[0], reverse=True)
        
        # 绘制每个面
        for depth, face_indices, color in face_depths:
            # 背面剔除：只绘制朝向玩家的面
            if self._is_face_visible(face_indices, vertices_3d, eye_x, eye_y, eye_z):
                face_2d = [vertices_2d[i] for i in face_indices]
                self._poly(draw, face_2d, color)

    def _draw_first_person_grass_block(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int) -> None:
        """第一人称视角下的草方块绘制 - 3D立体效果"""
        tile_w = s
        tile_h = s // 2
        h = int(round(s * self.config.vertical_scale))

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

        # 顶面：上边 1/4 绿色，下边 3/4 仍为绿色，但我们用一条水平带体现"上1/4"
        top_poly = [
            (cx, cy - tile_h - 1),
            (cx + tile_w + 1, cy - 1),
            (cx, cy + tile_h + 1),
            (cx - tile_w - 1, cy - 1),
        ]
        self._poly(draw, top_poly, grass_top)

        # 在顶面内画一条稍亮的上边带，近似"上1/4"为绿色高光
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

    def _draw_first_person_grass_block_perspective(self, draw: ImageDraw.ImageDraw, block_x: int, block_y: int, block_z: int) -> None:
        """第一人称视角下的草方块透视绘制"""
        # 基础颜色：顶部草绿，侧面为土的明暗
        grass_top = (95, 159, 53, 255)  # 草绿
        dirt_base = (160, 120, 80)      # 土色

        def tone(rgb: Tuple[int, int, int], mul: float, a: int = 255) -> Tuple[int, int, int, int]:
            rr = max(0, min(255, int(rgb[0] * mul)))
            gg = max(0, min(255, int(rgb[1] * mul)))
            bb = max(0, min(255, int(rgb[2] * mul)))
            return rr, gg, bb, a

        # 构建面颜色字典
        face_colors = {
            "top": grass_top,
            "bottom": tone(dirt_base, 0.60),
            "left": tone(dirt_base, 0.85),
            "right": tone(dirt_base, 0.70),
            "front": tone(dirt_base, 0.75),
            "back": tone(dirt_base, 0.65),
        }
        
        # 使用标准的透视投影方块绘制
        self._draw_first_person_block(draw, block_x, block_y, block_z, face_colors)

    def _draw_first_person_crossed_planes_perspective(self, draw: ImageDraw.ImageDraw, block_x: int, block_y: int, block_z: int,
                                                     color: Tuple[int, int, int, int]) -> None:
        """第一人称视角下的交叉平面透视绘制"""
        # 获取玩家位置
        from .renderer import global_environment
        player_pos = global_environment.get('player_pos')
        if not player_pos:
            return
            
        eye_x = player_pos.x
        eye_y = player_pos.y + self.config.player_height
        eye_z = player_pos.z
        
        # 创建两个相互垂直的薄片
        # 平面1: X-Y平面
        plane1_vertices = [
            (block_x + 0.5, block_y, block_z + 0.5),      # 底中
            (block_x + 0.5, block_y + 1, block_z + 0.5),  # 顶中
        ]
        
        # 平面2: Z-Y平面  
        plane2_vertices = [
            (block_x + 0.5, block_y, block_z + 0.5),      # 底中
            (block_x + 0.5, block_y + 1, block_z + 0.5),  # 顶中
        ]
        
        # 简化为两条垂直线的投影
        # 垂直线从底部到顶部
        bottom_2d = self._project_3d_to_2d(block_x + 0.5, block_y, block_z + 0.5, eye_x, eye_y, eye_z)
        top_2d = self._project_3d_to_2d(block_x + 0.5, block_y + 1, block_z + 0.5, eye_x, eye_y, eye_z)
        
        # 计算宽度（基于距离）
        distance = math.sqrt((block_x + 0.5 - eye_x)**2 + (block_z + 0.5 - eye_z)**2)
        width = max(2, int(10 / (1 + distance * 0.1)))
        
        # 绘制垂直的十字形
        # 垂直线
        draw.line([bottom_2d, top_2d], fill=color, width=width)
        
        # 水平线（在中间高度）
        mid_y = block_y + 0.5
        left_2d = self._project_3d_to_2d(block_x + 0.2, mid_y, block_z + 0.5, eye_x, eye_y, eye_z)
        right_2d = self._project_3d_to_2d(block_x + 0.8, mid_y, block_z + 0.5, eye_x, eye_y, eye_z)
        draw.line([left_2d, right_2d], fill=color, width=width)
        
        # 前后线
        front_2d = self._project_3d_to_2d(block_x + 0.5, mid_y, block_z + 0.2, eye_x, eye_y, eye_z)
        back_2d = self._project_3d_to_2d(block_x + 0.5, mid_y, block_z + 0.8, eye_x, eye_y, eye_z)
        draw.line([front_2d, back_2d], fill=color, width=width)

    def _draw_first_person_crossed_planes(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int,
                                          color: Tuple[int, int, int, int]) -> None:
        """第一人称视角下的交叉平面绘制（如蕨类、草等）- 3D立体效果"""
        # 两张互相垂直的立面，与世界 X/Z 轴对齐，并按等距投影呈斜向
        tile_w = s
        tile_h = s // 2
        h = int(round(s * self.config.vertical_scale))

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

    def _project_3d_to_2d(self, world_x: float, world_y: float, world_z: float, 
                          eye_x: float, eye_y: float, eye_z: float) -> Tuple[int, int]:
        """将3D世界坐标投影到2D屏幕坐标"""
        # 相对于玩家的坐标
        dx = world_x - eye_x
        dy = world_y - eye_y  
        dz = world_z - eye_z
        
        # 视角方向是-x，所以我们需要旋转坐标系
        # 原来的x变成新的-z，原来的z变成新的x
        view_x = dz   # 屏幕水平方向（原世界z轴）
        view_y = dy   # 屏幕垂直方向（原世界y轴）
        view_z = -dx  # 深度方向（原世界-x轴）
        
        # 防止除零
        if view_z <= 0.01:
            view_z = 0.01
            
        # 透视投影
        fov_h_rad = math.radians(self.config.fov_horizontal)
        fov_v_rad = math.radians(self.config.fov_vertical)
        
        # 计算投影比例
        focal_length_h = (self.config.image_width / 2) / math.tan(fov_h_rad / 2)
        focal_length_v = (self.config.image_height / 2) / math.tan(fov_v_rad / 2)
        
        # 投影到屏幕
        screen_x = int(self.config.image_width / 2 + (view_x * focal_length_h) / view_z)
        screen_y = int(self.config.image_height / 2 - (view_y * focal_length_v) / view_z)
        
        return screen_x, screen_y
    
    def _is_face_visible(self, face_indices: List[int], vertices_3d: List[Tuple[float, float, float]], 
                        eye_x: float, eye_y: float, eye_z: float) -> bool:
        """检测面是否朝向玩家（背面剔除）"""
        # 取面上的前三个顶点计算法向量
        v0 = vertices_3d[face_indices[0]]
        v1 = vertices_3d[face_indices[1]] 
        v2 = vertices_3d[face_indices[2]]
        
        # 计算两个边向量
        edge1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        edge2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        
        # 叉积得到法向量
        normal = (
            edge1[1] * edge2[2] - edge1[2] * edge2[1],
            edge1[2] * edge2[0] - edge1[0] * edge2[2], 
            edge1[0] * edge2[1] - edge1[1] * edge2[0]
        )
        
        # 从面中心到玩家的向量
        face_center = (
            sum(vertices_3d[i][0] for i in face_indices) / len(face_indices),
            sum(vertices_3d[i][1] for i in face_indices) / len(face_indices),
            sum(vertices_3d[i][2] for i in face_indices) / len(face_indices)
        )
        
        to_eye = (eye_x - face_center[0], eye_y - face_center[1], eye_z - face_center[2])
        
        # 点积 > 0 表示面朝向玩家
        dot_product = normal[0] * to_eye[0] + normal[1] * to_eye[1] + normal[2] * to_eye[2]
        return dot_product > 0

    def _draw_crosshair(self, draw: ImageDraw.ImageDraw, cfg: RenderConfig) -> None:
        """绘制准星"""
        center_x = cfg.image_width // 2
        center_y = cfg.image_height // 2
        crosshair_size = 10
        crosshair_thickness = 2
        
        # 水平线
        draw.line([(center_x - crosshair_size, center_y), (center_x + crosshair_size, center_y)],
                  fill=(255, 255, 255, 255), width=crosshair_thickness)
        # 垂直线
        draw.line([(center_x, center_y - crosshair_size), (center_x, center_y + crosshair_size)],
                  fill=(255, 255, 255, 255), width=crosshair_thickness)

# 测试代码 - 如果直接运行此文件
if __name__ == "__main__":
    print("🎮 3D渲染系统测试")
    print("================")
    
    # 运行3D渲染测试
    success = test_3d_rendering()
    
    if success:
        print("\n🎯 系统特性：")
        print("✅ 3D空间存储方块")
        print("✅ 相机外参系统（位置、旋转、FOV）")
        print("✅ 3D到2D坐标变换管道")
        print("✅ 透视投影矩阵")
        print("✅ 视锥剔除优化")
        print("✅ 背面剔除")
        print("✅ 深度排序")
        print("✅ 2D颜色渲染")
        print("✅ 第一人称视角支持")
        print("\n🎨 新的渲染管道已经准备就绪！")
        print("可以按 I 键在游戏中切换到第一人称模式")
    else:
        print("\n❌ 测试失败，请检查错误信息")


__all__ = ["BlockCacheRenderer", "RenderConfig"]


