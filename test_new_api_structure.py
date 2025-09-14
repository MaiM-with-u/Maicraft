#!/usr/bin/env python3
"""
测试新的API结构
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_structure():
    """测试新的API结构"""
    print("🧪 测试新的API结构...")

    try:
        # 测试API包导入
        from api import create_websocket_app, get_websocket_server
        print("✅ API包导入成功")

        # 测试创建应用
        app = create_websocket_app()
        print("✅ FastAPI应用创建成功")

        # 测试路由
        routes = [route.path for route in app.routes]
        expected_routes = [
            "/health",
            "/api/logs/config",
            "/api/logs/level",
            "/api/logs/recent",
            "/api/logs/stats",
            "/api/logs/clear",
            "/ws/logs"
        ]

        for route in expected_routes:
            if route in routes:
                print(f"✅ 路由 {route} 存在")
            else:
                print(f"❌ 路由 {route} 不存在")
                return False

        # 测试服务器实例
        server = get_websocket_server()
        print("✅ API服务器实例创建成功")

        print("🎉 所有API结构测试通过！")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_structure()
    if success:
        print("\n🎯 新的API目录结构工作正常！")
        print("📁 结构说明：")
        print("   api/")
        print("   ├── server.py          # 主API服务器")
        print("   ├── routers/           # 路由模块")
        print("   │   └── logs.py        # 日志相关路由")
        print("   ├── services/          # 业务逻辑服务")
        print("   │   ├── log_service.py     # 日志业务逻辑")
        print("   │   └── websocket_manager.py # WebSocket管理")
        print("   └── models/            # 数据模型")
        print("       ├── requests.py    # 请求模型")
        print("       └── responses.py   # 响应模型")
    else:
        print("\n❌ API结构测试失败！")
        sys.exit(1)
