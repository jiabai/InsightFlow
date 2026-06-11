import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from server.common.insight_sqlite_repository import InsightSQLiteRepository


async def insert_file_metadata(
    file_id: str,
    user_id: str,
    filename: str,
    file_size: int,
    file_type: str,
    stored_filename: str,
) -> bool:
    repo = InsightSQLiteRepository()
    await repo.initialize()
    await repo.init_db()
    try:
        async with repo.get_db() as db:
            await repo.save_file_metadata(
                db,
                file_id=file_id,
                user_id=user_id,
                filename=filename,
                file_size=file_size,
                file_type=file_type,
                stored_filename=stored_filename,
            )
        print(f"Inserted file metadata for file_id: {file_id}")
        return True
    finally:
        await repo.dispose_engine()


async def main():
    await insert_file_metadata(
        file_id="test_file_id_12345",
        user_id="test_user_1",
        filename="example.txt",
        file_size=1024,
        file_type="text/plain",
        stored_filename="test_user_1_test_file_id_12345_example.txt",
    )


if __name__ == "__main__":
    asyncio.run(main())
