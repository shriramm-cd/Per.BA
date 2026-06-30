import logging
import json
import sys
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    """
    Custom formatter that transforms default log records into structured JSON.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        
        # Merge extra parameters passed in logger calls
        if hasattr(record, "__dict__"):
            for key, val in record.__dict__.items():
                if key not in {"args", "asctime", "created", "exc_info", "exc_text", 
                               "filename", "funcName", "levelname", "levelno", "lineno", 
                               "module", "msecs", "msg", "name", "pathname", "process", 
                               "processName", "relativeCreated", "stack_info", "thread", 
                               "threadName"}:
                    log_record[key] = val
                    
        return json.dumps(log_record)

def get_logger(name: str) -> logging.Logger:
    """
    Utility constructor to retrieve a pre-configured JSON logging instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    # Check if stream handler already exists to prevent duplicate logs
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.propagate = False
    return logger

# INTEGRATION NOTE
# All application modules must obtain loggers using `get_logger(__name__)`.
# This ensures that all log outputs remain structured and parseable for monitoring.
