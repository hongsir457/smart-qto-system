from app.database import get_db
from app.models.user import User
from app.models.drawing import Drawing
from app.core.security import get_password_hash
import requests

def create_test_data():
    """创建测试数据"""
    base_url = "http://localhost:8000"
    db = next(get_db())
    
    try:
        # 1. 检查现有用户
        users = db.query(User).all()
        print(f"现有用户: {len(users)} 个")
        for user in users:
            print(f"  ID: {user.id}, 用户名: {user.username}")
        
        # 2. 检查现有图纸
        drawings = db.query(Drawing).all()
        print(f"\n现有图纸: {len(drawings)} 个")
        for drawing in drawings:
            print(f"  ID: {drawing.id}, 文件名: {drawing.filename}, 用户ID: {drawing.user_id}")
        
        # 3. 创建一个新的测试用户，并将图纸2转移给这个用户
        test_username = "api_test_user"
        existing_user = db.query(User).filter(User.username == test_username).first()
        
        if not existing_user:
            new_user = User(
                username=test_username,
                email="api_test@test.com",
                hashed_password=get_password_hash("password123")
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            print(f"\n创建了新用户: ID {new_user.id}, 用户名: {new_user.username}")
            test_user_id = new_user.id
        else:
            print(f"\n用户已存在: ID {existing_user.id}, 用户名: {existing_user.username}")
            test_user_id = existing_user.id
        
        # 4. 将图纸2转移给测试用户
        drawing_2 = db.query(Drawing).filter(Drawing.id == 2).first()
        if drawing_2:
            old_user_id = drawing_2.user_id
            drawing_2.user_id = test_user_id
            db.commit()
            print(f"\n图纸2已从用户ID {old_user_id} 转移到用户ID {test_user_id}")
        
        # 5. 测试登录并访问OCR API
        login_data = {
            "username": test_username,
            "password": "password123"
        }
        
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print(f"\n登录成功，获取token: {access_token[:20]}...")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 测试OCR API
            response = requests.post(f"{base_url}/api/v1/drawings/2/ocr", headers=headers)
            print(f"OCR API测试结果: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  - 成功: {result}")
            else:
                print(f"  - 失败: {response.text}")
                
            # 测试构件检测API
            response = requests.post(f"{base_url}/api/v1/drawings/2/detect-components", headers=headers)
            print(f"构件检测API测试结果: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  - 成功: {result}")
            else:
                print(f"  - 失败: {response.text}")
        else:
            print(f"登录失败: {response.status_code}")
        
    except Exception as e:
        print(f"创建测试数据时出错: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data() 