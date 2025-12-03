import os

# Try to import RTC and utime for MicroPython
try:
    from machine import RTC
    import utime

    RTC_AVAILABLE = True
except ImportError:
    RTC_AVAILABLE = False
    try:
        from datetime import datetime
    except ImportError:
        pass

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_SAVE_LOG = True


# Initialize RTC if available
_rtc = None
if RTC_AVAILABLE:
    try:
        _rtc = RTC()
    except:
        RTC_AVAILABLE = False


def get_timestamp():
    """
    Get formatted timestamp in format HH:MM:SS,mmm
    Uses RTC for MicroPython, datetime for CPython
    """
    if RTC_AVAILABLE and _rtc:
        try:
            _, _, _, _, h, m, s, _ = _rtc.datetime()
            # Get milliseconds from ticks_ms (approximate, but close enough)
            ms = utime.ticks_ms() % 1000
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        except:
            pass

    # Fallback for CPython
    try:
        dt = datetime.now()
        return (
            f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d},{dt.microsecond//1000:03d}"
        )
    except:
        return "00:00:00,000"


def get_fs_root_for_storage():
    has_sdcard = True
    try:
        os.listdir("/sdcard")
        print("INFO - SD card available")
    except OSError:
        print("ERROR - SD card not found!")
        has_sdcard = False

    if has_sdcard:
        return "/sdcard"
    else:
        return "/flash"


def create_dir_if_not_exists(dir_path):
    try:
        parts = [p for p in dir_path.split("/") if p]
        if len(parts) < 2:
            print(f"WARNING - Invalid directory path (no parent): {dir_path}")
            return
        parent = "/" + "/".join(parts[:-1])
        dir_name = parts[-1]
        if dir_name not in os.listdir(parent):
            os.mkdir(dir_path)
            print(f"INFO - Created {dir_path}")
        else:
            print(f"INFO - {dir_path} directory already exists")
    except OSError as e:
        print(f"ERROR - Failed to create/access {dir_path} directory: {e}")


FS_ROOT = get_fs_root_for_storage()
LOG_DIR = f"{FS_ROOT}/logs"
LOG_FILE_NAME = "main.log"


# Log level hierarchy (lower number = lower priority)
# Messages at or above the configured level will be printed
LOG_LEVELS = {
    "DEBUG": 10,  # Shows: DEBUG, INFO, WARNING, ERROR, CRITICAL
    "INFO": 20,  # Shows: INFO, WARNING, ERROR, CRITICAL
    "WARNING": 30,  # Shows: WARNING, ERROR, CRITICAL
    "ERROR": 40,  # Shows: ERROR, CRITICAL
    "CRITICAL": 50,  # Shows: CRITICAL only
}


