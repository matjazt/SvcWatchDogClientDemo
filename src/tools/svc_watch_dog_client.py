# -*-coding:utf-8

import logging
import os
import socket
import threading
import time
import uuid
from typing import Optional

import win32api
import win32event

import tools.gen_tools as gen_tools
from tools.gen_ini import GenIni
from tools.log_tools import LogTools


class SvcWatchDogClient:
    SECTION: str = "SvcWatchDogClient"
    DISTANT_FUTURE: int = 0x7fffffff

    # runtime
    _lock = threading.RLock()
    _background_loop_thread: Optional[threading.Thread] = None
    _trigger = threading.Event()  # Event to trigger the background loop
    _next_check: int = DISTANT_FUTURE
    _stopped: bool = False
    _udp_ping_task_name: str = f"_udpPing.{uuid.uuid4()}"    # Unique name for the internal UDP ping task
    _tasks: dict[str, int] = {}
    _timed_out_tasks: set[str] = set()

    # configuration
    _enabled: bool = True
    _udp_ping_interval: int = 0  # in milliseconds
    _shutdown_event: str = ""
    _watchdog_secret: bytes = bytes()
    _udp_port: int = 0

    @classmethod
    def initialize(cls,  ini: Optional["GenIni"] = None) -> None:

        if ini is None:
            ini = GenIni.get_default_instance()

        cls._enabled = ini.get_bool(cls.SECTION, "Enabled", True)
        cls._udp_ping_interval = ini.get_int(cls.SECTION, "UdpPingInterval", 10) * 1000

        if cls._stopped:
            # clean up so we can start again later if needed (mostly for testing purposes)
            cls._stopped = False
            cls._next_check = cls.DISTANT_FUTURE
            cls._tasks = {}
            cls._timed_out_tasks = set()

    @classmethod
    def start(cls) -> None:

        if cls._stopped:
            raise RuntimeError("SvcWatchDogClient is already stopped, not allowed to start it again.")

        cls._shutdown_event = gen_tools.empty_if_none(os.getenv("SHUTDOWN_EVENT"))

        if not cls._enabled:
            logging.info("not enabled")
            return

        logging.info("starting")

        cls._watchdog_secret = gen_tools.empty_if_none(os.getenv("WATCHDOG_SECRET")).encode("utf-8")

        watchdog_port = os.getenv("WATCHDOG_PORT")
        if watchdog_port:
            try:
                cls._udp_port = int(watchdog_port)
                # Schedule the first immediate ping
                cls._tasks[cls._udp_ping_task_name] = 1
                logging.debug("UDP pinging configured")
            except ValueError:
                logging.error(f"Invalid WATCHDOG_PORT value: {watchdog_port}")
                cls._udp_port = 0

        cls._background_loop_thread = threading.Thread(target=cls.background_loop, name="SvcWatchDogClient background loop")
        cls._background_loop_thread.start()
        logging.info("done")

    @classmethod
    def stop(cls) -> None:
        logging.info("stopping")
        cls._stopped = True
        while cls._background_loop_thread and cls._background_loop_thread.is_alive():
            cls._trigger.set()
            cls._background_loop_thread.join(1)

        logging.info("done")

    @classmethod
    def wait_for_shutdown_event(cls, timeout: float) -> bool:
        """
        Wait for the shutdown event to be signaled.
        :param timeout: Timeout in seconds.
        :return: True if the shutdown event was signaled, False if timed out.
        """
        if not cls._shutdown_event:
            time.sleep(timeout)
            return False

        # open the global event
        try:
            event_handle = win32event.OpenEvent(win32event.EVENT_ALL_ACCESS, False, cls._shutdown_event)
            if event_handle:
                retval = win32event.WaitForSingleObject(event_handle, (int)(timeout * 1000))
                win32api.CloseHandle(event_handle)
                shutdown_requested = retval != win32event.WAIT_TIMEOUT
                if shutdown_requested:
                    logging.info("shutdown requested")
                return shutdown_requested
        except:
            logging.error(f"shutdown event {cls._shutdown_event} not available", exc_info=True)

        time.sleep(timeout)
        return False

    @classmethod
    def is_timed_out(cls) -> bool:
        """
        Check if the watchdog has timed out.
        """
        with cls._lock:
            return cls._enabled and cls._timed_out_tasks.__len__() > 0

    @classmethod
    def is_udp_pinging_active(cls) -> bool:
        """
        Check if UDP pinging is active.
        """
        with cls._lock:
            return cls._udp_ping_task_name in cls._tasks

    @classmethod
    def task_list(cls) -> list[str]:
        """
        Get a list of tasks that are being monitored.
        """
        with cls._lock:
            return list(cls._tasks.keys())

    @classmethod
    def ping(cls, task_name: str, timeout_seconds: int) -> None:

        logging.debug(f"task_name={task_name}, timeout_seconds={timeout_seconds}")

        if not cls._enabled:
            return

        task_check_time = gen_tools.steady_time() + (timeout_seconds * 1000)
        with cls._lock:
            cls._tasks[task_name] = task_check_time
            do_trigger = task_check_time < cls._next_check

        # If needed, trigger the background thread to recheck the tasks and recalculate the next check time
        if do_trigger:
            cls._trigger.set()

    @classmethod
    def close_timeout(cls, task_name: str) -> None:
        """
        Remove a task from monitoring, closing its timeout.
        """
        logging.debug(f"task_name={task_name}")
        with cls._lock:
            if task_name in cls._tasks:
                del cls._tasks[task_name]

    @classmethod
    def background_loop(cls):
        logging.debug("starting")
        try:

            while not cls._stopped:

                #  Check all tasks
                now = gen_tools.steady_time()
                timeout_detected = False
                udp_ping_needed = False

                with cls._lock:
                    cls._next_check = cls.DISTANT_FUTURE

                    # create a copy of the task names to allow modifying the collection while iterating
                    task_names = list(cls._tasks.keys())
                    for name in task_names:

                        if timeout_detected and name == cls._udp_ping_task_name:
                            LogTools.assert_log(cls._udp_ping_task_name not in cls._tasks)
                            # Skip the internal ping task if a timeout has already been detected
                            continue

                        timeout = cls._tasks[name]
                        if timeout <= now:
                            if name == cls._udp_ping_task_name:
                                # This is the internal ping task; we need to send a ping unless a timeout has been detected
                                if not timeout_detected:
                                    timeout = cls._tasks[cls._udp_ping_task_name] = now + cls._udp_ping_interval
                                    udp_ping_needed = True
                            elif name not in cls._timed_out_tasks:
                                # A new timed-out task has been detected
                                cls._timed_out_tasks.add(name)
                                timeout_detected = True
                                del cls._tasks[name]
                                # Prevent future UDP pings
                                if cls._udp_ping_task_name in cls._tasks:
                                    del cls._tasks[cls._udp_ping_task_name]

                        if timeout > now and timeout < cls._next_check:
                            # When the loop ends, _nextCheck contains the nearest future timeout. This way we can determine optimal wait time.
                            cls._next_check = timeout

                # Perform logging and UDP ping outside the critical section
                if timeout_detected:
                    logging.error("timed out tasks: " + ",".join(cls._timed_out_tasks))
                elif udp_ping_needed:
                    LogTools.assert_log(cls._udp_ping_task_name in cls._tasks)

                    logging.debug("sending UDP ping")
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                        sock.sendto(cls._watchdog_secret, ("127.0.0.1", cls._udp_port))

                # Wait for the next timeout or a trigger, with a 50 ms buffer to avoid premature detection attempts
                # 60 seconds maximum is just a safety measure, as well as 100 ms minimum.
                waitTime = min(max(cls._next_check - now + 50, 100) / 1000.0, 60.0)

                if cls._trigger.wait(waitTime):
                    cls._trigger.clear()

        except:
            # this should never happen, but if it does, we need to know about it
            logging.critical("exception/bug in background loop, PLEASE CHECK AND FIX", exc_info=True)

        logging.debug("done")


class TimeoutDetector:

    _name: str
    _closed: bool

    def __init__(self, name: str, timeout_seconds: int, name_postfix: bool = True):
        self._closed = False
        if name_postfix:
            self._name = f"{name}.{uuid.uuid4()}"
        else:
            self._name = name
        SvcWatchDogClient.ping(self._name, timeout_seconds)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if not self._closed:
            SvcWatchDogClient.close_timeout(self._name)
            self._closed = True
