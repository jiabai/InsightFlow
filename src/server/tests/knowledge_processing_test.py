import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from server.common.insight_sqlite_repository import InsightSQLiteRepository
from server.llm_knowledge_processing.markdown_splitter import MarkdownSplitter


TEST_FILE = "README.md"


async def main():
    splitter = MarkdownSplitter()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, "data", TEST_FILE)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = splitter.split_markdown(content, min_length=1000, max_length=3000) or []
    print(f"Total chunks: {len(chunks)}")

    file_id = "test_file"
    user_id = "test_user"
    file_name = TEST_FILE

    repo = InsightSQLiteRepository()
    await repo.initialize()
    await repo.init_db()
    try:
        async with repo.get_db() as db:
            await repo.delete_chunks_by_file_id(db, file_id)
            saved_chunks = await repo.save_chunks(db, chunks, user_id, file_id, file_name)
            print(f"Saved chunks: {len(saved_chunks)}")

            all_file_chunks = await repo.get_chunks_by_file_ids(db, [file_id])
            print(f"Chunks for {file_id}: {len(all_file_chunks)}")
            for chunk in all_file_chunks:
                print(f"- ID: {chunk.id}, Name: {chunk.name}")
    finally:
        await repo.dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
