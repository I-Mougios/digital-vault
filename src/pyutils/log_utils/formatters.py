import logging
from datetime import UTC, datetime


class DictFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> dict:  # type: ignore[override]
        log_dict = {
            # "level": record.levelname,
            "created": self.serialize_local_timestamp(record.created),
            "msec": record.msecs,
            "loggerName": record.name,
            "module": record.module,
            "lineno": record.lineno,
            "message": record.getMessage(),
            "exceptionInfo": (self.formatException(record.exc_info) if record.exc_info else None),
            "stackTrace": (self.formatStack(record.stack_info) if record.stack_info else None),
        }

        return log_dict

    @staticmethod
    def serialize_local_timestamp(t: float) -> str:
        dt = datetime.fromtimestamp(t, UTC)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
