import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_file='app.log', level=logging.INFO, max_bytes=10*1024*1024, backup_count=5):
    """
    配置应用程序的日志记录。

    Args:
        log_file (str): 日志文件名。
        level (int): 日志级别 (e.g., logging.INFO, logging.DEBUG)。
        max_bytes (int): 单个日志文件的最大字节数。
        backup_count (int): 保留的日志文件备份数量。
    """
    # 获取日志器实例
    logger = logging.getLogger()
    logger.setLevel(level)

    # 避免重复添加处理器
    if not logger.handlers:
        # 创建文件处理器，用于写入日志文件
        # RotatingFileHandler 会在日志文件达到 max_bytes 时自动轮换，并保留 backup_count 个备份
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)

        # 创建控制台处理器，用于输出到控制台
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # 定义日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 为处理器设置格式
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 将处理器添加到日志器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

# 可以在需要时调用此函数来初始化日志
# 例如：
# if __name__ == "__main__":
#     setup_logging()
#     logging.info("This is an info message.")
#     logging.warning("This is a warning message.")
#     logging.error("This is an error message.")