import asyncio
import sys
import os
import logging

logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from be.common.database_manager import FileMetadata

# 数据库配置
DATABASE_URL = (
    f"mysql+aiomysql://root:123456@192.168.31.233/insight_flow?charset=utf8mb4"
)

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=False)

# 创建异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def insert_file_metadata(file_id: str, user_id: str, filename: str, file_size: int, file_type: str, stored_filename: str):
    async with AsyncSessionLocal() as db:
        try:
            new_file_metadata = FileMetadata(
                file_id=file_id,
                user_id=user_id,
                filename=filename,
                file_size=file_size,
                file_type=file_type,
                upload_time=datetime.now(),
                stored_filename=stored_filename
            )
            db.add(new_file_metadata)
            await db.commit()
            await db.refresh(new_file_metadata)
            print(f"Successfully inserted file metadata for file_id: {file_id}")
            return True
        except SQLAlchemyError as e:
            await db.rollback()
            print(f"Failed to insert file metadata for file_id {file_id}: {str(e)}")
            return False
        except Exception as e:
            await db.rollback()
            print(f"An unexpected error occurred while inserting file metadata for file_id {file_id}: {str(e)}")
            return False

# 使用示例
async def main():
    test_file_id = "test_file_id_12345"
    test_user_id = "test_user_1"
    test_filename = "example.txt"
    test_file_size = 1024
    test_file_type = "text/plain"
    test_stored_filename = "stored_example.txt"
    # 尝试插入数据
    success = await insert_file_metadata(
        test_file_id, test_user_id, test_filename, test_file_size, test_file_type, test_stored_filename
    )

    if success:
        print(f"文件 {test_filename} 元数据插入成功")
    else:
        print(f"文件 {test_filename} 元数据插入失败")

async def run_main():
    try:
        await main()
        # await asyncio.sleep(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_main())
