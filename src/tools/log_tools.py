# -*-coding:utf-8

import datetime
import glob
import inspect
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

from tools.gen_ini import GenIni


class CustomRotatingFileHandler(RotatingFileHandler):
    # Custom RotatingFileHandler that calls cleanup on rollover
    def doRollover(self):
        super().doRollover()  # Perform the default rollover behavior
        LogTools.cleanup_old_logs()


class LogTools:
    """
    Utility class for configuring and managing application logging with support for rotating file handlers
    and cleanup of old log files.
    This class provides methods to initialize logging based on configuration from an INI file,
    supports custom file naming for rotated logs with timestamps, and cleans up old log files beyond a specified limit.
    Class Variables:
        _filename (str): The absolute path to the log file currently in use.
        _max_old_files (int): The maximum number of old log files to retain during cleanup.
      """
    _filename: str = ""
    _max_old_files: int = 0

    @staticmethod
    def timestamp_namer(filename: str) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # strip off the numeric extension (typically .1 because we're setting backupCount=1)
        (root, extension) = os.path.splitext(filename)
        # then do it again to get the actual extension (typically .log)
        (root, extension) = os.path.splitext(root)
        # print(f"Renaming {filename} to {root}.{timestamp}{extension}")

        # make sure the filename is unique by appending a sequential number if necessary
        i = 0
        while True:
            sequential_postfix = f".{i}" if i > 0 else ""
            target_filename = f"{root}.{timestamp}{sequential_postfix}{extension}"
            if not os.path.exists(target_filename):
                break
            i += 1

        return target_filename

    @classmethod
    def initialize(cls, ini: Optional["GenIni"] = None) -> None:
        """Initialize logging configuration."""

        if ini is None:
            ini = GenIni.get_default_instance()

        section = "Log"
        minimum_file_log_level = ini.get_int(section, "MinimumFileLogLevel", logging.CRITICAL + 1)  # Default to nothing
        LogTools._filename = ini.get_string(section, "FileName", "")

        if minimum_file_log_level <= logging.CRITICAL and LogTools._filename:
            LogTools._max_old_files = ini.get_int(section, "MaxOldFiles", 0)
            LogTools._filename = os.path.abspath(LogTools._filename)
            # Ensure the directory exists
            try:
                t = os.path.split(LogTools._filename)
                os.mkdir(t[0])
            except:
                pass
            # Configure rotating file handler
            file_handler = CustomRotatingFileHandler(
                LogTools._filename,
                maxBytes=ini.get_int(section, "MaxFileSize", 10 * 1024 * 1024),
                encoding=ini.get_string(section, "FileEncoding", "utf-8"),
                backupCount=1,  # if not specified, rotation will not happen, regardless of file size and custom namer
                delay=True,
            )
            file_handler.namer = LogTools.timestamp_namer
            file_handler.setLevel(minimum_file_log_level)
        else:
            file_handler = None

        minimum_console_log_level = ini.get_int(section, "MinimumConsoleLogLevel", 0)  # Default to everything
        if minimum_console_log_level <= logging.CRITICAL:
            # Configure console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(minimum_console_log_level)
        else:
            console_handler = None

        handlers = []
        if file_handler:
            handlers.append(file_handler)
        if console_handler:
            handlers.append(console_handler)

        # Configure root logger
        logging.basicConfig(
            level=min(minimum_file_log_level, minimum_console_log_level),
            format=ini.get_string(section, "LogFormat", "%(asctime)s.%(msecs)03d [%(levelname)s]: %(module)s.%(funcName)s: %(message)s"),
            datefmt=ini.get_string(section, "DateFormat", "%Y-%m-%d %H:%M:%S"),
            handlers=handlers
        )

        # Map default log levels to custom names
        logging.addLevelName(logging.DEBUG, "DBG")
        logging.addLevelName(logging.INFO, "INF")
        logging.addLevelName(logging.WARNING, "WRN")
        logging.addLevelName(logging.ERROR, "ERR")
        logging.addLevelName(logging.CRITICAL, "FAT")

    @classmethod
    def cleanup_old_logs(cls):
        if not LogTools._filename or LogTools._max_old_files <= 0:
            return
        (root, extension) = os.path.splitext(LogTools._filename)
        log_files = sorted(glob.glob(f"{root}.2*{extension}"), key=os.path.getctime, reverse=True)
        # Keep only the latest LogTools._max_old_files logs
        for old_log in log_files[LogTools._max_old_files:]:
            os.remove(old_log)

    @classmethod
    def assert_log(cls, condition: bool) -> None:
        """Assert a condition and log an error if it fails."""
        if not condition:
            frame = inspect.stack()[1]
            logging.log(level=logging.CRITICAL, msg=f"assertion failure at line {frame.lineno}", stacklevel=2)
