"""
3D Minecraft第一人称窗口渲染器
使用pygame和OpenGL渲染方块环境，显示坐标和方块名称
"""
import math
import pygame
import threading
from typing import Dict, List, Optional, Tuple, Set
try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    OPENGL_AVAILABLE = True
except ImportError:
    print("警告: PyOpenGL未安装，3D渲染器将无法工作。请运行: pip install PyOpenGL PyOpenGL-accelerate")
    OPENGL_AVAILABLE = False
import time
import numpy as np

from agent.block_cache.block_cache import BlockCache, Block, global_block_cache
from agent.environment.environment import global_environment
from utils.logger import get_logger

logger = get_logger("Renderer3D")


class Renderer3D:
    """3D Minecraft第一人称窗口渲染器"""
    
    def __init__(self, cache: Optional[BlockCache] = None, window_size: Tuple[int, int] = (1200, 800)):
        self.cache = cache or global_block_cache
        self.window_size = window_size
        self.running = False
        self.thread = None
        
        # 相机参数
        self.camera_pos = [0.0, 70.0, 0.0]  # 默认相机位置
        self.camera_yaw = 0.0
        self.camera_pitch = 0.0
        self.camera_speed = 0.5
        self.mouse_sensitivity = 0.1
        
        # 视角控制模式
        self.use_bot_camera = True  # 默认使用bot视角
        self.last_mouse_move_time = 0  # 记录最后一次鼠标移动时间
        
        # 渲染参数
        self.render_distance = 50  # 渲染距离
        self.last_update_time = 0
        self.update_interval = 0.1  # 100ms更新一次
        
        # 方块颜色映射
        self.block_colors = {
            'air': None,  # 不渲染空气
            'stone': (0.5, 0.5, 0.5),
            'dirt': (0.6, 0.4, 0.2),
            'grass_block': (0.2, 0.8, 0.2),
            'oak_log': (0.4, 0.2, 0.1),
            'spruce_log': (0.3, 0.2, 0.1),
            'oak_leaves': (0.1, 0.6, 0.1),
            'spruce_leaves': (0.0, 0.4, 0.0),
            'water': (0.0, 0.3, 0.8),
            'sand': (0.9, 0.8, 0.4),
            'gravel': (0.6, 0.6, 0.6),
            'coal_ore': (0.2, 0.2, 0.2),
            'iron_ore': (0.7, 0.5, 0.3),
            'gold_ore': (0.8, 0.7, 0.2),
            'diamond_ore': (0.4, 0.8, 0.8),
        }
        
        # 缓存的方块数据
        self.cached_blocks: List[Block] = []
        # 方块位置快速查找字典（用于面剔除）
        self.block_positions: Dict[Tuple[int, int, int], Block] = {}
        
        # 字体和文本相关
        self.font = None
        self.show_labels = True  # 是否显示方块标签
        self.label_distance = 15  # 标签显示距离（可调节）
        self.text_surfaces = {}  # 缓存文本表面
        self.text_textures = {}  # 缓存OpenGL纹理ID

        # 鼠标锁定相关
        self.mouse_locked = True  # 是否锁定鼠标控制相机
        
    def start(self):
        """启动3D渲染器（在单独线程中运行）"""
        if self.running:
            logger.warning("3D渲染器已在运行中")
            return

        if not OPENGL_AVAILABLE:
            logger.error("OpenGL不可用，无法启动3D渲染器")
            raise RuntimeError("OpenGL不可用")

        try:
            self.running = True
            self.thread = threading.Thread(target=self._run_render_loop, daemon=True)
            self.thread.start()
            logger.info("3D渲染器线程已启动")

            # 等待一小段时间确保线程正常启动
            time.sleep(0.5)

            if self.thread.is_alive():
                logger.info("3D渲染器启动成功")
                return True
            else:
                logger.error("3D渲染器线程启动失败")
                self.running = False
                return False

        except Exception as e:
            logger.error(f"启动3D渲染器时发生错误: {e}")
            self.running = False
            raise
        
    def stop(self):
        """停止3D渲染器"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self._cleanup_textures()
        logger.info("3D渲染器已停止")

    def toggle_mouse_lock(self):
        """切换鼠标锁定状态"""
        self.mouse_locked = not self.mouse_locked

        # 确保pygame已初始化
        try:
            # 设置鼠标可见性和抓取状态
            if self.mouse_locked:
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                logger.info("鼠标锁定已启用 - 鼠标控制相机")
            else:
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                logger.info("鼠标锁定已禁用 - 可以自由移动鼠标")
        except Exception as e:
            logger.warning(f"设置鼠标状态失败: {e}")

        return self.mouse_locked

    def _cleanup_textures(self):
        """清理文字纹理资源"""
        try:
            # 删除所有OpenGL纹理
            texture_ids = list(self.text_textures.values())
            if texture_ids:
                # 过滤有效的纹理ID
                valid_texture_ids = [tid for tid in texture_ids if tid > 0]
                if valid_texture_ids:
                    glDeleteTextures(valid_texture_ids)
                    logger.info(f"清理了 {len(valid_texture_ids)} 个文字纹理")

            # 清空缓存
            self.text_textures.clear()
            self.text_surfaces.clear()
        except Exception as e:
            logger.warning(f"清理文字纹理时发生错误: {e}")
        
    def _run_render_loop(self):
        """渲染循环主函数"""
        try:
            logger.info("初始化pygame和OpenGL...")
            # 初始化pygame和OpenGL
            pygame.init()
            pygame.font.init()

            # 设置OpenGL显示模式（先创建上下文）
            pygame.display.set_mode(self.window_size, pygame.DOUBLEBUF | pygame.OPENGL)
            pygame.display.set_caption("Minecraft 3D View - MaicraftAgent")
            logger.info(f"创建窗口成功: {self.window_size[0]}x{self.window_size[1]}")

            # OpenGL设置（必须在字体初始化之前，因为需要有效的上下文）
            self._setup_opengl()
            logger.info("OpenGL初始化完成")

            # 初始化字体（在OpenGL上下文之后）
            try:
                # 尝试多种字体选项
                font_options = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Helvetica', 'sans-serif']
                self.font = None

                for font_name in font_options:
                    try:
                        self.font = pygame.font.SysFont(font_name, 16, bold=True)
                        if self.font is not None:
                            logger.info(f"字体初始化成功: {font_name}")
                            break
                    except Exception as e:
                        logger.debug(f"字体 '{font_name}' 初始化失败: {e}")
                        continue

                # 如果系统字体都失败，使用默认字体
                if self.font is None:
                    try:
                        self.font = pygame.font.Font(None, 24)
                        logger.info("使用默认字体初始化成功")
                    except Exception as e:
                        logger.warning(f"默认字体初始化失败: {e}")
                        self.font = None

                if self.font is None:
                    logger.warning("所有字体初始化都失败，将跳过文本渲染")

            except Exception as e:
                self.font = None
                logger.warning(f"字体初始化失败: {e}，将跳过文本渲染")

            # 根据鼠标锁定状态设置鼠标
            if self.mouse_locked:
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                logger.info("鼠标锁定已启用")
            else:
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                logger.info("鼠标锁定已禁用")
            
            clock = pygame.time.Clock()
            
            while self.running:
                current_time = time.time()
                
                # 处理事件
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.running = False
                        elif event.key == pygame.K_F2:
                            self.show_labels = not self.show_labels
                            logger.info(f"方块标签显示: {'开启' if self.show_labels else '关闭'}")
                        elif event.key == pygame.K_F3:
                            self.toggle_mouse_lock()
                        elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:  # 增加标签显示距离
                            self.label_distance = min(50, self.label_distance + 5)
                            logger.info(f"标签显示距离增加到: {self.label_distance}")
                        elif event.key == pygame.K_MINUS:  # 减少标签显示距离
                            self.label_distance = max(5, self.label_distance - 5)
                            logger.info(f"标签显示距离减少到: {self.label_distance}")
                        elif event.key == pygame.K_F4:  # 切换相机控制模式
                            self.use_bot_camera = not self.use_bot_camera
                            mode_text = "Bot自动控制" if self.use_bot_camera else "手动控制"
                            logger.info(f"相机控制模式切换为: {mode_text}")
                            if not self.use_bot_camera:
                                self.last_mouse_move_time = time.time()
                    elif event.type == pygame.MOUSEMOTION and self.mouse_locked:
                        self._handle_mouse_movement(event.rel)
                
                # 处理键盘输入
                self._handle_keyboard_input()
                
                # 更新bot相机视角
                self._update_bot_camera()
                
                # 更新相机位置（跟随玩家）
                self._update_camera_from_player()
                
                # 更新方块缓存数据
                if current_time - self.last_update_time > self.update_interval:
                    self._update_cached_blocks()
                    self.last_update_time = current_time
                
                # 渲染场景
                self._render_scene()
                
                pygame.display.flip()
                clock.tick(60)  # 60 FPS
                
        except Exception as e:
            logger.error(f"3D渲染器运行错误: {e}")
        finally:
            try:
                pygame.event.set_grab(False)
                pygame.mouse.set_visible(True)
                pygame.quit()
            except:
                pass
    
    def _setup_opengl(self):
        """设置OpenGL参数"""
        # 启用深度测试
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glClearDepth(1.0)

        # 启用背面剔除（重要：防止看到方块内部）
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glFrontFace(GL_CCW)  # 逆时针为正面

        # 设置透视投影
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60, self.window_size[0] / self.window_size[1], 0.1, 1000.0)

        # 设置模型视图矩阵
        glMatrixMode(GL_MODELVIEW)

        # 设置光照
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        # 环境光
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.4, 0.4, 0.4, 1.0])
        # 漫反射光
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        # 镜面反射光
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])
        # 光源位置
        glLightfv(GL_LIGHT0, GL_POSITION, [100.0, 200.0, 100.0, 0.0])

        # 材质设置
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        # 背景色（天空蓝）
        glClearColor(0.5, 0.8, 1.0, 1.0)

        # 其他渲染设置
        glShadeModel(GL_SMOOTH)
        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        
    def _handle_mouse_movement(self, rel: Tuple[int, int]):
        """处理鼠标移动"""
        dx, dy = rel
        
        # 检测到鼠标移动，切换到手动控制模式
        if abs(dx) > 1 or abs(dy) > 1:  # 只有明显的鼠标移动才切换模式
            self.use_bot_camera = False
            self.last_mouse_move_time = time.time()
            logger.info("切换到手动相机控制模式")
        
        self.camera_yaw += dx * self.mouse_sensitivity
        self.camera_pitch += dy * self.mouse_sensitivity  # 修正垂直反转问题
        
        # 限制俯仰角
        self.camera_pitch = max(-89, min(89, self.camera_pitch))
        
    def _update_bot_camera(self):
        """更新bot的相机视角"""
        try:
            # 检查是否应该切换回bot控制模式
            current_time = time.time()
            if not self.use_bot_camera and (current_time - self.last_mouse_move_time > 3.0):
                # 3秒没有鼠标移动，切换回bot控制
                self.use_bot_camera = True
                logger.info("切换回bot相机控制模式")
            
            if self.use_bot_camera and global_environment:
                # 使用bot的视角
                if hasattr(global_environment, 'yaw') and hasattr(global_environment, 'pitch'):
                    self.camera_yaw = global_environment.yaw
                    self.camera_pitch = global_environment.pitch
                    
                    # 限制俯仰角
                    self.camera_pitch = max(-89, min(89, self.camera_pitch))
                    
                # 使用bot的位置（如果有的话）
                if hasattr(global_environment, 'position') and global_environment.position:
                    self.camera_pos[0] = global_environment.position.x
                    self.camera_pos[1] = global_environment.position.y + 1.6  # 眼睛高度
                    self.camera_pos[2] = global_environment.position.z
                    
        except Exception as e:
            logger.warning(f"更新bot相机视角失败: {e}")
    
    def _handle_keyboard_input(self):
        """处理键盘输入"""
        keys = pygame.key.get_pressed()
        
        # 计算前向和右向向量
        yaw_rad = math.radians(self.camera_yaw)
        forward = [math.sin(yaw_rad), 0, -math.cos(yaw_rad)]
        right = [math.cos(yaw_rad), 0, math.sin(yaw_rad)]
        
        speed = self.camera_speed
        if keys[pygame.K_LSHIFT]:
            speed *= 3  # 加速
        
        # WASD移动
        if keys[pygame.K_w]:
            for i in range(3):
                self.camera_pos[i] += forward[i] * speed
        if keys[pygame.K_s]:
            for i in range(3):
                self.camera_pos[i] -= forward[i] * speed
        if keys[pygame.K_a]:
            for i in range(3):
                self.camera_pos[i] -= right[i] * speed
        if keys[pygame.K_d]:
            for i in range(3):
                self.camera_pos[i] += right[i] * speed
        
        # 上下移动
        if keys[pygame.K_SPACE]:
            self.camera_pos[1] += speed
        if keys[pygame.K_LCTRL]:
            self.camera_pos[1] -= speed
            
    def _update_camera_from_player(self):
        """从玩家位置更新相机位置"""
        try:
            player_positions = self.cache.get_player_positions()
            if player_positions:
                player_pos = player_positions[0].position
                # 相机跟随玩家，但允许手动偏移
                target_pos = [player_pos.x, player_pos.y + 1.7, player_pos.z]  # 玩家眼睛高度
                
                # 平滑跟随
                alpha = 0.1
                for i in range(3):
                    self.camera_pos[i] = self.camera_pos[i] * (1 - alpha) + target_pos[i] * alpha
                    
        except Exception as e:
            logger.debug(f"更新相机位置失败: {e}")
    
    def _update_cached_blocks(self):
        """更新缓存的方块数据"""
        try:
            # 获取相机周围的方块
            cx, cy, cz = self.camera_pos
            self.cached_blocks = self.cache.get_blocks_in_range(
                cx, cy, cz, self.render_distance
            )
            
            # 过滤空气方块
            self.cached_blocks = [
                block for block in self.cached_blocks
                if block.block_type != 'air' and block.block_type is not None
            ]
            
            # 更新位置查找字典（用于快速面剔除）
            self.block_positions = {}
            for block in self.cached_blocks:
                pos = (int(block.position.x), int(block.position.y), int(block.position.z))
                self.block_positions[pos] = block
            
        except Exception as e:
            logger.debug(f"更新方块缓存失败: {e}")
            self.cached_blocks = []
            self.block_positions = {}
    
    def _render_scene(self):
        """渲染场景"""
        # 清除颜色和深度缓冲区
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # 应用相机变换
        glRotatef(self.camera_pitch, 1, 0, 0)
        glRotatef(self.camera_yaw, 0, 1, 0)
        glTranslatef(-self.camera_pos[0], -self.camera_pos[1], -self.camera_pos[2])

        # 确保背面剔除启用
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)

        # 渲染方块（按照距离从远到近排序，避免深度冲突）
        sorted_blocks = sorted(self.cached_blocks,
                              key=lambda b: -(b.position.x + b.position.y + b.position.z))
        for block in sorted_blocks:
            self._render_block(block)  # 恢复正常的方块渲染

        # 渲染UI信息（在屏幕空间）
        self._render_ui()
        
        # 最后渲染所有标签，确保不被覆盖
        if self.show_labels:
            self._render_all_labels(sorted_blocks)
    
    def _render_block(self, block: Block):
        """渲染单个方块（不包含标签）"""
        x, y, z = block.position.x, block.position.y, block.position.z
        block_type = str(block.block_type).lower()
        
        # 获取方块颜色
        color = self.block_colors.get(block_type, (0.8, 0.8, 0.8))
        if color is None:
            return  # 跳过不渲染的方块
        
        glPushMatrix()
        glTranslatef(x, y, z)
        
        # 设置方块颜色
        glColor3f(*color)
        
        # 检查哪些面是可见的（面剔除）
        visible_faces = self._get_visible_faces(block)
        
        # 只渲染可见的面
        self._draw_cube_selective(visible_faces)
        
        glPopMatrix()
        # 注意：标签渲染已移至 _render_all_labels()
    
    def _render_block_only(self, block: Block):
        """只渲染方块几何体，不渲染标签"""
        x, y, z = block.position.x, block.position.y, block.position.z
        block_type = str(block.block_type).lower()
        
        # 获取方块颜色
        color = self.block_colors.get(block_type, (0.8, 0.8, 0.8))
        if color is None:
            return  # 跳过不渲染的方块
        
        glPushMatrix()
        glTranslatef(x, y, z)
        
        # 设置方块颜色
        glColor3f(*color)
        
        # 检查哪些面是可见的（面剔除）
        visible_faces = self._get_visible_faces(block)
        
        # 只渲染可见的面
        self._draw_cube_selective(visible_faces)
        
        glPopMatrix()
    
    def _render_all_labels(self, blocks):
        """渲染所有标签，在所有3D内容之后"""
        # logger.info("开始渲染所有标签...")
        
        # 保存当前3D状态
        glPushMatrix()
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        
        try:
            label_count = 0
            for block in blocks:
                # 距离检查
                x, y, z = block.position.x, block.position.y, block.position.z
                cam_x, cam_y, cam_z = self.camera_pos
                distance = math.sqrt((x - cam_x)**2 + (y - cam_y)**2 + (z - cam_z)**2)
                
                if distance <= self.label_distance:
                    self._render_block_label(block, x, y, z)
                    label_count += 1
            
            # logger.info(f"渲染了 {label_count} 个标签")
            
        except Exception as e:
            logger.error(f"标签批量渲染失败: {e}")
        finally:
            # 恢复3D状态
            glPopAttrib()
            glPopMatrix()
    
    def _get_visible_faces(self, block: Block) -> Set[str]:
        """检查方块的哪些面是可见的（面剔除）"""
        x, y, z = int(block.position.x), int(block.position.y), int(block.position.z)
        visible_faces = set()

        # 检查6个相邻位置是否有方块
        # 如果相邻位置没有方块，或者相邻方块是透明的，则该面可见
        neighbors = {
            'front': (x, y, z + 1),   # +Z 方向
            'back': (x, y, z - 1),    # -Z 方向
            'right': (x + 1, y, z),   # +X 方向
            'left': (x - 1, y, z),    # -X 方向
            'top': (x, y + 1, z),     # +Y 方向
            'bottom': (x, y - 1, z)   # -Y 方向
        }

        # 透明方块类型（包括空气和其他透明方块）
        transparent_blocks = {'air', 'water', 'glass', 'leaves', 'oak_leaves', 'spruce_leaves', 'glass_pane', 'stained_glass'}

        # 当前方块类型
        current_block_type = str(block.block_type).lower()

        for face, neighbor_pos in neighbors.items():
            # 使用快速查找检查相邻位置是否有方块
            neighbor_block = self.block_positions.get(neighbor_pos)

            # 如果没有邻居方块，该面可见
            if neighbor_block is None:
                visible_faces.add(face)
            else:
                # 如果邻居方块是透明的，该面可见
                neighbor_type = str(neighbor_block.block_type).lower()
                if neighbor_type in transparent_blocks:
                    visible_faces.add(face)
                # 如果邻居方块和当前方块都是透明的，也要显示（避免透明方块之间相互遮挡）
                elif current_block_type in transparent_blocks and neighbor_type in transparent_blocks:
                    visible_faces.add(face)

        # 如果没有可见面，强制显示至少一个面（避免方块完全消失）
        if not visible_faces:
            visible_faces.add('top')  # 默认显示顶面

        return visible_faces
    
    def _draw_cube_selective(self, visible_faces: Set[str]):
        """只绘制指定的可见面"""
        # 立方体的8个顶点（按照OpenGL标准顺序）
        # 顶点顺序：0:左下后, 1:右下后, 2:右上后, 3:左上后, 4:左下前, 5:右下前, 6:右上前, 7:左上前
        vertices = [
            [-0.5, -0.5, -0.5],  # 0: 左下后
            [0.5, -0.5, -0.5],   # 1: 右下后
            [0.5, 0.5, -0.5],    # 2: 右上后
            [-0.5, 0.5, -0.5],   # 3: 左上后
            [-0.5, -0.5, 0.5],   # 4: 左下前
            [0.5, -0.5, 0.5],    # 5: 右下前
            [0.5, 0.5, 0.5],     # 6: 右上前
            [-0.5, 0.5, 0.5]     # 7: 左上前
        ]

        # 面定义和对应的可见性检查（逆时针顺序，确保正面朝外）
        faces_info = {
            'back': {   # -Z方向（后面）
                'indices': [0, 3, 2, 1],  # 左下->左上->右上->右下
                'normal': [0, 0, -1],
                'brightness': 0.6
            },
            'front': {  # +Z方向（前面）
                'indices': [4, 5, 6, 7],  # 左下->右下->右上->左上
                'normal': [0, 0, 1],
                'brightness': 1.0
            },
            'bottom': { # -Y方向（底面）
                'indices': [0, 1, 5, 4],  # 左后->右后->右前->左前
                'normal': [0, -1, 0],
                'brightness': 0.5
            },
            'top': {    # +Y方向（顶面）
                'indices': [3, 7, 6, 2],  # 左后->左前->右前->右后
                'normal': [0, 1, 0],
                'brightness': 1.0
            },
            'left': {   # -X方向（左面）
                'indices': [0, 4, 7, 3],  # 下后->下前->上前->上后
                'normal': [-1, 0, 0],
                'brightness': 0.8
            },
            'right': {  # +X方向（右面）
                'indices': [1, 2, 6, 5],  # 下后->上后->上前->下前
                'normal': [1, 0, 0],
                'brightness': 0.9
            }
        }
        
        # 获取当前颜色
        current_color = glGetFloatv(GL_CURRENT_COLOR)
        
        # 只绘制可见的面
        for face_name, face_info in faces_info.items():
            if face_name in visible_faces:
                # 应用面的亮度
                brightness = face_info['brightness']
                glColor3f(current_color[0] * brightness, 
                         current_color[1] * brightness, 
                         current_color[2] * brightness)
                
                glBegin(GL_QUADS)
                glNormal3f(*face_info['normal'])
                for vertex_index in face_info['indices']:
                    glVertex3f(*vertices[vertex_index])
                glEnd()
        
        # 恢复原始颜色
        glColor3f(current_color[0], current_color[1], current_color[2])
        
        # 如果有可见面，绘制边框
        if visible_faces:
            self._draw_cube_edges_selective(vertices, visible_faces, faces_info)
    
    def _draw_cube_edges_selective(self, vertices, visible_faces: Set[str], faces_info):
        """只为可见面绘制边框"""
        # 暂时禁用光照
        glDisable(GL_LIGHTING)

        # 设置边框颜色（深色）
        glColor3f(0.1, 0.1, 0.1)
        glLineWidth(1.0)

        # 收集所有可见面的边
        visible_edges = set()
        edge_definitions = {
            'back': [(0, 1), (1, 2), (2, 3), (3, 0)],      # 后面四条边
            'front': [(4, 5), (5, 6), (6, 7), (7, 4)],     # 前面四条边
            'bottom': [(0, 1), (1, 5), (5, 4), (4, 0)],    # 底面四条边
            'top': [(3, 2), (2, 6), (6, 7), (7, 3)],       # 顶面四条边
            'left': [(0, 3), (3, 7), (7, 4), (4, 0)],      # 左面四条边
            'right': [(1, 2), (2, 6), (6, 5), (5, 1)]      # 右面四条边
        }

        for face_name in visible_faces:
            if face_name in edge_definitions:
                for edge in edge_definitions[face_name]:
                    # 添加边（处理顺序，确保每条边只绘制一次）
                    sorted_edge = tuple(sorted(edge))
                    visible_edges.add(sorted_edge)

        # 绘制所有可见边
        glBegin(GL_LINES)
        for edge in visible_edges:
            for vertex_index in edge:
                glVertex3f(*vertices[vertex_index])
        glEnd()

        # 重新启用光照
        glEnable(GL_LIGHTING)
    
    def _draw_cube(self):
        """绘制实心立方体"""
        # 立方体的8个顶点
        vertices = [
            [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5], [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5],  # 后面
            [-0.5, -0.5, 0.5], [0.5, -0.5, 0.5], [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5]      # 前面
        ]
        
        # 立方体的6个面（每个面4个顶点索引）
        faces = [
            [0, 1, 2, 3],  # 后面 (Z-)
            [4, 7, 6, 5],  # 前面 (Z+)
            [0, 4, 5, 1],  # 底面 (Y-)
            [2, 6, 7, 3],  # 顶面 (Y+)
            [0, 3, 7, 4],  # 左面 (X-)
            [1, 5, 6, 2]   # 右面 (X+)
        ]
        
        # 每个面的法向量
        normals = [
            [0, 0, -1],   # 后面
            [0, 0, 1],    # 前面
            [0, -1, 0],   # 底面
            [0, 1, 0],    # 顶面
            [-1, 0, 0],   # 左面
            [1, 0, 0]     # 右面
        ]
        
        # 面的亮度变化（模拟光照）
        face_brightness = [0.6, 1.0, 0.5, 1.0, 0.8, 0.9]
        
        # 获取当前颜色
        current_color = glGetFloatv(GL_CURRENT_COLOR)
        
        # 绘制每个面
        for i, face in enumerate(faces):
            # 应用面的亮度
            brightness = face_brightness[i]
            glColor3f(current_color[0] * brightness, 
                     current_color[1] * brightness, 
                     current_color[2] * brightness)
            
            glBegin(GL_QUADS)
            glNormal3f(*normals[i])
            for vertex_index in face:
                glVertex3f(*vertices[vertex_index])
            glEnd()
        
        # 恢复原始颜色
        glColor3f(current_color[0], current_color[1], current_color[2])
        
        # 绘制细边框（可选，让方块边界更清晰）
        self._draw_cube_edges(vertices)
    
    def _draw_cube_edges(self, vertices):
        """绘制立方体边框"""
        # 暂时禁用光照
        glDisable(GL_LIGHTING)
        
        # 设置边框颜色（深色）
        glColor3f(0.1, 0.1, 0.1)
        glLineWidth(1.0)
        
        # 绘制立方体的12条边
        edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],  # 后面
            [4, 5], [5, 6], [6, 7], [7, 4],  # 前面
            [0, 4], [1, 5], [2, 6], [3, 7]   # 连接前后
        ]
        
        glBegin(GL_LINES)
        for edge in edges:
            for vertex_index in edge:
                glVertex3f(*vertices[vertex_index])
        glEnd()
        
        # 重新启用光照
        glEnable(GL_LIGHTING)
    
    def _render_block_label(self, block: Block, x: float, y: float, z: float):
        """直接在方块的顶面渲染标签（3D空间中）"""
        if self.font is None:
            logger.debug("字体未初始化，跳过文字标签渲染")
            return

        cam_x, cam_y, cam_z = self.camera_pos
        distance = math.sqrt((x - cam_x)**2 + (y - cam_y)**2 + (z - cam_z)**2)

        # 严格的距离和视角控制，减少标签数量
        if distance > 6.0:  # 只显示很近的方块
            return
        
        # 添加视角过滤：只显示玩家正在看向的方块
        rel_x = x - cam_x
        rel_y = y - cam_y
        rel_z = z - cam_z
        
        # 计算相机朝向
        yaw_rad = math.radians(self.camera_yaw)
        pitch_rad = math.radians(self.camera_pitch)
        
        # 相机前向量
        cam_forward_x = math.sin(yaw_rad) * math.cos(pitch_rad)
        cam_forward_y = -math.sin(pitch_rad)
        cam_forward_z = math.cos(yaw_rad) * math.cos(pitch_rad)
        
        # 标准化相对位置向量
        rel_length = math.sqrt(rel_x*rel_x + rel_y*rel_y + rel_z*rel_z)
        if rel_length > 0:
            rel_x /= rel_length
            rel_y /= rel_length
            rel_z /= rel_length
            
            # 计算点积（角度余弦值）
            dot_product = rel_x * cam_forward_x + rel_y * cam_forward_y + rel_z * cam_forward_z
            
            # 只显示在视野前方45度内的标签
            if dot_product < 0.707:  # cos(45°) = 0.707
                return
        
        # 限制同时显示的标签数量（基于哈希随机采样）
        if hash(f"{int(x)}_{int(y)}_{int(z)}") % 3 != 0:  # 只显示1/3的标签
            return

        block_type = str(block.block_type).replace('_', ' ').title()
        coord_text = f"({int(x)}, {int(y)}, {int(z)})"

        try:
            # 在3D空间中直接渲染，位置在方块顶部稍微上方
            glPushMatrix()
            glPushAttrib(GL_ALL_ATTRIB_BITS)
            
            # 移动到方块中心稍微上方，确保位置准确
            glTranslatef(x + 0.5, y + 1.3, z + 0.5)  # 方块中心偏移
            
            # Billboard效果：让标签始终面向相机
            glRotatef(-self.camera_yaw, 0, 1, 0)
            glRotatef(-self.camera_pitch, 1, 0, 0)
            
            # 禁用深度测试，确保标签可见
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # 更小的标签，减少遮挡
            scale = max(0.3, min(0.7, 4.0 / distance))  # 更小的缩放
            glScalef(scale, scale, scale)
            
            # 渲染背景矩形 - 更紧凑
            glColor4f(0.0, 0.0, 0.0, 0.6)  # 半透明黑色背景
            glBegin(GL_QUADS)
            glVertex3f(-0.8, -0.2, 0.01)
            glVertex3f(0.8, -0.2, 0.01)
            glVertex3f(0.8, 0.4, 0.01)
            glVertex3f(-0.8, 0.4, 0.01)
            glEnd()
            
            # 渲染文字纹理
            if hasattr(self, '_text_cache') and block_type in self._text_cache:
                # 使用缓存的文字纹理
                texture_id, text_width, text_height = self._text_cache[block_type]
            else:
                # 创建新的文字纹理
                texture_id, text_width, text_height = self._create_text_texture(block_type)
                if not hasattr(self, '_text_cache'):
                    self._text_cache = {}
                self._text_cache[block_type] = (texture_id, text_width, text_height)
            
            if texture_id > 0:
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, texture_id)
                glColor4f(1.0, 1.0, 1.0, 1.0)  # 白色文字
                
                # 计算文字的实际显示尺寸 - 紧凑大小
                aspect = text_width / text_height if text_height > 0 else 1.0
                text_w = min(0.7, 0.6 * aspect)  # 更小的宽度
                text_h = 0.18
                
                glBegin(GL_QUADS)
                glTexCoord2f(0, 0); glVertex3f(-text_w, 0.15, 0.02)
                glTexCoord2f(1, 0); glVertex3f(text_w, 0.15, 0.02)
                glTexCoord2f(1, 1); glVertex3f(text_w, 0.15 + text_h, 0.02)
                glTexCoord2f(0, 1); glVertex3f(-text_w, 0.15 + text_h, 0.02)
                glEnd()
                
                glDisable(GL_TEXTURE_2D)
            
            # 渲染坐标纹理
            coord_key = f"coord_{int(x)}_{int(y)}_{int(z)}"
            if hasattr(self, '_coord_cache') and coord_key in self._coord_cache:
                coord_texture_id, coord_width, coord_height = self._coord_cache[coord_key]
            else:
                coord_texture_id, coord_width, coord_height = self._create_text_texture(coord_text)
                if not hasattr(self, '_coord_cache'):
                    self._coord_cache = {}
                self._coord_cache[coord_key] = (coord_texture_id, coord_width, coord_height)
            
            if coord_texture_id > 0:
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, coord_texture_id)
                glColor4f(0.8, 0.8, 1.0, 1.0)  # 淡蓝色坐标
                
                coord_aspect = coord_width / coord_height if coord_height > 0 else 1.0
                coord_w = min(0.6, 0.5 * coord_aspect)  # 更小的坐标
                coord_h = 0.12
                
                glBegin(GL_QUADS)
                glTexCoord2f(0, 0); glVertex3f(-coord_w, -0.18, 0.02)
                glTexCoord2f(1, 0); glVertex3f(coord_w, -0.18, 0.02)
                glTexCoord2f(1, 1); glVertex3f(coord_w, -0.18 + coord_h, 0.02)
                glTexCoord2f(0, 1); glVertex3f(-coord_w, -0.18 + coord_h, 0.02)
                glEnd()
                
                glDisable(GL_TEXTURE_2D)
            
            logger.debug(f"已渲染3D标签: {block_type} at ({x:.1f}, {y:.1f}, {z:.1f})")
            
        except Exception as e:
            logger.error(f"3D标签渲染失败: {e}")
        finally:
            glPopAttrib()
            glPopMatrix()
    
    def _create_text_texture(self, text: str):
        """创建文字纹理"""
        try:
            # 使用更大的字体获得更清晰的文字
            font_size = 48  # 增加字体大小
            large_font = pygame.font.Font(None, font_size)
            
            # 渲染高质量文字，使用抗锯齿
            text_surface = large_font.render(text, True, (255, 255, 255), (0, 0, 0, 0))
            text_width, text_height = text_surface.get_size()
            
            # 创建OpenGL纹理
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            
            # 设置纹理参数
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            
            # 转换surface到纹理数据
            texture_data = pygame.image.tostring(text_surface, "RGBA", True)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_width, text_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
            
            logger.debug(f"创建文字纹理: '{text}', 大小: {text_width}x{text_height}, ID: {texture_id}")
            return texture_id, text_width, text_height
            
        except Exception as e:
            logger.error(f"创建文字纹理失败: {e}")
            return 0, 0, 0

    def _render_screen_label(self, block_type: str, coord_text: str, screen_x: float, screen_y: float, distance: float):
        """在屏幕空间渲染标签（使用实际投影位置）"""
        logger.debug(f"渲染标签: {block_type} at 投影位置 ({screen_x:.1f}, {screen_y:.1f})")
        
        try:
            # 保存当前状态
            glPushAttrib(GL_ALL_ATTRIB_BITS)
            glPushMatrix()
            
            # 切换到屏幕空间
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, self.window_size[0], 0, self.window_size[1], -1, 1)
            
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            
            # 设置2D渲染状态
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_LIGHTING)
            glDisable(GL_TEXTURE_2D)
            glDisable(GL_CULL_FACE)
            
            # 转换Y坐标（OpenGL Y轴与屏幕相反）
            screen_y = self.window_size[1] - screen_y
            
            # 检查是否在屏幕范围内
            if 0 <= screen_x <= self.window_size[0] and 0 <= screen_y <= self.window_size[1]:
                # 在实际投影位置绘制标签
                rect_size = 25
                
                # 绘制红色矩形作为背景
                glColor3f(1.0, 0.0, 0.0)  # 红色
                glBegin(GL_QUADS)
                glVertex2f(screen_x - rect_size, screen_y - rect_size)
                glVertex2f(screen_x + rect_size, screen_y - rect_size)
                glVertex2f(screen_x + rect_size, screen_y + rect_size)
                glVertex2f(screen_x - rect_size, screen_y + rect_size)
                glEnd()
                
                # 绘制黄色小矩形作为方块名称占位符
                glColor3f(1.0, 1.0, 0.0)  # 黄色
                glBegin(GL_QUADS)
                glVertex2f(screen_x - 20, screen_y - 40)
                glVertex2f(screen_x + 20, screen_y - 40)
                glVertex2f(screen_x + 20, screen_y - 30)
                glVertex2f(screen_x - 20, screen_y - 30)
                glEnd()
                
                # 绘制青色小矩形作为坐标占位符
                glColor3f(0.0, 1.0, 1.0)  # 青色
                glBegin(GL_QUADS)
                glVertex2f(screen_x - 20, screen_y + 30)
                glVertex2f(screen_x + 20, screen_y + 30)
                glVertex2f(screen_x + 20, screen_y + 40)
                glVertex2f(screen_x - 20, screen_y + 40)
                glEnd()
                
                logger.debug(f"已绘制标签矩形 for {block_type} at ({screen_x:.0f}, {screen_y:.0f})")
            else:
                logger.debug(f"标签 {block_type} 超出屏幕范围")
                
        except Exception as e:
            logger.error(f"标签渲染失败: {e}")
        finally:
            try:
                # 恢复状态
                glMatrixMode(GL_PROJECTION)
                glPopMatrix()
                glMatrixMode(GL_MODELVIEW)
                glPopMatrix()
                glPopAttrib()
            except Exception as e:
                logger.error(f"恢复OpenGL状态失败: {e}")
    
    def _render_simple_text(self, text: str, x: float, y: float, color: tuple):
        """简化的2D文字渲染"""
        try:
            logger.debug(f"渲染文字: '{text}' at ({x:.1f}, {y:.1f})")
            
            # 使用已有的字体
            if not self.font:
                logger.warning("字体未初始化")
                return
                
            # 创建文字表面
            text_surface = self.font.render(text, True, color, (0, 0, 0, 0))
            if not text_surface:
                logger.warning(f"创建文字表面失败: {text}")
                return
                
            # 转换为纹理数据
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            width, height = text_surface.get_size()
            
            logger.debug(f"文字尺寸: {width}x{height}")
            
            # 创建OpenGL纹理
            texture_id = glGenTextures(1)
            if texture_id == 0:
                logger.warning("创建纹理失败")
                return
                
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            
            # 上传纹理数据
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            
            # 检查OpenGL错误
            error = glGetError()
            if error != GL_NO_ERROR:
                logger.warning(f"纹理上传错误: {error}")
                glDeleteTextures([texture_id])
                return
            
            # 绘制半透明背景
            glDisable(GL_TEXTURE_2D)
            glColor4f(0.0, 0.0, 0.0, 0.8)  # 半透明黑色
            padding = 4
            glBegin(GL_QUADS)
            glVertex2f(x - width//2 - padding, y - height//2 - padding)
            glVertex2f(x + width//2 + padding, y - height//2 - padding)
            glVertex2f(x + width//2 + padding, y + height//2 + padding)
            glVertex2f(x - width//2 - padding, y + height//2 + padding)
            glEnd()
            
            # 绘制文字纹理（修复Y轴翻转）
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glColor4f(1.0, 1.0, 1.0, 1.0)  # 白色，让纹理原色显示
            
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(x - width//2, y - height//2)  # 修复纹理坐标
            glTexCoord2f(1, 0); glVertex2f(x + width//2, y - height//2)
            glTexCoord2f(1, 1); glVertex2f(x + width//2, y + height//2)
            glTexCoord2f(0, 1); glVertex2f(x - width//2, y + height//2)
            glEnd()
            
            # 立即清理纹理
            glDeleteTextures([texture_id])
            
            logger.debug(f"文字渲染成功: {text}")
            
        except Exception as e:
            logger.error(f"简化文字渲染失败: {e}")
    
    def _render_2d_text(self, text: str, x: float, y: float, color: tuple, size: int):
        """在2D屏幕空间渲染文字"""
        try:
            # 创建临时字体
            temp_font = pygame.font.SysFont('Arial', size, bold=True)
            text_surface = temp_font.render(text, True, color, (0, 0, 0, 0))
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            
            # 创建临时纹理
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            
            width, height = text_surface.get_size()
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            
            # 渲染到屏幕
            glEnable(GL_TEXTURE_2D)
            glColor4f(1.0, 1.0, 1.0, 1.0)
            
            # 绘制背景
            glDisable(GL_TEXTURE_2D)
            glColor4f(0.0, 0.0, 0.0, 0.7)
            padding = 2
            glBegin(GL_QUADS)
            glVertex2f(x - width//2 - padding, y - height//2 - padding)
            glVertex2f(x + width//2 + padding, y - height//2 - padding)
            glVertex2f(x + width//2 + padding, y + height//2 + padding)
            glVertex2f(x - width//2 - padding, y + height//2 + padding)
            glEnd()
            
            # 绘制文字
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glColor4f(1.0, 1.0, 1.0, 1.0)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1); glVertex2f(x - width//2, y - height//2)
            glTexCoord2f(1, 1); glVertex2f(x + width//2, y - height//2)
            glTexCoord2f(1, 0); glVertex2f(x + width//2, y + height//2)
            glTexCoord2f(0, 0); glVertex2f(x - width//2, y + height//2)
            glEnd()
            
            # 清理临时纹理
            glDeleteTextures([texture_id])
            
        except Exception as e:
            logger.debug(f"2D文字渲染失败: {e}")
            # 回退到简单矩形
            glDisable(GL_TEXTURE_2D)
            glColor3f(*[c/255.0 for c in color])
            glBegin(GL_QUADS)
            glVertex2f(x - 30, y - 5)
            glVertex2f(x + 30, y - 5)
            glVertex2f(x + 30, y + 5)
            glVertex2f(x - 30, y + 5)
            glEnd()
    
    def _draw_text_background(self, x: float, y: float, w: float, h: float):
        """绘制文本背景"""
        glBegin(GL_QUADS)
        glVertex3f(x, y, 0)
        glVertex3f(x + w, y, 0)
        glVertex3f(x + w, y + h, 0)
        glVertex3f(x, y + h, 0)
        glEnd()
    
    def _draw_text_border(self, x: float, y: float, w: float, h: float):
        """绘制文本边框"""
        glBegin(GL_LINE_LOOP)
        glVertex3f(x, y, 0)
        glVertex3f(x + w, y, 0)
        glVertex3f(x + w, y + h, 0)
        glVertex3f(x, y + h, 0)
        glEnd()
        
    def _get_text_texture(self, text: str, color: Tuple[int, int, int]) -> int:
        """获取或创建文字纹理"""
        key = (text, color)
        if key in self.text_textures:
            return self.text_textures[key]

        if self.font is None:
            logger.debug(f"字体未初始化，无法创建文字纹理: {text}")
            return 0

        try:
            # 渲染文字到pygame表面
            text_surface = self.font.render(text, True, color, (0, 0, 0, 0))
            if text_surface is None:
                logger.warning(f"渲染文字表面失败: {text}")
                return 0

            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            if text_data is None:
                logger.warning(f"转换文字表面数据失败: {text}")
                return 0

            # 创建OpenGL纹理
            texture_id = glGenTextures(1)
            if texture_id == 0:
                logger.warning(f"创建OpenGL纹理失败，纹理ID为0: {text}")
                return 0

            glBindTexture(GL_TEXTURE_2D, texture_id)

            # 设置纹理参数
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

            width, height = text_surface.get_size()
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

            # 检查OpenGL错误
            error = glGetError()
            if error != GL_NO_ERROR:
                error_messages = {
                    0x0500: "GL_INVALID_ENUM",
                    0x0501: "GL_INVALID_VALUE",
                    0x0502: "GL_INVALID_OPERATION",
                    0x0503: "GL_STACK_OVERFLOW",
                    0x0504: "GL_STACK_UNDERFLOW",
                    0x0505: "GL_OUT_OF_MEMORY",
                    0x0506: "GL_INVALID_FRAMEBUFFER_OPERATION"
                }
                error_desc = error_messages.get(error, f"Unknown error {error}")
                logger.warning(f"OpenGL纹理创建错误: {error_desc} (代码: {error}) for text: {text}")
                glDeleteTextures([texture_id])
                return 0

            # 缓存纹理
            self.text_textures[key] = texture_id
            self.text_surfaces[key] = text_surface

            logger.debug(f"创建文字纹理成功: '{text}' ({width}x{height}), 纹理ID: {texture_id}")
            return texture_id

        except Exception as e:
            logger.warning(f"创建文字纹理失败: {text}, 错误: {e}")
            return 0
    
    def _render_text_with_background(self, text: str, x: float, y: float, color: Tuple[int, int, int], scale: float = 0.005):
        """渲染带背景的3D文字"""
        texture_id = self._get_text_texture(text, color)
        if texture_id == 0:
            return

        key = (text, color)
        if key not in self.text_surfaces:
            return

        text_surface = self.text_surfaces[key]
        width, height = text_surface.get_size()

        # 计算纹理尺寸
        tex_width = width * scale
        tex_height = height * scale

        # 背景框的尺寸（稍微大一点）
        bg_padding = 0.02 * scale * 100  # 根据文字大小调整内边距
        bg_width = tex_width + bg_padding
        bg_height = tex_height + bg_padding

        # 保存当前OpenGL状态
        glPushAttrib(GL_ENABLE_BIT | GL_TEXTURE_BIT | GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # 禁用光照
        glDisable(GL_LIGHTING)

        # 设置混合模式
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # 启用深度测试，但禁用深度写入
        glEnable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)

        # 首先绘制半透明背景框
        glDisable(GL_TEXTURE_2D)
        glColor4f(0.0, 0.0, 0.0, 0.7)  # 半透明黑色背景
        glBegin(GL_QUADS)
        glVertex3f(x - bg_width/2, y - bg_height/2, -0.01)  # 稍微靠后，避免z-fighting
        glVertex3f(x + bg_width/2, y - bg_height/2, -0.01)
        glVertex3f(x + bg_width/2, y + bg_height/2, -0.01)
        glVertex3f(x - bg_width/2, y + bg_height/2, -0.01)
        glEnd()

        # 绘制背景边框
        glColor4f(1.0, 1.0, 1.0, 0.8)  # 白色边框
        glLineWidth(1.0)
        glBegin(GL_LINE_LOOP)
        glVertex3f(x - bg_width/2, y - bg_height/2, -0.005)
        glVertex3f(x + bg_width/2, y - bg_height/2, -0.005)
        glVertex3f(x + bg_width/2, y + bg_height/2, -0.005)
        glVertex3f(x - bg_width/2, y + bg_height/2, -0.005)
        glEnd()

        # 然后绘制文字
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)

        # 设置纹理参数
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        # 设置颜色（白色，让纹理颜色生效）
        glColor4f(1.0, 1.0, 1.0, 1.0)

        # 清除OpenGL错误
        glGetError()

        # 绘制纹理四边形
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1)  # 翻转Y坐标以匹配pygame表面
        glVertex3f(x - tex_width/2, y - tex_height/2, 0)
        glTexCoord2f(1, 1)
        glVertex3f(x + tex_width/2, y - tex_height/2, 0)
        glTexCoord2f(1, 0)
        glVertex3f(x + tex_width/2, y + tex_height/2, 0)
        glTexCoord2f(0, 0)
        glVertex3f(x - tex_width/2, y + tex_height/2, 0)
        glEnd()

        # 检查并记录OpenGL错误
        error = glGetError()
        if error != GL_NO_ERROR:
            logger.warning(f"文字渲染OpenGL错误: {error}")

        # 恢复状态
        glPopAttrib()

    def _render_text(self, text: str, x: float, y: float, color: Tuple[int, int, int], scale: float = 0.005):
        """渲染3D空间中的文字（不带背景，用于UI）"""
        texture_id = self._get_text_texture(text, color)
        if texture_id == 0:
            return

        key = (text, color)
        if key not in self.text_surfaces:
            return

        text_surface = self.text_surfaces[key]
        width, height = text_surface.get_size()

        # 计算纹理尺寸
        tex_width = width * scale
        tex_height = height * scale

        # 保存当前OpenGL状态
        glPushAttrib(GL_ENABLE_BIT | GL_TEXTURE_BIT | GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # 禁用光照
        glDisable(GL_LIGHTING)

        # 设置混合模式
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # 启用深度测试，但禁用深度写入（文字可以被遮挡，但不遮挡其他物体）
        glEnable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)

        # 启用纹理
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)

        # 设置纹理参数
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        # 设置颜色（白色，让纹理颜色生效）
        glColor4f(1.0, 1.0, 1.0, 1.0)

        # 清除OpenGL错误
        glGetError()

        # 绘制纹理四边形
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1)  # 翻转Y坐标以匹配pygame表面
        glVertex3f(x - tex_width/2, y - tex_height/2, 0)
        glTexCoord2f(1, 1)
        glVertex3f(x + tex_width/2, y - tex_height/2, 0)
        glTexCoord2f(1, 0)
        glVertex3f(x + tex_width/2, y + tex_height/2, 0)
        glTexCoord2f(0, 0)
        glVertex3f(x - tex_width/2, y + tex_height/2, 0)
        glEnd()

        # 检查并记录OpenGL错误
        error = glGetError()
        if error != GL_NO_ERROR:
            logger.warning(f"文字渲染OpenGL错误: {error}")

        # 恢复状态
        glPopAttrib()
    
    def _render_ui_text(self, text: str, x: float, y: float, color: Tuple[int, int, int]):
        """渲染UI文字"""
        if self.font is None:
            return

        texture_id = self._get_text_texture(text, color)
        if texture_id == 0:
            return

        key = (text, color)
        if key not in self.text_surfaces:
            return

        text_surface = self.text_surfaces[key]
        width, height = text_surface.get_size()

        # 保存当前OpenGL状态
        glPushAttrib(GL_ENABLE_BIT | GL_TEXTURE_BIT | GL_COLOR_BUFFER_BIT)

        # 禁用深度测试（UI文字始终在最前面）
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

        # 设置混合模式
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # 启用纹理
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture_id)

        # 设置纹理参数
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        # 设置颜色（白色，让纹理颜色生效）
        glColor4f(1.0, 1.0, 1.0, 1.0)

        # 绘制纹理四边形
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(x, y + height)
        glTexCoord2f(1, 0)
        glVertex2f(x + width, y + height)
        glTexCoord2f(1, 1)
        glVertex2f(x + width, y)
        glTexCoord2f(0, 1)
        glVertex2f(x, y)
        glEnd()

        # 恢复状态
        glPopAttrib()
    
    def _render_ui(self):
        """渲染UI信息"""
        # 暂时保存当前矩阵
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        
        # 设置正交投影用于UI渲染
        glOrtho(0, self.window_size[0], 0, self.window_size[1], -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # 禁用深度测试和光照
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        
        # 渲染信息文本
        mouse_status = "锁定" if self.mouse_locked else "自由"
        label_status = f"标签: {'开启' if self.show_labels else '关闭'} ({self.label_distance}格)"
        camera_mode = "Bot控制" if self.use_bot_camera else "手动控制"
        controls = "WASD=Move F2=Labels +/-=LabelDist F3=Mouse F4=CameraMode ESC=Exit"

        info_lines = [
            f"Camera: ({self.camera_pos[0]:.1f}, {self.camera_pos[1]:.1f}, {self.camera_pos[2]:.1f}) | 模式: {camera_mode}",
            f"View: Yaw={self.camera_yaw:.1f} Pitch={self.camera_pitch:.1f}",
            f"Blocks: {len(self.cached_blocks)} | Mouse: {mouse_status} | {label_status}",
            controls
        ]
        
        # 绘制半透明背景
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.0, 0.0, 0.0, 0.7)  # 半透明黑色
        glBegin(GL_QUADS)
        glVertex2f(5, self.window_size[1] - 125)
        glVertex2f(500, self.window_size[1] - 125)
        glVertex2f(500, self.window_size[1] - 5)
        glVertex2f(5, self.window_size[1] - 5)
        glEnd()
        
        # 绘制边框
        glColor3f(1.0, 1.0, 1.0)  # 白色边框
        glBegin(GL_LINE_LOOP)
        glVertex2f(5, self.window_size[1] - 125)
        glVertex2f(500, self.window_size[1] - 125)
        glVertex2f(500, self.window_size[1] - 5)
        glVertex2f(5, self.window_size[1] - 5)
        glEnd()
        
        # 如果有字体，渲染真正的文字
        if self.font is not None:
            colors = [(255, 255, 0), (0, 255, 255), (255, 0, 255), (0, 255, 0)]
            for i, line in enumerate(info_lines):
                y_pos = self.window_size[1] - 30 - i * 25
                self._render_ui_text(line, 10, y_pos, colors[i % len(colors)])
        else:
            # 回退到彩色矩形
            colors = [(1.0, 1.0, 0.0), (0.0, 1.0, 1.0), (1.0, 0.0, 1.0), (0.0, 1.0, 0.0)]
            for i, line in enumerate(info_lines):
                y_pos = self.window_size[1] - 25 - i * 25
                glColor3f(*colors[i % len(colors)])
                glBegin(GL_QUADS)
                glVertex2f(10, y_pos - 8)
                glVertex2f(10 + len(line) * 6, y_pos - 8)
                glVertex2f(10 + len(line) * 6, y_pos + 8)
                glVertex2f(10, y_pos + 8)
                glEnd()
        
        glDisable(GL_BLEND)
        
        # 恢复设置
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        
        # 恢复矩阵
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    

    
    def get_camera_info(self) -> Dict:
        """获取相机信息"""
        return {
            "position": self.camera_pos.copy(),
            "yaw": self.camera_yaw,
            "pitch": self.camera_pitch,
            "render_distance": self.render_distance,
            "cached_blocks_count": len(self.cached_blocks)
        }


# 全局3D渲染器实例
global_renderer_3d: Optional[Renderer3D] = None


def get_global_renderer_3d() -> Renderer3D:
    """获取全局3D渲染器实例"""
    global global_renderer_3d
    if global_renderer_3d is None:
        global_renderer_3d = Renderer3D()
    return global_renderer_3d


def start_3d_renderer():
    """启动全局3D渲染器"""
    renderer = get_global_renderer_3d()
    renderer.start()
    return renderer


def stop_3d_renderer():
    """停止全局3D渲染器"""
    global global_renderer_3d
    if global_renderer_3d is not None:
        global_renderer_3d.stop()
        global_renderer_3d = None


if __name__ == "__main__":
    # 独立运行模式
    print("启动3D Minecraft渲染器...")
    renderer = Renderer3D()
    try:
        renderer.start()
        # 等待渲染器线程结束
        if renderer.thread:
            renderer.thread.join()
    except KeyboardInterrupt:
        print("正在退出...")
    finally:
        renderer.stop()
