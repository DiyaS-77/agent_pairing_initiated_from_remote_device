import inspect
import logging
import os
import sys
import time
import traceback


class CustomFormatter(logging.Formatter):
    """Custom formatter for console logs that applies colored output
    based on the log level (DEBUG, INFO, ERROR)."""
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    base_format = "%(asctime)s | %(levelname)s | %(message)s"

    formats = {
        logging.DEBUG: ''.join([grey, base_format]),
        logging.INFO: ''.join([yellow, base_format]),
        logging.ERROR: ''.join([red, base_format])
    }

    def format(self, record):
        """Overrides the default format method to apply custom styling.

        Args:
            record: The log record to format.

        Returns:
            formatted_log: The formatted log string.
        """
        log_fmt = self.formats.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class Logger:
    """Adds functionality like log file separation, colored console output,
    and automatic function/file tagging."""

    def __init__(self, name=None):
        """Initializes the Logger instance.

        Args:
            name: Name for the logger. Defaults to None.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.log_path = None
        self.stream_handler = None
        self.logger_init()

    def logger_init(self):
        """Creates a timestamped log directory and sets up the logger
        This ensures every app session logs to its own unique folder"""
        log_time = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime(time.time()))
        cur_file = os.path.abspath(__file__)
        ui_dir = os.path.dirname(cur_file)
        test_automation_dir = os.path.dirname(ui_dir)
        workspace_root = os.path.dirname(test_automation_dir)
        base_log_dir = os.path.join(workspace_root, "logs")
        os.makedirs(base_log_dir, exist_ok = True)
        self.log_path = os.path.join(base_log_dir, f"{log_time}_logs")
        os.makedirs(self.log_path, exist_ok = True)
        self.setup_logger_file(self.log_path)

    def setup_logger_file(self, path, device=''):
        """Sets up log files for DEBUG, INFO, and ERROR levels separately
        and initializes colored console output.

        Args:
            path: Directory path where log files will be saved.
            device: Optional device prefix for log files.
        """
        self.log_path = path
        log_format = "%(asctime)s | %(levelname)s | %(message)s"
        formatter = logging.Formatter(log_format)
        if device:
            device = '_'.join([device, ''])
        info_path = os.path.join(self.log_path, f"{device}info.log")
        info_handler = logging.FileHandler(info_path)
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)
        self.logger.addHandler(info_handler)
        if not self.stream_handler:
            self.stream_handler = logging.StreamHandler(sys.stdout)
            self.stream_handler.setLevel(logging.DEBUG)
            self.stream_handler.setFormatter(CustomFormatter())
            self.logger.addHandler(self.stream_handler)

    def cleanup_logger(self, name):
        """Removes all log handlers from the logger.

        Args:
            name: The logger's name to clean up.
        """
        self.logger = logging.getLogger(name)
        while self.logger.handlers:
            if isinstance(self.logger.handlers[0], logging.StreamHandler):
                self.stream_handler = None
            self.logger.removeHandler(self.logger.handlers[0])

    def get_logger(self, name):
        """Sets or updates the logger instance by name.

        Args:
            name: Logger name.
        """
        self.logger = logging.getLogger(name)

    def function_property(self):
        """Gets the caller's function name and file name for context-aware logging.

        Returns:
            function_name: Name of the calling function.
            file_name: Name of the file where the function is defined.
        """
        function = inspect.currentframe().f_back.f_back.f_code
        function_name = function.co_name
        filename = os.path.splitext(function.co_filename.split('/')[-1])[0]
        return function_name, filename

    def info(self, message, *args):
        """Logs an INFO-level message with context.

        Args:
            message: The message format string.
            *args: Arguments for formatting.
        """
        function_name, filename = self.function_property()
        if args:
            message = message % args
        self.logger.info("%s | %s | %s", filename, function_name, message)

    def debug(self, message, *args):
        """Logs a DEBUG-level message with context.

        Args:
            message: The message to log.
            *args: Arguments for formatting.
        """
        function_name, filename = self.function_property()
        if args:
            message = message % args
        self.logger.debug("%s | %s | %s", filename, function_name, message)

    def error(self, message, *args):
        """Logs an ERROR-level message with context and full traceback.

        Args:
            message: The error message to log.
            *args: Arguments for formatting.
        """
        function_name, filename = self.function_property()
        if args:
            message = message % args
        self.logger.error("%s | %s | %s", filename, function_name, message)
        self.logger.error(traceback.format_exc())

    def warning(self, message, *args):
        """Logs a WARNING-level message with context.

        Args:
            message: The warning message to log.
            *args: Arguments for formatting.
        """
        function_name, filename = self.function_property()
        if args:
            message = message % args
        self.logger.warning("%s | %s | %s", filename, function_name, message)
