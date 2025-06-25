import sys
from pathlib import Path

# 将项目根目录添加到Python路径
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import engine, Base
from app.models import user, drawing  # 导入所有模型

def create_database_tables():
    """
    根据所有已定义的模型，创建数据库表。
    """
    print("正在连接到数据库并创建表...")
    try:
        # Base.metadata.create_all 会检查表是否存在，只创建不存在的表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功！")
        print("现在你可以正常启动FastAPI应用了。")
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        print("请检查你的数据库连接配置 (DATABASE_URL) 和模型定义。")

if __name__ == "__main__":
    create_database_tables() 