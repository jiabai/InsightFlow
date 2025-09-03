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
from be.common.database_manager import Chunk
from be.api_services.shared_resources import db_manager, redis_manager
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
    def __init__(self, user_id: str, file_id: str):

        # 初始化配置
        self.config = ConfigManager()
        # 初始化组件
        self.db_manager = db_manager
        self.redis_manager = redis_manager
        self.file_id = file_id
        self.user_id = user_id

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

        logger.info("Knowledge processing service started, polling upload directory...")
        async with self.db_manager.get_db() as db:
            file_metadata = await self.db_manager.get_file_metadata_by_file_id(db, self.file_id)
            if file_metadata is None:
                logger.error("File metadata not found for file ID: %s", self.file_id)
                return
            try:
                # Get all markdown files in upload directory
                files_to_process = get_markdown_files_from_upload_dir(
                    self.config.upload_dir,
                    self.user_id,
                    file_metadata.stored_filename
                )
                if not files_to_process:
                    time.sleep(5)
                    raise ValueError("No files to process")
                logger.debug("found file_path %s", files_to_process[0][0])
                logger.debug("file_id %s", files_to_process[0][1])
                logger.debug("user_id %s", files_to_process[0][2])

                for current_file_path, current_file_id, current_user_id in files_to_process:
                    logger.debug("Processing file '%s'", current_file_id)
                    await self.process_file(current_file_path, current_file_id)
                    # 移动文件到 'completed' 目录
                    logger.debug("Moving file '%s' to completed directory.", current_file_id)
                    move_processed_file(
                        current_user_id,
                        current_file_path,
                        current_file_id,
                        self.config.completed_dir
                    )
            except (IOError, OSError, asyncio.CancelledError, RuntimeError, ValueError) as e:
                logger.error("Error during polling: %s", e, exc_info=True)

    async def process_file(self, file_path: str, stored_filename: str) -> bool:
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
        user_id, file_id, original_filename = parse_stored_filename(stored_filename)

        async with self.db_manager.get_db() as mysql_db:
            try:
                # 1. 获得id和文件名
                file_id, original_filename = await self._get_file_metadata_and_ids(
                    mysql_db,
                    file_id
                )
                if file_id is None:
                    return False
                logger.debug("Processing file '%s' (File ID: %s)", original_filename, file_id)

                # 2. 更新Redis状态为 'Processing'
                await self.redis_manager.set_file_status(file_id, "Processing")
                logger.debug("Redis status updated to 'Processing'.")

                # 3. 读取和分割Markdown文件，得到chunks
                content = await self._read_and_validate_file(file_path, file_id)
                if content is None:
                    return False
                splitter = MarkdownSplitter()
                chunks = splitter.split_markdown(
                    content,
                    min_length=1000,
                    max_length=3000
                ) or []
                logger.debug("File '%s' split into %s chunks.", original_filename, len(chunks))
                if chunks:
                    db_chunks = await self.db_manager.save_chunks(
                        mysql_db,
                        chunks,
                        user_id,
                        file_id,
                        original_filename
                    )
                else:
                    logger.error("No chunks generated from file '%s'.", original_filename)
                    return False
            except (IOError, ValueError, RuntimeError, asyncio.CancelledError) as e:
                logger.error("Error processing file '%s': %s", stored_filename, e, exc_info=True) 
                if file_id:
                    await self.redis_manager.set_file_status(file_id, "Failed")
                    logger.debug("Redis status updated to 'Failed'.")  
                return False
            # 4. 生成问题
            if chunks:
                logger.info("Start to generate questions for file '%s'.", original_filename)
                total_questions = 0
                for chunk in db_chunks:
                    # 生成问题（LLM调用）
                    generated_questions = await self._generate_questions(
                        chunk.content,
                        self.config.project_config,
                        self.config.project_details,
                        []
                    )
                    if generated_questions:
                        async with self.db_manager.get_db() as mysql_db:
                            saved_count = await self.db_manager.save_questions(
                                mysql_db, user_id, file_id, generated_questions, chunk.id
                            )
                            total_questions += saved_count
            # 5. 更新Redis状态为 'Completed'
            await self.redis_manager.set_file_status(file_id, "Completed")
            logger.debug(
                "File '%s' processing completed, Redis status updated to 'Completed'.",
                original_filename
            )
        return True

    async def _get_file_metadata_and_ids(self, mysql_db, file_id: str):
        file_metadata = await self.db_manager.get_file_metadata_by_file_id(
            mysql_db,
            file_id
        )
        if not file_metadata:
            logger.error("File '%s' not found in database, skipping processing.", file_id)
            return None, None
        logger.debug("Successfully retrieved file '%s' metadata from database.", file_id)

        file_id = file_metadata.file_id
        original_filename = file_metadata.filename

        return file_id, original_filename

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
        return generated_questions

    async def _generate_questions_and_save(
        self,
        mysql_db,
        db_chunks: list[Chunk],
        user_id: str,
        file_id: str,
        p_config: dict,
        p_details: dict
    ) -> int:
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
                        user_id,
                        file_id,
                        generated_questions,
                        chunk.id
                    )
                total_questions += saved_count
                logger.info(
                    "Successfully generated and saved %s questions for chunk %s.",
                    saved_count,
                    chunk.id
                )
        return total_questions

def parse_stored_filename(stored_filename: str):
    """
    Parse the stored filename to extract user_id, file_id, and filename.

    Args:
        stored_filename (str): The stored filename in the format 'user_id_file_id_filename'

    Returns:
        tuple: A tuple containing (user_id, file_id, filename)

    Raises:
        ValueError: If the stored_filename format is invalid
    """
    parts = stored_filename.split('_', 2) # Split at most twice
    if len(parts) == 3:
        user_id = parts[0]
        file_id = parts[1]
        filename = parts[2]
        return user_id, file_id, filename
    else:
        # Handle cases where the format might not match, or raise an error
        raise ValueError("Invalid stored_filename format")

def get_markdown_files_from_upload_dir(upload_dir: str, user_id: str, file_id: str) -> list:
    """
    Scans the upload directory for a specific markdown file within a user subdirectory.

    Args:
        upload_dir (str): Path to the upload directory to scan
        user_id (str): The user ID to look for
        file_id (str): The file ID to look for

    Returns:
        list: List of tuples (file_path, filename, user_directory) for each markdown
        file found

    The function scans the user subdirectory in the upload directory and 
    looks for the specified file.
    If found, it returns a tuple containing the full path, filename, and 
    parent user directory name.
    """
    files_to_process = []

    # 构建用户目录路径
    user_path = os.path.join(upload_dir, user_id)

    # 检查用户目录是否存在
    if not os.path.exists(user_path) or not os.path.isdir(user_path):
        return files_to_process

    # 构建文件完整路径
    file_path = os.path.join(user_path, file_id)

    # 检查文件是否存在
    if os.path.exists(file_path) and os.path.isfile(file_path):
        files_to_process.append((file_path, file_id, user_id))

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
