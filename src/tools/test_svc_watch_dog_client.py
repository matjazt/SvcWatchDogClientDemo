# -*-coding:utf-8

import os
import tempfile
import time

import pytest
import win32event

import tools.gen_tools as gen_tools
from tools.gen_ini import GenIni
from tools.svc_watch_dog_client import SvcWatchDogClient, TimeoutDetector


@pytest.fixture
def fixture():
    fd, temp_file = tempfile.mkstemp()
    os.close(fd)  # Close the file descriptor
    print(f"temporary file name: {temp_file}")  # Outputs a unique file path
    yield temp_file  # Test runs after this
    print(f"\nshutting down SvcWatchDogClient and deleting {temp_file}")  # Cleanup happens after test execution
    SvcWatchDogClient.stop()
    os.unlink(temp_file)


def simulate_external_wd() -> int:
    """
    Simulate the external watchdog by creating a named event and setting it in the environment variable,
    as well as setting both UDP ping related environment variables.
    This is used to test the SvcWatchDogClient without needing an actual external watchdog.
    Returns:
        event_handle: The event handle for the shutdown event.
    """

    shutdown_event_name = "shutDownEvent"
    os.environ["SHUTDOWN_EVENT"] = shutdown_event_name
    os.environ["WATCHDOG_SECRET"] = "rubbish"
    os.environ["WATCHDOG_PORT"] = "12345"

    # Create a named event
    # This is a manual reset event, which means it will remain signaled until reset

    event_handle = win32event.CreateEvent(None, True, False, shutdown_event_name)
    return event_handle


def test_watchdog1(fixture):

    assert fixture is not None

    shutdown_event = simulate_external_wd()

    SvcWatchDogClient.initialize(GenIni())

    # Act & assert
    task1 = "task1"
    task2 = "task2"
    task3 = "task3"

    assert not SvcWatchDogClient.is_udp_pinging_active()
    assert not SvcWatchDogClient.is_timed_out()
    assert len(SvcWatchDogClient.task_list()) == 0
    SvcWatchDogClient.start()
    assert len(SvcWatchDogClient.task_list()) == 1
    assert SvcWatchDogClient.is_udp_pinging_active()
    assert not SvcWatchDogClient.is_timed_out()
    assert not SvcWatchDogClient.wait_for_shutdown_event(0.01)
    SvcWatchDogClient.ping(task1, 5)
    time.sleep(1)
    assert len(SvcWatchDogClient.task_list()) == 2
    assert not SvcWatchDogClient.is_timed_out()
    assert SvcWatchDogClient.is_udp_pinging_active()

    with TimeoutDetector(task2, 2):
        assert len(SvcWatchDogClient.task_list()) == 3
        time.sleep(1)

    assert len(SvcWatchDogClient.task_list()) == 2
    assert not SvcWatchDogClient.is_timed_out()
    assert SvcWatchDogClient.is_udp_pinging_active()

    SvcWatchDogClient.close_timeout(task1)
    assert len(SvcWatchDogClient.task_list()) == 1
    assert not SvcWatchDogClient.is_timed_out()
    assert SvcWatchDogClient.is_udp_pinging_active()

    with TimeoutDetector(task3, 1):
        assert len(SvcWatchDogClient.task_list()) == 2
        time.sleep(1.1)

        assert len(SvcWatchDogClient.task_list()) == 0
        assert SvcWatchDogClient.is_timed_out()
        assert not SvcWatchDogClient.is_udp_pinging_active()

        assert not SvcWatchDogClient.wait_for_shutdown_event(0.01)

        win32event.SetEvent(shutdown_event)

        assert SvcWatchDogClient.wait_for_shutdown_event(0.01)


def test_watchdog2(fixture):

    assert fixture is not None

    simulate_external_wd()

    gen_tools.store_text_file(fixture, "[SvcWatchDogClient]\nEnabled=false\n")

    SvcWatchDogClient.initialize(GenIni(fixture))

    # Act & assert
    task1 = "task1"
    task2 = "task2"

    assert not SvcWatchDogClient.is_udp_pinging_active()
    assert not SvcWatchDogClient.is_timed_out()
    assert len(SvcWatchDogClient.task_list()) == 0
    SvcWatchDogClient.start()
    assert len(SvcWatchDogClient.task_list()) == 0
    assert not SvcWatchDogClient.is_udp_pinging_active()
    assert not SvcWatchDogClient.is_timed_out()
    SvcWatchDogClient.ping(task1, 1)
    assert len(SvcWatchDogClient.task_list()) == 0
    time.sleep(1.2)
    assert len(SvcWatchDogClient.task_list()) == 0
    assert not SvcWatchDogClient.is_timed_out()
    assert not SvcWatchDogClient.is_udp_pinging_active()

    with TimeoutDetector(task2, 3):
        assert len(SvcWatchDogClient.task_list()) == 0
        time.sleep(1)

    assert len(SvcWatchDogClient.task_list()) == 0
    assert not SvcWatchDogClient.is_timed_out()
    assert not SvcWatchDogClient.is_udp_pinging_active()


def test_watchdog3(fixture):

    assert fixture is not None

    simulate_external_wd()

    del os.environ["SHUTDOWN_EVENT"]
    del os.environ["WATCHDOG_SECRET"]
    del os.environ["WATCHDOG_PORT"]

    SvcWatchDogClient.initialize(GenIni())

    # Act & assert
    task1 = "task1"
    task2 = "task2"

    assert not SvcWatchDogClient.is_udp_pinging_active()
    assert not SvcWatchDogClient.is_timed_out()
    assert len(SvcWatchDogClient.task_list()) == 0
    SvcWatchDogClient.start()
    assert len(SvcWatchDogClient.task_list()) == 0
    assert not SvcWatchDogClient.is_udp_pinging_active()
    assert not SvcWatchDogClient.is_timed_out()
    SvcWatchDogClient.ping(task1, 1)
    assert len(SvcWatchDogClient.task_list()) == 1
    time.sleep(1.2)
    assert len(SvcWatchDogClient.task_list()) == 0
    assert SvcWatchDogClient.is_timed_out()
    assert not SvcWatchDogClient.is_udp_pinging_active()

    with TimeoutDetector(task2, 1):
        assert len(SvcWatchDogClient.task_list()) == 1
        time.sleep(1.2)

    assert len(SvcWatchDogClient.task_list()) == 0
    assert SvcWatchDogClient.is_timed_out()
    assert not SvcWatchDogClient.is_udp_pinging_active()
