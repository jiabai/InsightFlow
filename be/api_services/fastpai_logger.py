import logging
import uuid
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
import contextvars
from fastapi import FastAPI, Request

# 创建 ContextVar 来存储请求上下文信息
url_var = contextvars.ContextVar('url', default='No_URL')
request_id_var = contextvars.ContextVar('request_id', default='No_Request_ID')

class RequestFormatter(logging.Formatter):
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
    """
    配置应用程序的日志记录并添加中间件
    
    Args:
        app: FastAPI 实例
        log_file: 日志文件名
        level: 日志级别
        max_bytes: 单个日志文件的最大字节数
        backup_count: 保留的日志文件备份数量
        rotation_type: 轮转类型 ('size' 或 'time')
        when: 时间轮转的时机
    
    Returns:
        配置好的 logger 实例
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    # 日志格式（包含请求上下文）
    log_format = ('%(asctime)s | %(levelname)s | %(url)s | %(request_id)s | '
                  '%(pathname)s:%(funcName)s:%(lineno)d - %(message)s')
    formatter = RequestFormatter(log_format)

    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    full_log_path = os.path.join(log_dir, log_file)

    # 根据 rotation_type 选择文件处理器
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

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # 添加中间件
    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = str(uuid.uuid4().hex)
        url = str(request.url)

        token_url = url_var.set(url)
        token_request_id = request_id_var.set(request_id)

        try:
            response = await call_next(request)
        finally:
            # 清除 ContextVar 的值
            url_var.reset(token_url)
            request_id_var.reset(token_request_id)

        return response

    return logger
