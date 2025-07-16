import os
import time
import shutil
import logging
from sqlalchemy.orm import Session
from be.common.redis_manager import RedisManager
from be.common.database_manager import DatabaseManager, FileMetadata
from be.common.logger_config import setup_logging

from .markdown_splitter import MarkdownSplitter
from .utils import generate_questions_for_chunk

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)
# 目录配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, 'data', 'upload_file')
COMPLETED_DIR = os.path.join(BASE_DIR, 'data', 'completed')

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(COMPLETED_DIR, exist_ok=True)

# SQLite数据库配置
SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'db.sqlite')

# LLM 配置 (需要根据实际情况填写)
llm_config = {
    'provider': 'siliconflow',
    'api_key': 'sk-wkguetxfwibczehkadqilsphgxtumfilykwselnurzxfrskf',
    'base_url': 'https://api.siliconflow.cn/v1',
    'model': 'Qwen/Qwen3-30B-A3B'
}

# MySQL
db_manager = DatabaseManager()
# Redis
redis_manager = RedisManager()

def get_file_details_from_mysql(stored_filename: str, db: Session):
    """
    根据存储的文件名从MySQL数据库中获取文件详情 (file_id, user_id)。
    """
    return (db.query(FileMetadata)
            .filter(FileMetadata.stored_filename == stored_filename)
            .first())

def process_file(file_path: str, stored_filename: str):
    """
    处理单个Markdown文件：分割、生成问题、更新状态。
    """
    mysql_db = next(db_manager.get_db())
    try:
        # 1. 从MySQL获取文件元数据
        file_metadata = get_file_details_from_mysql(stored_filename, mysql_db)
        if not file_metadata:
            logger.error(f"在数据库中未找到文件 '{stored_filename}' 的元数据，跳过处理。")
            return

        file_id = file_metadata.file_id
        original_filename = file_metadata.filename
        project_id = f"project_{file_id}" # 使用file_id作为项目ID

        logger.info(f"开始处理文件: {original_filename} (File ID: {file_id})")

        # 2. 更新Redis状态为 'Processing'
        redis_manager.set_file_status(file_id, "Processing")

        # 3. 读取和分割Markdown文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        splitter = MarkdownSplitter()
        chunks = splitter.split_markdown(content, min_length=1000, max_length=3000)
        logger.info(f"文件被分割成 {len(chunks)} 个块。")

        # 4. 将块保存到数据库
        db_manager.save_chunks(mysql_db, chunks, project_id, file_id, original_filename)

        # 5. 为每个块生成问题
        # 注意：这里需要从数据库中获取刚保存的块，因为需要它们的ID
        saved_chunks = db_manager.get_chunks_by_file_ids(mysql_db, [file_id])
        total_questions = 0
        for chunk_row in saved_chunks:
            chunk_id = chunk_row[0] # Chunks表的主键id
            logger.info(f"为块 {chunk_id} 生成问题...")
            # 这里的配置可以根据需要进行调整
            project_config = {
                'questionGenerationLength': 150,
                'questionMaskRemovingProbability': 60,
                'language': '中文'
            }
            project_details = {'globalPrompt': '', 'questionPrompt': ''}
            tags = [] # 如果需要，可以添加标签逻辑

            generated_questions = generate_questions_for_chunk(
                mysql_db,
                project_id,
                chunk_id,
                project_config,
                project_details,
                tags,
                llm_config
            )
            if generated_questions:
                saved_count = db_manager.save_questions(
                    mysql_db,
                    project_id,
                    generated_questions,
                    chunk_id
                )
                total_questions += saved_count
                logger.info(f"成功为块 {chunk_id} 生成并保存 {saved_count} 个问题。")

        logger.info(f"共生成 {total_questions} 个问题。")

        # 6. 更新Redis状态为 'Completed'
        redis_manager.set_file_status(file_id, "Completed")
        logger.info("文件处理完成，Redis状态更新为 'Completed'。")


        # 7. 移动文件到 'completed' 目录
        destination_path = os.path.join(COMPLETED_DIR, stored_filename)
        shutil.move(file_path, destination_path)
        logger.info(f"文件已移动到: {destination_path}")

    except Exception as e:
        logger.error(f"处理文件 '{stored_filename}' 时发生错误: {e}", exc_info=True)
        # 如果发生错误，也更新Redis状态
        if 'file_id' in locals():
            redis_manager.set_file_status(file_id, f"Failed: {str(e)}")
    finally:
        if mysql_db:
            mysql_db.close()

def poll_directory():
    """
    轮询上传目录并处理文件。
    """
    logger.info("知识处理服务已启动，开始轮询上传目录...")
    while True:
        try:
            files_to_process = [
                f for f in os.listdir(UPLOAD_DIR)
                if f.endswith('.md') and os.path.isfile(os.path.join(UPLOAD_DIR, f))
            ]

            if not files_to_process:
                time.sleep(5) # 目录为空时，等待5秒
                continue

            for filename in files_to_process:
                file_path = os.path.join(UPLOAD_DIR, filename)
                process_file(file_path, filename)

        except Exception as e:
            logger.error(f"轮询过程中发生未知错误: {e}", exc_info=True)
            time.sleep(10) # 发生错误时，等待更长时间

if __name__ == "__main__":
    poll_directory()
