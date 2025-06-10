import abc
from datetime import datetime, timezone
import signal
import sys
import time
from typing import Dict, Any, List, Tuple, Union
from command_center.utils.logger_utils import setup_logger
from pathlib import Path
import random
import string


class AbcService(abc.ABC):
    """
    Abstract base class for services that can be started, stopped, and monitored.
    All service implementations should inherit from this class.
    """

    def __init__(self, multi_thread: bool = False):
        self.is_running = False
        self.multi_thread = multi_thread
        self.logger = setup_logger(
            name=self.__class__.__module__ + "." + self.__class__.__name__,
            show_terminal=False,
        )
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(sig, frame):
            self.logger.info(
                f"Received signal {sig}, shutting down {self.__class__.__name__}..."
            )
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    @abc.abstractmethod
    def start(self):
        """
        Start the service. Must be implemented by subclasses.
        This method should set is_running to True when the service is successfully started.
        """
        pass

    @abc.abstractmethod
    def stop(self):
        """
        Stop the service. Must be implemented by subclasses.
        This method should set is_running to False when the service is successfully stopped.
        """
        pass

    def is_healthy(self):
        """
        Check if the service is healthy. Can be overridden by subclasses.
        """
        return self.is_running
