"""
Knowledge Processing Service Module

This module provides functionality for processing knowledge documents and generating questions.
It includes the KnowledgeProcessingService class which handles:
- Monitoring upload directories for new markdown files
- Processing and splitting markdown content into chunks
- Generating questions from content using LLM
- Managing file status through Redis
- Storing generated questions in database

The module is part of the insight-flow backend system and works with markdown files
to generate structured knowledge and questions.
"""

import os
import time
import shutil
import asyncio
from be.common.redis_manager import RedisManager
from be.common.database_manager import DatabaseManager, Chunk
from be.llm_knowledge_processing.markdown_splitter import MarkdownSplitter
from be.llm_knowledge_processing.question_generator import QuestionGenerator
from be.llm_knowledge_processing.config_manager import ConfigManager
from be.llm_knowledge_processing.asyncio_logger import get_logger, with_task_id

logger = get_logger()

class KnowledgeProcessingService:
    """
    A service for processing knowledge documents and generating questions.
    
    This service handles:
    - Monitoring upload directories for new markdown files
    - Processing and splitting markdown content into chunks
    - Generating questions from content using LLM
    - Managing file status through Redis
    - Storing generated questions in database
    """
    def __init__(self):
        # 初始化配置
        self.config = ConfigManager()
        # 初始化组件
        self.db_manager = DatabaseManager()
        self.redis_manager = RedisManager()

    @with_task_id
    async def run(self):
        """
        Main entry point to start the knowledge processing service.
        
        This method:
        1. Initializes required components (database and Redis connections)
        2. Starts polling the upload directory for new files to process
        
        The service will continue running until explicitly stopped.
        """
        await self.initialize()
        await self.poll_directory()

    async def initialize(self):
        """
        Initialize database and Redis connections.

        This method:
        1. Initializes the database manager and creates required tables
        2. Establishes connection to Redis server

        The initialization is required before the service can begin processing files.
        """
        await self.db_manager.initialize()
        await self.db_manager.init_db()
        await self.redis_manager.initialize()

    async def shutdown(self):
        """
        Gracefully shuts down the service by closing database and Redis connections.

        This method:
        1. Disposes of the database engine connection
        2. Closes the Redis connection

        Should be called when terminating the service to ensure proper cleanup of resources.
        """
        await self.db_manager.dispose_engine()
        await self.redis_manager.close_redis()

    async def poll_directory(self):
        """
        Continuously monitors the upload directory for new markdown files to process.

        This method:
        1. Polls the upload directory at regular intervals
        2. Identifies new markdown files that need processing
        3. Processes each file through the knowledge processing pipeline
        4. Moves processed files to the completed directory
        5. Handles any errors that occur during polling or processing

        The polling continues indefinitely until the service is stopped.
        Any errors encountered during polling are logged but don't stop the service.
        """
        logger.info("知识处理服务已启动，开始轮询上传目录...")
        while True:
            try:
                # Get all markdown files in upload directory
                files_to_process = get_markdown_files_from_upload_dir(self.config.upload_dir)
                if not files_to_process:
                    time.sleep(5)
                    continue

                for file_path, file, user_dir in files_to_process:
                    await self.process_file(file_path, file)
                    # 移动文件到 'completed' 目录
                    move_processed_file(user_dir, file_path, file, self.config.completed_dir)
                break
            except (IOError, OSError, asyncio.CancelledError, RuntimeError) as e:
                logger.error("轮询过程中发生未知错误: %s", e, exc_info=True)

    async def process_file(self, file_path: str, stored_filename: str):
        """
        Process a single markdown file by splitting it into chunks and generating questions.

        Args:
            file_path (str): The full path to the markdown file to process
            stored_filename (str): The filename as stored in the database

        This method:
        1. Retrieves file metadata and IDs from database
        2. Updates Redis status to 'Processing'
        3. Reads and validates the file content
        4. Splits content into chunks
        5. Generates questions for each chunk
        6. Updates Redis status to 'Completed' when done
        7. Updates Redis status to 'Failed' if errors occur

        The file processing status is tracked in Redis throughout the operation.
        """
        file_id = None
        async with self.db_manager.get_db() as mysql_db:
            try:
                # 1. 获得id和文件名
                file_id, original_filename, project_id = await self._get_file_metadata_and_ids(
                    mysql_db,
                    stored_filename
                )
                if file_id is None:
                    return
                logger.debug("开始处理文件 '%s' (File ID: %s)", original_filename, file_id)

                # 2. 更新Redis状态为 'Processing'
                await self.redis_manager.set_file_status(file_id, "Processing")
                logger.debug("Redis状态更新为 'Processing'。")

                # 3. 读取和分割Markdown文件，得到chunks
                content = await self._read_and_validate_file(file_path, file_id)
                if content is None:
                    return
                splitter = MarkdownSplitter()
                chunks = splitter.split_markdown(content, min_length=1000, max_length=3000) or []
                logger.debug("文件 '%s' 被分割成 %s 个块。", original_filename, len(chunks))

                # 4. 处理每个块，生成问题
                if chunks:
                    db_chunks = await self.db_manager.save_chunks(
                        mysql_db,
                        chunks,
                        project_id,
                        file_id,
                        original_filename
                    )
                    total_questions = await self._generate_questions_and_save(
                        mysql_db,
                        db_chunks,
                        project_id,
                        self.config.project_config,
                        self.config.project_details
                    )
                    logger.debug("共生成 %s 个问题。", total_questions)

                # 5. 更新Redis状态为 'Completed'
                await self.redis_manager.set_file_status(file_id, "Completed")
                logger.debug("文件处理完成，Redis状态更新为 'Completed'。")
            except (IOError, ValueError, RuntimeError, asyncio.CancelledError) as e:
                logger.error("处理文件 '%s' 时发生错误: %s", stored_filename, e, exc_info=True) 
                if file_id:
                    await self.redis_manager.set_file_status(file_id, "Failed")
                    self.logger.debug("Redis状态更新为 'Failed'。")  

    async def _get_file_metadata_and_ids(self, mysql_db, stored_filename):
        file_metadata = await self.db_manager.get_file_metadata_by_stored_filename(
            mysql_db,
            stored_filename
        )
        if not file_metadata:
            logger.error("在数据库中未找到文件 '%s' 的元数据，跳过处理。", stored_filename)
            return None, None, None
        logger.debug("从数据库中获取文件 '%s' 的元数据成功。", stored_filename)

        file_id = file_metadata.file_id
        original_filename = file_metadata.filename
        project_id = f"project_{file_id}" # 使用file_id作为项目ID

        return file_id, original_filename, project_id

    async def _read_and_validate_file(self, file_path: str, file_id: str):
        file_size = os.path.getsize(file_path)
        if file_size > 64 * 1024 * 1024:  # 64MB in bytes
            logger.error("File %s exceeds 64MB limit. Skipping.", file_id)
            await self.redis_manager.set_file_status(file_id, "Failed")
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content

    async def _generate_questions(
        self,
        content,
        p_config,
        p_details,
        tags
    ):
        question_generator = QuestionGenerator(
            self.config.llm_config,
            self.db_manager,
            is_mock=False
        )
        generated_questions = await question_generator.generate_for_chunk(
            content,
            p_config,
            p_details,
            tags
        )
        logger.debug(
            "Generated %d questions: %s",
            len(generated_questions),
            generated_questions
        )
        return generated_questions

    async def _generate_questions_and_save(
        self,
        mysql_db,
        db_chunks: list[Chunk],
        project_id: str,
        p_config: dict,
        p_details: dict
    ):
        total_questions = 0
        for chunk in db_chunks:
            content = chunk.content
            tags = []  # 如果需要，可以添加标签逻辑
            generated_questions = await self._generate_questions(
                content,
                p_config,
                p_details,
                tags
            )
            if generated_questions:
                saved_count = await self.db_manager.save_questions(
                        mysql_db,
                        project_id,
                        generated_questions,
                        chunk.id
                    )
                total_questions += saved_count
                logger.info("成功为块 %s 生成并保存 %s 个问题。", chunk.id, saved_count)
        return total_questions

