import inspect
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "rematch_italia.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class ClassNameFilter(logging.Filter):
    def filter(self, record):
        cwd = os.getcwd()
        abs_path = os.path.abspath(record.pathname)
        rel_path = os.path.relpath(abs_path, cwd)
        app_index = rel_path.find("app" + os.sep)
        if app_index != -1:
            relpath = rel_path[app_index + len("app" + os.sep):]
        else:
            relpath = rel_path.replace("\\", ".")
        if relpath.endswith(".py"):
            relpath = rel_path[:-3]
        record.relpath =  relpath.replace("\\", ".")  # For Windows paths
        # Existing classname logic
        record.classname = ""
        frame = inspect.currentframe()
        while frame:
            code = frame.f_code
            if code.co_name == record.funcName:
                self_obj = frame.f_locals.get("self")
                if self_obj:
                    record.classname = self_obj.__class__.__name__
                    break
            frame = frame.f_back
        return True


class SmartClassFormatter(logging.Formatter):
    def format(self, record):
        if record.classname:
            record.classname = f"{record.classname}"
        return super().format(record)


handler = logging.handlers.TimedRotatingFileHandler(
    LOG_FILE, when="midnight", interval=1, backupCount=5, encoding="utf-8"
)
console = logging.StreamHandler()

fmt = "%(asctime)s - [%(levelname)s] - %(relpath)s.%(classname)s.%(funcName)s(): %(message)s {%(lineno)d}"
formatter = SmartClassFormatter(fmt)

handler.setFormatter(formatter)
console.setFormatter(formatter)

logger = logging.getLogger("RematchItalia")
logger.setLevel(os.getenv("LOG_LEVEL", "DEBUG").upper())
logger.addFilter(ClassNameFilter())
logger.addHandler(handler)
logger.addHandler(console)
logger.propagate = False
