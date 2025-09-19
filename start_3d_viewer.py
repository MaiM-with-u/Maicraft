#!/usr/bin/env python3
"""
3D Minecraft查看器独立启动脚本
可以单独运行3D渲染器，无需启动完整的MaicraftAgent系统
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from view_render.renderer_3d import Renderer3D, OPENGL_AVAILABLE
    from agent.block_cache.block_cache import global_block_cache
    from utils.logger import setup_logging, get_logger
except ImportError as e:
    print(f"导入模块失败: {e}")  # 这里保持print，因为此时日志系统可能不可用
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)

# 设置日志系统
setup_logging("INFO")
logger = get_logger("Viewer3D")


def check_dependencies():
    """检查必要的依赖"""
    missing_deps = []
    
    try:
        import pygame
    except ImportError:
        missing_deps.append("pygame")
    
    if not OPENGL_AVAILABLE:
        missing_deps.append("PyOpenGL PyOpenGL-accelerate")
    
    if missing_deps:
        print("缺少必要的依赖包:")  # 保持print，因为这是错误信息需要立即显示
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\n请运行以下命令安装依赖:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True


def load_cached_data():
    """检查缓存的方块数据"""
    try:
        # BlockCache在初始化时会自动加载缓存文件
        block_count = len(global_block_cache._position_cache)
        if block_count > 0:
            logger.info(f"成功加载缓存数据，共 {block_count} 个方块")
            return True
        else:
            logger.warning("缓存中没有方块数据")
            logger.info("将使用空的方块缓存（需要先运行MaicraftAgent来收集方块数据）")
            return True
    except Exception as e:
        logger.error(f"检查缓存数据失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("3D Minecraft查看器 - MaicraftAgent")
    logger.info("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 设置日志
    try:
        setup_logging("INFO")
    except Exception:
        # 忽略日志设置错误
        pass
    
    
    # 加载缓存数据
    if not load_cached_data():
        response = input("是否继续启动3D查看器？(y/n): ")
        if response.lower() != 'y':
            return 1
    
    # 创建并启动3D渲染器
    logger.info("启动3D渲染器...")
    logger.info("控制说明:")
    logger.info("  - WASD: 移动相机")
    logger.info("  - 鼠标: 转向")
    logger.info("  - Shift: 加速移动")
    logger.info("  - Space: 上升")
    logger.info("  - Ctrl: 下降")
    logger.info("  - F2: 切换方块标签显示")
    logger.info("  - ESC: 退出")
    logger.info("-" * 40)
    
    renderer = Renderer3D()
    
    try:
        renderer.start()
        
        # 等待渲染器线程结束
        if renderer.thread:
            renderer.thread.join()
            
        logger.info("3D渲染器已退出")
        return 0
        
    except KeyboardInterrupt:
        logger.info("正在退出...")
        return 0
    except Exception as e:
        logger.error(f"运行3D渲染器时发生错误: {e}")
        return 1
    finally:
        renderer.stop()


if __name__ == "__main__":
    sys.exit(main())
