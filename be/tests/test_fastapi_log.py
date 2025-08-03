from fastapi import FastAPI
import os
import sys

# 将项目根目录添加到 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from be.api_services.fastapi_logger import setup_logging
import logging

app = FastAPI()

logger = setup_logging(app, log_file='my_fastapi_app.log', level=logging.INFO, max_bytes=10*1024*1024, backup_count=5, rotation_type='size')

logger.info("Log test started successfully.")
