# -*-coding:utf-8

import logging
import threading
from typing import Optional

from tools.gen_ini import GenIni
from tools.svc_watch_dog_client import SvcWatchDogClient


class DummyThread:
    """
    DummyThread is an example for implementing a typical worker thread that requires periodic monitoring by a watchdog service and supports fast, responsive shutdown.
    This class provides:
    - Automatic periodic "ping" to a watchdog (via SvcWatchDogClient) to signal liveness.
    - A background loop for executing periodic tasks, with a configurable delay.
    - Mechanisms for clean startup and shutdown, allowing the thread to be stopped quickly and safely.
    - Integration with a configuration system (GenIni) to enable or disable watchdog pings (only for testing).
    The conditional pinging feature is useful for testing the watchdog service without needing to modify the code. In normal operation, the pinging should be enabled
    and non-conditional.
    """
    SECTION: str = "dummy_thread"
    TASK_NAME: str = "DummyThreadLoop"
    LOOP_DELAY: int = 10  # seconds

    # runtime
    _background_loop_thread: Optional[threading.Thread]
    _trigger: threading.Event  # Event to trigger the background loop
    _stopped: bool
    _ini: "GenIni"

    # configuration
    _ping_enabled: bool = True

    def initialize(self,  ini: Optional["GenIni"] = None) -> None:
        self._trigger = threading.Event()
        self._ini = ini if ini is not None else GenIni.get_default_instance()
        self._auto_ping()

    def start(self) -> None:
        logging.info("starting")

        self._stopped = False
        self._background_loop_thread = threading.Thread(target=self._background_loop, name=f"{self.SECTION} background loop")
        self._background_loop_thread.start()

        logging.info("done")

    def stop(self) -> None:
        logging.info("stopping")

        self._stopped = True
        while self._background_loop_thread and self._background_loop_thread.is_alive():
            self._trigger.set()
            self._background_loop_thread.join(1)

        logging.info("done")

    def _background_loop(self) -> None:
        logging.debug("starting")

        try:
            while not self._stopped:

                self._auto_ping()

                # NOTE: this is the place where you would do your periodic tasks
                logging.info("doing nothing, except testing some unicode characters: šđčćžŠĐČĆŽ")

                # wait for the next iteration or for the trigger
                if self._trigger.wait(10):
                    self._trigger.clear()

        except:
            # this should never happen, but if it does, we need to know about it
            logging.critical("exception/bug in background loop, PLEASE CHECK AND FIX", exc_info=True)

        logging.debug("done")

    def _auto_ping(self) -> None:
        """auto ping the watchdog"""
        if self._ini.get_bool(self.SECTION, "ping_enabled", True):
            SvcWatchDogClient.ping(self.TASK_NAME, self.LOOP_DELAY * 2)
