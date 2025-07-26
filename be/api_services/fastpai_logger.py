"""FastAPI logging configuration module.

This module provides a custom logging setup for FastAPI applications with the following features:
- Request context tracking (URL and request ID)
- File rotation based on size or time
- Console and file output
- Custom formatting including request context information
- Middleware for automatic request context handling

The module uses contextvars to safely store request-specific information in an async environment.
"""
import logging
import uuid
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
import contextvars
from fastapi import FastAPI, Request

# Create ContextVar to store request context information
url_var = contextvars.ContextVar('url', default='No_URL')
request_id_var = contextvars.ContextVar('request_id', default='No_Request_ID')

class RequestFormatter(logging.Formatter):
    """A custom logging formatter that adds request context information.
    
    This formatter extends the base logging.Formatter to include URL and request ID
    from the request context variables into log records. If the context variables
    are not found, it falls back to default values.
    """
    def format(self, record):
        try:
            record.url = url_var.get()
            record.request_id = request_id_var.get()
        except LookupError:
            record.url = "No_URL"
            record.request_id = "No_Request_ID"
        return super().format(record)

def setup_logging(app: FastAPI, log_file='app.log', level=logging.INFO,
                  max_bytes=10*1024*1024, backup_count=5, rotation_type='size',
                  when='midnight') -> logging.Logger:
    """Set up logging for a FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.
        log_file (str, optional): The name of the log file. Defaults to 'app.log'.
        level (int, optional): The logging level. Defaults to logging.INFO.
        max_bytes (int, optional): The maximum size of the log file in bytes before rotation. 
        Defaults to 10MB.
        backup_count (int, optional): The number of backup log files to keep. Defaults to 5.
        rotation_type (str, optional): The type of log rotation. Can be 'size' or 'time'. 
        Defaults to 'size'.
        when (str, optional): The time interval for time-based rotation. Defaults to 'midnight'.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    # Log format (including request context)
    log_format = ('%(asctime)s | %(levelname)s | %(url)s | %(request_id)s | '
                  '%(pathname)s:%(funcName)s:%(lineno)d - %(message)s')
    formatter = RequestFormatter(log_format)

    # Create log directory
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    full_log_path = os.path.join(log_dir, log_file)

    # Select file handler based on rotation_type
    if rotation_type == 'size':
        file_handler = RotatingFileHandler(
            full_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
    elif rotation_type == 'time':
        file_handler = TimedRotatingFileHandler(
            full_log_path,
            when=when,
            backupCount=backup_count
        )
    else:
        raise ValueError("Invalid rotation_type. Must be 'size' or 'time'.")

    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    if app:
        @app.middleware("http")
        async def add_request_context(request: Request, call_next):
            request_id = str(uuid.uuid4().hex)
            url = str(request.url)

            token_url = url_var.set(url)
            token_request_id = request_id_var.set(request_id)

            try:
                response = await call_next(request)
                return response
            finally:
                # Reset ContextVar values
                url_var.reset(token_url)
                request_id_var.reset(token_request_id)

    return logger
