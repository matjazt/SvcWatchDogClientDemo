﻿# -*-coding:utf-8
#!/usr/bin/python


import logging
import os

from tools.crypto_tools import CryptoTools
import tools.gen_tools as gen_tools
from dummy_thread import DummyThread
from tools.gen_ini import GenIni
from tools.log_email import LogEmailHandler
from tools.log_tools import LogTools
from tools.svc_watch_dog_client import SvcWatchDogClient


class Main:

    TASK_NAME: str = "mainLoop"

    def __init__(self):
        self._ini = GenIni()
        GenIni.set_default_instance(self._ini)
        self._dummy_thread: DummyThread | None = None

    def initialize(self):
        gen_tools.set_program_name("SvcWatchDogClientDemo")
        self._ini.open(f"etc/{gen_tools.get_program_name()}.ini")

        LogTools.initialize()
        CryptoTools.set_default_instance(CryptoTools("yLCJt6ZcPVvILzwgQRKh"))
        LogEmailHandler.configure_all_handlers()
        logging.info("running in base folder: " + os.getcwd())

        SvcWatchDogClient.initialize(self._ini)
        SvcWatchDogClient.ping(Main.TASK_NAME, 15)
        SvcWatchDogClient.start()

        self._dummy_thread = DummyThread()
        self._dummy_thread.initialize(self._ini)
        self._dummy_thread.start()

    def main_loop(self):
        """main loop, including periodic tasks which have to be done by various modules"""

        try:
            # the periodic tasks tipically don't need to be run in every iteration of the loop
            # but only every n-th iteration, so we use a counter
            r = 0

            while not SvcWatchDogClient.wait_for_shutdown_event(1) and not SvcWatchDogClient.is_timed_out():

                if r % 10 == 0:
                    SvcWatchDogClient.ping(Main.TASK_NAME, 30)

                if r % 3 == 0 and self._ini.auto_refresh():
                    logging.info(f"ini file {self._ini.get_file_name()} reloaded")

                # keep the counter in reasonable bounds
                r = (r + 1) % 99999999

        except KeyboardInterrupt:
            logging.info("interrupted by user")
        except:
            logging.error("exception:", exc_info=True)

        logging.info("exiting")

    def shutdown(self):
        """shut down everything"""
        if self._dummy_thread:
            self._dummy_thread.stop()
        SvcWatchDogClient.stop()
        logging.shutdown()


if __name__ == "__main__":
    gen_tools.cd_to_app_base_folder()

    main = Main()
    main.initialize()
    main.main_loop()
    main.shutdown()

# CryptoTools.self_test()