class SimpleLogger:
    """Simple logger for MicroPython when logging module is not available
    Singleton class - only one instance exists, ensuring single log file handle
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Singleton pattern - return the same instance every time"""
        if cls._instance is None:
            print("INFO - Singleton Logger class Initiated, __new__")
            cls._instance = super(SimpleLogger, cls).__new__(cls)
        else:
            # print("DEBUG - Singleton Logger class already instantiated, __new__")
            pass
        return cls._instance

    def __init__(
        self,
        name=None,
        show_terminal=False,
        log_level=DEFAULT_LOG_LEVEL,
        save_log=DEFAULT_SAVE_LOG,
        log_dir=None,
        log_file_name=None,
    ):
        # Only initialize once - use first set of parameters
        if SimpleLogger._initialized:
            # print("DEBUG - Logger already initialized, __init__, returning")
            return # TODO, we may update settings later

        # First initialization
        self.name = name or ""
        self.show_terminal = show_terminal
        self.log_level = log_level or DEFAULT_LOG_LEVEL
        self.save_log = save_log or DEFAULT_SAVE_LOG
        # Handle both string and numeric log levels
        if isinstance(self.log_level, str):
            self.log_level_value = LOG_LEVELS.get(
                self.log_level.upper(), LOG_LEVELS["INFO"]
            )
        else:
            # If it's already a numeric value, use it directly
            self.log_level_value = self.log_level

        # File logging setup - open file once at initialization
        self.log_file = None
        if self.save_log and log_dir and log_file_name:
            self._open_log_file(log_dir, log_file_name)

        SimpleLogger._initialized = True

    def _open_log_file(self, log_dir, log_file_name):
        """
        Open log file once for the entire SimpleLogger instance.
        Creates directory if it doesn't exist.
        Singleton ensures this is only called once.
        """
        # Check if file is already open (shouldn't happen with singleton, but safety check)
        if self.log_file is not None:
            try:
                # Check if file is still valid by trying to access it
                self.log_file.flush()
                print("INFO - Log file already open, reusing existing handle")
                return
            except (ValueError, OSError):
                # File was closed or invalid, continue to reopen
                self.log_file = None

        try:
            # Check if directory exists by trying to list it
            create_dir_if_not_exists(log_dir)

            # MicroPython/OpenMV doesn't have os.path - use manual join
            clean_log_dir = log_dir.strip()
            if clean_log_dir.endswith("/"):
                log_file_path = clean_log_dir + log_file_name
            else:
                log_file_path = clean_log_dir + "/" + log_file_name

            # Ensure file exists - create it if it doesn't exist
            try:
                # Try to open in read mode to check if file exists
                test_file = open(log_file_path, "r")
                test_file.close()
            except OSError:
                # File doesn't exist, create it by opening in write mode first
                try:
                    new_file = open(log_file_path, "w")
                    new_file.close()
                    print(f"INFO - Log file created: {log_file_path}")
                except Exception as e:
                    print(f"WARNING - Failed to create log file: {e}")

            # Open file in append mode and keep it open
            self.log_file = open(log_file_path, "a")
            self.log_file.flush()
            print(f"DEBUG - Log file opened: {log_file_path}")
        except Exception as e:
            print(f"WARNING - Failed to open log file: {e}")
            self.log_file = None

    def _log(self, level, msg):
        # Get numeric value for the message level
        level_value = LOG_LEVELS.get(level, LOG_LEVELS["INFO"])

        # Only print if message level is >= configured log level
        # (higher number = higher priority, so we want to show it)
        if level_value >= self.log_level_value:
            timestamp = get_timestamp()
            log_message = f"{timestamp} - {level} - {msg}"

            # Write to terminal if enabled
            if self.show_terminal:
                print(log_message)

            # Write to file if file logging is enabled
            if self.log_file:
                try:
                    self.log_file.write(log_message + "\n")
                    self.log_file.flush()  # Ensure data is written immediately
                    # Try to sync to disk if available (MicroPython/OpenMV)
                    try:
                        if hasattr(self.log_file, "sync"):
                            self.log_file.sync()
                        else:
                            pass  # TODO sync is not available in micropython
                            # print("____log sync failed, not available")
                    except (AttributeError, OSError):
                        print("____log sync failed, AttributeError, OSError")
                        pass
                except Exception as e:
                    print(f"WARNING - Failed to write to log file: {e}")

    def info(self, msg):
        self._log("INFO", msg)

    def warning(self, msg):
        self._log("WARNING", msg)

    def error(self, msg):
        self._log("ERROR", msg)

    def debug(self, msg):
        self._log("DEBUG", msg)

    def critical(self, msg):
        self._log("CRITICAL", msg)

    def close(self):
        """Close the log file if it's open - ensures proper cleanup"""
        if self.log_file:
            try:
                # Flush and sync before closing
                self.log_file.flush()
                # Sync to disk if available (MicroPython might not have this)
                try:
                    if hasattr(self.log_file, "sync"):
                        self.log_file.sync()
                    else:
                        pass  # TODO sync is not available in micropython
                        # print("____log close failed, sync not available")
                except (AttributeError, OSError):
                    pass
                    # print("____log close failed, AttributeError, OSError")

                # Close the file
                self.log_file.close()
                self.log_file = None
                print("INFO - Log file closed")
            except Exception as e:
                print(f"WARNING - Failed to close log file: {e}")
                # Try to set to None even if close failed
                try:
                    self.log_file = None
                except:
                    pass


def log_level_type(log_level):
    return log_level  # Return as-is for SimpleLogger

    if log_level == "INFO":
        return logging.INFO
    elif log_level == "WARNING":
        return logging.WARNING
    elif log_level == "ERROR":
        return logging.ERROR
    elif log_level == "DEBUG":
        return logging.DEBUG
    elif log_level == "CRITICAL":
        return logging.CRITICAL
    else:
        print("[ERROR] invalid log level type")
        return logging.INFO


def setup_logger(
    name=None,
    show_terminal=False,
    log_level=DEFAULT_LOG_LEVEL,
    save_log=DEFAULT_SAVE_LOG,
    log_dir=LOG_DIR,
    log_file_name=LOG_FILE_NAME,
):
    """
    Setup a logger with optional file and terminal handlers.
    Works in both CPython (with logging module) and MicroPython (with fallback).

    Args:
        name: Logger name (None for root logger)
        show_terminal: If True, log to terminal/console
        log_level: Logging level (string like "INFO", "DEBUG", etc. or logging constant, or may be int value)
        save_log: If True, save logs to file (default: False)
        log_dir: Directory to save log file (only used if save_log=True)
        log_file_name: Name of log file (only used if save_log=True)

    Returns:
        logging.Logger or SimpleLogger: Configured logger instance
    """
    return SimpleLogger(
        name=name,
        show_terminal=show_terminal,
        log_level=log_level,
        save_log=save_log,
        log_dir=log_dir,
        log_file_name=log_file_name,
    )

# Initialize the singleton instance
logger = setup_logger(show_terminal=True, log_level=DEFAULT_LOG_LEVEL, save_log=DEFAULT_SAVE_LOG)

# can be used like
# logger = setup_logger(show_terminal=True, log_level="INFO", save_log=False)
# logger = setup_logger(name=__name__, show_terminal=True, log_level="DEBUG", save_log=True)
# logger = setup_logger(show_terminal=True, log_level="INFO", save_log=True, log_dir="/sdcard", log_file_name="mainlog.txt")