def get_markdown_files_from_upload_dir(upload_dir):
    """
    Scans the upload directory for markdown files within user subdirectories.

    Args:
        upload_dir (str): Path to the upload directory to scan

    Returns:
        list: List of tuples (file_path, filename, user_directory) for each markdown
        file found

    The function scans user subdirectories in the upload directory and 
    looks for .md files.
    Each file found is returned as a tuple containing its full path, filename, and 
    parent user directory name.
    """
    def is_entries_valid(entries):
        if not any(True for _ in entries):
            time.sleep(5)
            return False
        return True

    files_to_process = []
    with os.scandir(upload_dir) as entries:
        entries_list = list(entries)
        if not is_entries_valid(entries_list):
            entries.close()
            return files_to_process
        for entry in entries_list:
            if entry.is_dir():
                user_dir = entry.name
                user_path = os.path.join(upload_dir, user_dir)
                # Process files in user directory
                files = os.listdir(user_path)
                if not files:
                    continue
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(user_path, file)
                        if os.path.isfile(file_path):
                            files_to_process.append((file_path, file, user_dir))
    return files_to_process

def move_processed_file(user_dir, file_path, file, completed_dir):
    """
    Moves a processed file from its original location to the completed directory.

    Args:
        user_dir (str): The user directory name where the file originated
        file_path (str): The full path to the original file
        file (str): The filename
        completed_dir (str): The base directory for completed files

    The function creates a user-specific subdirectory in the completed directory
    if it doesn't exist, then moves the processed file there while preserving
    the original directory structure.
    """
    completed_user_dir = os.path.join(completed_dir, user_dir)
    os.makedirs(completed_user_dir, exist_ok=True)
    destination_path = os.path.join(completed_user_dir, file)
    shutil.move(file_path, destination_path)
