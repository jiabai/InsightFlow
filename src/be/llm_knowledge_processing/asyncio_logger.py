"""
Asynchronous logging module with task ID tracking and rotation capabilities.

This module provides a singleton AsyncLogger class for handling asynchronous logging
with support for both size-based and time-based log rotation. It includes task ID
tracking across asynchronous operations using contextvars, custom formatting, and
convenient setup functions for global logger configuration.

Key components:
- AsyncLogger: Singleton class for managing the logging configuration
- RequestFormatter: Custom formatter that includes task IDs in log records
- with_task_id: Decorator for tracking async operations with unique task IDs
- setup_logger: Function to initialize the global logger instance
- get_logger: Function to access the configured logger instance
"""

import logging
import uuid
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
import contextvars

task_id_var = contextvars.ContextVar('task_id', default='No_Task_ID')

class RequestFormatter(logging.Formatter):
    """A custom formatter that adds task ID to log records.
    
    This formatter extends the base logging.Formatter to include a task_id field
    in each log record. The task_id is retrieved from a ContextVar and helps track
    requests across asynchronous operations.
    """
    def format(self, record):
        try:
            record.task_id = task_id_var.get()
        except LookupError:
            record.task_id = "No_Task_ID"
        return super().format(record)

class AsyncLogger:
    """A singleton logger class that handles asynchronous logging with rotation capabilities.

    This class implements a singleton pattern to ensure only one logger instance exists.
    It supports both size-based and time-based log rotation, console output, and custom
    formatting that includes task IDs for tracking asynchronous operations.

    Attributes:
        _instance: Class variable storing the singleton instance
        logger: The configured logging.Logger instance
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_file='app.log', level=logging.INFO,
                 max_bytes=10 * 1024 * 1024, backup_count=5,
                 rotation_type='size', when='midnight'):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level)

        # 避免重复添加 handler
        if not self.logger.handlers:
            self._setup_formatter(log_file, level, max_bytes, backup_count, rotation_type, when)

    def _setup_formatter(self, log_file, level, max_bytes, backup_count, rotation_type, when):
        log_format = ('%(asctime)s | %(levelname)s | %(task_id)s | '
                      '%(pathname)s:%(funcName)s:%(lineno)d - %(message)s')
        formatter = RequestFormatter(log_format)

        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        full_log_path = os.path.join(log_dir, log_file)

        if rotation_type == 'size':
            handler = RotatingFileHandler(
                full_log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
        elif rotation_type == 'time':
            handler = TimedRotatingFileHandler(
                full_log_path,
                when=when,
                backupCount=backup_count
            )
        else:
            raise ValueError("Invalid rotation_type. Must be 'size' or 'time'.")

        handler.setFormatter(formatter)
        handler.setLevel(level)
        self.logger.addHandler(handler)

        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(formatter)
        # console_handler.setLevel(level)
        # self.logger.addHandler(console_handler)

    @property
    def logger(self):
        """Gets the logger instance.

        Returns:
            logging.Logger: The configured logger instance for this AsyncLogger.
        """
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value

def with_task_id(func):
    """A decorator that assigns a unique task ID to the current async context.

    This decorator generates a UUID for each decorated coroutine execution and sets it
    in the task_id_var ContextVar. This allows tracking of asynchronous operations
    across the application through logging.

    Args:
        func: The coroutine function to be decorated.

    Returns:
        A wrapped coroutine function that manages the task ID context.
    """
    async def wrapper(*args, **kwargs):
        task_id = uuid.uuid4().hex
        token = task_id_var.set(task_id)
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            task_id_var.reset(token)
    return wrapper

def setup_logger(log_file='app.log', level=logging.INFO,
                 max_bytes=10 * 1024 * 1024, backup_count=5,
                 rotation_type='size', when='midnight'):
    """Initializes and configures the global AsyncLogger instance.

    This function creates a new AsyncLogger instance with the specified configuration
    and stores it in a global variable for access throughout the application.

    Args:
        log_file (str, optional): Name of the log file. Defaults to 'app.log'.
        level (int, optional): Logging level. Defaults to logging.INFO.
        max_bytes (int, optional): Maximum size of log file before rotation in bytes.
            Defaults to 10MB.
        backup_count (int, optional): Number of backup files to keep. Defaults to 5.
        rotation_type (str, optional): Type of log rotation - 'size' or 'time'.
            Defaults to 'size'.
        when (str, optional): Time interval for rotation when using time-based rotation.
            Defaults to 'midnight'.
    """
    global async_logger
    async_logger = AsyncLogger(log_file, level, max_bytes, backup_count, rotation_type, when)

def get_logger():
    """Gets the configured AsyncLogger instance.

    This function returns the global AsyncLogger instance that must be initialized
    by calling setup_logger() first. It provides access to the configured logger
    for use throughout the application.

    Returns:
        logging.Logger: The configured logger instance.

    Raises:
        RuntimeError: If setup_logger() hasn't been called to initialize the logger.
    """
    if 'async_logger' not in globals():
        raise RuntimeError("Logger not initialized. Call setup_logger() first.")
    return async_logger.logger

setup_logger(log_file='knowledge_processing.log', level=logging.DEBUG)
