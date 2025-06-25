from app.database import Base, get_db
import app.models  # 确保所有模型都被注册

def main():
    db = next(get_db())
    Base.metadata.create_all(bind=db.get_bind())
    print("数据库表结构已初始化")

if __name__ == "__main__":
    main() 