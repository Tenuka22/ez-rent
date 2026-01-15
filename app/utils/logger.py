import sys

from loguru import logger

# Remove default handler
logger.remove()

# Configure console logger
logger.add(
    sys.stderr,
    level="INFO",
    format="<level>{message}</level>",
    colorize=True,
)

# Configure file logger
logger.add(
    "logs/app.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="10 MB",  # Rotate after 10 MB
    retention="7 days",  # Keep logs for 7 days
    enqueue=True,  # Make logging asynchronous
    backtrace=True,
    diagnose=True,
)

# Export the configured logger
__all__ = ["logger"]
