# -*-coding:utf-8


from datetime import datetime
import logging

from tools import gen_tools
from tools.email_sender import EmailSender
from tools.gen_ini import GenIni
import threading


class LogEmailHandler(logging.Handler):

    _lock = threading.RLock()
    _timer: threading.Timer | None = None
    _first_log_time: datetime | None = None
    _max_logs: int = 0
    _max_delay: int = 0
    _buffer: list[str] = []
    _closing: bool = False

    def __init__(self, section: str, ini: GenIni | None = None):
        super().__init__()

        self._section = section

        self._ini = ini if ini else GenIni.get_default_instance()

        self._max_logs = self._ini.get_int(self._section, "max_logs", 1000)
        self._max_delay = self._ini.get_int(self._section, "max_delay", 300)

        minimum_log_level = self._ini.get_int(self._section, "minimum_log_level", 0)  # Default to everything
        self.setLevel(minimum_log_level)

    def emit(self, record: logging.LogRecord):
        if self._closing or record.module == "email_sender":
            return  # skip messages from the email sender itself

        with self._lock:
            self._buffer.append(self.format(record))
            if not self._first_log_time:
                self._first_log_time = datetime.now()
                self._start_timer()

            if len(self._buffer) >= self._max_logs:
                self._flush()

    def _start_timer(self):
        if not self._closing:
            self._timer = threading.Timer(self._max_delay, self._flush)
            self._timer.start()

    def _flush(self):

        with self._lock:
            # compose email body, then reset the buffer
            if not self._buffer:
                return

            message = "\n".join(self._buffer)

            self._buffer.clear()
            self._first_log_time = None
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

        # figure out the email parameters, then send the email asynchronously (fire-and-forget)

        subject = self._ini.get_string(self._section, "Subject", gen_tools.get_program_name() +
                                       " @ " + gen_tools.get_computer_name())
        recipients = [addr.strip() for addr in self._ini.get_string(self._section, "recipients", "").split(",")]

        email_sender = EmailSender(self._section, self._ini)

        if not recipients or not email_sender.is_configured():
            logging.warning(f"not all email parameters are set in section {self._section}, email will not be sent")
            return

        email_sender.send_email(subject, message, recipients)

    def close(self):
        # note: this method is called when the handler is removed from the logger. It can be called multiple times.
        self._closing = True
        self._flush()
        super().close()

    @staticmethod
    def configure_all_handlers(ini: GenIni | None = None):

        root_logger = logging.getLogger()
        if not root_logger or not root_logger.handlers:
            raise RuntimeError("No root logger or no handlers configured")

        if ini is None:
            # if no ini is provided, use the default instance
            ini = GenIni.get_default_instance()

        sections = ini.get_sections()
        for section in sections:
            if section.startswith("log_email") and \
                    ini.get_optional_string(section, "recipients") and \
                    ini.get_optional_string(section, "Host") and \
                    ini.get_optional_string(section, "default_source_address"):

                logging.debug(f"configuring email handler for section {section}")
                email_handler = LogEmailHandler(section, ini)
                email_handler.setFormatter(root_logger.handlers[0].formatter)
                root_logger.addHandler(email_handler)
