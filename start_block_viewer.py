#!/usr/bin/env python3
"""
方块缓存浏览器启动脚本
启动一个独立的 pygame 窗口来预览方块缓存
"""
import sys
import os
import asyncio
from pathlib import Path
from view_render.block_cache_viewer import BlockCacheViewer
from view_render.renderer import BlockCacheRenderer, RenderConfig
from utils.logger import setup_logging, get_logger

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))





def main():
    """主函数"""
    print("=" * 50)
    print("方块缓存浏览器启动器")
    print("=" * 50)
    
    # 设置日志
    try:
        setup_logging("INFO")
        logger = get_logger("BlockViewerLauncher")
        logger.info("方块缓存浏览器启动中...")
    except Exception as e:
        print(f"[警告] 日志初始化失败: {e}")
    
    # 创建渲染器配置
    config = RenderConfig(
        image_width=1200,      # 稍微大一点的窗口
        image_height=800,
        block_size=20,         # 稍大的方块尺寸
        vertical_scale=1.2,    # 稍微增加垂直高度
        trail_enabled=True,    # 启用玩家轨迹
        trail_max_points=300,  # 轨迹点数
        background_color=(20, 20, 25, 255)  # 深色背景
    )
    
    # 创建渲染器
    renderer = BlockCacheRenderer(config=config)
    
    # 创建浏览器
    viewer = BlockCacheViewer(
        renderer=renderer,
        update_interval_seconds=2.0  # 每2秒更新一次
    )
    
    print("[配置] 渲染配置:")
    print(f"  - 窗口尺寸: {config.image_width} x {config.image_height}")
    print(f"  - 方块尺寸: {config.block_size}")
    print(f"  - 更新间隔: {viewer.update_interval_seconds} 秒")
    print(f"  - 玩家轨迹: {'启用' if config.trail_enabled else '禁用'}")
    print(f"  - 数据来源: BlockCache 方块缓存 + PlayerPositionCache 玩家位置")
    
    print("\n[提示] 控制说明:")
    print("  - ESC 或 Q: 退出程序")
    print("  - 关闭窗口: 退出程序")
    print("  - 程序会自动每2秒刷新一次方块缓存")
    
    print("\n[启动] 正在启动 pygame 窗口...")
    
    try:
        # 启动浏览器
        # 可以指定中心点和半径来限制渲染范围
        # 例如: viewer.run(center=(0, 64, 0), radius=50)
        viewer.run()
    except KeyboardInterrupt:
        print("\n[退出] 用户中断")
    except Exception as e:
        print(f"\n[错误] 运行时错误: {e}")
        if hasattr(e, '__traceback__'):
            import traceback
            traceback.print_exc()
    finally:
        print("[退出] 方块缓存浏览器已关闭")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[退出] 程序被用户中断")
    except Exception as e:
        print(f"\n[致命错误] {e}")
        sys.exit(1)
