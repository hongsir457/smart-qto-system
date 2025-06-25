#!/usr/bin/env python3

import sys
from app.api.v1.websockets import router

def verify_websocket_routes():
    """验证WebSocket路由是否正确注册"""
    print("🔍 验证WebSocket路由注册...")
    
    print("\n=== 路由器信息 ===")
    print(f"路由器类型: {type(router)}")
    print(f"路由数量: {len(router.routes)}")
    
    print("\n=== 已注册的路由详情 ===")
    websocket_count = 0
    
    for i, route in enumerate(router.routes):
        route_type_name = type(route).__name__
        methods = getattr(route, 'methods', ['Unknown'])
        endpoint = getattr(route, 'endpoint', None)
        endpoint_name = endpoint.__name__ if endpoint else "Unknown"
        
        print(f"{i+1}. {route.path}")
        print(f"   类型: {route_type_name}")
        print(f"   方法: {methods}")
        print(f"   端点: {endpoint_name}")
        print(f"   名称: {getattr(route, 'name', 'N/A')}")
        
        # 检查是否为WebSocket
        is_websocket = (
            'WebSocketRoute' in route_type_name or
            'WebSocket' in str(methods) or
            hasattr(route, 'websocket')
        )
        
        if is_websocket:
            websocket_count += 1
            print(f"   🌐 WebSocket路由: ✅")
        else:
            print(f"   🌐 WebSocket路由: ❌")
        print()
    
    print(f"🎯 WebSocket路由总数: {websocket_count}")
    
    # 测试路由是否真正工作
    print("\n=== 路由功能测试 ===")
    
    # 检查路由端点是否可调用
    for route in router.routes:
        if hasattr(route, 'endpoint') and route.endpoint:
            try:
                # 检查端点函数是否有WebSocket参数
                import inspect
                sig = inspect.signature(route.endpoint)
                params = list(sig.parameters.keys())
                has_websocket_param = 'websocket' in params
                
                print(f"路由 {route.path}:")
                print(f"  参数: {params}")
                print(f"  包含websocket参数: {has_websocket_param}")
                print()
                
            except Exception as e:
                print(f"检查路由 {route.path} 时出错: {e}")
                print()
    
    return websocket_count > 0

if __name__ == "__main__":
    success = verify_websocket_routes()
    if success:
        print("🎉 WebSocket路由验证成功！")
        sys.exit(0)
    else:
        print("❌ WebSocket路由验证失败！")
        sys.exit(1) 