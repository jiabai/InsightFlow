import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from server.common.insight_sqlite_repository import InsightSQLiteRepository


async def delete_file_metadata(file_id: str) -> bool:
    repo = InsightSQLiteRepository()
    await repo.initialize()
    await repo.init_db()
    try:
        async with repo.get_db() as db:
            deleted = await repo.delete_file_metadata(db, file_id)
        if deleted:
            print(f"Deleted file metadata for file_id: {file_id}")
            return True
        print(f"File metadata not found for file_id: {file_id}")
        return False
    finally:
        await repo.dispose_engine()


async def main():
    await delete_file_metadata("test_file_id_12345")


if __name__ == "__main__":
    asyncio.run(main())
