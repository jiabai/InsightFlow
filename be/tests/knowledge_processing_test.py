import os
from nanoid import generate

from be.common.database_manager import DatabaseManager, Chunk
from be.llm_knowledge_processing.utils import generate_questions_for_chunk
from be.llm_knowledge_processing.markdown_splitter import MarkdownSplitter

TEST_FILE = 'README.md'

if __name__ == '__main__':

    splitter = MarkdownSplitter()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(dir_path, 'data', TEST_FILE)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    chunks = splitter.split_markdown(content, min_length=1000, max_length=3000)
    # 输出分块结果
    print(f'总共分块数量: {len(chunks)}')
    for i, chunk in enumerate(chunks):
        print(f'\n--- Chunk {i + 1} ---')
        print(f"摘要: {chunk['summary']}")
        print(f"内容长度: {len(chunk['content'])}")
        print(f"内容预览:\n{chunk['content'][:200]}...")

    project_id = 'test_project'
    file_id = 'test_file'
    file_name = TEST_FILE

    # --- Test DatabaseManager ---
    db_manager = DatabaseManager()
    db = next(db_manager.get_db())

    # Clear previous data for a clean test
    db_manager.delete_chunks_by_file_id(db, file_id)
    print(f"Cleaned up old data for fileId: {file_id}")

    # 1. Test save_chunks
    saved_count = db_manager.save_chunks(db, chunks, project_id, file_id, file_name)
    print(f'\n1. Successfully saved {saved_count} chunks.')

    # 2. Test get_all_chunks
    all_chunks = db.query(Chunk).all()
    print(f'\n2. Found {len(all_chunks)} chunks in total:')
    for chunk in all_chunks:
        print(f'   - ID: {chunk.id}, Name: {chunk.name}')

    # Get the ID of the first chunk for further tests
    first_chunk_id = all_chunks[0][0] if all_chunks else None

    if first_chunk_id:
        # 3. Test get_chunk_by_id
        chunk = db_manager.get_chunk_by_id(db, first_chunk_id)
        print(f'\n3. Fetched chunk by ID ({first_chunk_id}): {chunk.name}')

        # 4. Test update_chunk_by_id
        # update_count = db_manager.update_chunk_by_id(db, first_chunk_id, {'name': 'UPDATED HEADING'})
        # print(f'\n4. Updated {update_count} chunk. New name: {db_manager.get_chunk_by_id(db, first_chunk_id).name}')

        # 5. Test generate_questions_for_chunk
        print(f'\n5. Generating questions for chunk {first_chunk_id}...')
        project_config = {'questionGenerationLength': 100, 'questionMaskRemovingProbability': 60, 'language': '中文'}
        project_details = {'globalPrompt': '', 'questionPrompt': ''}
        tags = [{'name': 'tag1'}, {'name': 'tag2'}]
        llm_config = {
            'provider': 'siliconflow',
            'api_key': 'sk-wkguetxfwibczehkadqilsphgxtumfilykwselnurzxfrskf',
            'base_url': 'https://api.siliconflow.cn/v1',
            'model': 'Qwen/Qwen3-30B-A3B'
        }
        generated_questions = generate_questions_for_chunk(db, project_id, first_chunk_id, project_config, project_details, tags, llm_config)
        if generated_questions:
            print(f"   Generated {len(generated_questions)} questions.")
            for q in generated_questions:
                print(f"      - {q.get('question')} (Label: {q.get('label', 'N/A')})")

        # 6. Test get_questions_by_chunk_id
        questions_in_db = db_manager.get_questions_by_chunk_id(db, first_chunk_id)
        print(f'\n6. Questions in DB for chunk {first_chunk_id}: {len(questions_in_db)}')
        for q_db in questions_in_db:
            print(f"   - {q_db.question} (Label: {q_db.label})")

        # 7. Test delete_chunk_by_id
        delete_count = db_manager.delete_chunk_by_id(db, first_chunk_id)
        print(f'\n7. Deleted {delete_count} chunk and its questions.')
        print(f'   Chunk {first_chunk_id} exists after deletion: {db_manager.get_chunk_by_id(db, first_chunk_id) is not None}')

    # 8. Test get_chunks_by_file_ids
    print(f'\n8. Testing get_chunks_by_file_ids:')
    all_file_chunks = db_manager.get_chunks_by_file_ids(db, [file_id])
    print(f'   All chunks for file {file_id}: {len(all_file_chunks)}')
    print("\nDatabase connection closed.")
