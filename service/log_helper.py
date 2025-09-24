import logging
import datetime
import inspect
import pathlib
import sys
from typing import Optional


class LogHelper:
    """
    Centralized logger:
      1) Creates /logs/YYYY-MM-DD/ if missing (under project root).
      2) Writes file logs as: <file_stem>_YYYY-MM-DD.log
      3) Sends logs to both file and console.
      4) Optional: capture uncaught exceptions via install_global_excepthook().

    Usage:
        from service.log_helper import LogHelper
        logger = LogHelper.get_logger()               # auto file_stem from caller
        # or logger = LogHelper.get_logger("ingest")  # explicit stem
        logger.info("hello")
        logger.exception("boom")

        # (optional) route uncaught exceptions:
        LogHelper.install_global_excepthook()
    """

    @staticmethod
    def _project_root() -> pathlib.Path:
        # service/ is one level under project root
        return pathlib.Path(__file__).resolve().parents[1]

    @staticmethod
    def _today_str() -> str:
        return datetime.date.today().strftime("%Y-%m-%d")

    @staticmethod
    def _caller_file_stem() -> str:
        # first frame outside this module
        for frame_info in inspect.stack()[1:]:
            module = inspect.getmodule(frame_info.frame)
            if module and getattr(module, "__file__", None) != __file__:
                return pathlib.Path(frame_info.filename).stem
        return "app"

    @classmethod
    def get_logger(cls, name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
        file_stem = name or cls._caller_file_stem()
        date_str = cls._today_str()

        logs_dir = cls._project_root() / "logs" / date_str
        logs_dir.mkdir(parents=True, exist_ok=True)

        file_path = logs_dir / f"{file_stem}_{date_str}.log"

        logger = logging.getLogger(file_stem)
        if logger.handlers:
            return logger  # already configured

        logger.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # File handler
        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)
        logger.propagate = False

        return logger

    @classmethod
    def install_global_excepthook(cls, name: Optional[str] = None, level: int = logging.ERROR) -> None:
        """Route uncaught exceptions to the day's file log for the calling module."""
        def _hook(exc_type, exc, tb):
            log = cls.get_logger(name=name, level=level)
            log.error("Uncaught exception", exc_info=(exc_type, exc, tb))
        sys.excepthook = _hook
