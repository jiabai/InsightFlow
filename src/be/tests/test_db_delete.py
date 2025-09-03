import asyncio
import sys
import os
import logging

logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
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

async def delete_file_metadata(file_id: str):
    async with AsyncSessionLocal() as db:
        try:
            # 查询文件元数据
            result = await db.execute(select(FileMetadata).filter(FileMetadata.file_id == file_id))
            file_metadata = result.scalars().first()

            if not file_metadata:
                print(f"File with file_id {file_id} not found for deletion.")
                return False

            # 删除元数据
            await db.delete(file_metadata)
            print(f"Deleted file metadata for file_id {file_id}.")
            await db.commit()
            return True

        except SQLAlchemyError as e:
            await db.rollback()
            print(f"Failed to delete file metadata for file_id {file_id}: {str(e)}")
            raise
        except Exception as e:
            await db.rollback()
            print(f"Unexpected error deleting file metadata for file_id {file_id}: {str(e)}")
            raise

# 使用示例
async def main():
    file_id = "test_file_id_12345"
    try:
        success = await delete_file_metadata(file_id)
        if success:
            print(f"文件 {file_id} 元数据删除成功")
        else:
            print(f"文件 {file_id} 不存在")
    except Exception as e:
        print(f"删除文件元数据时出错: {str(e)}")

async def run_with_delay():
    try:
        await main()
        # await asyncio.sleep(1)
    finally:
        await engine.dispose()

asyncio.run(run_with_delay())
