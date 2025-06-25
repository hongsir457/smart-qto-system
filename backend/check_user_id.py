import requests
from app.database import get_db
from app.models.user import User

def check_user_info():
    """检查用户信息"""
    base_url = "http://localhost:8000"
    
    # 1. 检查数据库中的用户
    db = next(get_db())
    try:
        users = db.query(User).all()
        print(f"数据库中总共有 {len(users)} 个用户:")
        for user in users:
            print(f"  ID: {user.id}, 用户名: {user.username}, 邮箱: {user.email}")
    except Exception as e:
        print(f"检查用户数据库时出错: {e}")
    finally:
        db.close()
    
    # 2. 测试登录并获取当前用户信息
    login_data = {
        "username": "test_user",
        "password": "test123456"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print(f"\n登录成功，token: {access_token[:20]}...")
            
            # 获取当前用户信息
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{base_url}/api/v1/users/me", headers=headers)
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"当前用户信息:")
                print(f"  ID: {user_info.get('id')}")
                print(f"  用户名: {user_info.get('username')}")
                print(f"  邮箱: {user_info.get('email')}")
                
                # 现在测试用这个用户访问图纸2
                current_user_id = user_info.get('id')
                print(f"\n测试用户ID {current_user_id} 访问图纸ID 2:")
                
                response = requests.post(f"{base_url}/api/v1/drawings/2/ocr", headers=headers)
                print(f"OCR端点状态: {response.status_code}")
                if response.status_code == 404:
                    print("  - 图纸不存在或无权限访问")
                    print("  - 图纸所有者可能是其他用户")
                elif response.status_code == 200:
                    print("  - 请求成功")
                else:
                    print(f"  - 其他错误: {response.text}")
            else:
                print(f"获取用户信息失败: {response.status_code}")
        else:
            print(f"登录失败: {response.status_code}")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    check_user_info() 